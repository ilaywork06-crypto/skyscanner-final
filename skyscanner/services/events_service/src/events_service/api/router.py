"""
The single router that carries every endpoint of the events service under the shared API prefix.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from fastapi import APIRouter

from events_service.api import (
    entities,
    events,
    exports,
    fields,
    grid,
    health,
    industries,
    revisions,
    subscriptions,
    templates,
    types,
)

# ----- CONSTS ----- #

API_PREFIX: str = "/api"

# ----- FUNCTIONS ----- #


def build_api_router() -> APIRouter:
    """
    Collect every endpoint router of the service into the router the application mounts.

    :return: The router carrying every endpoint of the service.
    """
    router = APIRouter(prefix=API_PREFIX)
    modules = (
        health,
        events,
        entities,
        revisions,
        fields,
        types,
        industries,
        grid,
        templates,
        subscriptions,
        exports,
    )
    for module in modules:
        router.include_router(module.ROUTER)

    return router
