"""
The fixed vocabulary of the events service - collection names, queryable attributes and the built in table columns.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from enum import Enum
from typing import Type

from ag_grid_lib.columns import BaseColumnSpec
from ag_grid_lib.constants import STAMP_CELL_CLASS, STAMP_HEADER_CLASS, CellRenderer

from skyscanner_common.text import humanize_key
from skyscanner_models.enums import EntityStatus, EventStatus, ExperimentResult, FieldType, UploadSource
from skyscanner_models.grid import FilterOption

# ----- CONSTS ----- #

SERVICE_NAME: str = "events-service"

EVENTS_COLLECTION: str = "events"
FIELDS_COLLECTION: str = "fields"
INDUSTRIES_COLLECTION: str = "industries"
TYPES_COLLECTION: str = "types"
TEMPLATES_COLLECTION: str = "templates"
SUBSCRIPTIONS_COLLECTION: str = "subscriptions"
COUNTERS_COLLECTION: str = "counters"
OUTBOX_COLLECTION: str = "notification_outbox"
REVISIONS_COLLECTION: str = "revisions"

EVENT_ID_COUNTER: str = "event_id"

EVENT_TYPE_KIND: str = "event"
ENTITY_TYPE_KIND: str = "entity"
# A platform is declared exactly like a type is - a key, a label and the industries it belongs to - so it
# shares their collection and their service instead of growing a second copy of all three layers.
PLATFORM_TYPE_KIND: str = "platform"

FIXED_EVENT_KEYS: frozenset[str] = frozenset(
    {
        "id",
        "event_id",
        "reference_id",
        "name",
        "event_type_names",
        "industry",
        "platforms",
        "status",
        "experiment_result",
        "event_date",
        "created_at",
        "updated_at",
        "notes",
        "created_by",
        "updated_by",
        "upload_source",
        "additional_files",
    },
)

FIXED_ENTITY_KEYS: frozenset[str] = frozenset(
    {
        "id",
        "object_id",
        "name",
        "object_type_name",
        "module",
        "code_version",
        "status",
        "notes",
        "requested_at",
        "received_at",
        "created_at",
        "updated_at",
        "upload_source",
    },
)

EVENT_SEARCH_PATHS: list[str] = [
    "name",
    "reference_id",
    "notes",
    "industry",
    "platforms",
    "status",
    "event_type_names",
    "objects.name",
    "objects.module",
    "objects.notes",
    "additional_files.name",
]

# What a column holding a moment and its time needs before the value it renders is cut short.
DATETIME_MIN_WIDTH: float = 190

# The same moment written the short way - 26/08/26, 14:32 - which is what the bookkeeping stamps of the
# entity table are rendered as. They are the least read columns of that table and used to take the two
# widest places in it, pushing the values a reader actually opened the row for off the side of the screen.
COMPACT_DATETIME_MIN_WIDTH: float = 132

# The vocabularies the built in columns name rather than spell out, because each of them is a collection
# somebody writes to rather than a list that could sit in this file. The grid service resolves them.
PLATFORM_VOCABULARY: str = "platforms"
INDUSTRY_VOCABULARY: str = "industries"
EVENT_TYPE_VOCABULARY: str = "event_types"
ENTITY_TYPE_VOCABULARY: str = "entity_types"
MODULE_VOCABULARY: str = "modules"


def enum_options(values: Type[Enum]) -> list[FilterOption]:
    """
    Offer a fixed enumeration as the values a filter picks from.

    A status is stored as a key and read out as a label, so the filter offers both: the reader picks
    "Not parsed" and the query is written against the key that was actually stored.

    :param values: Enumeration the column is allowed to hold.
    :return: One option per member of the enumeration.
    """
    return [FilterOption(value=str(member.value), label=humanize_key(str(member.value))) for member in values]


EVENT_BASE_COLUMNS: list[BaseColumnSpec] = [
    BaseColumnSpec(
        col_id="expander",
        field="id",
        header_name="",
        renderer=CellRenderer.EXPAND,
        filterable=False,
        sortable=False,
        flex=None,
        min_width=None,
        width=64,
        pinned="left",
        order=10,
    ),
    # The identity of an event is three separate things and each of them gets its own column: the number the
    # system minted, the name it was given, and the identifier the user knows it by. They lead the table
    # because a reader identifies the row before asking anything else about it, and both the number and the
    # name lead to the event page, because the name is what a reader actually recognises and clicks.
    BaseColumnSpec(
        col_id="event_id",
        field="event_id",
        header_name="EVENT ID",
        renderer=CellRenderer.EVENT_LINK,
        field_type=FieldType.INTEGER,
        min_width=120,
        flex=0.6,
        order=20,
    ),
    # The short line an event is listed and recognised by. It is stored as the name of the event and always
    # was; what changed is what it is called on screen, because a reader writes a brief of what happened
    # rather than a name for it.
    BaseColumnSpec(
        col_id="name",
        field="name",
        header_name="EVENT BRIEF",
        renderer=CellRenderer.EVENT_LINK,
        renderer_params={"display": "name"},
        min_width=170,
        flex=1.2,
        order=30,
    ),
    BaseColumnSpec(
        col_id="reference_id",
        field="reference_id",
        header_name="REFERENCE ID",
        renderer=CellRenderer.TEXT,
        min_width=140,
        order=40,
    ),
    # How far an event was processed is the next question after which event this is, so the status follows the
    # identity rather than sitting at the far end of a horizontal scroll.
    BaseColumnSpec(
        col_id="status",
        field="status",
        header_name="STATUS",
        renderer=CellRenderer.STATUS,
        field_type=FieldType.ENUM,
        options=enum_options(EventStatus),
        quick_filter=True,
        min_width=140,
        order=50,
    ),
    # How the activity turned out is a different question from how far its files were processed, so the
    # outcome sits in its own column next to the parsing status rather than inside it.
    BaseColumnSpec(
        col_id="experiment_result",
        field="experiment_result",
        header_name="RESULT",
        renderer=CellRenderer.STATUS,
        renderer_params={"palette": "experiment"},
        field_type=FieldType.ENUM,
        options=enum_options(ExperimentResult),
        quick_filter=True,
        min_width=140,
        order=60,
    ),
    BaseColumnSpec(
        col_id="event_type_names",
        field="event_type_names",
        header_name="EVENT TYPE",
        renderer=CellRenderer.CHIP_LIST,
        renderer_params={"variant": "plain"},
        field_type=FieldType.ENUM,
        options_source=EVENT_TYPE_VOCABULARY,
        quick_filter=True,
        min_width=150,
        order=70,
    ),
    BaseColumnSpec(
        col_id="industry",
        field="industry",
        header_name="INDUSTRY",
        renderer=CellRenderer.CHIP,
        renderer_params={"palette": "industry"},
        field_type=FieldType.ENUM,
        options_source=INDUSTRY_VOCABULARY,
        quick_filter=True,
        min_width=140,
        order=80,
    ),
    # An event may have run on more than one platform, so the column paints the whole list rather than a
    # single chip, and the values are the keys of the platforms declared on the Types page.
    BaseColumnSpec(
        col_id="platforms",
        field="platforms",
        header_name="PLATFORM",
        renderer=CellRenderer.CHIP_LIST,
        renderer_params={"palette": "platform"},
        field_type=FieldType.ENUM,
        options_source=PLATFORM_VOCABULARY,
        quick_filter=True,
        min_width=140,
        order=90,
    ),
    BaseColumnSpec(
        col_id="event_date",
        field="event_date",
        header_name="EVENT DATE",
        renderer=CellRenderer.DATE,
        field_type=FieldType.DATETIME,
        min_width=150,
        order=100,
    ),
    BaseColumnSpec(
        col_id="additional_files",
        field="additional_files",
        header_name="ADDITIONAL FILES",
        renderer=CellRenderer.FILES,
        field_type=FieldType.FILE,
        filterable=False,
        sortable=False,
        auto_height=True,
        min_width=210,
        flex=1.4,
        order=110,
    ),
    # The information of an event is free text and carries no list rendering, which is what tells it apart
    # from the notes of an entity: those are typed as a list of items and say so through their renderer.
    BaseColumnSpec(
        col_id="notes",
        field="notes",
        header_name="INFO",
        renderer=CellRenderer.TEXT,
        field_type=FieldType.TEXT,
        min_width=140,
        order=120,
    ),
    # A moment rendered with its time reads as 26/08/2026, 14:32 - seventeen characters, which is wider than
    # the room a column of a hundred and sixty pixels has left once its padding is taken off. Every column
    # that carries one is therefore given the width its own value needs rather than the width of its header.
    BaseColumnSpec(
        col_id="created_at",
        field="created_at",
        header_name="CREATED AT",
        renderer=CellRenderer.DATE,
        field_type=FieldType.DATETIME,
        renderer_params={"withTime": True},
        min_width=DATETIME_MIN_WIDTH,
        order=130,
    ),
    BaseColumnSpec(
        col_id="updated_at",
        field="updated_at",
        header_name="UPDATED AT",
        renderer=CellRenderer.DATE,
        field_type=FieldType.DATETIME,
        renderer_params={"withTime": True},
        min_width=DATETIME_MIN_WIDTH,
        order=140,
    ),
    # Every event is a page of its own, and the only way into it used to be knowing that the number and the
    # brief are links. Nothing on a row said so, so a reader who did not happen to click one of those two
    # cells never found the page at all. The arrow says it: it is pinned to the end of the row, where the
    # eye lands after reading it, and it leads exactly where the two links do.
    BaseColumnSpec(
        col_id="open",
        field="id",
        header_name="",
        renderer=CellRenderer.OPEN_EVENT,
        filterable=False,
        sortable=False,
        flex=None,
        min_width=None,
        width=56,
        pinned="right",
        order=150,
    ),
]

ENTITY_BASE_COLUMNS: list[BaseColumnSpec] = [
    BaseColumnSpec(
        col_id="expander",
        field="id",
        header_name="",
        renderer=CellRenderer.EXPAND,
        filterable=False,
        sortable=False,
        flex=None,
        min_width=None,
        width=44,
        order=10,
        pinned="left",
    ),
    # The entities of an event are worked through raw first and parsed later, so how far one of them got is
    # what the reader looks for first and the status leads this table exactly as it leads the inventory.
    BaseColumnSpec(
        col_id="status",
        field="status",
        header_name="STATUS",
        renderer=CellRenderer.STATUS,
        field_type=FieldType.ENUM,
        options=enum_options(EntityStatus),
        min_width=110,
        order=20,
    ),
    BaseColumnSpec(
        col_id="name",
        field="name",
        header_name="NAME",
        renderer=CellRenderer.TEXT,
        min_width=130,
        order=30,
    ),
    # What an entity is and where its data came from is what a reader asks straight after which entity this
    # is, so the type and the module follow the name. The two stamps used to sit here instead, which put the
    # least interesting pair of columns in front of the two that say what the row actually holds.
    BaseColumnSpec(
        col_id="object_type_name",
        field="object_type_name",
        header_name="ENTITY TYPE",
        renderer=CellRenderer.TEXT,
        field_type=FieldType.ENUM,
        options_source=ENTITY_TYPE_VOCABULARY,
        min_width=110,
        order=40,
    ),
    # Module names the system or sensor the data came from, and its vocabulary is declared per industry, so
    # it renders as a chip out of a known set rather than as free text.
    BaseColumnSpec(
        col_id="module",
        field="module",
        header_name="MODULE",
        renderer=CellRenderer.CHIP,
        field_type=FieldType.ENUM,
        options_source=MODULE_VOCABULARY,
        min_width=110,
        order=50,
    ),
    BaseColumnSpec(
        col_id="code_version",
        field="code_version",
        header_name="CODE VERSION",
        renderer=CellRenderer.TEXT,
        min_width=110,
        order=60,
    ),
    # Raw first, parsed later is the whole life of an entity, and the one question a reader asks of this part
    # of the row is which half of that it has reached. The files therefore stand in two columns of their own,
    # side by side, rather than in one column of folders that had to be opened before it said anything. The
    # products of the parsing - the statistics, the plots - are parsed files as well and sit with them.
    BaseColumnSpec(
        col_id="raw_files",
        field="raw_files",
        header_name="RAW FILES",
        renderer=CellRenderer.FILES,
        renderer_params={"flat": True},
        field_type=FieldType.FILE,
        filterable=False,
        sortable=False,
        auto_height=True,
        min_width=150,
        flex=1.2,
        order=70,
    ),
    BaseColumnSpec(
        col_id="parsed_files",
        field="parsed_all_files",
        header_name="PARSED FILES",
        renderer=CellRenderer.FILES,
        renderer_params={"flat": True},
        field_type=FieldType.FILE,
        filterable=False,
        sortable=False,
        auto_height=True,
        min_width=150,
        flex=1.2,
        order=80,
    ),
    # The one column the two above replaced. It is kept, hidden, so that a saved view or a script that still
    # names it finds a column rather than nothing at all, and the row it reads still carries every file.
    BaseColumnSpec(
        col_id="files",
        field="files",
        header_name="ALL FILES",
        renderer=CellRenderer.FILES,
        field_type=FieldType.FILE,
        filterable=False,
        sortable=False,
        auto_height=True,
        min_width=180,
        flex=1.4,
        hide=True,
        order=90,
    ),
    # The notes of an entity are typed as a list of items and stored as one string whose items are separated
    # by line breaks, so the column says so and is rendered as the list it was written as. The information of
    # an event is free text and deliberately carries no such parameter.
    BaseColumnSpec(
        col_id="notes",
        field="notes",
        header_name="NOTES",
        renderer=CellRenderer.TEXT,
        renderer_params={"display": "list"},
        field_type=FieldType.TEXT,
        min_width=120,
        order=100,
    ),
    # When the row was written and when it last moved are bookkeeping: worth having, rarely what anybody is
    # reading the table for. They come after everything that describes the entity itself, they are written
    # the short way, and they carry the stamp class - which sets them at the end of their column behind the
    # mark of a date, quieter than the columns beside them, exactly as the event page reads its own dates.
    BaseColumnSpec(
        col_id="created_at",
        field="created_at",
        header_name="CREATED",
        renderer=CellRenderer.DATE,
        field_type=FieldType.DATETIME,
        renderer_params={"withTime": True, "stamp": True},
        cell_class=STAMP_CELL_CLASS,
        header_class=STAMP_HEADER_CLASS,
        min_width=COMPACT_DATETIME_MIN_WIDTH,
        flex=0.7,
        order=110,
    ),
    BaseColumnSpec(
        col_id="updated_at",
        field="updated_at",
        header_name="UPDATED",
        renderer=CellRenderer.DATE,
        field_type=FieldType.DATETIME,
        renderer_params={"withTime": True, "stamp": True},
        cell_class=STAMP_CELL_CLASS,
        header_class=STAMP_HEADER_CLASS,
        min_width=COMPACT_DATETIME_MIN_WIDTH,
        flex=0.7,
        order=120,
    ),
    # What produced the data and when it was asked for belong to the entity just as much as its name does.
    # They were readable only inside the edit dialog, so they are columns here like everything else, and the
    # ones a reader rarely needs start hidden rather than being absent.
    BaseColumnSpec(
        col_id="requested_at",
        field="requested_at",
        header_name="REQUESTED",
        renderer=CellRenderer.DATE,
        field_type=FieldType.DATETIME,
        renderer_params={"withTime": True, "stamp": True},
        cell_class=STAMP_CELL_CLASS,
        header_class=STAMP_HEADER_CLASS,
        min_width=COMPACT_DATETIME_MIN_WIDTH,
        flex=0.7,
        hide=True,
        order=130,
    ),
    BaseColumnSpec(
        col_id="received_at",
        field="received_at",
        header_name="RECEIVED",
        renderer=CellRenderer.DATE,
        field_type=FieldType.DATETIME,
        renderer_params={"withTime": True, "stamp": True},
        cell_class=STAMP_CELL_CLASS,
        header_class=STAMP_HEADER_CLASS,
        min_width=COMPACT_DATETIME_MIN_WIDTH,
        flex=0.7,
        hide=True,
        order=140,
    ),
    BaseColumnSpec(
        col_id="upload_source",
        field="upload_source",
        header_name="UPLOAD SOURCE",
        renderer=CellRenderer.CHIP,
        field_type=FieldType.ENUM,
        options=enum_options(UploadSource),
        min_width=130,
        hide=True,
        order=150,
    ),
    BaseColumnSpec(
        col_id="created_by",
        field="created_by",
        header_name="CREATED BY",
        renderer=CellRenderer.TEXT,
        min_width=120,
        hide=True,
        order=160,
    ),
    BaseColumnSpec(
        col_id="updated_by",
        field="updated_by",
        header_name="UPDATED BY",
        renderer=CellRenderer.TEXT,
        min_width=120,
        hide=True,
        order=170,
    ),
]
