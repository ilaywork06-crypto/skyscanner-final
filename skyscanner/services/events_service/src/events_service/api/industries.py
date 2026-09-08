"""
The endpoints of the industries, which the client renders as the tabs above the inventory table.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends, status

from skyscanner_models.common import UserContext
from skyscanner_models.enums import Permission
from skyscanner_models.industry import IndustryCreateRequest, IndustryResponse, IndustryUpdateRequest

from events_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from events_service.dependencies import IndustryServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/industries", tags=["industries"])

# ----- FUNCTIONS ----- #


@ROUTER.get("", response_model=list[IndustryResponse])
async def list_industries(
    service: IndustryServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[IndustryResponse]:
    """
    Read every registered industry together with the amount of events it holds.

    :param service: Owner of the industries.
    :param offset: Amount of industries skipped before collecting.
    :param limit: Largest amount of industries that is returned, zero for all of them.
    :return: Every registered industry.
    """
    return await service.list_industries(offset=offset, limit=limit)


@ROUTER.get("/{key}", response_model=IndustryResponse)
async def read_industry(
    key: str,
    service: IndustryServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
) -> IndustryResponse:
    """
    Read a single industry addressed by its machine key.

    :param key: Machine key of the industry.
    :param service: Owner of the industries.
    :return: The industry together with the amount of events it holds.
    """
    return await service.get_industry(key=key)


@ROUTER.post("", response_model=IndustryResponse, status_code=status.HTTP_201_CREATED)
async def create_industry(
    request: IndustryCreateRequest,
    service: IndustryServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.INDUSTRY_MANAGE))],
) -> IndustryResponse:
    """
    Register a new industry.

    :param request: Industry supplied by the user.
    :param service: Owner of the industries.
    :return: The stored industry.
    """
    return await service.create_industry(request=request)


@ROUTER.patch("/{key}", response_model=IndustryResponse)
async def update_industry(
    key: str,
    request: IndustryUpdateRequest,
    service: IndustryServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.INDUSTRY_MANAGE))],
) -> IndustryResponse:
    """
    Change a registered industry, which is how the vocabulary of the entity origins is maintained.

    :param key: Machine key of the industry that is changed.
    :param request: Attributes the caller wants to change.
    :param service: Owner of the industries.
    :return: The changed industry.
    """
    return await service.update_industry(key=key, request=request)
