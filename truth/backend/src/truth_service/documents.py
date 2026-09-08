"""
The persistence shape of the register - one document per industry, per schema revision and per assumption.

Two decisions are worth stating here, because everything else follows from them.

A revision is a document of its own rather than an entry inside the thing it revises. Every revision of one
declaration carries the identifier of the first of them in ``lineage``, and exactly one of them carries
``latest_revision``. Reading the register is then a query over the latest ones, which is an indexed
restriction rather than a walk through embedded history, and it stays that whether a declaration has been
revised twice or two thousand times.

The names of the schemas and of the industries an assumption belongs to are copied onto the assumption. The
register is read far more often than it is written, and a listing that had to join would be one round trip
per row - the very thing that made the client read every assumption on its own. Denormalising costs a
rewrite whenever a name changes, and nothing in this API can rename an industry or a schema at all.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.ids import new_id

from truth_service.models.common import IndustryReference, SchemaReference

# ----- CLASSES ----- #


class SoftDeletable(BaseModel):
    """
    The marker every document that can be removed carries instead of being erased.
    """

    deleted: bool = Field(default=False, description="Whether the document was removed")
    deleted_at: datetime | None = Field(default=None, description="UTC moment the document was removed")
    deleted_by: str | None = Field(default=None, description="User that removed the document")


class StoredScheme(BaseModel):
    """
    A declaration exactly as it is stored, which is a list of dictionaries the service promises nothing about.

    The service stores what it was handed. The client reads it generously and writes it strictly, and the
    two spellings of the constraint list are both accepted on the way in because the original API read one
    and answered with the other.
    """

    model_config = ConfigDict(populate_by_name=True)

    fields: list[dict[str, JsonValue]] = Field(default_factory=list, description="The attributes declared")
    constraints: list[dict[str, JsonValue]] = Field(
        default_factory=list,
        description="The rules the declared attributes are checked against",
    )


class IndustryDocument(SoftDeletable):
    """
    One industry, which is the vocabulary the assumptions and the schemas are filed under.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the industry")
    name: str = Field(description="Name of the industry")
    description: str = Field(default="", description="What the industry covers")
    creator: str = Field(default="", description="User that registered the industry")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the industry was registered")


class SchemaDocument(SoftDeletable):
    """
    One revision of one declaration, which is what decides the attributes an assumption may carry.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of this revision")
    lineage: str = Field(description="Identifier of the first revision, which groups the whole declaration")
    name: str = Field(description="Name of the declaration, which every revision of it shares")
    description: str = Field(default="", description="What the declaration is for")
    type: int = Field(default=0, description="Kind of declaration, which the register offers no vocabulary for")
    revision: int = Field(default=1, description="Running number of this revision inside its lineage")
    revision_reason: str = Field(default="", description="Why this revision was written")
    latest_revision: bool = Field(default=True, description="Whether this is the current revision of the lineage")
    scheme: StoredScheme = Field(default_factory=StoredScheme, description="The attributes this revision declares")
    creator: str = Field(default="", description="User that wrote this revision")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment this revision was written")
    industries: list[IndustryReference] = Field(default_factory=list, description="Industries it reaches")
    archived: bool = Field(default=False, description="Whether the declaration was put out of use")


class AssumptionDocument(SoftDeletable):
    """
    One revision of one assumption, which is a condition, a figure or a behaviour a project is planned on.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of this revision")
    lineage: str = Field(description="Identifier of the first revision, which groups the whole assumption")
    name: str = Field(description="Name of the assumption")
    assumption_text: str = Field(default="", description="What is being assumed, in words")
    proposing_party: str = Field(default="", description="Who put the assumption forward")
    tags: list[str] = Field(default_factory=list, description="Free vocabulary the assumption was filed under")
    validation_responsible_parties: list[str] = Field(
        default_factory=list,
        description="Who is answerable for checking the assumption holds",
    )
    revision: int = Field(default=1, description="Running number of this revision inside its lineage")
    revision_reason: str = Field(default="", description="Why this revision was written")
    latest_revision: bool = Field(default=True, description="Whether this is the current revision of the lineage")
    creator: str = Field(default="", description="User that wrote this revision")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment this revision was written")
    schemas: list[SchemaReference] = Field(default_factory=list, description="Declarations that apply")
    industries: list[IndustryReference] = Field(default_factory=list, description="Industries it belongs to")
    values: dict[str, JsonValue] = Field(default_factory=dict, description="What the declared attributes hold")
    special_fields: dict[str, JsonValue] = Field(default_factory=dict, description="Reserved by the register")
    archived: bool = Field(default=False, description="Whether the assumption was put out of use")
    search_text: str = Field(default="", description="Every searchable attribute folded into one indexed blob")


# ----- FUNCTIONS ----- #


def flatten_text(value: JsonValue) -> str:
    """
    Render any stored value as the words a search is matched against.

    :param value: Value carried by an assumption, of any shape the register accepts.
    :return: The words of that value, separated by single spaces.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(flatten_text(item) for item in value)

    if isinstance(value, dict):
        return " ".join(flatten_text(item) for item in value.values())

    return str(value)


def build_search_text(document: AssumptionDocument) -> str:
    """
    Fold every searchable attribute of an assumption into the one blob its text index is built over.

    The values are folded in as well as the words of the assumption itself, because a register whose columns
    come from its schemas is one where the thing worth searching for is as likely to be a value as a name.

    :param document: Assumption whose searchable text is being built.
    :return: The blob that is stored and indexed alongside the assumption.
    """
    parts = [
        document.name,
        document.assumption_text,
        document.proposing_party,
        document.creator,
        " ".join(document.tags),
        " ".join(document.validation_responsible_parties),
        " ".join(schema.name for schema in document.schemas),
        " ".join(industry.name for industry in document.industries),
        flatten_text(document.values),
    ]

    return " ".join(part for part in parts if part).strip()
