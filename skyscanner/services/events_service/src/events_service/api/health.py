"""
The liveness endpoint of the events service, reporting whether the document store still answers.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from fastapi import APIRouter

from skyscanner_common.datetime_utils import utc_now

from events_service.constants import SERVICE_NAME
from events_service.dependencies import ProviderDependency

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(tags=["health"])

# ----- FUNCTIONS ----- #


@ROUTER.get("/health")
async def read_health(provider: ProviderDependency) -> dict[str, str]:
    """
    Report whether the service and its document store are healthy.

    :param provider: Owner of the shared motor client.
    :return: The health report of the service.
    """
    reachable = await provider.ping()

    return {
        "service": SERVICE_NAME,
        "status": "healthy" if reachable else "degraded",
        "database": "up" if reachable else "down",
        "checked_at": utc_now().isoformat(),
    }
