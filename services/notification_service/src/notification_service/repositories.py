"""
The persistence layer of the notification service, reading the pending notifications and the matching subscribers.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from pymongo import ASCENDING

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.mongo import MongoProvider

from notification_service.constants import BATCH_SIZE, OUTBOX_COLLECTION, SUBSCRIPTIONS_COLLECTION
from notification_service.documents import OutboxDocument, SubscriptionDocument

# ----- CONSTS ----- #

IDENTIFIER_FIELD: str = "_id"

# ----- CLASSES ----- #


class OutboxRepository:
    """
    Reader of the pending notifications, marking each of them as processed once its mails went out.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the outbox collection.

        :param provider: Owner of the shared motor client.
        """
        self._provider = provider

    async def pending(self, limit: int = BATCH_SIZE) -> list[OutboxDocument]:
        """
        Read the notifications that were not sent yet, oldest first.

        :param limit: Largest amount of notifications that is returned.
        :return: The pending notifications.
        """
        cursor = (
            self._provider.collection(OUTBOX_COLLECTION)
            .find({"processed_at": None})
            .sort([("created_at", ASCENDING)])
            .limit(limit)
        )

        return [OutboxDocument.model_validate(raw) async for raw in cursor]

    async def mark_processed(self, identifier: str) -> None:
        """
        Record that every mail of one notification went out.

        :param identifier: Identifier of the notification.
        """
        await self._provider.collection(OUTBOX_COLLECTION).update_one(
            {IDENTIFIER_FIELD: identifier},
            {"$set": {"processed_at": utc_now()}},
        )

    async def record_failure(self, identifier: str) -> None:
        """
        Count one failed delivery round, so that a notification is retried instead of being dropped.

        :param identifier: Identifier of the notification.
        """
        await self._provider.collection(OUTBOX_COLLECTION).update_one(
            {IDENTIFIER_FIELD: identifier},
            {"$inc": {"attempts": 1}},
        )

    async def count_pending(self) -> int:
        """
        Count the notifications that are still waiting to be sent.

        :return: The amount of pending notifications.
        """
        return int(await self._provider.collection(OUTBOX_COLLECTION).count_documents({"processed_at": None}))


class SubscriptionRepository:
    """
    Reader of the subscriptions, resolving which users have to hear about one notification.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the subscriptions collection.

        :param provider: Owner of the shared motor client.
        """
        self._provider = provider

    async def matching(self, notification: OutboxDocument) -> list[SubscriptionDocument]:
        """
        Read every active subscription that follows the industry, the type or the event of a notification.

        :param notification: Pending notification the subscribers are resolved for.
        :return: The subscriptions that have to receive a mail.
        """
        targets: list[dict[str, Any]] = [
            {"industry": notification.industry},
            {"event_id": notification.event_id},
        ]
        if notification.event_type_keys:
            targets.append({"event_type_key": {"$in": notification.event_type_keys}})

        # A subscription is removed by being marked rather than erased, so an unsubscribe has to be read
        # here as well or the mails would keep going out after it.
        query: dict[str, Any] = {
            "active": True,
            "deleted": {"$ne": True},
            "triggers": notification.trigger.value,
            "$or": targets,
        }
        cursor = self._provider.collection(SUBSCRIPTIONS_COLLECTION).find(query)

        return [SubscriptionDocument.model_validate(raw) async for raw in cursor]

    async def mark_notified(self, identifier: str) -> None:
        """
        Record the moment a subscription received its last mail.

        :param identifier: Identifier of the subscription.
        """
        await self._provider.collection(SUBSCRIPTIONS_COLLECTION).update_one(
            {IDENTIFIER_FIELD: identifier},
            {"$set": {"last_notified_at": utc_now()}},
        )
