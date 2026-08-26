"""
The generation of the tables - the column definitions of an industry and the flattened rows the grid renders.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from math import ceil
from typing import Any

from pydantic_core import to_jsonable_python

from ag_grid_lib.columns import DYNAMIC_FIELD_PREFIX
from ag_grid_lib.configuration import build_grid_configuration
from ag_grid_lib.datasource import resolve_path
from ag_grid_lib.introspection import SchemaIntrospector
from skyscanner_models.enums import FieldScope
from skyscanner_models.grid import GridConfiguration, GridRowsRequest, GridRowsResponse

from events_service.constants import (
    ENTITY_BASE_COLUMNS,
    EVENT_BASE_COLUMNS,
    FIXED_EVENT_KEYS,
)
from events_service.documents import EntityDocument, EventDocument
from events_service.repositories.event_repository import EventRepository
from events_service.services.field_service import FieldService

# ----- CONSTS ----- #

EVENT_SORT_KEY: str = "created_at"
ENTITY_SORT_KEY: str = "created_at"
DISTINCT_LIMIT: int = 50

# ----- CLASSES ----- #


class GridService:
    """
    Owner of the generated tables, merging the built in columns with the schema an industry declared.
    """

    def __init__(
        self,
        event_repository: EventRepository,
        field_service: FieldService,
        introspector: SchemaIntrospector,
    ) -> None:
        """
        Bind the service to the sources of the columns and of the rows.

        :param event_repository: Persistence of the events the rows are read from.
        :param field_service: Owner of the declared dynamic schema.
        :param introspector: Reader of the keys that were written without a declaration.
        """
        self._event_repository = event_repository
        self._field_service = field_service
        self._introspector = introspector

    async def event_configuration(self, industry: str | None = None, discover: bool = True) -> GridConfiguration:
        """
        Build the configuration of the inventory table for the global view or for a single industry.

        :param industry: Industry the table is generated for, empty for the shared view of every industry.
        :param discover: Whether keys written without a declaration are added as hidden columns.
        :return: The complete configuration of the inventory table.
        """
        declared = await self._field_service.list_fields(scope=FieldScope.EVENT, industry=industry)
        if discover:
            declared_keys = {definition.key for definition in declared}
            scope_filter = {"industry": industry} if industry else None
            declared = declared + await self._introspector.infer_missing_fields(
                declared_keys=declared_keys,
                scope=FieldScope.EVENT,
                industry=industry,
                scope_filter=scope_filter,
            )

        return build_grid_configuration(
            scope=FieldScope.EVENT,
            base_columns=EVENT_BASE_COLUMNS,
            declared_fields=declared,
            industry=industry,
            default_sort_key=EVENT_SORT_KEY,
        )

    async def entity_configuration(
        self,
        industry: str | None = None,
        entity_type: str | None = None,
    ) -> GridConfiguration:
        """
        Build the configuration of the table that renders the entities of one event.

        :param industry: Industry the table is generated for, empty for the shared view of every industry.
        :param entity_type: Entity type the table is generated for.
        :return: The complete configuration of the entity table.
        """
        declared = await self._field_service.list_fields(
            scope=FieldScope.ENTITY,
            industry=industry,
            entity_type=entity_type,
        )

        return build_grid_configuration(
            scope=FieldScope.ENTITY,
            base_columns=ENTITY_BASE_COLUMNS,
            declared_fields=declared,
            industry=industry,
            default_sort_key=ENTITY_SORT_KEY,
        )

    async def event_rows(self, request: GridRowsRequest) -> GridRowsResponse:
        """
        Read one block of inventory rows, already flattened into the shape the column definitions address.

        :param request: Query the grid data source sent for the block.
        :return: The rows of the block together with the total amount of matching events.
        """
        documents, total = await self._event_repository.search(search=request)

        return GridRowsResponse(
            rows=[event_row(document=document) for document in documents],
            total=total,
            page=request.page,
            page_size=request.page_size,
            pages=ceil(total / request.page_size) if request.page_size else 0,
        )

    async def distinct_values(self, key: str) -> list[str]:
        """
        Read the values one column currently holds, so that the client can offer them as filter options.

        :param key: Key of the column the values are read for.
        :return: The values of the column ordered by how often they appear.
        """
        path = resolve_path(key=key, fixed_keys=FIXED_EVENT_KEYS)

        return await self._introspector.distinct_values(path=path, limit=DISTINCT_LIMIT)


# ----- FUNCTIONS ----- #


def event_row(document: EventDocument) -> dict[str, Any]:
    """
    Flatten one stored event into the row object the generated columns address.

    :param document: Event that is rendered as a row.
    :return: The row object of the event.
    """
    row: dict[str, Any] = to_jsonable_python(document.to_summary().model_dump())
    row["event_type_names"] = list(document.event_type_names)
    row["event_type_keys"] = list(document.event_type_keys)
    row[DYNAMIC_FIELD_PREFIX] = to_jsonable_python(document.data)

    return row


def entity_row(document: EntityDocument, event_id: str) -> dict[str, Any]:
    """
    Flatten one stored entity into the row object the generated columns address.

    :param document: Entity that is rendered as a row.
    :param event_id: Identifier of the event the entity belongs to.
    :return: The row object of the entity.
    """
    row: dict[str, Any] = to_jsonable_python(document.to_response(event_id=event_id).model_dump())
    row["object_type_name"] = document.object_type_name
    row["object_type_key"] = document.object_type_key
    row["files"] = row["raw_files"] + row["parsed_files"] + row["parsed_additional_files"]
    row[DYNAMIC_FIELD_PREFIX] = to_jsonable_python(document.data)

    return row
