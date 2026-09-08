"""
The atomic counters behind the human readable running numbers such as the event number shown in the table.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from pymongo import ReturnDocument

from skyscanner_common.mongo import MongoProvider

from events_service.constants import COUNTERS_COLLECTION

# ----- CONSTS ----- #

IDENTIFIER_FIELD: str = "_id"
VALUE_FIELD: str = "value"

# ----- CLASSES ----- #


class CounterRepository:
    """
    Keeper of the named counters, handing out gap free running numbers in a single atomic write.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the counters collection.

        :param provider: Owner of the shared motor client.
        """
        self._provider = provider

    async def next_value(self, name: str) -> int:
        """
        Increase a named counter and read the value it reached.

        :param name: Name of the counter.
        :return: The value the counter reached after the increase.
        """
        collection = self._provider.collection(COUNTERS_COLLECTION)
        document: dict[str, Any] | None = await collection.find_one_and_update(
            {IDENTIFIER_FIELD: name},
            {"$inc": {VALUE_FIELD: 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return 1

        return int(document.get(VALUE_FIELD, 1))

    async def set_minimum(self, name: str, minimum: int) -> None:
        """
        Lift a named counter to at least a given value, used when data is seeded into an empty system.

        :param name: Name of the counter.
        :param minimum: Smallest value the counter has to reach.
        """
        collection = self._provider.collection(COUNTERS_COLLECTION)
        await collection.update_one(
            {IDENTIFIER_FIELD: name},
            {"$max": {VALUE_FIELD: minimum}},
            upsert=True,
        )
