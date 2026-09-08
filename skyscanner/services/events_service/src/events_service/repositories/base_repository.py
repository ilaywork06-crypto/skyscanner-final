"""
The generic document store access every repository of the events service builds upon.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any, Generic, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel
from pymongo.errors import OperationFailure

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.mongo import MongoProvider

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)
IDENTIFIER_FIELD: str = "_id"
INDEX_CONFLICT_CODES: frozenset[int] = frozenset({85, 86})
INDEX_MISSING_CODES: frozenset[int] = frozenset({26, 27})

DELETED_FIELD: str = "deleted"

# A removal writes a flag rather than erasing the document, so every read has to say that it wants the ones
# that are still there. The test is "not true" rather than "is false" so that documents written before the
# flag existed keep answering, without a migration having to touch every collection first.
NOT_DELETED: dict[str, Any] = {DELETED_FIELD: {"$ne": True}}

# ----- CLASSES ----- #

DocumentT = TypeVar("DocumentT", bound=BaseModel)


class BaseRepository(Generic[DocumentT]):
    """
    A typed wrapper around one collection, translating between stored documents and their pydantic representation.
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

    async def ensure_indexes(self) -> None:
        """
        Create the index every collection needs, extended by the repositories that carry their own.

        Every single read of every collection now narrows on the removal flag, so that one attribute is
        indexed everywhere rather than being left to a scan. The repositories that declare indexes of their
        own call up to this one first.
        """
        await self.create_indexes(
            [IndexModel([(DELETED_FIELD, ASCENDING)], name="deleted")],
        )

    async def create_indexes(self, indexes: list[IndexModel]) -> None:
        """
        Create a set of indexes, tolerating the ones an earlier deployment already created under another name.

        :param indexes: Index definitions the repository relies on.
        :raises OperationFailure: When the document store refused the creation for any other reason.
        """
        try:
            await self.collection.create_indexes(indexes)
        except OperationFailure as error:
            if error.code not in INDEX_CONFLICT_CODES:
                raise
            LOGGER.warning(
                "The collection %s already carries an equivalent index: %s",
                self._collection_name,
                error.details,
            )

    async def drop_index_if_present(self, name: str) -> None:
        """
        Remove one index by name, doing nothing when the collection never carried it.

        An index that encoded a rule the service has since changed keeps enforcing that rule on a database
        that was created before the change, so it has to be taken down rather than merely stopped being
        declared.

        :param name: Name of the index that is removed.
        :raises OperationFailure: When the document store refused the removal for any other reason.
        """
        try:
            await self.collection.drop_index(name)
        except OperationFailure as error:
            if error.code not in INDEX_MISSING_CODES:
                raise
            LOGGER.debug("The collection %s carries no index named %s", self._collection_name, name)

    async def find_one(self, query: dict[str, Any]) -> DocumentT | None:
        """
        Read the first document matching a restriction.

        :param query: Restriction the document has to satisfy.
        :return: The parsed document, or nothing when the restriction matched none.
        """
        raw = await self.collection.find_one(_alive(query))
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
        Read every document matching a restriction, applying an ordering and a paging window.

        :param query: Restriction the documents have to satisfy.
        :param sort: Ordering applied before the paging window is taken.
        :param skip: Amount of documents skipped before collecting.
        :param limit: Largest amount of documents that is returned, zero for all of them.
        :param projection: Attributes that are read, all of them when omitted.
        :return: The parsed documents of the window.
        """
        cursor = self.collection.find(_alive(query), projection)
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
        return int(await self.collection.count_documents(_alive(query)))

    def _on_write(self) -> None:
        """
        React to a write against the collection, overridden by the repositories that keep derived state.
        """
        return None

    async def insert(self, document: DocumentT) -> DocumentT:
        """
        Write a new document into the collection.

        :param document: Document that is written.
        :return: The very same document, so that callers can chain on the write.
        """
        await self.collection.insert_one(document.model_dump(by_alias=True))
        self._on_write()

        return document

    async def replace(self, identifier: str, document: DocumentT) -> bool:
        """
        Overwrite a stored document as a whole.

        :param identifier: Identifier of the document that is overwritten.
        :param document: New content of the document.
        :return: Whether a stored document was overwritten.
        """
        result = await self.collection.replace_one(
            {IDENTIFIER_FIELD: identifier},
            document.model_dump(by_alias=True),
        )
        self._on_write()

        return bool(result.matched_count)

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
        self._on_write()

        return bool(result.matched_count)

    async def delete(self, identifier: str, user: str | None = None) -> bool:
        """
        Remove a stored document, which marks it as removed rather than erasing it.

        Nothing is taken out of the document store. The document keeps its identifier, its history and the
        files it points at, and every read of the collection leaves it behind from this moment on. A removal
        that has to be undone is therefore a matter of clearing one flag.

        :param identifier: Identifier of the document that is removed.
        :param user: Identity the removal is attributed to.
        :return: Whether a stored document was removed.
        """
        result = await self.collection.update_one(
            {IDENTIFIER_FIELD: identifier, **NOT_DELETED},
            {"$set": {DELETED_FIELD: True, "deleted_at": utc_now(), "deleted_by": user}},
        )
        self._on_write()

        return bool(result.matched_count)


# ----- FUNCTIONS ----- #


def _alive(query: dict[str, Any] | None) -> dict[str, Any]:
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
