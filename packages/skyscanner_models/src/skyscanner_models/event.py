"""
Payloads for the events themselves - the inventory rows of the main table and the detail page of a single event.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from skyscanner_models.common import Artifact, MetadataAttribute, ObjectTypeReference
from skyscanner_models.entity import EntityCreateRequest, EntityResponse
from skyscanner_models.enums import EventStatus, ExperimentResult, OptionalEventField, UploadSource

# ----- CLASSES ----- #


class EventTypeResponse(BaseModel):
    """
    A declared event type, offered by the first step of the create wizard and shown as a chip in the table.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the event type")
    key: str = Field(description="Machine key of the event type")
    name: str = Field(description="Label shown for the event type")
    description: str = Field(default="", description="Explanation of what the event type covers")
    industries: list[str] = Field(
        default_factory=list,
        description="Industries the type belongs to, empty when the type is shared by all of them",
    )
    fields: list[OptionalEventField] = Field(
        default_factory=list,
        description="Built in event fields this type asks for on top of the ones every event carries",
    )
    custom_fields: list[str] = Field(
        default_factory=list,
        description="Keys of the declared event fields this type asks for on top of the built in ones",
    )


class EventTypeCreateRequest(BaseModel):
    """
    The payload accepted when a new event type is declared for the system or for a single industry.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Machine key of the event type")
    name: str = Field(description="Label shown for the event type")
    description: str = Field(default="", description="Explanation of what the event type covers")
    industries: list[str] = Field(
        default_factory=list,
        description="Industries the type belongs to, empty when the type is shared by all of them",
    )
    # An experiment result means nothing on a type that does not describe an experiment, which is exactly why
    # the built in fields a type asks for are declared rather than shown to everybody.
    fields: list[OptionalEventField] = Field(
        default_factory=list,
        description="Built in event fields this type asks for on top of the ones every event carries",
    )
    # The built in fields above are the ones the service itself understands, and their vocabulary is fixed.
    # Anything else an event ought to be asked for is declared as an event field of its own on the Schema
    # page, and a type names the ones it wants here - so a new question about an event costs a declaration
    # rather than a change to this enumeration and to every form that reads it.
    custom_fields: list[str] = Field(
        default_factory=list,
        description="Keys of the declared event fields this type asks for on top of the built in ones",
    )
    order: int = Field(default=100, description="Relative position of the type in the selectors")


class EventTypeUpdateRequest(BaseModel):
    """
    A partial update of an event type, where every omitted attribute keeps its stored value.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="New label of the event type")
    description: str | None = Field(default=None, description="New explanation of what the type covers")
    industries: list[str] | None = Field(default=None, description="New industries the type belongs to")
    fields: list[OptionalEventField] | None = Field(default=None, description="New built in fields the type asks for")
    custom_fields: list[str] | None = Field(default=None, description="New declared event fields the type asks for")
    order: int | None = Field(default=None, description="New relative position of the type")


class EventCreateRequest(BaseModel):
    """
    The payload produced by the two steps of the create wizard, including the entities added in the last step.
    """

    model_config = ConfigDict(populate_by_name=True)

    # The brief an event is listed and searched by. It is optional: an uploader who does not write one gets
    # one written for them out of what the event already says about itself - its type, its platforms, its
    # industry and its date - so that a missing brief never stands between anybody and a filed event.
    name: str | None = Field(
        default=None,
        description="Brief of the event, generated from its type, platforms, industry and date when omitted",
    )
    reference_id: str = Field(default="", description="Identifier the user knows the event by")
    event_type_keys: list[str] = Field(default_factory=list, description="Keys of the event types the event matches")
    industry: str = Field(description="Industry key the event belongs to")
    platforms: list[str] = Field(default_factory=list, description="Keys of the platforms the event was produced on")
    status: EventStatus = Field(default=EventStatus.RAW, description="Initial life cycle state of the event")
    experiment_result: ExperimentResult | None = Field(default=None, description="How the activity itself turned out")
    event_date: datetime | None = Field(default=None, description="UTC moment the activity itself happened")
    notes: str = Field(default="", description="Free text information supplied by the user")
    upload_source: UploadSource = Field(default=UploadSource.MANUAL, description="How the event reached the system")
    additional_files: list[Artifact] = Field(default_factory=list, description="Files attached to the event itself")
    metadata: list[MetadataAttribute] = Field(
        default_factory=list,
        description="Free values written onto the event, which only an automated caller supplies",
    )
    entities: list[EntityCreateRequest] = Field(default_factory=list, description="Entities created with the event")


class EventUpdateRequest(BaseModel):
    """
    A partial update of an event, letting the user fill in data that was only revealed after the upload.

    Every update is recorded in the history of the event, so it has to say why it was made. An automated
    caller supplies the reason the same way a person does, for example "imported from the parsing run".
    """

    model_config = ConfigDict(populate_by_name=True)

    reason: str = Field(min_length=1, description="Why the change is being made, kept in the edit history")
    name: str | None = Field(
        default=None,
        description="New brief of the event, regenerated from the convention when it is handed over empty",
    )
    reference_id: str | None = Field(default=None, description="New identifier the user knows the event by")
    event_type_keys: list[str] | None = Field(default=None, description="Replacement list of event type keys")
    industry: str | None = Field(default=None, description="New industry key of the event")
    platforms: list[str] | None = Field(default=None, description="Replacement list of platform keys")
    status: EventStatus | None = Field(default=None, description="New life cycle state of the event")
    experiment_result: ExperimentResult | None = Field(default=None, description="New outcome of the activity")
    event_date: datetime | None = Field(default=None, description="New UTC moment the activity happened")
    notes: str | None = Field(default=None, description="New free text information of the event")
    additional_files: list[Artifact] | None = Field(default=None, description="Replacement list of attached files")
    metadata: list[MetadataAttribute] | None = Field(default=None, description="Replacement dynamic field values")


class EventSummaryResponse(BaseModel):
    """
    The lightweight representation of an event that feeds one row of the inventory grid.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the event")
    event_id: int = Field(description="Running number of the event inside the system")
    reference_id: str = Field(default="", description="Identifier the user knows the event by")
    name: str = Field(description="Name of the event")
    event_type: list[ObjectTypeReference] = Field(default_factory=list, description="Types the event matches")
    industry: str = Field(description="Industry key the event belongs to")
    platforms: list[str] = Field(default_factory=list, description="Keys of the platforms the event was produced on")
    status: EventStatus = Field(default=EventStatus.RAW, description="Life cycle state of the event")
    experiment_result: ExperimentResult | None = Field(default=None, description="How the activity itself turned out")
    event_date: datetime | None = Field(default=None, description="UTC moment the activity itself happened")
    created_at: datetime = Field(description="UTC moment the event was uploaded")
    updated_at: datetime | None = Field(default=None, description="UTC moment the event last changed")
    notes: str = Field(default="", description="Free text information supplied by the user")
    additional_files: list[Artifact] = Field(default_factory=list, description="Files attached to the event itself")
    metadata: list[MetadataAttribute] = Field(default_factory=list, description="Values of the dynamic event fields")
    entity_counts: dict[str, int] = Field(default_factory=dict, description="Amount of entities per entity type key")
    created_by: str | None = Field(default=None, description="User that uploaded the event")
    updated_by: str | None = Field(default=None, description="User that last changed the event")


class EventResponse(EventSummaryResponse):
    """
    The full representation of a single event, adding the entities that are nested inside it.
    """

    objects: list[EntityResponse] = Field(default_factory=list, description="Entities nested inside the event")
    upload_source: UploadSource = Field(default=UploadSource.MANUAL, description="How the event reached the system")
