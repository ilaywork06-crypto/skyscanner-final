"""
The web layer of the notification service, reporting its health and letting an operator flush the queue by hand.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.mongo import MongoProvider
from skyscanner_models.common import OperationResult

from notification_service.constants import SERVICE_NAME
from notification_service.repositories import OutboxRepository
from notification_service.services import DispatchService

# ----- CONSTS ----- #

API_PREFIX: str = "/api/notifications"
ROUTER: APIRouter = APIRouter(prefix=API_PREFIX, tags=["notifications"])

# ----- FUNCTIONS ----- #


def get_mongo_provider(request: Request) -> MongoProvider:
    """
    Fetch the shared document store provider that was opened when the service started.

    :param request: Incoming request carrying the application state.
    :return: The shared document store provider.
    """
    return cast(MongoProvider, request.app.state.mongo)


def get_dispatch_service(request: Request) -> DispatchService:
    """
    Fetch the running dispatch loop of the service.

    :param request: Incoming request carrying the application state.
    :return: The dispatch loop of the service.
    """
    return cast(DispatchService, request.app.state.dispatch)


ProviderDependency = Annotated[MongoProvider, Depends(get_mongo_provider)]
DispatchDependency = Annotated[DispatchService, Depends(get_dispatch_service)]


@ROUTER.get("/health")
async def read_health(provider: ProviderDependency) -> dict[str, str]:
    """
    Report whether the service, its document store and its queue are healthy.

    :param provider: Owner of the shared motor client.
    :return: The health report of the service.
    """
    reachable = await provider.ping()
    pending = await OutboxRepository(provider=provider).count_pending() if reachable else 0

    return {
        "service": SERVICE_NAME,
        "status": "healthy" if reachable else "degraded",
        "database": "up" if reachable else "down",
        "pending": str(pending),
        "checked_at": utc_now().isoformat(),
    }


@ROUTER.post("/dispatch", response_model=OperationResult)
async def dispatch_now(service: DispatchDependency) -> OperationResult:
    """
    Work through the pending notifications right away instead of waiting for the next round of the loop.

    :param service: Owner of the poll loop.
    :return: The acknowledgement carrying the amount of mails that went out.
    """
    sent = await service.dispatch_once()

    return OperationResult(success=True, message="The pending notifications were dispatched", affected=sent)
