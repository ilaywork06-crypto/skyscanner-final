"""
Names of the AG Grid filter components and of the cell renderers the web client registers for the generated columns.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from enum import Enum

from skyscanner_models.enums import FieldType

# ----- CLASSES ----- #


class GridFilter(str, Enum):
    """
    The AG Grid community filter components that a generated column may declare.
    """

    TEXT = "agTextColumnFilter"
    NUMBER = "agNumberColumnFilter"
    DATE = "agDateColumnFilter"


class CellRenderer(str, Enum):
    """
    The renderers the web client registers, keeping the visual language of the design in one place.
    """

    EVENT_LINK = "EventLinkCellRenderer"
    CHIP = "ChipCellRenderer"
    CHIP_LIST = "ChipListCellRenderer"
    STATUS = "StatusCellRenderer"
    DATE = "DateCellRenderer"
    FILES = "FilesCellRenderer"
    JSON = "JsonCellRenderer"
    BOOLEAN = "BooleanCellRenderer"
    TEXT = "TextCellRenderer"
    EXPAND = "ExpandCellRenderer"


# ----- CONSTS ----- #

FIELD_TYPE_FILTERS: dict[FieldType, GridFilter | bool] = {
    FieldType.STRING: GridFilter.TEXT,
    FieldType.TEXT: GridFilter.TEXT,
    FieldType.NUMBER: GridFilter.NUMBER,
    FieldType.INTEGER: GridFilter.NUMBER,
    FieldType.BOOLEAN: GridFilter.TEXT,
    FieldType.DATE: GridFilter.DATE,
    FieldType.DATETIME: GridFilter.DATE,
    FieldType.ENUM: GridFilter.TEXT,
    FieldType.FILE: False,
    FieldType.JSON: False,
}

FIELD_TYPE_RENDERERS: dict[FieldType, CellRenderer] = {
    FieldType.STRING: CellRenderer.TEXT,
    FieldType.TEXT: CellRenderer.TEXT,
    FieldType.NUMBER: CellRenderer.TEXT,
    FieldType.INTEGER: CellRenderer.TEXT,
    FieldType.BOOLEAN: CellRenderer.BOOLEAN,
    FieldType.DATE: CellRenderer.DATE,
    FieldType.DATETIME: CellRenderer.DATE,
    FieldType.ENUM: CellRenderer.CHIP,
    FieldType.FILE: CellRenderer.FILES,
    FieldType.JSON: CellRenderer.JSON,
}

DEFAULT_MIN_WIDTH: float = 120
DEFAULT_FLEX: float = 1
WIDE_MIN_WIDTH: float = 180
