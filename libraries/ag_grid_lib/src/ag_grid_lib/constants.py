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
    The filter components a generated column may declare - the ones AG Grid ships with, and the one we do.

    A column whose values are a declared vocabulary is not filtered by typing a key from memory: the reader
    picks from the list the vocabulary already is. The community build of the grid carries no such filter, so
    the web client registers one and the backend names it here exactly as it names the built in ones.
    """

    TEXT = "agTextColumnFilter"
    NUMBER = "agNumberColumnFilter"
    DATE = "agDateColumnFilter"
    SET = "SetColumnFilter"


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
    COORDINATE = "CoordinateCellRenderer"
    OPEN_EVENT = "OpenEventCellRenderer"


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
    # A point is three numbers at once, so none of the single value filters can express a question about it.
    FieldType.COORDINATE: False,
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
    FieldType.COORDINATE: CellRenderer.COORDINATE,
}

DEFAULT_MIN_WIDTH: float = 120
DEFAULT_FLEX: float = 1
WIDE_MIN_WIDTH: float = 180

# The class a column of bookkeeping stamps carries, which is what sets it apart from the values a reader is
# actually here for: the moment sits at the end of its column, quieter than the columns around it.
STAMP_CELL_CLASS: str = "sky-cell--stamp"
STAMP_HEADER_CLASS: str = "sky-header--stamp"
