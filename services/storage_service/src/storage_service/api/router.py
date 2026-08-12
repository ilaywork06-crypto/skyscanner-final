"""
The single router that carries every endpoint of the storage service under the shared API prefix.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from fastapi import APIRouter

from storage_service.api import artifacts, health

# ----- CONSTS ----- #

API_PREFIX: str = "/api/storage"

# ----- FUNCTIONS ----- #


def build_api_router() -> APIRouter:
    """
    Collect every endpoint router of the service into the router the application mounts.

    :return: The router carrying every endpoint of the service.
    """
    router = APIRouter(prefix=API_PREFIX)
    for module in (health, artifacts):
        router.include_router(module.ROUTER)

    return router
