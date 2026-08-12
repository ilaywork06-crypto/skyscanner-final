"""
The endpoints of the mail subscriptions, where a user starts or stops following an industry or a single event.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends, status

from skyscanner_models.common import OperationResult, UserContext
from skyscanner_models.enums import Permission
from skyscanner_models.subscription import SubscriptionCreateRequest, SubscriptionResponse

from events_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from events_service.dependencies import CurrentUser, SubscriptionServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# ----- FUNCTIONS ----- #


@ROUTER.get("", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    service: SubscriptionServiceDependency,
    user: CurrentUser,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[SubscriptionResponse]:
    """
    Read every subscription of the caller.

    :param service: Owner of the subscriptions.
    :param user: Identity the subscriptions are read for.
    :param offset: Amount of subscriptions skipped before collecting.
    :param limit: Largest amount of subscriptions that is returned, zero for all of them.
    :return: The subscriptions of the caller.
    """
    return await service.list_subscriptions(user=user, offset=offset, limit=limit)


@ROUTER.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    request: SubscriptionCreateRequest,
    service: SubscriptionServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.SUBSCRIPTION_MANAGE))],
) -> SubscriptionResponse:
    """
    Start following an industry, an event type or a single event.

    :param request: Subscription supplied by the user.
    :param service: Owner of the subscriptions.
    :param user: Identity the subscription belongs to.
    :return: The stored subscription.
    """
    return await service.create_subscription(request=request, user=user)


@ROUTER.delete("/{subscription_id}", response_model=OperationResult)
async def delete_subscription(
    subscription_id: str,
    service: SubscriptionServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.SUBSCRIPTION_MANAGE))],
) -> OperationResult:
    """
    Stop following a target the caller follows.

    :param subscription_id: Identifier of the subscription that is removed.
    :param service: Owner of the subscriptions.
    :param user: Identity that asks for the removal.
    :return: The acknowledgement of the removal.
    """
    await service.delete_subscription(subscription_id=subscription_id, user=user)

    return OperationResult(success=True, message="The subscription was removed", affected=1)
