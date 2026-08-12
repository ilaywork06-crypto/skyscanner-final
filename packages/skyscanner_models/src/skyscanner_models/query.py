"""
Search, filter and sort payloads that translate the toolbar and the grid filter model into a backend query.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skyscanner_models.enums import ParseState, SortDirection

# ----- CLASSES ----- #


class FilterOperator(str, Enum):
    """
    The comparison a single filter condition applies to the value of one field.
    """

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_THAN = "less_than"
    LESS_OR_EQUAL = "less_or_equal"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


class FilterCondition(BaseModel):
    """
    A single field level restriction, addressing either a fixed column or a dynamic metadata attribute.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Key of the field the condition applies to")
    operator: FilterOperator = Field(default=FilterOperator.EQUALS, description="Comparison to apply")
    value: JsonValue = Field(default=None, description="Value compared against the field")
    values: list[JsonValue] = Field(default_factory=list, description="Values used by the in and between operators")


class SortSpecification(BaseModel):
    """
    One ordering instruction, applied in the order the specifications were received.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Key of the field to order by")
    direction: SortDirection = Field(default=SortDirection.DESC, description="Direction of the ordering")


class SearchQuery(BaseModel):
    """
    The complete query behind the events table - free text, structured filters, ordering and the paging window.
    """

    model_config = ConfigDict(populate_by_name=True)

    search: str | None = Field(default=None, description="Free text matched against the indexed event fields")
    industry: str | None = Field(default=None, description="Industry key the results are restricted to")
    parse_state: ParseState = Field(default=ParseState.ALL, description="Parsed or not parsed restriction")
    filters: list[FilterCondition] = Field(default_factory=list, description="Structured field level restrictions")
    sort: list[SortSpecification] = Field(default_factory=list, description="Ordering applied to the results")
    page: int = Field(default=1, ge=1, description="One based index of the requested page")
    page_size: int = Field(default=50, ge=1, le=500, description="Amount of documents to return for the page")
