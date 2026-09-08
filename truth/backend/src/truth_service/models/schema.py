"""
The payloads of the schemas, which declare what attributes an assumption carries.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from truth_service.models.common import IndustryReference, SchemeRequest, SchemeResponse

# ----- CLASSES ----- #


class SchemaSummaryResponse(BaseModel):
    """
    A schema as the listing hands it over, which is everything but the declaration itself.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of this revision of the schema")
    name: str = Field(description="Name of the schema")
    revision: int = Field(description="Running number of this revision")
    creator: str = Field(default="", description="User that wrote this revision")
    created_at: datetime | None = Field(default=None, description="UTC moment this revision was written")


class SchemaDetailResponse(SchemaSummaryResponse):
    """
    A schema read on its own, which carries the declaration and everything around it.
    """

    description: str = Field(default="", description="What the schema is for")
    revision_reason: str = Field(default="", description="Why this revision was written")
    latest_revision: bool = Field(default=True, description="Whether this is the current revision")
    scheme: SchemeResponse = Field(default_factory=SchemeResponse, description="The attributes declared")
    archived: bool = Field(default=False, description="Whether the schema was put out of use")
    deleted: bool = Field(default=False, description="Whether the schema was removed")
    industries: list[IndustryReference] = Field(default_factory=list, description="Industries the schema reaches")


class SchemaCreateRequest(BaseModel):
    """
    What declaring a schema asks for.

    The industries are accepted as identifiers, as names, or as the bare numbers the original service wanted
    and never handed out. A number names nothing this register holds, so it is read as the empty list it
    always effectively was - which leaves the schema reaching across every industry.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, description="Name of the schema")
    description: str = Field(default="", description="What the schema is for")
    type: int = Field(default=0, description="Kind of schema, which the register offers no vocabulary for")
    scheme: SchemeRequest = Field(default_factory=SchemeRequest, description="The attributes being declared")
    creator: str = Field(default="", description="User declaring the schema")
    industries: list[JsonValue] = Field(default_factory=list, description="Industries named by id, by name or not")


class SchemaRevisionRequest(BaseModel):
    """
    What revising a schema asks for, which is a new declaration and the reason it was changed.
    """

    model_config = ConfigDict(populate_by_name=True)

    creator: str = Field(default="", description="User writing the revision")
    revision_reason: str = Field(default="", description="Why the declaration was changed")
    scheme: SchemeRequest = Field(default_factory=SchemeRequest, description="The attributes as they now stand")
