"""
The endpoints that hand the web client its generated tables - the column definitions and the blocks of rows.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends

from skyscanner_models.common import UserContext
from skyscanner_models.enums import Permission
from skyscanner_models.grid import GridConfiguration, GridRowsRequest, GridRowsResponse

from events_service.dependencies import GridServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/grid", tags=["grid"])

# ----- FUNCTIONS ----- #


@ROUTER.get("/events/columns", response_model=GridConfiguration)
async def read_event_columns(
    service: GridServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    industry: str | None = None,
    discover: bool = True,
) -> GridConfiguration:
    """
    Build the configuration of the inventory table for the global view or for a single industry.

    :param service: Generator of the tables.
    :param industry: Industry the table is generated for, empty for the shared view of every industry.
    :param discover: Whether keys written without a declaration are added as hidden columns.
    :return: The complete configuration of the inventory table.
    """
    return await service.event_configuration(industry=industry, discover=discover)


@ROUTER.get("/entities/columns", response_model=GridConfiguration)
async def read_entity_columns(
    service: GridServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    industry: str | None = None,
    entity_type: str | None = None,
) -> GridConfiguration:
    """
    Build the configuration of the table that renders the entities of one event.

    :param service: Generator of the tables.
    :param industry: Industry the table is generated for, empty for the shared view of every industry.
    :param entity_type: Entity type the table is generated for.
    :return: The complete configuration of the entity table.
    """
    return await service.entity_configuration(industry=industry, entity_type=entity_type)


@ROUTER.post("/events/rows", response_model=GridRowsResponse)
async def read_event_rows(
    request: GridRowsRequest,
    service: GridServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
) -> GridRowsResponse:
    """
    Read one block of inventory rows, already flattened into the shape the column definitions address.

    :param request: Query the grid data source sent for the block.
    :param service: Generator of the tables.
    :return: The rows of the block together with the total amount of matching events.
    """
    return await service.event_rows(request=request)


@ROUTER.get("/events/values/{key}", response_model=list[str])
async def read_column_values(
    key: str,
    service: GridServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
) -> list[str]:
    """
    Read the values one column currently holds, so that the client can offer them as filter options.

    :param key: Key of the column the values are read for.
    :param service: Generator of the tables.
    :return: The values of the column ordered by how often they appear.
    """
    return await service.distinct_values(key=key)
