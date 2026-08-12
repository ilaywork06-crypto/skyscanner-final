"""
The generic document store access every repository of the events service builds upon.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any, Generic, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel
from pymongo import IndexModel
from pymongo.errors import OperationFailure

from skyscanner_common.logging_utils import get_logger
from skyscanner_common.mongo import MongoProvider

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)
IDENTIFIER_FIELD: str = "_id"
INDEX_CONFLICT_CODES: frozenset[int] = frozenset({85, 86})
INDEX_MISSING_CODES: frozenset[int] = frozenset({26, 27})

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
        Create the indexes the repository relies on, overridden by the repositories that need them.
        """
        return None

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
        raw = await self.collection.find_one(query)
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
        cursor = self.collection.find(query or {}, projection)
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
        return int(await self.collection.count_documents(query or {}))

    async def estimated_count(self) -> int:
        """
        Read how many documents the collection holds without looking at a single one of them.

        The document store keeps the size of a collection in its own metadata, so answering this costs one
        metadata read instead of a scan. The number is exact for a collection that was shut down cleanly and
        may be off by the writes an unclean shutdown lost, which is why it only ever stands in for the total
        of an unrestricted query.

        :return: The amount of documents the collection holds.
        """
        return int(await self.collection.estimated_document_count())

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

    async def delete(self, identifier: str) -> bool:
        """
        Remove a stored document.

        :param identifier: Identifier of the document that is removed.
        :return: Whether a stored document was removed.
        """
        result = await self.collection.delete_one({IDENTIFIER_FIELD: identifier})
        self._on_write()

        return bool(result.deleted_count)
