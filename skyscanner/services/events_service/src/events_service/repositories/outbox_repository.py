"""
Persistence of the pending notifications, the hand over point between the events service and the mail service.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from pymongo import ASCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider

from events_service.constants import OUTBOX_COLLECTION
from events_service.documents import OutboxDocument
from events_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class OutboxRepository(BaseRepository[OutboxDocument]):
    """
    The single door to the outbox collection the notification service polls.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the outbox collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=OUTBOX_COLLECTION, document_type=OutboxDocument)

    async def ensure_indexes(self) -> None:
        """
        Create the index the notification service uses to pick up the pending notifications in order.
        """
        await self.create_indexes(
            [IndexModel([("processed_at", ASCENDING), ("created_at", ASCENDING)], name="pending")],
        )
