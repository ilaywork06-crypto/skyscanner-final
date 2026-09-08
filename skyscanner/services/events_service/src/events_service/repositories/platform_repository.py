"""
Persistence of the declared platforms an event may name, which are their own collection rather than a kind of type.

:date: 2026-09-08
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from pymongo import ASCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider

from events_service.constants import PLATFORMS_COLLECTION
from events_service.documents import PlatformDocument
from events_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class PlatformRepository(BaseRepository[PlatformDocument]):
    """
    The single door to the platforms collection.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the platforms collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=PLATFORMS_COLLECTION, document_type=PlatformDocument)

    async def ensure_indexes(self) -> None:
        """
        Create the index that keeps a platform key unique.
        """
        await super().ensure_indexes()
        await self.create_indexes(
            [IndexModel([("key", ASCENDING)], unique=True, name="platform_key_unique")],
        )

    async def list_all(self, industry: str | None = None, offset: int = 0, limit: int = 0) -> list[PlatformDocument]:
        """
        Read the platforms an industry may name, shared ones included.

        A platform belongs to as many industries as it names, and one that names none is offered to every
        industry, so an industry is offered the platforms that list it plus the ones that list nobody.

        :param industry: Industry whose own platforms are added to the shared ones.
        :param offset: Amount of platforms skipped before collecting.
        :param limit: Largest amount of platforms that is returned, zero for all of them.
        :return: The matching platforms ordered by their relative position.
        """
        query: dict[str, Any] = {}
        if industry:
            query["$or"] = [{"industries": []}, {"industries": industry}]

        return await self.find_many(
            query=query or None,
            sort=[("order", ASCENDING), ("name", ASCENDING)],
            skip=offset,
            limit=limit,
        )

    async def find_by_key(self, key: str) -> PlatformDocument | None:
        """
        Read a single platform addressed by its machine key.

        :param key: Machine key of the platform.
        :return: The platform, or nothing when the key is unknown.
        """
        return await self.find_one(query={"key": key})
