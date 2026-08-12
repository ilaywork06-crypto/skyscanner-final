"""
The rules around the mail subscriptions, letting a user follow an industry, an event type or one single event.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from skyscanner_common.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from skyscanner_models.common import UserContext
from skyscanner_models.subscription import SubscriptionCreateRequest, SubscriptionResponse, SubscriptionTrigger

from events_service.documents import SubscriptionDocument
from events_service.repositories.subscription_repository import SubscriptionRepository

# ----- CLASSES ----- #


class SubscriptionService:
    """
    Owner of the subscriptions, making sure a user follows one target only once.
    """

    def __init__(self, repository: SubscriptionRepository) -> None:
        """
        Bind the service to the repository of the subscriptions.

        :param repository: Persistence of the subscriptions.
        """
        self._repository = repository

    async def list_subscriptions(
        self,
        user: UserContext,
        offset: int = 0,
        limit: int = 0,
    ) -> list[SubscriptionResponse]:
        """
        Read every subscription of the caller.

        :param user: Identity the subscriptions are read for.
        :param offset: Amount of subscriptions skipped before collecting.
        :param limit: Largest amount of subscriptions that is returned, zero for all of them.
        :return: The subscriptions of the caller.
        """
        documents = await self._repository.list_for_owner(owner=user.username, offset=offset, limit=limit)

        return [document.to_response() for document in documents]

    async def create_subscription(
        self,
        request: SubscriptionCreateRequest,
        user: UserContext,
    ) -> SubscriptionResponse:
        """
        Start following an industry, an event type or a single event.

        :param request: Subscription supplied by the user.
        :param user: Identity the subscription belongs to.
        :return: The stored subscription.
        :raises ValidationError: When the subscription follows no target at all or asks for a trigger that
            can never fire for the target it names.
        :raises ConflictError: When the caller already follows the very same target.
        """
        if not any((request.industry, request.event_id, request.event_type_key)):
            raise ValidationError(message="A subscription has to follow an industry, an event type or an event")

        # An event that already exists is never uploaded again, so a subscription that names one would wait
        # for a mail about its creation forever.
        if request.event_id is not None and SubscriptionTrigger.EVENT_CREATED in request.triggers:
            raise ValidationError(
                message="A subscription to a single event cannot be notified about the upload of an event",
                details={"event_id": request.event_id},
            )

        # Two people following the same industry are two subscriptions, and until the services are handed
        # real identities the mail address is what tells those two people apart.
        existing = await self._repository.find_one(
            query={
                "owner": user.username,
                "email": request.email,
                "industry": request.industry,
                "event_type_key": request.event_type_key,
                "event_id": request.event_id,
            },
        )
        if existing is not None:
            raise ConflictError(
                message="This target is already followed by this mail address",
                details={"email": request.email},
            )

        document = SubscriptionDocument(**request.model_dump(), owner=user.username)
        await self._repository.insert(document=document)

        return document.to_response()

    async def delete_subscription(self, subscription_id: str, user: UserContext) -> None:
        """
        Stop following a target the caller follows.

        :param subscription_id: Identifier of the subscription that is removed.
        :param user: Identity that asks for the removal.
        :raises NotFoundError: When the identifier is unknown.
        :raises PermissionDeniedError: When the subscription belongs to somebody else.
        """
        document = await self._repository.find_by_id(identifier=subscription_id)
        if document is None:
            raise NotFoundError(message="The subscription does not exist", details={"id": subscription_id})

        if document.owner != user.username:
            raise PermissionDeniedError(message="Only the owner of a subscription may remove it")

        await self._repository.delete(identifier=subscription_id)
