"""
Building blocks reused by most payloads - stored files, free form metadata attributes and the caller identity.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skyscanner_models.enums import ArtifactKind, FieldType, Permission, Role

# ----- CLASSES ----- #


class ObjectTypeReference(BaseModel):
    """
    A reference to a named type definition, kept denormalised so that a document stays readable on its own.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the type definition")
    name: str = Field(description="Human readable name of the type")


class Artifact(BaseModel):
    """
    A single file kept in the object storage and linked to an event or to one of its entities.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the artifact")
    name: str = Field(description="Original file name including its suffix")
    path: str = Field(description="Object storage key the file is stored under")
    descriptor: str = Field(default="", description="Free text describing what the file holds")
    kind: ArtifactKind = Field(default=ArtifactKind.ADDITIONAL, description="Role the file plays for its owner")
    suffix: str = Field(default="", description="File extension without the leading dot")
    folder: str | None = Field(default=None, description="Virtual folder used to group files in the table")
    source: str | None = Field(default=None, description="Where the file arrived from - a link, a path or an id")
    size_bytes: int = Field(default=0, ge=0, description="Size of the stored file in bytes")
    content_type: str = Field(default="application/octet-stream", description="Detected MIME type of the file")
    checksum: str | None = Field(default=None, description="MD5 checksum reported by the object storage")
    uploaded_by: str | None = Field(default=None, description="User that put the file into the object storage")
    created_at: datetime | None = Field(default=None, description="UTC moment the file was uploaded")
    updated_at: datetime | None = Field(default=None, description="UTC moment the file record last changed")


class Coordinate(BaseModel):
    """
    A single point on the globe, held as the three numbers a map picker hands back.

    The altitude is optional because a point picked off a map has no height to report, while one that came
    from a flight recorder does; nothing else about the value changes between the two.
    """

    model_config = ConfigDict(populate_by_name=True)

    lon: float = Field(ge=-180, le=180, description="Longitude of the point in decimal degrees")
    lat: float = Field(ge=-90, le=90, description="Latitude of the point in decimal degrees")
    alt: float | None = Field(default=None, description="Altitude of the point in metres above sea level")


class MetadataAttribute(BaseModel):
    """
    A dynamic key and value pair holding the value of a user defined field on an event or an entity.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Key of the dynamic field the value belongs to")
    value: JsonValue = Field(default=None, description="Value stored for the field")
    type: FieldType = Field(default=FieldType.STRING, description="Primitive type the value was declared with")


class UserContext(BaseModel):
    """
    The identity resolved from the headers injected by the authenticating reverse proxy.
    """

    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(default="anonymous", description="Login name of the caller")
    email: str | None = Field(default=None, description="Mail address of the caller")
    roles: list[Role] = Field(default_factory=list, description="Roles granted to the caller")
    industries: list[str] = Field(default_factory=list, description="Industry keys the caller belongs to")
    permissions: list[Permission] = Field(default_factory=list, description="Capabilities derived from the roles")


class OperationResult(BaseModel):
    """
    A tiny acknowledgement returned by endpoints that do not have a richer body to hand back.
    """

    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(default=True, description="Whether the requested operation completed")
    message: str = Field(default="", description="Human readable detail about the operation")
    affected: int = Field(default=0, ge=0, description="Number of documents the operation touched")
