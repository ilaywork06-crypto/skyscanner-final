"""
The endpoints of the platforms an event may name, which are their own page rather than a corner of the types.

:date: 2026-09-08
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends, status

from skyscanner_models.common import OperationResult, RenameResult, UserContext
from skyscanner_models.enums import Permission
from skyscanner_models.platform import PlatformCreateRequest, PlatformResponse, PlatformUpdateRequest

from events_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from events_service.dependencies import PlatformServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/platforms", tags=["platforms"])

# ----- FUNCTIONS ----- #


@ROUTER.get("", response_model=list[PlatformResponse])
async def list_platforms(
    service: PlatformServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    industry: str | None = None,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[PlatformResponse]:
    """
    Read the platforms an industry may name on its events.

    :param service: Owner of the declared platforms.
    :param industry: Industry whose own platforms are added to the shared ones.
    :param offset: Amount of platforms skipped before collecting.
    :param limit: Largest amount of platforms that is returned, zero for all of them.
    :return: The matching platforms.
    """
    return await service.list_platforms(industry=industry, offset=offset, limit=limit)


@ROUTER.get("/{key}", response_model=PlatformResponse)
async def read_platform(
    key: str,
    service: PlatformServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
) -> PlatformResponse:
    """
    Read a single platform addressed by its machine key.

    :param key: Machine key of the platform.
    :param service: Owner of the declared platforms.
    :return: The platform.
    """
    return await service.get_platform(key=key)


@ROUTER.post("", response_model=PlatformResponse, status_code=status.HTTP_201_CREATED)
async def create_platform(
    request: PlatformCreateRequest,
    service: PlatformServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> PlatformResponse:
    """
    Declare a new platform the create wizard offers for the industries it belongs to.

    :param request: Platform supplied by the user.
    :param service: Owner of the declared platforms.
    :return: The stored platform.
    """
    return await service.create_platform(request=request)


@ROUTER.get("/{platform_id}/rename", response_model=RenameResult)
async def preview_platform_rename(
    platform_id: str,
    key: str,
    service: PlatformServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> RenameResult:
    """
    Say what renaming a platform would touch, so that the change is made knowing its size.

    An event names the platforms it ran on by their key rather than pointing at the declaration, so a rename
    is a write across the events, the saved views and everything else naming it. This answers how much of
    that there is without doing any of it.

    :param platform_id: Identifier of the platform that would be renamed.
    :param key: Key it would be renamed to.
    :param service: Owner of the declared platforms.
    :return: How many documents of each collection carry the current key.
    """
    return await service.preview_rename(platform_id=platform_id, key=key)


@ROUTER.patch("/{platform_id}", response_model=PlatformResponse)
async def update_platform(
    platform_id: str,
    request: PlatformUpdateRequest,
    service: PlatformServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> PlatformResponse:
    """
    Change a declared platform, carrying a changed key through every event that named it.

    :param platform_id: Identifier of the platform that is changed.
    :param request: Attributes the caller wants to change.
    :param service: Owner of the declared platforms.
    :return: The changed platform.
    """
    return await service.update_platform(platform_id=platform_id, request=request)


@ROUTER.delete("/{platform_id}", response_model=OperationResult)
async def delete_platform(
    platform_id: str,
    service: PlatformServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> OperationResult:
    """
    Remove a declared platform, which hides it from the selectors without touching the events naming it.

    :param platform_id: Identifier of the platform that is removed.
    :param service: Owner of the declared platforms.
    :param user: Identity the removal is attributed to.
    :return: The acknowledgement of the removal.
    """
    await service.delete_platform(platform_id=platform_id, user=user)

    return OperationResult(success=True, message="The platform was removed", affected=1)
