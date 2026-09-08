"""
The payloads of the assumptions themselves - the rows of the register and the reading of a single one.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from truth_service.models.common import IndustryReference
from truth_service.models.schema import SchemaDetailResponse, SchemaSummaryResponse

# ----- CLASSES ----- #


class AssumptionBase(BaseModel):
    """
    Everything an assumption carries whichever way it is being handed over.

    This carries the values and the industries even when it is being listed. The original listing carried
    neither, which is what forced the client to read every listed assumption again on its own - one request
    per row, and a register of a hundred thousand rows that could never finish loading.

    What the two shapes below disagree about is only the declarations: a listed assumption names them, and a
    read one carries them whole.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of this revision of the assumption")
    name: str = Field(description="Name of the assumption")
    assumption_text: str = Field(default="", description="What is being assumed, in words")
    proposing_party: str = Field(default="", description="Who put the assumption forward")
    tags: list[str] = Field(default_factory=list, description="Free vocabulary the assumption was filed under")
    validation_responsible_parties: list[str] = Field(
        default_factory=list,
        description="Who is answerable for checking the assumption holds",
    )
    revision: int = Field(default=1, description="Running number of this revision")
    revision_reason: str = Field(default="", description="Why this revision was written")
    creator: str = Field(default="", description="User that wrote this revision")
    created_at: datetime | None = Field(default=None, description="UTC moment this revision was written")
    industries: list[IndustryReference] = Field(default_factory=list, description="Industries it belongs to")
    values: dict[str, JsonValue] = Field(default_factory=dict, description="What the declared attributes hold")
    archived: bool = Field(default=False, description="Whether the assumption was put out of use")
    deleted: bool = Field(default=False, description="Whether the assumption was removed")


class AssumptionRowResponse(AssumptionBase):
    """
    An assumption as the register lists it, which is everything the table draws a row out of.
    """

    schemas: list[SchemaSummaryResponse] = Field(default_factory=list, description="Declarations that apply")


class AssumptionDetailResponse(AssumptionBase):
    """
    An assumption read on its own, which is the only shape carrying the declarations whole.
    """

    schemas: list[SchemaDetailResponse] = Field(default_factory=list, description="Declarations, whole")
    aggregated_scheme: list[dict[str, JsonValue]] = Field(
        default_factory=list,
        description="Every attribute the declarations of this assumption name, merged into one flat list",
    )
    special_fields: dict[str, JsonValue] = Field(default_factory=dict, description="Reserved by the register")


class AssumptionCreateRequest(BaseModel):
    """
    What creating an assumption asks for.

    A schema and an industry are both named by their identifier or by their name, whichever the caller has.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, description="Name of the assumption")
    assumption_text: str = Field(default="", description="What is being assumed, in words")
    proposing_party: str = Field(default="", description="Who put the assumption forward")
    schemas: list[str] = Field(default_factory=list, description="Declarations that apply, by identifier or name")
    values: dict[str, JsonValue] = Field(default_factory=dict, description="What the declared attributes hold")
    tags: list[str] = Field(default_factory=list, description="Free vocabulary to file the assumption under")
    validation_responsible_parties: list[str] = Field(
        default_factory=list,
        description="Who is answerable for checking the assumption holds",
    )
    creator: str = Field(default="", description="User creating the assumption")
    industries: list[str] = Field(default_factory=list, description="Industries it belongs to, by identifier or name")
    special_fields: dict[str, JsonValue] = Field(default_factory=dict, description="Reserved by the register")
