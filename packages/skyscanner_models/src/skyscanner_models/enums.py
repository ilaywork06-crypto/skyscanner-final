"""
Enumerations shared by every Skyscanner service, describing field types, life cycle states, roles and permissions.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from enum import Enum

# ----- CLASSES ----- #


class FieldType(str, Enum):
    """
    The primitive type a dynamic field holds, used both for validation and for the generated grid column.
    """

    STRING = "string"
    TEXT = "text"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ENUM = "enum"
    FILE = "file"
    JSON = "json"
    # A point on the globe, stored as a longitude, a latitude and an altitude rather than as free text, so
    # that it can be picked off a map and read back onto one.
    COORDINATE = "coordinate"


class FieldScope(str, Enum):
    """
    Declares whether a dynamic field is attached to an event document or to an entity nested inside an event.
    """

    EVENT = "event"
    ENTITY = "entity"


class EventStatus(str, Enum):
    """
    The life cycle state of an event, driving the coloured status chip shown in the events table.
    """

    DRAFT = "draft"
    RAW = "raw"
    PARSED = "parsed"
    PARTIAL = "partial"
    FAILED = "failed"
    ARCHIVED = "archived"


class ExperimentResult(str, Enum):
    """
    How the activity behind an event turned out, which is a different question from how far its files were processed.
    """

    SUCCESSFUL = "successful"
    PARTIAL = "partial"
    FAILED = "failed"


class EntityStatus(str, Enum):
    """
    The life cycle state of a single entity such as a telemetry or a log collection.
    """

    RAW = "raw"
    PARSING = "parsing"
    PARTIALLY_PARSED = "partially_parsed"
    PARSED = "parsed"
    FAILED = "failed"


class OptionalEventField(str, Enum):
    """
    A built in field of an event that only some event types ask for, switched on by the type declaration.

    The dynamic schema shapes the entities of an event, never the event form itself, so the built in fields
    that are not universal are named here and every event type says which of them it wants. An experiment
    result, for instance, only means anything for a type that describes an experiment.
    """

    REFERENCE_ID = "reference_id"
    EVENT_DATE = "event_date"
    EXPERIMENT_RESULT = "experiment_result"
    NOTES = "notes"


class ParseState(str, Enum):
    """
    The coarse parsed / not parsed toggle exposed by the "Show" selector above the events table.
    """

    ALL = "all"
    PARSED = "parsed"
    NOT_PARSED = "not_parsed"


class DependencyOperator(str, Enum):
    """
    How a field dependency tests the value of the field it depends on.
    """

    HAS_VALUE = "has_value"
    IS_EMPTY = "is_empty"
    EQUALS = "equals"
    ONE_OF = "one_of"
    NOT_EQUALS = "not_equals"


class RevisionTarget(str, Enum):
    """
    What a recorded edit changed, so that the history of an event and of its entities can be told apart.
    """

    EVENT = "event"
    ENTITY = "entity"


class ArtifactKind(str, Enum):
    """
    The role a stored file plays for the object it belongs to.
    """

    RAW = "raw"
    PARSED = "parsed"
    PARSED_ADDITIONAL = "parsed_additional"
    ADDITIONAL = "additional"


class UploadSource(str, Enum):
    """
    How a document reached the system, so that manual uploads can later be told apart from watchdog ingestion.
    """

    MANUAL = "manual"
    WATCHDOG = "watchdog"
    AUTOMATION = "automation"
    SCRIPT = "script"


class Role(str, Enum):
    """
    The coarse role handed over by the authenticating reverse proxy through the roles header.
    """

    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


class Permission(str, Enum):
    """
    A single capability inside the system, granted to a role and verified by the API dependency layer.
    """

    EVENT_READ = "event:read"
    EVENT_CREATE = "event:create"
    EVENT_UPDATE = "event:update"
    EVENT_DELETE = "event:delete"
    ENTITY_MANAGE = "entity:manage"
    FILE_UPLOAD = "file:upload"
    FILE_DOWNLOAD = "file:download"
    FIELD_MANAGE = "field:manage"
    TEMPLATE_MANAGE = "template:manage"
    INDUSTRY_MANAGE = "industry:manage"
    SUBSCRIPTION_MANAGE = "subscription:manage"


class SortDirection(str, Enum):
    """
    The direction applied to a single sort specification.
    """

    ASC = "asc"
    DESC = "desc"
