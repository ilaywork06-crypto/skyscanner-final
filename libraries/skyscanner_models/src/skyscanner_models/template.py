"""
Payloads for the saved table templates, letting a user store which columns, filters and ordering they want to see.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from skyscanner_models.enums import FieldScope
from skyscanner_models.query import FilterCondition, SortSpecification

# ----- CLASSES ----- #


class TemplateColumn(BaseModel):
    """
    The stored presentation of a single column inside a template.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Key of the field the column renders")
    visible: bool = Field(default=True, description="Whether the column is shown")
    order: int = Field(default=100, description="Relative position of the column")
    width: float | None = Field(default=None, description="Pinned width of the column in pixels")
    pinned: str | None = Field(default=None, description="Side the column is pinned to, left or right")


class TemplateBase(BaseModel):
    """
    The attributes shared by the create, update and response representations of a table template.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(description="Label the user gave the template")
    description: str = Field(default="", description="Explanation of what the template shows")
    scope: FieldScope = Field(default=FieldScope.EVENT, description="Whether the template targets events or entities")
    industry: str | None = Field(default=None, description="Industry the template belongs to, empty when it is global")
    shared: bool = Field(default=False, description="Whether other users may load the template")
    columns: list[TemplateColumn] = Field(default_factory=list, description="Presentation of every column")
    filters: list[FilterCondition] = Field(default_factory=list, description="Filters restored with the template")
    sort: list[SortSpecification] = Field(default_factory=list, description="Ordering restored with the template")


class TemplateCreateRequest(TemplateBase):
    """
    The payload accepted when a user saves the current table layout as a template.
    """


class TemplateUpdateRequest(BaseModel):
    """
    A partial update of a template, where every omitted attribute keeps its stored value.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="New label of the template")
    description: str | None = Field(default=None, description="New explanation of the template")
    shared: bool | None = Field(default=None, description="New sharing behaviour of the template")
    columns: list[TemplateColumn] | None = Field(default=None, description="Replacement column presentation")
    filters: list[FilterCondition] | None = Field(default=None, description="Replacement filters of the template")
    sort: list[SortSpecification] | None = Field(default=None, description="Replacement ordering of the template")


class TemplateResponse(TemplateBase):
    """
    A stored template as it is handed back to the client.
    """

    id: str = Field(description="Identifier of the template")
    owner: str = Field(description="User that saved the template")
    created_at: datetime = Field(description="UTC moment the template was saved")
    updated_at: datetime | None = Field(default=None, description="UTC moment the template last changed")
