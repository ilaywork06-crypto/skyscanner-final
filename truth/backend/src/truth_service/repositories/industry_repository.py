"""
The collection of the industries, which is the vocabulary the whole register is filed under.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from typing import Any

from pymongo import ASCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider

from truth_service.constants import INDUSTRIES_COLLECTION
from truth_service.documents import IndustryDocument
from truth_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class IndustryRepository(BaseRepository[IndustryDocument]):
    """
    Reads and writes of the industries.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the industries collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=INDUSTRIES_COLLECTION, document_type=IndustryDocument)

    def indexes(self) -> list[IndexModel]:
        """
        Declare the indexes the industries are read through.

        The name is unique because the register addresses an industry by it, and two industries answering to
        one name would make that address mean nothing.

        :return: The index definitions of the collection.
        """
        return [
            IndexModel([("name", ASCENDING)], name="name_unique", unique=True),
            IndexModel([("deleted", ASCENDING)], name="deleted"),
        ]

    async def find_by_name(self, name: str) -> IndustryDocument | None:
        """
        Read one industry addressed by its name.

        :param name: Name of the industry.
        :return: The industry, or nothing when no industry answers to that name.
        """
        return await self.find_one(query={"name": name})

    async def find_by_key(self, key: str) -> IndustryDocument | None:
        """
        Read one industry addressed by whichever of its identifier and its name the caller had.

        :param key: Identifier or name of the industry.
        :return: The industry, or nothing when neither addresses one.
        """
        return await self.find_one(query={"$or": [{"_id": key}, {"name": key}]})

    async def list_window(self, offset: int, limit: int) -> list[IndustryDocument]:
        """
        Read one window of the industries, in the order they were registered.

        :param offset: Amount of industries skipped before collecting.
        :param limit: Largest amount of industries that is returned, zero for all of them.
        :return: The industries of the window.
        """
        return await self.find_many(sort=[("created_at", 1), ("_id", 1)], skip=offset, limit=limit)

    async def counts_by_industry(self, collection_name: str) -> dict[str, int]:
        """
        Count the current assumptions of every industry at once.

        One pass answers for every industry, which is what keeps the industries page from being one count per
        row. It is asked for only by the listing that says it wants the counts.

        :param collection_name: Name of the collection holding the assumptions.
        :return: How many current assumptions name each industry, keyed by industry identifier.
        """
        pipeline: list[dict[str, Any]] = [
            {"$match": {"latest_revision": True, "deleted": {"$ne": True}}},
            {"$unwind": "$industries"},
            {"$group": {"_id": "$industries.id", "total": {"$sum": 1}}},
        ]
        cursor = self._provider.collection(collection_name).aggregate(pipeline)

        return {str(entry["_id"]): int(entry["total"]) async for entry in cursor}
