"""
The endpoints of the industries, which are the vocabulary the register is filed under.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from fastapi import APIRouter, Query, status

from truth_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from truth_service.dependencies import IndustryServiceDependency
from truth_service.models.industry import IndustryCreateRequest, IndustryResponse

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/industry", tags=["industries"])

COUNTS_QUERY = Query(default=False, description="Whether each industry is answered with its assumption count")

# ----- FUNCTIONS ----- #


@ROUTER.get("", response_model=list[IndustryResponse])
async def list_industries(
    service: IndustryServiceDependency,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
    with_counts: bool = COUNTS_QUERY,
) -> list[IndustryResponse]:
    """
    Read one window of the registered industries.

    :param service: Owner of the industries.
    :param offset: Amount of industries skipped before collecting.
    :param limit: Largest amount of industries that is returned.
    :param with_counts: Whether each industry is answered with how many assumptions name it.
    :return: The industries of the window.
    """
    return await service.list_industries(offset=offset, limit=limit, with_counts=with_counts)


@ROUTER.post("", response_model=IndustryResponse, status_code=status.HTTP_201_CREATED)
async def create_industry(request: IndustryCreateRequest, service: IndustryServiceDependency) -> IndustryResponse:
    """
    Register a new industry.

    :param request: Industry supplied by the caller.
    :param service: Owner of the industries.
    :return: The industry as it was stored, carrying the identifier it was given.
    """
    return await service.create_industry(request=request)


@ROUTER.get("/name/{name}", response_model=IndustryResponse)
async def read_industry_by_name(name: str, service: IndustryServiceDependency) -> IndustryResponse:
    """
    Read one industry addressed by its name.

    :param name: Name of the industry.
    :param service: Owner of the industries.
    :return: The industry.
    """
    return await service.get_industry_by_name(name=name)


@ROUTER.get("/{industry_id}", response_model=IndustryResponse)
async def read_industry(industry_id: str, service: IndustryServiceDependency) -> IndustryResponse:
    """
    Read one industry addressed by its identifier.

    :param industry_id: Identifier of the industry.
    :param service: Owner of the industries.
    :return: The industry.
    """
    return await service.get_industry(key=industry_id)
