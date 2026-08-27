"""
Translation of one field definition, declared or built in, into the AG Grid column definition the client renders.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skyscanner_models.enums import FieldType
from skyscanner_models.field import FieldResponse
from skyscanner_models.grid import ColumnDefinition, FilterOption

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
    cell_class: str | None = Field(default=None, description="Extra class applied to every body cell")
    header_class: str | None = Field(default=None, description="Extra class applied to the header cell")
    # A built in column whose values are a vocabulary the service knows says which one, and the generator
    # fills the values in - a platform and an industry are read out of the collections, while a fixed
    # enumeration such as a status is spelled out by the column itself.
    options: list[FilterOption] = Field(
        default_factory=list,
        description="Values the column is known to hold, offered by its filter instead of being typed",
    )
    options_source: str | None = Field(
        default=None,
        description="Name of the vocabulary the generator fills the options of this column in from",
    )
    quick_filter: bool = Field(default=False, description="Whether the column is offered as a quick filter")


# ----- FUNCTIONS ----- #


def column_from_spec(spec: BaseColumnSpec) -> ColumnDefinition:
    """
    Turn a built in column description into the definition handed to the grid.

    :param spec: Description of the built in column.
    :return: The generated column definition.
    """
    grid_filter = _resolve_filter(field_type=spec.field_type, filterable=spec.filterable, options=spec.options)

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
        cell_class=spec.cell_class,
        header_class=spec.header_class,
        auto_height=spec.auto_height,
        field_type=spec.field_type.value,
        dynamic=False,
        discovered=False,
        industry=None,
        filter_options=list(spec.options),
        quick_filter=spec.quick_filter and bool(spec.options),
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
    # A declared enum already carries the values it is allowed to hold, so its filter offers them.
    options = [FilterOption(value=option, label=option) for option in definition.metadata.options]
    grid_filter = _resolve_filter(
        field_type=definition.type,
        filterable=definition.filterable,
        options=options,
    )

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
        auto_height=definition.type is FieldType.FILE,
        field_type=definition.type.value,
        dynamic=True,
        discovered=definition.discovered,
        industry=definition.industry,
        filter_options=options,
        # A field somebody declared as an enum of three values is exactly the kind of thing a reader narrows
        # by every day, so it joins the quick filters beside the built in vocabularies.
        quick_filter=bool(options) and not definition.discovered,
    )


def _resolve_filter(field_type: FieldType, filterable: bool, options: list[FilterOption]) -> str | bool:
    """
    Pick the filter component of a column, which the values it may hold decide before its type does.

    A column whose vocabulary is written down is filtered by picking from that vocabulary, whatever the
    primitive type underneath happens to be - remembering that a platform is keyed `rig_a` and not `Rig A`
    is not something a table should ask of anybody. Everything else falls back to the type.

    :param field_type: Primitive type the column holds.
    :param filterable: Whether the column was declared filterable at all.
    :param options: Values the column is known to hold, empty when its values are not a vocabulary.
    :return: The name of the filter component, or false when the column carries no filter.
    """
    if not filterable:
        return False

    if options:
        return GridFilter.SET.value

    resolved = FIELD_TYPE_FILTERS.get(field_type, GridFilter.TEXT)
    if isinstance(resolved, GridFilter):
        return resolved.value

    return resolved
