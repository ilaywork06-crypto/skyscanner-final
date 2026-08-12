"""
Persistence of the declared event types and entity types offered by the create wizard and the event page.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from pymongo import ASCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider

from events_service.constants import ENTITY_TYPE_KIND, EVENT_TYPE_KIND, TYPES_COLLECTION
from events_service.documents import TypeDocument
from events_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class TypeRepository(BaseRepository[TypeDocument]):
    """
    The single door to the type declarations, keeping the event types and the entity types in one collection.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the types collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=TYPES_COLLECTION, document_type=TypeDocument)

    async def ensure_indexes(self) -> None:
        """
        Create the index that keeps a type key unique inside its kind.
        """
        await self.create_indexes(
            [IndexModel([("kind", ASCENDING), ("key", ASCENDING)], unique=True, name="type_key_unique")],
        )

    async def list_event_types(self, industry: str | None = None, offset: int = 0, limit: int = 0) -> list[TypeDocument]:
        """
        Read the event types that an industry may choose from, shared ones included.

        :param industry: Industry whose own types are added to the shared ones.
        :param offset: Amount of types skipped before collecting.
        :param limit: Largest amount of types that is returned, zero for all of them.
        :return: The matching event types ordered by their relative position.
        """
        return await self._list_kind(kind=EVENT_TYPE_KIND, industry=industry, offset=offset, limit=limit)

    async def list_entity_types(self, industry: str | None = None, offset: int = 0, limit: int = 0) -> list[TypeDocument]:
        """
        Read the entity types that an industry may choose from, shared ones included.

        :param industry: Industry whose own types are added to the shared ones.
        :param offset: Amount of types skipped before collecting.
        :param limit: Largest amount of types that is returned, zero for all of them.
        :return: The matching entity types ordered by their relative position.
        """
        return await self._list_kind(kind=ENTITY_TYPE_KIND, industry=industry, offset=offset, limit=limit)

    async def find_by_key(self, kind: str, key: str) -> TypeDocument | None:
        """
        Read a single type declaration addressed by its kind and its key.

        :param kind: Whether an event type or an entity type is looked up.
        :param key: Machine key of the type.
        :return: The type declaration, or nothing when the key is unknown.
        """
        return await self.find_one(query={"kind": kind, "key": key})

    async def _list_kind(self, kind: str, industry: str | None, offset: int = 0, limit: int = 0) -> list[TypeDocument]:
        """
        Read the declarations of one kind, adding the types of an industry to the shared ones.

        :param kind: Whether event types or entity types are read.
        :param industry: Industry whose own types are added to the shared ones.
        :param offset: Amount of types skipped before collecting.
        :param limit: Largest amount of types that is returned, zero for all of them.
        :return: The matching type declarations ordered by their relative position.
        """
        query: dict[str, Any] = {"kind": kind}
        if industry:
            query["$or"] = [{"industry": None}, {"industry": industry}]

        return await self.find_many(
            query=query,
            sort=[("order", ASCENDING), ("name", ASCENDING)],
            skip=offset,
            limit=limit,
        )
