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
from skyscanner_models.enums import EventStatus, ExperimentResult, UploadSource

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
    industry: str | None = Field(default=None, description="Industry owning the type, empty when the type is shared")


class EventTypeCreateRequest(BaseModel):
    """
    The payload accepted when a new event type is declared for the system or for a single industry.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Machine key of the event type")
    name: str = Field(description="Label shown for the event type")
    description: str = Field(default="", description="Explanation of what the event type covers")
    industry: str | None = Field(default=None, description="Industry owning the type, empty when the type is shared")
    order: int = Field(default=100, description="Relative position of the type in the selectors")


class EventTypeUpdateRequest(BaseModel):
    """
    A partial update of an event type, where every omitted attribute keeps its stored value.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="New label of the event type")
    description: str | None = Field(default=None, description="New explanation of what the type covers")
    industry: str | None = Field(default=None, description="New industry owning the type")
    order: int | None = Field(default=None, description="New relative position of the type")


class EventCreateRequest(BaseModel):
    """
    The payload produced by the three steps of the create wizard, including the entities added in the last step.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="Name of the event, derived from the type when omitted")
    reference_id: str = Field(default="", description="Identifier the user knows the event by")
    event_type_keys: list[str] = Field(default_factory=list, description="Keys of the event types the event matches")
    industry: str = Field(description="Industry key the event belongs to")
    platform: str = Field(default="", description="Platform the event was produced on")
    status: EventStatus = Field(default=EventStatus.RAW, description="Initial life cycle state of the event")
    experiment_result: ExperimentResult | None = Field(default=None, description="How the activity itself turned out")
    event_date: datetime | None = Field(default=None, description="UTC moment the activity itself happened")
    notes: str = Field(default="", description="Free text information supplied by the user")
    upload_source: UploadSource = Field(default=UploadSource.MANUAL, description="How the event reached the system")
    additional_files: list[Artifact] = Field(default_factory=list, description="Files attached to the event itself")
    metadata: list[MetadataAttribute] = Field(default_factory=list, description="Values of the dynamic event fields")
    entities: list[EntityCreateRequest] = Field(default_factory=list, description="Entities created with the event")


class EventUpdateRequest(BaseModel):
    """
    A partial update of an event, letting the user fill in data that was only revealed after the upload.

    Every update is recorded in the history of the event, so it has to say why it was made. An automated
    caller supplies the reason the same way a person does, for example "imported from the parsing run".
    """

    model_config = ConfigDict(populate_by_name=True)

    reason: str = Field(min_length=1, description="Why the change is being made, kept in the edit history")
    name: str | None = Field(default=None, description="New name of the event")
    reference_id: str | None = Field(default=None, description="New identifier the user knows the event by")
    event_type_keys: list[str] | None = Field(default=None, description="Replacement list of event type keys")
    industry: str | None = Field(default=None, description="New industry key of the event")
    platform: str | None = Field(default=None, description="New platform of the event")
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
    platform: str = Field(default="", description="Platform the event was produced on")
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
