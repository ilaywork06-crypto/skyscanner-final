"""
Payloads of the edit history - who changed an event or an entity, when, why, and what the values were before.

:date: 2026-08-12
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skyscanner_models.enums import RevisionTarget

# ----- CLASSES ----- #


class FieldChange(BaseModel):
    """
    One attribute that a single edit moved from one value to another.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Key of the attribute that changed")
    label: str = Field(default="", description="Label of the attribute as the user reads it")
    before: JsonValue = Field(default=None, description="Value the attribute held before the edit")
    after: JsonValue = Field(default=None, description="Value the attribute holds after the edit")


class RevisionResponse(BaseModel):
    """
    One recorded edit, carrying its reason, its author and the attributes it moved.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the revision")
    target: RevisionTarget = Field(description="Whether the edit changed an event or an entity")
    event_id: str = Field(description="Identifier of the event the edit belongs to")
    entity_id: str | None = Field(default=None, description="Identifier of the entity, empty for an event edit")
    entity_name: str = Field(default="", description="Name of the entity at the moment of the edit")
    version: int = Field(description="Running number of the edit for its target, starting at one")
    reason: str = Field(default="", description="Why the change was made, supplied by the person making it")
    changed_by: str = Field(description="User that made the change")
    changed_at: datetime = Field(description="UTC moment the change was made")
    changes: list[FieldChange] = Field(default_factory=list, description="Attributes the edit moved")
