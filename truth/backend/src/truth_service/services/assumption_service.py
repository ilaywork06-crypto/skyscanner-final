"""
The assumptions themselves, which are what the register is for and the one collection expected to grow.

Every read here is written for a register far larger than anything can be read through. A listing answers out
of the assumptions alone - it joins nothing, because a listing that joined would be one round trip per row,
which is exactly what made the client read every assumption on its own before this service existed. The
declarations are read whole only when a single assumption is, which is one row at a time.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from skyscanner_common.errors import NotFoundError
from skyscanner_common.ids import new_id

from truth_service.constants import FIRST_REVISION
from truth_service.documents import AssumptionDocument, SchemaDocument, build_search_text
from truth_service.models.assumption import (
    AssumptionCreateRequest,
    AssumptionDetailResponse,
    AssumptionRowResponse,
)
from truth_service.models.common import IndustryReference, SchemaReference
from truth_service.models.query import AssumptionPage, AssumptionQuery, FacetResponse
from truth_service.models.schema import SchemaSummaryResponse
from truth_service.query.filters import build_query, build_sort, resolve_field
from truth_service.repositories.assumption_repository import AssumptionRepository
from truth_service.repositories.industry_repository import IndustryRepository
from truth_service.repositories.schema_repository import SchemaRepository
from truth_service.services.schema_service import to_detail as schema_to_detail
from truth_service.services.scheme_reader import check_values, merge_fields, read_scheme

# ----- CONSTS ----- #

# How many values a filter is offered before the answer says the register holds more than it showed.
DEFAULT_FACET_LIMIT: int = 500

# ----- CLASSES ----- #


class AssumptionService:
    """
    Everything the register does with its assumptions.
    """

    def __init__(
        self,
        assumptions: AssumptionRepository,
        schemas: SchemaRepository,
        industries: IndustryRepository,
    ) -> None:
        """
        Bind the service to the assumptions and to the two collections they name.

        :param assumptions: Reads and writes of the assumptions.
        :param schemas: Reads of the declarations, for resolving the ones an assumption names.
        :param industries: Reads of the industries, for resolving the ones an assumption belongs to.
        """
        self._assumptions = assumptions
        self._schemas = schemas
        self._industries = industries

    async def query(self, request: AssumptionQuery) -> AssumptionPage:
        """
        Answer the whole question a table is asking - narrowed, ordered and cut to one window.

        The count is asked for separately from the window, and only when the caller wants it. A table needs
        it to draw its pager; anything walking the answer in blocks already knows when it has reached the
        end, and counting again for every block would double the work for nothing.

        :param request: Everything the table is asking at once.
        :return: The window of the answer, and how many assumptions the whole of it holds.
        """
        query = build_query(
            search=request.search,
            industry=request.industry,
            schema_key=request.schema_key,
            filters=request.filters,
        )
        documents = await self._assumptions.query_page(
            query=query,
            sort=build_sort(request.sort),
            offset=request.offset,
            limit=request.limit,
        )
        total = await self._assumptions.count(query) if request.include_total else len(documents) + request.offset

        return AssumptionPage(
            rows=[to_row(document) for document in documents],
            total=total,
            offset=request.offset,
            limit=request.limit,
        )

    async def list_window(self, offset: int, limit: int) -> list[AssumptionRowResponse]:
        """
        Read one window of the register, newest first.

        :param offset: Amount of assumptions skipped before collecting.
        :param limit: Largest amount of assumptions that is returned.
        :return: The assumptions of the window.
        """
        documents = await self._assumptions.query_page(
            query=build_query(),
            sort=build_sort(None),
            offset=offset,
            limit=limit,
        )

        return [to_row(document) for document in documents]

    async def get_revision(self, identifier: str) -> AssumptionDetailResponse:
        """
        Read exactly the revision that was addressed, whether or not it is the current one.

        :param identifier: Identifier of the revision.
        :return: That revision, whole.
        :raises NotFoundError: When no assumption answers to that identifier.
        """
        document = await self._assumptions.find_by_id(identifier)
        if document is None:
            return await self.get_latest(identifier)

        return await self._to_detail(document)

    async def get_latest(self, key: str) -> AssumptionDetailResponse:
        """
        Read the current revision of the assumption addressed by either key it answers to.

        :param key: Identifier of a revision or identifier of the lineage.
        :return: The current revision, whole.
        :raises NotFoundError: When neither addresses an assumption.
        """
        document = await self._assumptions.find_latest_by_key(key)
        if document is None:
            raise NotFoundError(message="No assumption answers to that identifier", details={"key": key})

        return await self._to_detail(document)

    async def create(self, request: AssumptionCreateRequest) -> AssumptionDetailResponse:
        """
        Write a new assumption, checked against every declaration it names.

        :param request: Assumption as the caller described it.
        :return: The assumption as it was stored.
        :raises NotFoundError: When it names a declaration or an industry the register does not hold.
        """
        schemas = await self._resolve_schemas(request.schemas)
        industries = await self._resolve_industries(request.industries)

        merged = merge_fields([schema.scheme.fields for schema in schemas])
        check_values(fields=read_scheme(merged), values=request.values)

        lineage = new_id()
        document = AssumptionDocument(
            id=lineage,
            lineage=lineage,
            name=request.name.strip(),
            assumption_text=request.assumption_text,
            proposing_party=request.proposing_party,
            tags=request.tags,
            validation_responsible_parties=request.validation_responsible_parties,
            revision=FIRST_REVISION,
            latest_revision=True,
            creator=request.creator,
            schemas=[
                SchemaReference(id=schema.lineage, name=schema.name, revision=schema.revision)
                for schema in schemas
            ],
            industries=industries,
            values=request.values,
            special_fields=request.special_fields,
        )
        document.search_text = build_search_text(document)

        return await self._to_detail(await self._assumptions.insert(document))

    async def facet(self, key: str, industry: str | None, limit: int = DEFAULT_FACET_LIMIT) -> FacetResponse:
        """
        Read every value one attribute is known to hold, which is what a set filter offers to pick from.

        The vocabulary is read off the register rather than off the declarations, so a column offers what is
        actually there - including the values written before a schema was revised to name them.

        :param key: Attribute as the table addresses it.
        :param industry: Industry the vocabulary is gathered within, or nothing for the whole register.
        :param limit: Largest amount of values that is returned.
        :return: The values that attribute holds.
        """
        values, truncated = await self._assumptions.facet(
            field=resolve_field(key),
            query=build_query(industry=industry),
            limit=limit,
        )

        return FacetResponse(key=key, values=values, truncated=truncated)

    async def _resolve_schemas(self, named: list[str]) -> list[SchemaDocument]:
        """
        Work out which declarations an assumption names, by identifier or by name.

        :param named: Declarations as the caller named them.
        :return: The current revision of each of them, in the order they were named.
        :raises NotFoundError: When one of them names no declaration the register holds.
        """
        resolved: list[SchemaDocument] = []
        for key in named:
            if not key or not key.strip():
                continue
            document = await self._schemas.find_latest_by_key(key.strip())
            if document is None:
                raise NotFoundError(message="No schema answers to that name or identifier", details={"key": key})
            resolved.append(document)

        return resolved

    async def _resolve_industries(self, named: list[str]) -> list[IndustryReference]:
        """
        Work out which industries an assumption belongs to, by identifier or by name.

        :param named: Industries as the caller named them.
        :return: The industries, in the order they were named.
        :raises NotFoundError: When one of them names no industry the register holds.
        """
        resolved: list[IndustryReference] = []
        for key in named:
            if not key or not key.strip():
                continue
            document = await self._industries.find_by_key(key.strip())
            if document is None:
                raise NotFoundError(message="No industry answers to that name or identifier", details={"key": key})
            resolved.append(IndustryReference(id=document.id, name=document.name))

        return resolved

    async def _to_detail(self, document: AssumptionDocument) -> AssumptionDetailResponse:
        """
        Shape one stored assumption into the payload a reading of it answers with.

        This is the one read that resolves the declarations whole, because it is the one that happens a
        single row at a time. Every listing answers out of what the assumption itself carries.

        :param document: Assumption as it is stored.
        :return: The assumption as a reading hands it over.
        """
        declarations = [await self._schemas.find_latest_by_key(schema.id) for schema in document.schemas]
        present = [declaration for declaration in declarations if declaration is not None]
        row = to_row(document)

        return AssumptionDetailResponse(
            **row.model_dump(exclude={"schemas"}),
            schemas=[schema_to_detail(declaration) for declaration in present],
            aggregated_scheme=merge_fields([declaration.scheme.fields for declaration in present]),
            special_fields=document.special_fields,
        )


# ----- FUNCTIONS ----- #


def to_row(document: AssumptionDocument) -> AssumptionRowResponse:
    """
    Shape one stored assumption into the payload the register lists it as.

    :param document: Assumption as it is stored.
    :return: The assumption as a listing hands it over.
    """
    return AssumptionRowResponse(
        id=document.id,
        name=document.name,
        assumption_text=document.assumption_text,
        proposing_party=document.proposing_party,
        tags=list(document.tags),
        validation_responsible_parties=list(document.validation_responsible_parties),
        revision=document.revision,
        revision_reason=document.revision_reason,
        creator=document.creator,
        created_at=document.created_at,
        schemas=[
            SchemaSummaryResponse(id=schema.id, name=schema.name, revision=schema.revision)
            for schema in document.schemas
        ],
        industries=list(document.industries),
        values=dict(document.values),
        archived=document.archived,
        deleted=document.deleted,
    )
