"""
The persistence shape of every collection of the events service and the projections handed back to the API layer.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.ids import new_id
from skyscanner_models.common import Artifact, MetadataAttribute, ObjectTypeReference
from skyscanner_models.entity import EntityResponse, EntityTypeResponse
from skyscanner_models.enums import (
    EntityStatus,
    EventStatus,
    ExperimentResult,
    FieldScope,
    FieldType,
    OptionalEventField,
    RevisionTarget,
    UploadSource,
)
from skyscanner_models.event import EventResponse, EventSummaryResponse, EventTypeResponse
from skyscanner_models.field import FieldConstraint, FieldDependency, FieldMetadata, FieldResponse
from skyscanner_models.query import FilterCondition, SortSpecification
from skyscanner_models.revision import FieldChange, RevisionResponse
from skyscanner_models.subscription import SubscriptionResponse, SubscriptionTrigger
from skyscanner_models.industry import IndustryResponse
from skyscanner_models.platform import PlatformResponse
from skyscanner_models.template import TemplateColumn, TemplateResponse

# ----- CLASSES ----- #


class SoftDeletable(BaseModel):
    """
    The marker every document and sub document that can be removed carries instead of being erased.

    Nothing is ever taken out of the document store: a removal writes this flag and every read leaves the
    flagged documents behind. That keeps the history, the exports and the file references of a removed
    object answerable, and it is the only way a deletion can be undone at all.
    """

    deleted: bool = Field(default=False, description="Whether the document was removed")
    deleted_at: datetime | None = Field(default=None, description="UTC moment the document was removed")
    deleted_by: str | None = Field(default=None, description="User that removed the document")


class EntityDocument(SoftDeletable):
    """
    One entity stored inside the objects list of an event, holding its file sets and its dynamic values.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, description="Identifier of the entity")
    object_id: int = Field(default=1, description="Running number of the entity inside its event")
    name: str = Field(default="", description="Name of the entity")
    object_type: ObjectTypeReference = Field(description="Type definition the entity is an instance of")
    object_type_name: str = Field(default="", description="Denormalised type name used by the table")
    object_type_key: str = Field(default="", description="Denormalised type key used to group the entities")
    module: str | None = Field(default=None, description="System or sensor module the entity came from")
    code_version: str | None = Field(default=None, description="Version of the code that produced the data")
    status: EntityStatus = Field(default=EntityStatus.RAW, description="Parsing state of the entity")
    notes: str = Field(default="", description="Free text information supplied by the user")
    upload_source: UploadSource = Field(default=UploadSource.MANUAL, description="How the entity reached the system")
    requested_at: datetime | None = Field(default=None, description="UTC moment the data was requested")
    received_at: datetime | None = Field(default=None, description="UTC moment the data was received")
    raw_files: list[Artifact] = Field(default_factory=list, description="Unparsed files of the entity")
    parsed_files: list[Artifact] = Field(default_factory=list, description="Parsed files of the entity")
    parsed_additional_files: list[Artifact] = Field(default_factory=list, description="Extra parsing products")
    metadata: list[MetadataAttribute] = Field(default_factory=list, description="Values of the dynamic entity fields")
    data: dict[str, Any] = Field(default_factory=dict, description="Flattened dynamic values used for queries")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the entity was created")
    updated_at: datetime | None = Field(default=None, description="UTC moment the entity last changed")
    created_by: str | None = Field(default=None, description="User that created the entity")
    updated_by: str | None = Field(default=None, description="User that last changed the entity")

    def to_response(self, event_id: str) -> EntityResponse:
        """
        Project the stored entity into the representation handed back by the API.

        :param event_id: Identifier of the event the entity belongs to.
        :return: The API representation of the entity.
        """
        return EntityResponse(
            id=self.id,
            object_id=self.object_id,
            name=self.name,
            event_id=event_id,
            object_type=self.object_type,
            object_type_key=self.object_type_key,
            module=self.module,
            code_version=self.code_version,
            status=self.status,
            notes=self.notes,
            upload_source=self.upload_source,
            requested_at=self.requested_at,
            received_at=self.received_at,
            raw_files=self.raw_files,
            parsed_files=self.parsed_files,
            parsed_additional_files=self.parsed_additional_files,
            metadata=self.metadata,
            created_at=self.created_at,
            updated_at=self.updated_at,
            created_by=self.created_by,
            updated_by=self.updated_by,
        )


class EventDocument(SoftDeletable):
    """
    One event of the inventory, carrying its own files, its dynamic values and every entity nested inside it.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the event")
    event_id: int = Field(default=0, description="Running number of the event inside the system")
    reference_id: str = Field(default="", description="Identifier the user knows the event by")
    name: str = Field(default="", description="Name of the event")
    event_type: list[ObjectTypeReference] = Field(default_factory=list, description="Types the event matches")
    event_type_names: list[str] = Field(default_factory=list, description="Denormalised type names for the table")
    event_type_keys: list[str] = Field(default_factory=list, description="Denormalised type keys used for filtering")
    industry: str = Field(default="", description="Industry key the event belongs to")
    platforms: list[str] = Field(default_factory=list, description="Keys of the platforms the event was produced on")
    status: EventStatus = Field(default=EventStatus.RAW, description="Life cycle state of the event")
    experiment_result: ExperimentResult | None = Field(default=None, description="How the activity itself turned out")
    event_date: datetime | None = Field(default=None, description="UTC moment the activity itself happened")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the event was uploaded")
    updated_at: datetime | None = Field(default=None, description="UTC moment the event last changed")
    notes: str = Field(default="", description="Free text information supplied by the user")
    additional_files: list[Artifact] = Field(default_factory=list, description="Files attached to the event itself")
    metadata: list[MetadataAttribute] = Field(default_factory=list, description="Values of the dynamic event fields")
    data: dict[str, Any] = Field(default_factory=dict, description="Flattened dynamic values used for queries")
    objects: list[EntityDocument] = Field(default_factory=list, description="Entities nested inside the event")
    entity_counts: dict[str, int] = Field(default_factory=dict, description="Amount of entities per entity type key")
    upload_source: UploadSource = Field(default=UploadSource.MANUAL, description="How the event reached the system")
    created_by: str | None = Field(default=None, description="User that uploaded the event")
    updated_by: str | None = Field(default=None, description="User that last changed the event")

    @property
    def live_objects(self) -> list["EntityDocument"]:
        """
        Read the entities of the event that were not removed, which is the only list anybody outside sees.

        :return: The entities still belonging to the event.
        """
        return [entity for entity in self.objects if not entity.deleted]

    def to_summary(self) -> EventSummaryResponse:
        """
        Project the stored event into the lightweight representation that feeds one row of the inventory grid.

        :return: The row representation of the event.
        """
        return EventSummaryResponse(
            id=self.id,
            event_id=self.event_id,
            reference_id=self.reference_id,
            name=self.name,
            event_type=self.event_type,
            industry=self.industry,
            platforms=list(self.platforms),
            status=self.status,
            experiment_result=self.experiment_result,
            event_date=self.event_date,
            created_at=self.created_at,
            updated_at=self.updated_at,
            notes=self.notes,
            additional_files=self.additional_files,
            metadata=self.metadata,
            entity_counts=self.entity_counts,
            created_by=self.created_by,
            updated_by=self.updated_by,
        )

    def to_response(self) -> EventResponse:
        """
        Project the stored event into the full representation used by the detail page.

        :return: The detail representation of the event.
        """
        summary = self.to_summary()

        return EventResponse(
            **summary.model_dump(),
            objects=[entity.to_response(event_id=self.id) for entity in self.live_objects],
            upload_source=self.upload_source,
        )


class RevisionDocument(BaseModel):
    """
    One recorded edit of an event or of one of its entities, kept forever so the history can be replayed.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the revision")
    target: RevisionTarget = Field(default=RevisionTarget.EVENT, description="What the edit changed")
    event_id: str = Field(description="Identifier of the event the edit belongs to")
    entity_id: str | None = Field(default=None, description="Identifier of the entity, empty for an event edit")
    entity_name: str = Field(default="", description="Name of the entity at the moment of the edit")
    version: int = Field(default=1, description="Running number of the edit for its target, starting at one")
    reason: str = Field(default="", description="Why the change was made")
    changed_by: str = Field(default="", description="User that made the change")
    changed_at: datetime = Field(default_factory=utc_now, description="UTC moment the change was made")
    changes: list[FieldChange] = Field(default_factory=list, description="Attributes the edit moved")

    def to_response(self) -> RevisionResponse:
        """
        Project the stored revision into the representation handed back by the API.

        :return: The API representation of the revision.
        """
        return RevisionResponse(
            id=self.id,
            target=self.target,
            event_id=self.event_id,
            entity_id=self.entity_id,
            entity_name=self.entity_name,
            version=self.version,
            reason=self.reason,
            changed_by=self.changed_by,
            changed_at=self.changed_at,
            changes=self.changes,
        )


class FieldDocument(SoftDeletable):
    """
    One dynamic field declaration, shaping the create wizard, the validation and the generated grid column.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the field definition")
    name: str = Field(description="Label shown to the user for the field")
    key: str = Field(description="Machine key the value is stored under")
    type: FieldType = Field(default=FieldType.STRING, description="Primitive type the field holds")
    array: bool = Field(default=False, description="Whether the field holds a list of values")
    default: JsonValue = Field(default=None, description="Value used when the user leaves the field empty")
    required: bool = Field(default=False, description="Whether a value has to be supplied")
    scope: FieldScope = Field(default=FieldScope.EVENT, description="Whether the field belongs to events or entities")
    industry: str | None = Field(
        default=None,
        description="Industry key owning the field, empty when the field is shared",
    )
    entity_type: str | None = Field(default=None, description="Entity type key the field is limited to")
    additional: bool = Field(default=False, description="Whether the field belongs to the additional data block")
    metadata: FieldMetadata = Field(default_factory=FieldMetadata, description="Rendering descriptors of the field")
    constraints: list[FieldConstraint] = Field(default_factory=list, description="Validation rules of the field")
    depends_on: list[FieldDependency] = Field(
        default_factory=list,
        description="Conditions on other fields that all have to hold before this field applies",
    )
    filterable: bool = Field(default=True, description="Whether the generated column offers a filter")
    sortable: bool = Field(default=True, description="Whether the generated column can be sorted")
    editable: bool = Field(default=True, description="Whether the value may be changed after creation")
    visible: bool = Field(default=True, description="Whether the generated column is shown by default")
    order: int = Field(default=100, description="Relative position of the generated column")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the field was declared")
    updated_at: datetime | None = Field(default=None, description="UTC moment the field last changed")
    created_by: str | None = Field(default=None, description="User that declared the field")

    def to_response(self) -> FieldResponse:
        """
        Project the stored field declaration into the representation handed back by the API.

        :return: The API representation of the field declaration.
        """
        return FieldResponse(**self.model_dump(by_alias=False))


class TypeDocument(SoftDeletable):
    """
    One declared event type or entity type, offered by the create wizard and shown as a tab on the event page.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the type")
    kind: str = Field(
        default="event",
        description="Whether the declaration describes an event, an entity or a platform",
    )
    key: str = Field(description="Machine key of the type")
    name: str = Field(description="Label shown for the type")
    description: str = Field(default="", description="Explanation of what the type covers")
    icon: str | None = Field(default=None, description="Icon name rendered next to the type")
    # A declaration may serve several industries at once, and one that names none is shared by all of them.
    industries: list[str] = Field(default_factory=list, description="Industries the declaration belongs to")
    fields: list[OptionalEventField] = Field(
        default_factory=list,
        description="Built in event fields an event type asks for, empty for the other kinds",
    )
    # The declared event fields an event type asks for, named by their key. A key whose declaration was
    # removed since is simply not offered any more, which is why nothing here is resolved on write.
    custom_fields: list[str] = Field(
        default_factory=list,
        description="Keys of the declared event fields an event type asks for, empty for the other kinds",
    )
    order: int = Field(default=100, description="Relative position of the type in the selectors")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the type was declared")

    def to_event_type(self) -> EventTypeResponse:
        """
        Project the stored type into the event type representation used by the create wizard.

        :return: The API representation of the event type.
        """
        return EventTypeResponse(
            id=self.id,
            key=self.key,
            name=self.name,
            description=self.description,
            industries=list(self.industries),
            fields=list(self.fields),
            custom_fields=list(self.custom_fields),
        )

    def to_entity_type(self) -> EntityTypeResponse:
        """
        Project the stored type into the entity type representation used by the event page tabs.

        :return: The API representation of the entity type.
        """
        return EntityTypeResponse(
            id=self.id,
            key=self.key,
            name=self.name,
            description=self.description,
            icon=self.icon,
            industries=list(self.industries),
        )

    def to_platform(self) -> PlatformResponse:
        """
        Project the stored declaration into the platform representation the wizard offers.

        :return: The API representation of the platform.
        """
        return PlatformResponse(
            id=self.id,
            key=self.key,
            name=self.name,
            description=self.description,
            industries=list(self.industries),
        )

    def to_reference(self) -> ObjectTypeReference:
        """
        Project the stored type into the denormalised reference kept inside the documents.

        :return: The reference stored next to an event or an entity.
        """
        return ObjectTypeReference(id=self.id, name=self.name)


class IndustryDocument(SoftDeletable):
    """
    One industry of the organisation, rendered as a tab above the inventory table and used to scope the schema.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the industry")
    key: str = Field(description="Machine key of the industry")
    name: str = Field(description="Label shown for the industry")
    description: str = Field(default="", description="Explanation of what the industry covers")
    color: str = Field(default="industryAmber", description="Theme colour token used for the industry chip")
    # The vocabulary an entity of this industry may name as its module. An industry that has not declared one
    # accepts any text, so an empty system keeps working before anybody sat down to define the list.
    modules: list[str] = Field(default_factory=list, description="Modules an entity of this industry may name")
    order: int = Field(default=100, description="Relative position of the industry tab")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the industry was registered")

    def to_response(self, event_count: int = 0) -> IndustryResponse:
        """
        Project the stored industry into the representation handed back by the API.

        :param event_count: Amount of events currently linked to the industry.
        :return: The API representation of the industry.
        """
        return IndustryResponse(
            id=self.id,
            key=self.key,
            name=self.name,
            description=self.description,
            color=self.color,
            modules=list(self.modules),
            event_count=event_count,
            created_at=self.created_at,
        )


class TemplateDocument(SoftDeletable):
    """
    One saved table layout, letting a user restore the columns, filters and ordering they work with.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the template")
    name: str = Field(description="Label the user gave the template")
    description: str = Field(default="", description="Explanation of what the template shows")
    scope: FieldScope = Field(default=FieldScope.EVENT, description="Whether the template targets events or entities")
    industry: str | None = Field(default=None, description="Industry the template belongs to, empty when it is global")
    owner: str = Field(default="anonymous", description="User that saved the template")
    shared: bool = Field(default=False, description="Whether other users may load the template")
    columns: list[TemplateColumn] = Field(default_factory=list, description="Presentation of every column")
    filters: list[FilterCondition] = Field(default_factory=list, description="Filters restored with the template")
    sort: list[SortSpecification] = Field(default_factory=list, description="Ordering restored with the template")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the template was saved")
    updated_at: datetime | None = Field(default=None, description="UTC moment the template last changed")

    def to_response(self) -> TemplateResponse:
        """
        Project the stored template into the representation handed back by the API.

        :return: The API representation of the template.
        """
        return TemplateResponse(**self.model_dump(by_alias=False))


class SubscriptionDocument(SoftDeletable):
    """
    One mail subscription, describing who wants to hear about which industry, event type or single event.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the subscription")
    owner: str = Field(default="anonymous", description="User the subscription belongs to")
    email: str = Field(description="Mail address the notifications are sent to")
    industry: str | None = Field(default=None, description="Industry followed by the subscription")
    event_id: str | None = Field(default=None, description="Single event followed by the subscription")
    event_type_key: str | None = Field(default=None, description="Event type followed by the subscription")
    triggers: list[SubscriptionTrigger] = Field(default_factory=list, description="Changes that make it fire")
    active: bool = Field(default=True, description="Whether the subscription currently sends mails")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the subscription was created")
    last_notified_at: datetime | None = Field(default=None, description="UTC moment the last mail was sent")

    def to_response(self) -> SubscriptionResponse:
        """
        Project the stored subscription into the representation handed back by the API.

        :return: The API representation of the subscription.
        """
        return SubscriptionResponse(**self.model_dump(by_alias=False))


class OutboxDocument(BaseModel):
    """
    One pending notification, written by the events service and picked up by the notification service.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the pending notification")
    trigger: SubscriptionTrigger = Field(description="Change that produced the notification")
    event_id: str = Field(description="Identifier of the event the notification is about")
    event_number: int = Field(default=0, description="Running number of the event the notification is about")
    event_name: str = Field(default="", description="Name of the event the notification is about")
    industry: str = Field(default="", description="Industry key of the event the notification is about")
    event_type_keys: list[str] = Field(default_factory=list, description="Type keys of the event")
    summary: str = Field(default="", description="Short sentence rendered in the body of the mail")
    attempts: int = Field(default=0, ge=0, description="Amount of rounds that tried to deliver the notification")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the notification was written")
    processed_at: datetime | None = Field(default=None, description="UTC moment the notification was sent")
