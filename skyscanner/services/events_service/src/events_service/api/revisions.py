"""
The endpoints of the edit history, answering who changed an event or one of its entities, when and why.

:date: 2026-08-12
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends

from skyscanner_models.common import UserContext
from skyscanner_models.enums import Permission
from skyscanner_models.revision import RevisionResponse

from events_service.dependencies import RevisionServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/events/{event_id}", tags=["revisions"])

# ----- FUNCTIONS ----- #


@ROUTER.get("/revisions", response_model=list[RevisionResponse])
async def list_event_revisions(
    event_id: str,
    service: RevisionServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    include_entities: bool = False,
) -> list[RevisionResponse]:
    """
    Read the recorded edits of one event, newest first.

    :param event_id: Identifier of the event the history is read for.
    :param service: Owner of the edit history.
    :param include_entities: Whether the edits of the entities inside the event are read as well.
    :return: The recorded edits of the event.
    """
    return await service.list_history(event_id=event_id, include_entities=include_entities)


@ROUTER.get("/entities/{entity_id}/revisions", response_model=list[RevisionResponse])
async def list_entity_revisions(
    event_id: str,
    entity_id: str,
    service: RevisionServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
) -> list[RevisionResponse]:
    """
    Read the recorded edits of one entity, newest first.

    :param event_id: Identifier of the event the entity belongs to.
    :param entity_id: Identifier of the entity the history is read for.
    :param service: Owner of the edit history.
    :return: The recorded edits of the entity.
    """
    return await service.list_history(event_id=event_id, entity_id=entity_id)
