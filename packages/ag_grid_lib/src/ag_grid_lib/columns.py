"""
Translation of one field definition, declared or built in, into the AG Grid column definition the client renders.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skyscanner_models.enums import FieldType
from skyscanner_models.field import FieldResponse
from skyscanner_models.grid import ColumnDefinition

from ag_grid_lib.constants import (
    DEFAULT_FLEX,
    DEFAULT_MIN_WIDTH,
    FIELD_TYPE_FILTERS,
    FIELD_TYPE_RENDERERS,
    CellRenderer,
    GridFilter,
)

# ----- CONSTS ----- #

DYNAMIC_FIELD_PREFIX: str = "data"

# ----- CLASSES ----- #


class BaseColumnSpec(BaseModel):
    """
    A built in column of a table, described in the very same shape a declared field is described in.
    """

    model_config = ConfigDict(populate_by_name=True)

    col_id: str = Field(description="Stable identifier of the column")
    field: str = Field(description="Path of the value inside the row object")
    header_name: str = Field(description="Label rendered in the header cell")
    field_type: FieldType = Field(default=FieldType.STRING, description="Primitive type the column holds")
    renderer: CellRenderer | None = Field(default=None, description="Renderer overriding the type default")
    renderer_params: dict[str, JsonValue] = Field(default_factory=dict, description="Parameters of the renderer")
    filterable: bool = Field(default=True, description="Whether the column offers a filter")
    sortable: bool = Field(default=True, description="Whether the column can be ordered by")
    hide: bool = Field(default=False, description="Whether the column starts hidden")
    flex: float | None = Field(default=DEFAULT_FLEX, description="Share of the free horizontal space")
    min_width: float | None = Field(default=DEFAULT_MIN_WIDTH, description="Smallest width the column may take")
    max_width: float | None = Field(default=None, description="Largest width the column may take")
    width: float | None = Field(default=None, description="Fixed width of the column")
    pinned: str | None = Field(default=None, description="Side the column is pinned to")
    auto_height: bool = Field(default=False, description="Whether the row grows to fit the rendered content")
    order: int = Field(default=10, description="Relative position of the column")
    tooltip_field: str | None = Field(default=None, description="Path of the value shown as the cell tooltip")


# ----- FUNCTIONS ----- #


def column_from_spec(spec: BaseColumnSpec) -> ColumnDefinition:
    """
    Turn a built in column description into the definition handed to the grid.

    :param spec: Description of the built in column.
    :return: The generated column definition.
    """
    grid_filter = _resolve_filter(field_type=spec.field_type, filterable=spec.filterable)

    return ColumnDefinition(
        col_id=spec.col_id,
        field=spec.field,
        header_name=spec.header_name,
        sortable=spec.sortable,
        filter=grid_filter,
        floating_filter=False,
        resizable=True,
        hide=spec.hide,
        editable=False,
        flex=spec.flex,
        min_width=spec.min_width,
        max_width=spec.max_width,
        width=spec.width,
        pinned=spec.pinned,
        cell_renderer=(spec.renderer or FIELD_TYPE_RENDERERS[spec.field_type]).value,
        cell_renderer_params=spec.renderer_params,
        cell_data_type=False,
        tooltip_field=spec.tooltip_field,
        auto_height=spec.auto_height,
        field_type=spec.field_type.value,
        dynamic=False,
        industry=None,
    )


def column_from_field(definition: FieldResponse) -> ColumnDefinition:
    """
    Turn a field declared by an industry into the definition handed to the grid.

    :param definition: Field definition stored for the industry.
    :return: The generated column definition.
    """
    renderer = FIELD_TYPE_RENDERERS[definition.type]
    renderer_params: dict[str, JsonValue] = {
        "unit": definition.metadata.unit,
        "array": definition.array,
        "options": list(definition.metadata.options),
    }
    grid_filter = _resolve_filter(field_type=definition.type, filterable=definition.filterable)

    return ColumnDefinition(
        col_id=definition.key,
        field=f"{DYNAMIC_FIELD_PREFIX}.{definition.key}",
        header_name=definition.name,
        sortable=definition.sortable and not definition.array,
        filter=grid_filter,
        floating_filter=False,
        resizable=True,
        hide=not definition.visible,
        editable=False,
        flex=DEFAULT_FLEX,
        min_width=DEFAULT_MIN_WIDTH,
        max_width=None,
        width=None,
        pinned=None,
        cell_renderer=renderer.value,
        cell_renderer_params=renderer_params,
        cell_data_type=False,
        tooltip_field=None,
        auto_height=definition.type is FieldType.FILE,
        field_type=definition.type.value,
        dynamic=True,
        industry=definition.industry,
    )


def _resolve_filter(field_type: FieldType, filterable: bool) -> str | bool:
    """
    Pick the AG Grid filter component that matches a primitive type.

    :param field_type: Primitive type the column holds.
    :param filterable: Whether the column was declared filterable at all.
    :return: The name of the filter component, or false when the column carries no filter.
    """
    if not filterable:
        return False

    resolved = FIELD_TYPE_FILTERS.get(field_type, GridFilter.TEXT)
    if isinstance(resolved, GridFilter):
        return resolved.value

    return resolved
