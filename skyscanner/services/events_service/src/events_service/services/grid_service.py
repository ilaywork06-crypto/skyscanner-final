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
from skyscanner_models.grid import FilterOption, GridConfiguration, GridRowsRequest, GridRowsResponse

from events_service.constants import (
    ENTITY_BASE_COLUMNS,
    ENTITY_TYPE_VOCABULARY,
    EVENT_BASE_COLUMNS,
    EVENT_TYPE_VOCABULARY,
    FIXED_EVENT_KEYS,
    INDUSTRY_VOCABULARY,
    MODULE_VOCABULARY,
    PLATFORM_VOCABULARY,
)
from events_service.documents import EntityDocument, EventDocument
from events_service.repositories.event_repository import EventRepository
from events_service.repositories.industry_repository import IndustryRepository
from events_service.repositories.type_repository import TypeRepository
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
        type_repository: TypeRepository,
        industry_repository: IndustryRepository,
    ) -> None:
        """
        Bind the service to the sources of the columns and of the rows.

        :param event_repository: Persistence of the events the rows are read from.
        :param field_service: Owner of the declared dynamic schema.
        :param introspector: Reader of the keys that were written without a declaration.
        :param type_repository: Persistence of the declared types and platforms a filter offers.
        :param industry_repository: Persistence of the industries a filter offers.
        """
        self._event_repository = event_repository
        self._field_service = field_service
        self._introspector = introspector
        self._type_repository = type_repository
        self._industry_repository = industry_repository

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
            vocabularies=await self._event_vocabularies(industry=industry),
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
            vocabularies=await self._entity_vocabularies(industry=industry),
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

    async def _event_vocabularies(self, industry: str | None) -> dict[str, list[FilterOption]]:
        """
        Read the declared vocabularies the columns of the inventory are filtered by.

        A reader narrowing the table to one platform should be handed the platforms rather than asked to
        remember that "Rig A" is stored as `rig_a`, so the declarations behind those columns travel with the
        table. Filtering by an industry narrows the platforms and the types to the ones it was offered,
        exactly as the create wizard narrows them.

        :param industry: Industry the table is generated for, empty for the shared view of every industry.
        :return: The values of each vocabulary the built in columns name.
        """
        platforms = await self._type_repository.list_platforms(industry=industry)
        event_types = await self._type_repository.list_event_types(industry=industry)
        industries = await self._industry_repository.list_all()

        return {
            # An event stores the keys of the platforms it ran on and the names of the types it was filed
            # under, so each vocabulary is keyed by whatever its own column actually holds.
            PLATFORM_VOCABULARY: [
                FilterOption(value=document.key, label=document.name) for document in platforms
            ],
            EVENT_TYPE_VOCABULARY: [
                FilterOption(value=document.name, label=document.name) for document in event_types
            ],
            INDUSTRY_VOCABULARY: [
                FilterOption(value=document.key, label=document.name) for document in industries
            ],
        }

    async def _entity_vocabularies(self, industry: str | None) -> dict[str, list[FilterOption]]:
        """
        Read the declared vocabularies the columns of an entity table are filtered by.

        :param industry: Industry the table is generated for, empty for the shared view of every industry.
        :return: The values of each vocabulary the built in columns name.
        """
        entity_types = await self._type_repository.list_entity_types(industry=industry)
        modules = await self._modules_of(industry=industry)

        return {
            ENTITY_TYPE_VOCABULARY: [
                FilterOption(value=document.name, label=document.name) for document in entity_types
            ],
            MODULE_VOCABULARY: [FilterOption(value=module, label=module) for module in modules],
        }

    async def _modules_of(self, industry: str | None) -> list[str]:
        """
        Read the modules an entity may name, which is a vocabulary each industry declares for itself.

        The shared view of every industry is offered every declared module, since an entity of any of them
        may appear in it.

        :param industry: Industry the modules are read for, empty for the shared view of every industry.
        :return: The declared modules, each of them named once.
        """
        documents = await self._industry_repository.list_all()
        matching = [document for document in documents if industry is None or document.key == industry]
        collected: list[str] = []
        for document in matching:
            collected.extend(module for module in document.modules if module not in collected)

        return collected

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
    # Two columns rather than one folder tree: what came in raw, and everything the parsing produced. The
    # single list every file used to be read out of is kept beside them, because a saved view or a script
    # may still be addressing it.
    row["parsed_all_files"] = row["parsed_files"] + row["parsed_additional_files"]
    row["files"] = row["raw_files"] + row["parsed_all_files"]
    row[DYNAMIC_FIELD_PREFIX] = to_jsonable_python(document.data)

    return row
