"""
Payloads for the entities nested inside an event, such as telemetries and log collections, and their file sets.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from skyscanner_models.common import Artifact, MetadataAttribute, ObjectTypeReference
from skyscanner_models.enums import EntityStatus, UploadSource

# ----- CLASSES ----- #


class EntityTypeResponse(BaseModel):
    """
    A declared entity type such as telemetry or logs, used to build the tabs of the event page.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the entity type")
    key: str = Field(description="Machine key of the entity type")
    name: str = Field(description="Label shown for the entity type")
    description: str = Field(default="", description="Explanation of what the entity type holds")
    icon: str | None = Field(default=None, description="Icon name rendered next to the entity type")
    industries: list[str] = Field(
        default_factory=list,
        description="Industries the type belongs to, empty when the type is shared by all of them",
    )


class EntityTypeCreateRequest(BaseModel):
    """
    The payload accepted when a new entity type is declared for the system or for a single industry.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Machine key of the entity type")
    name: str = Field(description="Label shown for the entity type")
    description: str = Field(default="", description="Explanation of what the entity type holds")
    icon: str | None = Field(default=None, description="Icon name rendered next to the entity type")
    industries: list[str] = Field(
        default_factory=list,
        description="Industries the type belongs to, empty when the type is shared by all of them",
    )
    order: int = Field(default=100, description="Relative position of the type in the selectors")


class EntityTypeUpdateRequest(BaseModel):
    """
    A partial update of an entity type, where every omitted attribute keeps its stored value.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="New label of the entity type")
    description: str | None = Field(default=None, description="New explanation of what the type holds")
    icon: str | None = Field(default=None, description="New icon rendered next to the entity type")
    industries: list[str] | None = Field(default=None, description="New industries the type belongs to")
    order: int | None = Field(default=None, description="New relative position of the type")


class EntityCreateRequest(BaseModel):
    """
    The payload accepted when an entity is attached to an event, either during creation or afterwards.
    """

    model_config = ConfigDict(populate_by_name=True)

    # A nameless entity cannot be told apart from the next one in any table or file tree, and an accidental
    # double click on the add button used to produce exactly that, so the name is asked for.
    name: str = Field(min_length=1, description="Name of the entity")
    entity_type_key: str = Field(description="Key of the entity type the entity is an instance of")
    module: str | None = Field(default=None, description="System or sensor module the entity came from")
    code_version: str | None = Field(default=None, description="Version of the code that produced the data")
    status: EntityStatus = Field(default=EntityStatus.RAW, description="Parsing state of the entity")
    notes: str = Field(default="", description="Free text information supplied by the user")
    upload_source: UploadSource = Field(default=UploadSource.MANUAL, description="How the entity reached the system")
    requested_at: datetime | None = Field(default=None, description="UTC moment the data was requested")
    received_at: datetime | None = Field(default=None, description="UTC moment the data was received")
    raw_files: list[Artifact] = Field(default_factory=list, description="Unparsed files of the entity")
    parsed_files: list[Artifact] = Field(default_factory=list, description="Parsed files of the entity")
    parsed_additional_files: list[Artifact] = Field(
        default_factory=list,
        description="Extra products of the parsing such as statistics or plots",
    )
    metadata: list[MetadataAttribute] = Field(default_factory=list, description="Values of the dynamic entity fields")


class EntityUpdateRequest(BaseModel):
    """
    A partial update of an entity, where every omitted attribute keeps its stored value.

    Every update is recorded in the history of the entity, so it has to say why it was made.
    """

    model_config = ConfigDict(populate_by_name=True)

    reason: str = Field(min_length=1, description="Why the change is being made, kept in the edit history")
    name: str | None = Field(default=None, description="New name of the entity")
    module: str | None = Field(default=None, description="New system or sensor module the entity came from")
    code_version: str | None = Field(default=None, description="New version of the producing code")
    status: EntityStatus | None = Field(default=None, description="New parsing state of the entity")
    notes: str | None = Field(default=None, description="New free text information of the entity")
    requested_at: datetime | None = Field(default=None, description="New UTC moment the data was requested")
    received_at: datetime | None = Field(default=None, description="New UTC moment the data was received")
    raw_files: list[Artifact] | None = Field(default=None, description="Replacement list of unparsed files")
    parsed_files: list[Artifact] | None = Field(default=None, description="Replacement list of parsed files")
    parsed_additional_files: list[Artifact] | None = Field(
        default=None,
        description="Replacement list of extra parsing products",
    )
    metadata: list[MetadataAttribute] | None = Field(default=None, description="Replacement dynamic field values")


class EntityResponse(BaseModel):
    """
    A stored entity of an event together with every file set and dynamic value attached to it.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the entity")
    object_id: int = Field(description="Running number of the entity inside its event")
    name: str = Field(description="Name of the entity")
    event_id: str = Field(description="Identifier of the event the entity belongs to")
    object_type: ObjectTypeReference = Field(description="Type definition the entity is an instance of")
    object_type_key: str = Field(default="", description="Key of the entity type, which selects the schema of the row")
    module: str | None = Field(default=None, description="System or sensor module the entity came from")
    code_version: str | None = Field(default=None, description="Version of the code that produced the data")
    status: EntityStatus = Field(default=EntityStatus.RAW, description="Parsing state of the entity")
    notes: str = Field(default="", description="Free text information supplied by the user")
    upload_source: UploadSource = Field(default=UploadSource.MANUAL, description="How the entity reached the system")
    requested_at: datetime | None = Field(default=None, description="UTC moment the data was requested")
    received_at: datetime | None = Field(default=None, description="UTC moment the data was received")
    raw_files: list[Artifact] = Field(default_factory=list, description="Unparsed files of the entity")
    parsed_files: list[Artifact] = Field(default_factory=list, description="Parsed files of the entity")
    parsed_additional_files: list[Artifact] = Field(
        default_factory=list,
        description="Extra products of the parsing such as statistics or plots",
    )
    metadata: list[MetadataAttribute] = Field(default_factory=list, description="Values of the dynamic entity fields")
    created_at: datetime = Field(description="UTC moment the entity was created")
    updated_at: datetime | None = Field(default=None, description="UTC moment the entity last changed")
    created_by: str | None = Field(default=None, description="User that created the entity")
    updated_by: str | None = Field(default=None, description="User that last changed the entity")
