"""
Persistence of the mail subscriptions that make a user hear about an industry, an event type or a single event.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from pymongo import ASCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider

from events_service.constants import SUBSCRIPTIONS_COLLECTION
from events_service.documents import SubscriptionDocument
from events_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class SubscriptionRepository(BaseRepository[SubscriptionDocument]):
    """
    The single door to the subscriptions collection.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the subscriptions collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(
            provider=provider,
            collection_name=SUBSCRIPTIONS_COLLECTION,
            document_type=SubscriptionDocument,
        )

    async def ensure_indexes(self) -> None:
        """
        Create the indexes that keep one subscription per recipient and target and speed up the fan out.

        The mail address is part of what makes a subscription unique. Without it, the whole installation
        shares one subscription per target while every caller reaches the service as the same anonymous
        account, so the second person asking to be told about an industry is refused because the first
        person already asked - even though the mail would go somewhere else entirely.
        """
        await super().ensure_indexes()
        await self.create_indexes(
            [
                IndexModel(
                    [
                        ("owner", ASCENDING),
                        ("email", ASCENDING),
                        ("industry", ASCENDING),
                        ("event_type_key", ASCENDING),
                        ("event_id", ASCENDING),
                    ],
                    unique=True,
                    name="subscription_recipient_target_unique",
                ),
                IndexModel([("active", ASCENDING), ("industry", ASCENDING)], name="active_industry"),
            ],
        )

    async def drop_legacy_indexes(self) -> None:
        """
        Remove the index that made a target unique per user regardless of the mail address it notified.
        """
        await self.drop_index_if_present(name="subscription_target_unique")

    async def list_for_owner(self, owner: str, offset: int = 0, limit: int = 0) -> list[SubscriptionDocument]:
        """
        Read every subscription of one user.

        :param owner: User the subscriptions are read for.
        :param offset: Amount of subscriptions skipped before collecting.
        :param limit: Largest amount of subscriptions that is returned, zero for all of them.
        :return: The subscriptions of the user ordered by when they were created.
        """
        return await self.find_many(
            query={"owner": owner},
            sort=[("created_at", ASCENDING)],
            skip=offset,
            limit=limit,
        )
