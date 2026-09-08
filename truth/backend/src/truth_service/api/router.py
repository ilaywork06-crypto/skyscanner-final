"""
The single router that carries every endpoint of the register.

The paths are not prefixed. The client reaches this service through a gateway that strips its own prefix
before forwarding, so what arrives here is the bare resource path.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from fastapi import APIRouter

from truth_service.api import assumptions, health, industries, schemas

# ----- CONSTS ----- #

API_PREFIX: str = ""

# ----- FUNCTIONS ----- #


def build_api_router() -> APIRouter:
    """
    Collect every endpoint router of the service into the router the application mounts.

    :return: The router carrying every endpoint of the service.
    """
    router = APIRouter()
    for module in (health, industries, schemas, assumptions):
        router.include_router(module.ROUTER)

    return router
