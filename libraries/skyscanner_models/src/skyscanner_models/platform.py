"""
Payloads describing the platforms an event may name, declared per industry the same way the types are.

:date: 2026-08-24
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from pydantic import BaseModel, ConfigDict, Field

# ----- CLASSES ----- #


class PlatformResponse(BaseModel):
    """
    A declared platform, offered by the create wizard and rendered as a chip in the inventory table.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the platform")
    key: str = Field(description="Machine key of the platform")
    name: str = Field(description="Label shown for the platform")
    description: str = Field(default="", description="Explanation of what the platform covers")
    industries: list[str] = Field(
        default_factory=list,
        description="Industries the platform belongs to, empty when every industry may name it",
    )


class PlatformCreateRequest(BaseModel):
    """
    The payload accepted when a new platform is declared for the system or for a set of industries.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Machine key of the platform")
    name: str = Field(description="Label shown for the platform")
    description: str = Field(default="", description="Explanation of what the platform covers")
    industries: list[str] = Field(
        default_factory=list,
        description="Industries the platform belongs to, empty when every industry may name it",
    )
    order: int = Field(default=100, description="Relative position of the platform in the selectors")


class PlatformUpdateRequest(BaseModel):
    """
    A partial update of a platform, where every omitted attribute keeps its stored value.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="New label of the platform")
    description: str | None = Field(default=None, description="New explanation of what the platform covers")
    industries: list[str] | None = Field(default=None, description="New industries the platform belongs to")
    order: int | None = Field(default=None, description="New relative position of the platform")
