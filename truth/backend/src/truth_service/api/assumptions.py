"""
The endpoints of the assumptions, which are the rows of the register.

Two of these are not in the original shape of this API, and both exist for the same reason: a register of a
hundred thousand assumptions cannot be answered by handing the whole of it to the browser.

``POST /assumption/query`` takes the whole question a table is asking - the search, the restrictions, the
ordering and the window - and answers one window of it. It is a POST because a filter model is a structure
rather than a word, and putting one in a query string means truncating it at whatever length the first proxy
in the way happens to allow.

``GET /assumption/facets/{key}`` answers what a set filter offers to pick from, read off the register rather
than off the declarations, so a column offers the values that are actually there.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from fastapi import APIRouter, Query, status

from truth_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from truth_service.dependencies import AssumptionServiceDependency
from truth_service.models.assumption import (
    AssumptionCreateRequest,
    AssumptionDetailResponse,
    AssumptionRowResponse,
)
from truth_service.models.query import AssumptionPage, AssumptionQuery, FacetResponse
from truth_service.services.assumption_service import DEFAULT_FACET_LIMIT

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/assumption", tags=["assumptions"])

INDUSTRY_QUERY = Query(default=None, description="Industry, by identifier or name, the answer is narrowed to")
FACET_LIMIT_QUERY = Query(
    default=DEFAULT_FACET_LIMIT,
    ge=1,
    le=5000,
    description="Largest amount of values that is returned",
)

# ----- FUNCTIONS ----- #


@ROUTER.get("", response_model=list[AssumptionRowResponse])
async def list_assumptions(
    service: AssumptionServiceDependency,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[AssumptionRowResponse]:
    """
    Read one window of the register, newest first.

    Every listed assumption carries its values and the industries it belongs to. The original listing carried
    neither, which is what left a client reading every row it had just listed all over again.

    :param service: Owner of the assumptions.
    :param offset: Amount of assumptions skipped before collecting.
    :param limit: Largest amount of assumptions that is returned.
    :return: The assumptions of the window.
    """
    return await service.list_window(offset=offset, limit=limit)


@ROUTER.post("/query", response_model=AssumptionPage)
async def query_assumptions(request: AssumptionQuery, service: AssumptionServiceDependency) -> AssumptionPage:
    """
    Answer the whole question a table is asking - narrowed, ordered and cut to one window.

    :param request: Everything the table is asking at once.
    :param service: Owner of the assumptions.
    :return: The window of the answer, and how many assumptions the whole of it holds.
    """
    return await service.query(request=request)


@ROUTER.get("/facets/{key}", response_model=FacetResponse)
async def read_facet(
    key: str,
    service: AssumptionServiceDependency,
    industry: str | None = INDUSTRY_QUERY,
    limit: int = FACET_LIMIT_QUERY,
) -> FacetResponse:
    """
    Read every value one attribute is known to hold, which is what its filter offers to pick from.

    :param key: Attribute as the table addresses it.
    :param service: Owner of the assumptions.
    :param industry: Industry the vocabulary is gathered within, or nothing for the whole register.
    :param limit: Largest amount of values that is returned.
    :return: The values that attribute holds.
    """
    return await service.facet(key=key, industry=industry, limit=limit)


@ROUTER.post("", response_model=AssumptionDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_assumption(
    request: AssumptionCreateRequest,
    service: AssumptionServiceDependency,
) -> AssumptionDetailResponse:
    """
    Write a new assumption, checked against every declaration it names.

    :param request: Assumption supplied by the caller.
    :param service: Owner of the assumptions.
    :return: The assumption as it was stored, carrying the identifier it was given.
    """
    return await service.create(request=request)


@ROUTER.get("/{assumption_id}/latest", response_model=AssumptionDetailResponse)
async def read_latest_assumption(
    assumption_id: str,
    service: AssumptionServiceDependency,
) -> AssumptionDetailResponse:
    """
    Read the current revision of one assumption, whole.

    :param assumption_id: Identifier of a revision or of the lineage.
    :param service: Owner of the assumptions.
    :return: The current revision, whole.
    """
    return await service.get_latest(key=assumption_id)


@ROUTER.get("/{assumption_id}", response_model=AssumptionDetailResponse)
async def read_assumption(assumption_id: str, service: AssumptionServiceDependency) -> AssumptionDetailResponse:
    """
    Read exactly the revision that was addressed, falling back to the current one of its lineage.

    :param assumption_id: Identifier of a revision or of the lineage.
    :param service: Owner of the assumptions.
    :return: That revision, whole.
    """
    return await service.get_revision(identifier=assumption_id)
