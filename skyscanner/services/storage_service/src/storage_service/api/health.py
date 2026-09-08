"""
The liveness endpoint of the storage service, reporting whether the bucket still answers.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from fastapi import APIRouter

from skyscanner_common.datetime_utils import utc_now

from storage_service.constants import SERVICE_NAME
from storage_service.dependencies import StorageDependency

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(tags=["health"])

# ----- FUNCTIONS ----- #


@ROUTER.get("/health")
async def read_health(storage: StorageDependency) -> dict[str, str]:
    """
    Report whether the service and its bucket are healthy.

    :param storage: Client of the object storage.
    :return: The health report of the service.
    """
    reachable = await storage.ping()

    return {
        "service": SERVICE_NAME,
        "status": "healthy" if reachable else "degraded",
        "bucket": "up" if reachable else "down",
        "checked_at": utc_now().isoformat(),
    }
