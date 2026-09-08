"""
The query payload behind the register's table - free text, structured restrictions, ordering and the window.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from pydantic import BaseModel, ConfigDict, Field

from skyscanner_models.query import FilterCondition, SortSpecification

from truth_service.models.assumption import AssumptionRowResponse

# ----- CONSTS ----- #

DEFAULT_LIMIT: int = 50
MAX_LIMIT: int = 1000

# ----- CLASSES ----- #


class AssumptionQuery(BaseModel):
    """
    Everything the table is asking the register for at once.

    The window is stated as an offset and a limit rather than as a page, so that the same payload serves the
    table, an export walking the whole answer and anything else reading in blocks.
    """

    model_config = ConfigDict(populate_by_name=True)

    search: str | None = Field(default=None, description="Free text matched against the indexed assumption text")
    industry: str | None = Field(default=None, description="Industry, by identifier or name, to narrow to")
    schema_key: str | None = Field(
        default=None,
        alias="schema",
        description="Declaration, by identifier or name, to narrow to",
    )
    filters: list[FilterCondition] = Field(default_factory=list, description="Structured attribute restrictions")
    sort: list[SortSpecification] = Field(default_factory=list, description="Ordering applied to the answer")
    offset: int = Field(default=0, ge=0, description="Amount of assumptions skipped before collecting")
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Largest amount to return")
    include_total: bool = Field(default=True, description="Whether the answer counts the whole match as well")


class AssumptionPage(BaseModel):
    """
    One window of an answer, together with how many assumptions the whole of it holds.
    """

    model_config = ConfigDict(populate_by_name=True)

    rows: list[AssumptionRowResponse] = Field(default_factory=list, description="The assumptions of this window")
    total: int = Field(default=0, description="How many assumptions matched, before the window was taken")
    offset: int = Field(default=0, description="Where this window starts")
    limit: int = Field(default=DEFAULT_LIMIT, description="How large this window was asked to be")


class FacetResponse(BaseModel):
    """
    Every value one attribute is known to hold, which is the vocabulary its filter offers to pick from.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="Attribute the values belong to")
    values: list[str] = Field(default_factory=list, description="The values that attribute is known to hold")
    truncated: bool = Field(default=False, description="Whether the register holds more values than were read")
