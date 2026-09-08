"""
The schemas, which are the declarations deciding what attributes an assumption may carry.

A declaration is never edited. It is revised: a new document is written, it becomes the current revision of
its lineage, and every revision before it stays exactly as it was. That is what lets an assumption written
last year still be read against the declaration it was actually written under.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from pydantic import JsonValue

from skyscanner_common.errors import ConflictError, NotFoundError
from skyscanner_common.ids import new_id

from truth_service.constants import FIRST_REVISION
from truth_service.documents import SchemaDocument, StoredScheme
from truth_service.models.common import IndustryReference
from truth_service.models.schema import (
    SchemaCreateRequest,
    SchemaDetailResponse,
    SchemaRevisionRequest,
    SchemaSummaryResponse,
)
from truth_service.repositories.industry_repository import IndustryRepository
from truth_service.repositories.schema_repository import SchemaRepository

# ----- CLASSES ----- #


class SchemaService:
    """
    Everything the register does with its declarations.
    """

    def __init__(self, schemas: SchemaRepository, industries: IndustryRepository) -> None:
        """
        Bind the service to the declarations and to the vocabulary they are filed under.

        :param schemas: Reads and writes of the declarations.
        :param industries: Reads of the industries, for resolving the ones a declaration names.
        """
        self._schemas = schemas
        self._industries = industries

    async def list_schemas(self, offset: int, limit: int) -> list[SchemaSummaryResponse]:
        """
        Read one window of the declarations, each at the revision it currently stands at.

        :param offset: Amount of declarations skipped before collecting.
        :param limit: Largest amount of declarations that is returned, zero for all of them.
        :return: The declarations of the window.
        """
        documents = await self._schemas.list_latest(offset=offset, limit=limit)

        return [to_summary(document) for document in documents]

    async def get_revision(self, identifier: str) -> SchemaDetailResponse:
        """
        Read exactly the revision that was addressed, whether or not it is the current one.

        :param identifier: Identifier of the revision.
        :return: That revision, whole.
        :raises NotFoundError: When no revision answers to that identifier.
        """
        document = await self._schemas.find_by_id(identifier)
        if document is None:
            return await self.get_latest(identifier)

        return to_detail(document)

    async def get_latest(self, key: str) -> SchemaDetailResponse:
        """
        Read the current revision of the declaration addressed by any of the three keys it answers to.

        :param key: Identifier of a revision, identifier of the lineage, or name of the declaration.
        :return: The current revision, whole.
        :raises NotFoundError: When none of the three addresses a declaration.
        """
        document = await self._schemas.find_latest_by_key(key)
        if document is None:
            raise NotFoundError(message="No schema answers to that name or identifier", details={"key": key})

        return to_detail(document)

    async def get_by_name(self, name: str) -> SchemaDetailResponse:
        """
        Read the current revision of the declaration answering to one name.

        :param name: Name of the declaration.
        :return: The current revision, whole.
        :raises NotFoundError: When no declaration answers to that name.
        """
        document = await self._schemas.find_latest_by_name(name)
        if document is None:
            raise NotFoundError(message="No schema answers to that name", details={"name": name})

        return to_detail(document)

    async def create_schema(self, request: SchemaCreateRequest) -> SchemaDetailResponse:
        """
        Declare a new schema, which is the first revision of a new lineage.

        :param request: Declaration as the caller described it.
        :return: The declaration as it was stored.
        :raises ConflictError: When a declaration of that name already exists.
        """
        name = request.name.strip()
        if await self._schemas.find_latest_by_name(name) is not None:
            raise ConflictError(message="A schema of that name is already declared", details={"name": name})

        industries = await self._resolve_industries(request.industries)
        lineage = new_id()
        document = SchemaDocument(
            id=lineage,
            lineage=lineage,
            name=name,
            description=request.description,
            type=request.type,
            revision=FIRST_REVISION,
            latest_revision=True,
            scheme=StoredScheme(fields=request.scheme.fields, constraints=request.scheme.rules()),
            creator=request.creator,
            industries=industries,
        )

        return to_detail(await self._schemas.insert(document))

    async def revise_schema(self, key: str, request: SchemaRevisionRequest) -> SchemaDetailResponse:
        """
        Write a new revision of a declaration, which is the only way one is ever changed.

        The revision that was current stops being so before the new one is written, so that a reader arriving
        between the two writes finds one current revision or the other rather than both.

        :param key: Identifier of a revision, identifier of the lineage, or name of the declaration.
        :param request: The declaration as it now stands, and why it was changed.
        :return: The revision that was written.
        :raises NotFoundError: When nothing addresses a declaration to revise.
        """
        current = await self._schemas.find_latest_by_key(key)
        if current is None:
            raise NotFoundError(message="No schema answers to that name or identifier", details={"key": key})

        await self._schemas.unmark_latest(current.lineage)
        document = SchemaDocument(
            lineage=current.lineage,
            name=current.name,
            description=current.description,
            type=current.type,
            revision=current.revision + 1,
            revision_reason=request.revision_reason,
            latest_revision=True,
            scheme=StoredScheme(fields=request.scheme.fields, constraints=request.scheme.rules()),
            creator=request.creator or current.creator,
            industries=list(current.industries),
        )

        return to_detail(await self._schemas.insert(document))

    async def _resolve_industries(self, named: list[JsonValue]) -> list[IndustryReference]:
        """
        Work out which industries a declaration names, whichever way the caller named them.

        The original service took these as numbers it never handed out, so a number names nothing this
        register holds and is left out. What remains is an identifier or a name, and both are looked up.

        :param named: Industries as the caller named them.
        :return: The industries that could be resolved, in the order they were named.
        """
        resolved: list[IndustryReference] = []
        for entry in named:
            if not isinstance(entry, str) or not entry.strip():
                continue
            document = await self._industries.find_by_key(entry.strip())
            if document is not None:
                resolved.append(IndustryReference(id=document.id, name=document.name))

        return resolved


# ----- FUNCTIONS ----- #


def to_summary(document: SchemaDocument) -> SchemaSummaryResponse:
    """
    Shape one stored revision into the payload the listing answers with.

    :param document: Revision as it is stored.
    :return: The revision as the listing hands it over.
    """
    return SchemaSummaryResponse(
        id=document.id,
        name=document.name,
        revision=document.revision,
        creator=document.creator,
        created_at=document.created_at,
    )


def to_detail(document: SchemaDocument) -> SchemaDetailResponse:
    """
    Shape one stored revision into the payload a reading of it answers with.

    :param document: Revision as it is stored.
    :return: The revision as a reading hands it over.
    """
    return SchemaDetailResponse(
        id=document.id,
        name=document.name,
        revision=document.revision,
        creator=document.creator,
        created_at=document.created_at,
        description=document.description,
        revision_reason=document.revision_reason,
        latest_revision=document.latest_revision,
        scheme={"fields": document.scheme.fields, "constraints": document.scheme.constraints},
        archived=document.archived,
        deleted=document.deleted,
        industries=list(document.industries),
    )
