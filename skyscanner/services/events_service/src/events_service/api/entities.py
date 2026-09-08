"""
The endpoints of the entities nested inside an event, which is where a raw telemetry later becomes a parsed one.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends, status

from skyscanner_models.common import OperationResult, UserContext
from skyscanner_models.entity import EntityCreateRequest, EntityResponse, EntityUpdateRequest
from skyscanner_models.enums import Permission

from events_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from events_service.dependencies import EntityServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/events/{event_id}/entities", tags=["entities"])

# ----- FUNCTIONS ----- #


@ROUTER.get("", response_model=list[EntityResponse])
async def list_entities(
    event_id: str,
    service: EntityServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    entity_type: str | None = None,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[EntityResponse]:
    """
    Read the entities of one event, optionally narrowed to a single entity type.

    :param event_id: Identifier of the event the entities belong to.
    :param service: Owner of the entities.
    :param entity_type: Type key the result is narrowed to.
    :param offset: Amount of entities skipped before collecting.
    :param limit: Largest amount of entities that is returned, zero for all of them.
    :return: The matching entities of the event.
    """
    return await service.list_entities(
        event_id=event_id,
        entity_type_key=entity_type,
        offset=offset,
        limit=limit,
    )


@ROUTER.post("", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def add_entity(
    event_id: str,
    request: EntityCreateRequest,
    service: EntityServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.ENTITY_MANAGE))],
) -> EntityResponse:
    """
    Attach a new entity to an event that already exists.

    :param event_id: Identifier of the event the entity is attached to.
    :param request: Entity supplied by the user.
    :param service: Owner of the entities.
    :param user: Identity the entity is attributed to.
    :return: The stored entity.
    """
    return await service.add_entity(event_id=event_id, request=request, user=user)


@ROUTER.patch("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    event_id: str,
    entity_id: str,
    request: EntityUpdateRequest,
    service: EntityServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.ENTITY_MANAGE))],
) -> EntityResponse:
    """
    Change an entity, which is how the parsed products of a telemetry reach the system after the raw upload.

    :param event_id: Identifier of the event the entity belongs to.
    :param entity_id: Identifier of the entity that is changed.
    :param request: Attributes the caller wants to change.
    :param service: Owner of the entities.
    :param user: Identity the change is attributed to.
    :return: The changed entity.
    """
    return await service.update_entity(event_id=event_id, entity_id=entity_id, request=request, user=user)


@ROUTER.delete("/{entity_id}", response_model=OperationResult)
async def delete_entity(
    event_id: str,
    entity_id: str,
    service: EntityServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.ENTITY_MANAGE))],
) -> OperationResult:
    """
    Remove an entity from an event.

    :param event_id: Identifier of the event the entity belongs to.
    :param entity_id: Identifier of the entity that is removed.
    :param service: Owner of the entities.
    :param user: Identity the removal is attributed to.
    :return: The acknowledgement of the removal.
    """
    await service.delete_entity(event_id=event_id, entity_id=entity_id, user=user)

    return OperationResult(success=True, message="The entity was removed", affected=1)
