"""
Generation of the AG Grid tables out of the stored schema, so that no column is ever hard coded in the web client.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from ag_grid_lib.columns import BaseColumnSpec, column_from_field, column_from_spec
from ag_grid_lib.configuration import build_grid_configuration, configuration_version
from ag_grid_lib.constants import CellRenderer, GridFilter
from ag_grid_lib.datasource import (
    DYNAMIC_VALUE_ROOT,
    build_mongo_filter,
    build_mongo_sort,
    build_text_search_filter,
)
from ag_grid_lib.introspection import SchemaIntrospector
