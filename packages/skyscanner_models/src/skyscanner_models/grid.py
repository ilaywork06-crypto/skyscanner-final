"""
Payloads of the generated grid configuration, so that the web client never hard codes a single column definition.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic.alias_generators import to_camel

from skyscanner_models.enums import FieldScope
from skyscanner_models.query import SearchQuery, SortSpecification

# ----- CLASSES ----- #


class ColumnDefinition(BaseModel):
    """
    One generated AG Grid column definition, serialised with the camel case names the grid expects.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    col_id: str = Field(description="Stable identifier of the column")
    field: str = Field(description="Path of the value inside the row object")
    header_name: str = Field(description="Label rendered in the header cell")
    sortable: bool = Field(default=True, description="Whether the column can be ordered by")
    filter: str | bool = Field(default=False, description="Name of the AG Grid filter component of the column")
    floating_filter: bool = Field(default=False, description="Whether a filter input is rendered under the header")
    resizable: bool = Field(default=True, description="Whether the column may be resized")
    hide: bool = Field(default=False, description="Whether the column starts hidden")
    editable: bool = Field(default=False, description="Whether the cell may be edited in place")
    flex: float | None = Field(default=None, description="Share of the free horizontal space taken by the column")
    min_width: float | None = Field(default=None, description="Smallest width the column may shrink to")
    max_width: float | None = Field(default=None, description="Largest width the column may grow to")
    width: float | None = Field(default=None, description="Fixed width of the column")
    pinned: str | None = Field(default=None, description="Side the column is pinned to, left or right")
    cell_renderer: str | None = Field(default=None, description="Registered renderer used for the cell body")
    cell_renderer_params: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Parameters handed over to the registered renderer",
    )
    cell_data_type: str | bool = Field(default=False, description="Data type hint given to the grid")
    header_class: str | None = Field(default=None, description="Extra class applied to the header cell")
    cell_class: str | None = Field(default=None, description="Extra class applied to every body cell")
    auto_height: bool = Field(default=False, description="Whether the row grows to fit the rendered content")
    field_type: str = Field(default="string", description="Primitive type the column was generated from")
    dynamic: bool = Field(default=False, description="Whether the column came from a user declared field")
    discovered: bool = Field(
        default=False,
        description="Whether the column was inferred from the stored documents rather than declared",
    )
    industry: str | None = Field(
        default=None,
        description="Industry owning the column, empty when the column is shared",
    )


class GridConfiguration(BaseModel):
    """
    The complete table configuration for one scope and industry, generated from the stored field definitions.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    scope: FieldScope = Field(default=FieldScope.EVENT, description="Whether the table renders events or entities")
    industry: str | None = Field(default=None, description="Industry the configuration was generated for")
    columns: list[ColumnDefinition] = Field(default_factory=list, description="Generated column definitions")
    default_sort: list[SortSpecification] = Field(default_factory=list, description="Ordering applied on first load")
    quick_filter_keys: list[str] = Field(default_factory=list, description="Keys the free text search looks at")
    row_height: float = Field(default=56, description="Height of a body row in pixels")
    header_height: float = Field(default=56, description="Height of the header row in pixels")
    version: str = Field(default="", description="Fingerprint of the configuration, used to invalidate caches")


class GridRowsRequest(SearchQuery):
    """
    The query the grid data source sends for one block of rows, extending the shared search payload.
    """

    columns: list[str] = Field(default_factory=list, description="Keys the caller wants materialised in the rows")


class EventExportRequest(GridRowsRequest):
    """
    The query behind an export, which is the current view of the table and optionally a hand picked subset of it.
    """

    event_ids: list[str] = Field(
        default_factory=list,
        description="Identifiers the export is narrowed to, empty to export the whole current view",
    )


class GridRowsResponse(BaseModel):
    """
    One block of grid rows together with the total amount of matching documents.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    rows: list[dict[str, JsonValue]] = Field(default_factory=list, description="Flattened documents of the block")
    total: int = Field(default=0, ge=0, description="Total amount of documents matching the query")
    page: int = Field(default=1, ge=1, description="One based index of the returned page")
    page_size: int = Field(default=50, ge=1, description="Amount of documents requested per page")
    pages: int = Field(default=0, ge=0, description="Total amount of pages available for the query")
