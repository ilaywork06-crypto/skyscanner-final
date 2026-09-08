"""
The payloads of the industries, which are the vocabulary the register is filed under.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ----- CLASSES ----- #


class IndustryResponse(BaseModel):
    """
    One industry as every endpoint hands it over.

    The count is filled in only by the listing that was asked for it: counting the assumptions of every
    industry is a pass over the whole register, and most readers of this payload only want the name.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the industry")
    name: str = Field(description="Name of the industry")
    description: str = Field(default="", description="What the industry covers")
    creator: str = Field(default="", description="User that registered the industry")
    created_at: datetime | None = Field(default=None, description="UTC moment the industry was registered")
    assumption_count: int | None = Field(default=None, description="How many assumptions name this industry")


class IndustryCreateRequest(BaseModel):
    """
    What registering an industry asks for.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, description="Name of the industry")
    description: str = Field(default="", description="What the industry covers")
    creator: str = Field(default="", description="User registering the industry")
