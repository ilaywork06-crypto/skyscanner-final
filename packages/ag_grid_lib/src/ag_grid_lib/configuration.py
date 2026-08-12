"""
Assembly of a complete table configuration out of the built in columns and the fields an industry declared.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from hashlib import sha256

from skyscanner_models.enums import FieldScope, SortDirection
from skyscanner_models.field import FieldResponse
from skyscanner_models.grid import ColumnDefinition, GridConfiguration
from skyscanner_models.query import SortSpecification

from ag_grid_lib.columns import BaseColumnSpec, column_from_field, column_from_spec

# ----- CONSTS ----- #

VERSION_LENGTH: int = 16
ROW_HEIGHT: float = 56
HEADER_HEIGHT: float = 56

# ----- FUNCTIONS ----- #


def configuration_version(columns: list[ColumnDefinition]) -> str:
    """
    Fingerprint a set of columns so that the client can tell a changed schema from an unchanged one.

    :param columns: Columns the configuration is made of.
    :return: A short stable fingerprint of the configuration.
    """
    payload = "|".join(f"{column.col_id}:{column.field_type}:{int(column.hide)}" for column in columns)

    return sha256(payload.encode("utf-8")).hexdigest()[:VERSION_LENGTH]


def build_grid_configuration(
    scope: FieldScope,
    base_columns: list[BaseColumnSpec],
    declared_fields: list[FieldResponse],
    industry: str | None = None,
    default_sort_key: str = "created_at",
) -> GridConfiguration:
    """
    Merge the built in columns with the fields declared for an industry into one ordered table configuration.

    :param scope: Whether the table renders events or entities.
    :param base_columns: Built in columns that are always present.
    :param declared_fields: Field definitions that apply to the requested industry.
    :param industry: Industry the configuration is generated for, empty for the shared view.
    :param default_sort_key: Key the table is ordered by when the user did not choose an ordering.
    :return: The complete configuration of the table.
    """
    ordered_specs = sorted(base_columns, key=lambda spec: spec.order)
    generated: list[ColumnDefinition] = [column_from_spec(spec) for spec in ordered_specs]

    ordered_fields = sorted(declared_fields, key=lambda declared: (declared.order, declared.name))
    generated.extend(column_from_field(declared) for declared in ordered_fields)

    quick_filter_keys = [column.field for column in generated if column.field_type in {"string", "text", "enum"}]

    return GridConfiguration(
        scope=scope,
        industry=industry,
        columns=generated,
        default_sort=[SortSpecification(key=default_sort_key, direction=SortDirection.DESC)],
        quick_filter_keys=quick_filter_keys,
        row_height=ROW_HEIGHT,
        header_height=HEADER_HEIGHT,
        version=configuration_version(generated),
    )
