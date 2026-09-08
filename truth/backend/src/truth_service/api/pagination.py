"""
The window every listing of the register takes, stated the one way.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from fastapi import Query

# ----- CONSTS ----- #

DEFAULT_LIMIT: int = 100
MAX_LIMIT: int = 1000

OFFSET_QUERY = Query(default=0, ge=0, description="Amount of documents skipped before collecting")
LIMIT_QUERY = Query(
    default=DEFAULT_LIMIT,
    ge=1,
    le=MAX_LIMIT,
    description="Largest amount of documents that is returned",
)
