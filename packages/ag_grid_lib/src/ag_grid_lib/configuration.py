"""
Assembly of a complete table configuration out of the built in columns and the fields an industry declared.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from hashlib import sha256

from skyscanner_models.enums import FieldScope, SortDirection
from skyscanner_models.field import FieldResponse
from skyscanner_models.grid import ColumnDefinition, FilterOption, GridConfiguration
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
    vocabularies: dict[str, list[FilterOption]] | None = None,
) -> GridConfiguration:
    """
    Merge the built in columns with the fields declared for an industry into one ordered table configuration.

    A built in column may name a vocabulary rather than spell one out - the platforms of an industry are a
    collection somebody writes to, not a list that can sit in the source - and the resolved vocabularies are
    handed in here so that the column definitions carry the values their filters offer.

    :param scope: Whether the table renders events or entities.
    :param base_columns: Built in columns that are always present.
    :param declared_fields: Field definitions that apply to the requested industry.
    :param industry: Industry the configuration is generated for, empty for the shared view.
    :param default_sort_key: Key the table is ordered by when the user did not choose an ordering.
    :param vocabularies: Resolved values of the vocabularies the built in columns name.
    :return: The complete configuration of the table.
    """
    resolved = vocabularies or {}
    ordered_specs = [_with_options(spec=spec, vocabularies=resolved) for spec in sorted(base_columns, key=_position)]
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


def _position(spec: BaseColumnSpec) -> int:
    """
    Read where one built in column stands in the table.

    :param spec: Description of the built in column.
    :return: The relative position of the column.
    """
    return spec.order


def _with_options(spec: BaseColumnSpec, vocabularies: dict[str, list[FilterOption]]) -> BaseColumnSpec:
    """
    Fill in the values of the vocabulary a built in column names, leaving every other column untouched.

    A column that names a vocabulary nobody has written a single entry into yet - an empty system, an
    industry with no platform declared - keeps no options at all and falls back to the filter of its type,
    rather than offering a list with nothing on it.

    :param spec: Description of the built in column.
    :param vocabularies: Resolved values of the vocabularies the built in columns name.
    :return: The column description with its options filled in.
    """
    if spec.options_source is None:
        return spec

    options = vocabularies.get(spec.options_source, [])
    if not options:
        return spec

    return spec.model_copy(update={"options": options})
