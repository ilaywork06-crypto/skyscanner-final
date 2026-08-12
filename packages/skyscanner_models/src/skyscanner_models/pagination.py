"""
Generic pagination envelope used by every listing endpoint so that the web client can page over large collections.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# ----- CONSTS ----- #

DEFAULT_PAGE_SIZE: int = 50
MAX_PAGE_SIZE: int = 500

# ----- CLASSES ----- #

ItemT = TypeVar("ItemT")


class PageRequest(BaseModel):
    """
    The paging window requested by the caller, expressed with a one based page number and a page size.
    """

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(default=1, ge=1, description="One based index of the requested page")
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Amount of documents to return for the page",
    )

    @property
    def offset(self) -> int:
        """
        Translate the one based page number into the amount of documents that have to be skipped.

        :return: The amount of documents to skip before collecting the page.
        """
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[ItemT]):
    """
    A single page of results together with the totals needed to render a pager.
    """

    model_config = ConfigDict(populate_by_name=True)

    items: list[ItemT] = Field(default_factory=list, description="Documents contained in the page")
    total: int = Field(default=0, ge=0, description="Total amount of documents matching the query")
    page: int = Field(default=1, ge=1, description="One based index of the returned page")
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, description="Amount of documents requested per page")
    pages: int = Field(default=0, ge=0, description="Total amount of pages available for the query")
