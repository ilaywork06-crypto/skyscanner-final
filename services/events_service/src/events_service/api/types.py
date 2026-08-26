"""
The endpoints of the declared event types and entity types the create wizard and the event page work with.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends, status

from skyscanner_models.common import OperationResult, UserContext
from skyscanner_models.entity import EntityTypeCreateRequest, EntityTypeResponse, EntityTypeUpdateRequest
from skyscanner_models.enums import Permission
from skyscanner_models.event import EventTypeCreateRequest, EventTypeResponse, EventTypeUpdateRequest
from skyscanner_models.platform import PlatformCreateRequest, PlatformResponse, PlatformUpdateRequest

from events_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from events_service.dependencies import TypeServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/types", tags=["types"])

# ----- FUNCTIONS ----- #


@ROUTER.get("/events", response_model=list[EventTypeResponse])
async def list_event_types(
    service: TypeServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    industry: str | None = None,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[EventTypeResponse]:
    """
    Read the event types an industry may choose from.

    :param service: Owner of the declared types.
    :param industry: Industry whose own types are added to the shared ones.
    :param offset: Amount of types skipped before collecting.
    :param limit: Largest amount of types that is returned, zero for all of them.
    :return: The matching event types.
    """
    return await service.list_event_types(industry=industry, offset=offset, limit=limit)


@ROUTER.get("/entities", response_model=list[EntityTypeResponse])
async def list_entity_types(
    service: TypeServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    industry: str | None = None,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[EntityTypeResponse]:
    """
    Read the entity types an industry may choose from.

    :param service: Owner of the declared types.
    :param industry: Industry whose own types are added to the shared ones.
    :param offset: Amount of types skipped before collecting.
    :param limit: Largest amount of types that is returned, zero for all of them.
    :return: The matching entity types.
    """
    return await service.list_entity_types(industry=industry, offset=offset, limit=limit)


@ROUTER.get("/platforms", response_model=list[PlatformResponse])
async def list_platforms(
    service: TypeServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    industry: str | None = None,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[PlatformResponse]:
    """
    Read the platforms an industry may name on its events.

    :param service: Owner of the declared types.
    :param industry: Industry whose own platforms are added to the shared ones.
    :param offset: Amount of platforms skipped before collecting.
    :param limit: Largest amount of platforms that is returned, zero for all of them.
    :return: The matching platforms.
    """
    return await service.list_platforms(industry=industry, offset=offset, limit=limit)


@ROUTER.post("/events", response_model=EventTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_event_type(
    request: EventTypeCreateRequest,
    service: TypeServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> EventTypeResponse:
    """
    Declare a new event type the create wizard offers.

    :param request: Event type supplied by the user.
    :param service: Owner of the declared types.
    :return: The stored event type.
    """
    return await service.create_event_type(request=request)


@ROUTER.post("/entities", response_model=EntityTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_entity_type(
    request: EntityTypeCreateRequest,
    service: TypeServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> EntityTypeResponse:
    """
    Declare a new entity type the event page groups its entities by.

    :param request: Entity type supplied by the user.
    :param service: Owner of the declared types.
    :return: The stored entity type.
    """
    return await service.create_entity_type(request=request)


@ROUTER.post("/platforms", response_model=PlatformResponse, status_code=status.HTTP_201_CREATED)
async def create_platform(
    request: PlatformCreateRequest,
    service: TypeServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> PlatformResponse:
    """
    Declare a new platform the create wizard offers for the industries it belongs to.

    :param request: Platform supplied by the user.
    :param service: Owner of the declared types.
    :return: The stored platform.
    """
    return await service.create_platform(request=request)


@ROUTER.patch("/platforms/{type_id}", response_model=PlatformResponse)
async def update_platform(
    type_id: str,
    request: PlatformUpdateRequest,
    service: TypeServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> PlatformResponse:
    """
    Change a declared platform.

    :param type_id: Identifier of the platform that is changed.
    :param request: Attributes the caller wants to change.
    :param service: Owner of the declared types.
    :return: The changed platform.
    """
    return await service.update_platform(type_id=type_id, request=request)


@ROUTER.patch("/events/{type_id}", response_model=EventTypeResponse)
async def update_event_type(
    type_id: str,
    request: EventTypeUpdateRequest,
    service: TypeServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> EventTypeResponse:
    """
    Change a declared event type.

    :param type_id: Identifier of the event type that is changed.
    :param request: Attributes the caller wants to change.
    :param service: Owner of the declared types.
    :return: The changed event type.
    """
    return await service.update_event_type(type_id=type_id, request=request)


@ROUTER.patch("/entities/{type_id}", response_model=EntityTypeResponse)
async def update_entity_type(
    type_id: str,
    request: EntityTypeUpdateRequest,
    service: TypeServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> EntityTypeResponse:
    """
    Change a declared entity type.

    :param type_id: Identifier of the entity type that is changed.
    :param request: Attributes the caller wants to change.
    :param service: Owner of the declared types.
    :return: The changed entity type.
    """
    return await service.update_entity_type(type_id=type_id, request=request)


@ROUTER.delete("/{type_id}", response_model=OperationResult)
async def delete_type(
    type_id: str,
    service: TypeServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> OperationResult:
    """
    Remove a declared type, which hides it from the selectors without touching the documents that use it.

    :param type_id: Identifier of the type that is removed.
    :param service: Owner of the declared types.
    :param user: Identity the removal is attributed to.
    :return: The acknowledgement of the removal.
    """
    await service.delete_type(type_id=type_id, user=user)

    return OperationResult(success=True, message="The type was removed", affected=1)
