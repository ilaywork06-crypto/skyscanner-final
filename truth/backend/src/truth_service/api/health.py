"""
The health endpoint, which says whether the register can currently be read at all.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from fastapi import APIRouter

from truth_service.dependencies import MongoProviderDependency

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(tags=["health"])

# ----- FUNCTIONS ----- #


@ROUTER.get("/health")
async def read_health(provider: MongoProviderDependency) -> dict[str, str]:
    """
    Say whether the document store behind the register is answering.

    :param provider: Owner of the shared motor client.
    :return: The state of the service and of the store it reads.
    """
    reachable = await provider.ping()

    return {"status": "ok" if reachable else "degraded", "store": "up" if reachable else "down"}
