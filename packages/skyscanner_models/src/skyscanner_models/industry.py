"""
Payloads describing the industries, rendered as the tabs above the inventory table and used to scope the dynamic schema.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ----- CLASSES ----- #


class IndustryCreateRequest(BaseModel):
    """
    The payload accepted when a new industry is registered in the system.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Machine key of the industry, used to scope fields and to filter events")
    name: str = Field(description="Label shown for the industry")
    description: str = Field(default="", description="Explanation of what the industry covers")
    color: str = Field(default="industryAmber", description="Theme colour token used for the industry chip")
    entity_origins: list[str] = Field(
        default_factory=list,
        description="The values an entity may name as its origin, empty to accept any text",
    )


class IndustryUpdateRequest(BaseModel):
    """
    A partial update of an industry, where every omitted attribute keeps its stored value.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="New label of the industry")
    description: str | None = Field(default=None, description="New explanation of what the industry covers")
    color: str | None = Field(default=None, description="New theme colour token of the industry chip")
    entity_origins: list[str] | None = Field(default=None, description="New vocabulary of the entity origins")


class IndustryResponse(BaseModel):
    """
    A stored industry as it is handed back to the client.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the industry")
    key: str = Field(description="Machine key of the industry")
    name: str = Field(description="Label shown for the industry")
    description: str = Field(default="", description="Explanation of what the industry covers")
    color: str = Field(default="industryAmber", description="Theme colour token used for the industry chip")
    entity_origins: list[str] = Field(
        default_factory=list,
        description="The values an entity may name as its origin, empty to accept any text",
    )
    event_count: int = Field(default=0, ge=0, description="Amount of events currently linked to the industry")
    created_at: datetime = Field(description="UTC moment the industry was registered")
