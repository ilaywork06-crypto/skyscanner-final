"""
The paging window every listing endpoint offers, expressed as the offset and the limit of the requested window.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from fastapi import Query

from skyscanner_models.pagination import MAX_PAGE_SIZE

# ----- CONSTS ----- #

UNLIMITED: int = 0

OFFSET_QUERY: Any = Query(
    default=0,
    ge=0,
    description="Amount of documents skipped before the window is collected",
)

LIMIT_QUERY: Any = Query(
    default=UNLIMITED,
    ge=0,
    le=MAX_PAGE_SIZE,
    description="Largest amount of documents the window returns, zero for every match",
)
