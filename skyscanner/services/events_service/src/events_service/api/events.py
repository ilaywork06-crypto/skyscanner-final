"""
The endpoints of the inventory itself - searching the events, reading one of them and creating or editing them.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends, status

from skyscanner_models.common import OperationResult, UserContext
from skyscanner_models.enums import Permission
from skyscanner_models.event import EventCreateRequest, EventResponse, EventSummaryResponse, EventUpdateRequest
from skyscanner_models.pagination import Page
from skyscanner_models.query import SearchQuery

from events_service.dependencies import EventServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/events", tags=["events"])

# ----- FUNCTIONS ----- #


@ROUTER.post("/search", response_model=Page[EventSummaryResponse])
async def search_events(
    query: SearchQuery,
    service: EventServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
) -> Page[EventSummaryResponse]:
    """
    Read one page of the inventory the way the toolbar and the table asked for it.

    :param query: Query requested by the client.
    :param service: Owner of the inventory.
    :return: The page of matching events.
    """
    return await service.search_events(query=query)


@ROUTER.get("/{event_id}", response_model=EventResponse)
async def read_event(
    event_id: str,
    service: EventServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
) -> EventResponse:
    """
    Read a single event together with every entity nested inside it.

    :param event_id: Identifier of the event.
    :param service: Owner of the inventory.
    :return: The detail representation of the event.
    """
    return await service.get_event(event_id=event_id)


@ROUTER.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    request: EventCreateRequest,
    service: EventServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.EVENT_CREATE))],
) -> EventResponse:
    """
    Store a new event with the files, the dynamic values and the entities the wizard collected.

    :param request: Event supplied by the user.
    :param service: Owner of the inventory.
    :param user: Identity the event is attributed to.
    :return: The stored event.
    """
    return await service.create_event(request=request, user=user)


@ROUTER.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    request: EventUpdateRequest,
    service: EventServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.EVENT_UPDATE))],
) -> EventResponse:
    """
    Change an event so that data revealed after the upload can be filled in later on.

    :param event_id: Identifier of the event that is changed.
    :param request: Attributes the caller wants to change.
    :param service: Owner of the inventory.
    :param user: Identity the change is attributed to.
    :return: The changed event.
    """
    return await service.update_event(event_id=event_id, request=request, user=user)


@ROUTER.delete("/{event_id}", response_model=OperationResult)
async def delete_event(
    event_id: str,
    service: EventServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.EVENT_DELETE))],
) -> OperationResult:
    """
    Remove an event together with the entities nested inside it.

    :param event_id: Identifier of the event that is removed.
    :param service: Owner of the inventory.
    :param user: Identity the removal is attributed to.
    :return: The acknowledgement of the removal.
    """
    await service.delete_event(event_id=event_id, user=user)

    return OperationResult(success=True, message="The event was removed", affected=1)


@ROUTER.get("", response_model=Page[EventSummaryResponse])
async def list_events(
    service: EventServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    industry: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Page[EventSummaryResponse]:
    """
    Read one page of the inventory with the few restrictions that fit into a link.

    :param service: Owner of the inventory.
    :param industry: Industry key the results are restricted to.
    :param search: Free text matched against the indexed event fields.
    :param page: One based index of the requested page.
    :param page_size: Amount of events to return for the page.
    :return: The page of matching events.
    """
    return await service.search_events(
        query=SearchQuery(industry=industry, search=search, page=page, page_size=page_size),
    )
