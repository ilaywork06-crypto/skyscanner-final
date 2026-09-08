"""
The generic document store access every repository of the register builds upon.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from typing import Any, Generic, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel
from pymongo import IndexModel
from pymongo.errors import OperationFailure

from skyscanner_common.logging_utils import get_logger
from skyscanner_common.mongo import MongoProvider

from truth_service.constants import IDENTIFIER_FIELD

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)

# The document store answers a repeated index declaration with one of these rather than creating it twice.
INDEX_CONFLICT_CODES: frozenset[int] = frozenset({85, 86})

DELETED_FIELD: str = "deleted"

# A removal writes a flag rather than erasing the document, so every read says that it wants the ones that
# are still there.
#
# The test is an equality rather than a "not true", and that is load bearing rather than a matter of taste.
# A negation is two ranges either side of the excluded value, and an index whose leading field is scanned as
# two ranges cannot hand back the fields after it in order - so the ordering the table asked for has to be
# redone in memory over the whole match, which is a sort of the entire register to draw twenty five rows.
# Equality binds the field to a point, the rest of the index stays in order, and the same read touches only
# the rows it returns. Every document this service writes carries the flag, so there is nothing to tolerate.
NOT_DELETED: dict[str, Any] = {DELETED_FIELD: False}

# ----- CLASSES ----- #

DocumentT = TypeVar("DocumentT", bound=BaseModel)


class BaseRepository(Generic[DocumentT]):
    """
    A typed wrapper around one collection, translating between stored documents and their pydantic shape.
    """

    def __init__(self, provider: MongoProvider, collection_name: str, document_type: type[DocumentT]) -> None:
        """
        Bind the repository to one collection of the document store.

        :param provider: Owner of the shared motor client.
        :param collection_name: Name of the collection the repository works against.
        :param document_type: Pydantic model the stored documents are parsed into.
        """
        self._provider = provider
        self._collection_name = collection_name
        self._document_type = document_type

    @property
    def collection(self) -> AsyncIOMotorCollection[dict[str, Any]]:
        """
        Fetch the handle of the bound collection.

        :return: The collection handle.
        """
        return self._provider.collection(self._collection_name)

    def indexes(self) -> list[IndexModel]:
        """
        Declare the indexes this collection is read through, which the repositories override.

        :return: The index definitions the repository relies on.
        """
        return []

    async def ensure_indexes(self) -> None:
        """
        Bring the indexes of the collection to what the repository currently declares.

        An index whose name is held but whose keys have since changed is taken down before the new one is
        put up. Creating it under the same name would otherwise be refused and the refusal is easy to
        swallow - which leaves a database quietly running the indexes of an older release while every plan
        that was rewritten for the new ones goes back to reading the whole collection.

        :raises OperationFailure: When the document store refused the change for any other reason.
        """
        declared = self.indexes()
        if not declared:
            return

        held = await self.collection.index_information()
        for model in declared:
            name = str(model.document["name"])
            if name in held and not _is_text(model) and _keys_of(model) != _held_keys(held[name]):
                LOGGER.info("The index %s of %s is redeclared, taking the old one down", name, self._collection_name)
                await self.collection.drop_index(name)

        try:
            await self.collection.create_indexes(declared)
        except OperationFailure as error:
            if error.code not in INDEX_CONFLICT_CODES:
                raise
            LOGGER.warning("The collection %s already carries an equivalent index", self._collection_name)

    async def find_one(self, query: dict[str, Any]) -> DocumentT | None:
        """
        Read the first document matching a restriction.

        :param query: Restriction the document has to satisfy.
        :return: The parsed document, or nothing when the restriction matched none.
        """
        raw = await self.collection.find_one(alive(query))
        if raw is None:
            return None

        return self._document_type.model_validate(raw)

    async def find_by_id(self, identifier: str) -> DocumentT | None:
        """
        Read a single document by its identifier.

        :param identifier: Identifier of the document.
        :return: The parsed document, or nothing when the identifier is unknown.
        """
        return await self.find_one(query={IDENTIFIER_FIELD: identifier})

    async def find_many(
        self,
        query: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int = 0,
        projection: dict[str, Any] | None = None,
    ) -> list[DocumentT]:
        """
        Read every document matching a restriction, applying an ordering and a window.

        :param query: Restriction the documents have to satisfy.
        :param sort: Ordering applied before the window is taken.
        :param skip: Amount of documents skipped before collecting.
        :param limit: Largest amount of documents that is returned, zero for all of them.
        :param projection: Attributes that are read, all of them when omitted.
        :return: The parsed documents of the window.
        """
        cursor = self.collection.find(alive(query), projection)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        return [self._document_type.model_validate(raw) async for raw in cursor]

    async def count(self, query: dict[str, Any] | None = None) -> int:
        """
        Count the documents matching a restriction.

        :param query: Restriction the documents have to satisfy.
        :return: The amount of matching documents.
        """
        return int(await self.collection.count_documents(alive(query)))

    async def distinct(self, field: str, query: dict[str, Any] | None = None) -> list[Any]:
        """
        Read every value one attribute is known to hold among the matching documents.

        :param field: Path of the attribute.
        :param query: Restriction the documents have to satisfy.
        :return: The values that attribute holds, in no particular order.
        """
        return list(await self.collection.distinct(field, alive(query)))

    async def insert(self, document: DocumentT) -> DocumentT:
        """
        Write a new document into the collection.

        :param document: Document that is written.
        :return: The very same document, so that a caller can chain on the write.
        """
        await self.collection.insert_one(document.model_dump(by_alias=True))

        return document

    async def insert_many(self, documents: list[DocumentT]) -> int:
        """
        Write a batch of documents in one round trip.

        :param documents: Documents that are written.
        :return: How many documents were written.
        """
        if not documents:
            return 0

        result = await self.collection.insert_many([document.model_dump(by_alias=True) for document in documents])

        return len(result.inserted_ids)

    async def update_fields(self, identifier: str, updates: dict[str, Any]) -> bool:
        """
        Change a subset of the attributes of a stored document.

        :param identifier: Identifier of the document that is changed.
        :param updates: Attributes and their new values.
        :return: Whether a stored document was changed.
        """
        if not updates:
            return False

        result = await self.collection.update_one({IDENTIFIER_FIELD: identifier}, {"$set": updates})

        return bool(result.matched_count)

    async def update_many_fields(self, query: dict[str, Any], updates: dict[str, Any]) -> int:
        """
        Change a subset of the attributes of every document matching a restriction.

        :param query: Restriction the documents have to satisfy.
        :param updates: Attributes and their new values.
        :return: How many documents were changed.
        """
        if not updates:
            return 0

        result = await self.collection.update_many(query, {"$set": updates})

        return int(result.modified_count)


# ----- FUNCTIONS ----- #


def _keys_of(model: IndexModel) -> list[tuple[str, Any]]:
    """
    Read the keys one declared index is built over.

    :param model: Index as the repository declares it.
    :return: The fields of the index and the direction each is held in.
    """
    return [(str(field), direction) for field, direction in model.document["key"].items()]


def _is_text(model: IndexModel) -> bool:
    """
    Decide whether a declared index is a text index.

    A text index is never compared against what the store holds: the store rewrites its keys into internal
    ones, so what it hands back never matches what was declared, and comparing the two would take the index
    down and build it again on every single start.

    :param model: Index as the repository declares it.
    :return: Whether the index is a text index.
    """
    return any(direction == "text" for _, direction in _keys_of(model))


def _held_keys(information: dict[str, Any]) -> list[tuple[str, Any]]:
    """
    Read the keys one index the collection already holds is built over.

    :param information: One entry of what the collection says about its indexes.
    :return: The fields of the index and the direction each is held in.
    """
    return [(str(field), direction) for field, direction in information.get("key", [])]


def alive(query: dict[str, Any] | None) -> dict[str, Any]:
    """
    Narrow a restriction to the documents that were not removed.

    :param query: Restriction the caller asked for.
    :return: The same restriction, extended so that removed documents never answer it.
    """
    if not query:
        return dict(NOT_DELETED)

    if DELETED_FIELD in query:
        return dict(query)

    return {"$and": [query, dict(NOT_DELETED)]}
