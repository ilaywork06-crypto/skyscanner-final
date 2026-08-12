"""
Persistence of the industries that appear as the tabs above the inventory table and scope the dynamic schema.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from pymongo import ASCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider

from events_service.constants import INDUSTRIES_COLLECTION
from events_service.documents import IndustryDocument
from events_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class IndustryRepository(BaseRepository[IndustryDocument]):
    """
    The single door to the industries collection.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the industries collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=INDUSTRIES_COLLECTION, document_type=IndustryDocument)

    async def ensure_indexes(self) -> None:
        """
        Create the index that keeps an industry key unique.
        """
        await self.create_indexes(
            [IndexModel([("key", ASCENDING)], unique=True, name="industry_key_unique")],
        )

    async def list_all(self, offset: int = 0, limit: int = 0) -> list[IndustryDocument]:
        """
        Read every registered industry ordered by the position of its tab.

        :param offset: Amount of industries skipped before collecting.
        :param limit: Largest amount of industries that is returned, zero for all of them.
        :return: Every registered industry inside the requested window.
        """
        return await self.find_many(
            sort=[("order", ASCENDING), ("name", ASCENDING)],
            skip=offset,
            limit=limit,
        )

    async def find_by_key(self, key: str) -> IndustryDocument | None:
        """
        Read a single industry addressed by its machine key.

        :param key: Machine key of the industry.
        :return: The industry, or nothing when the key is unknown.
        """
        return await self.find_one(query={"key": key})
