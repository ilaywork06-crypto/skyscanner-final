"""
Translation of the grid query into a document store query, covering free text search, filtering and ordering.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import re
from typing import Any

from skyscanner_models.enums import SortDirection
from skyscanner_models.query import FilterCondition, FilterOperator, SortSpecification

# ----- CONSTS ----- #

DYNAMIC_VALUE_ROOT: str = "data"
NESTED_PATH_SEPARATOR: str = "."
EMPTY_VALUES: list[Any] = [None, "", []]
ASCENDING: int = 1
DESCENDING: int = -1

_TEXT_OPERATORS: frozenset[FilterOperator] = frozenset(
    {
        FilterOperator.CONTAINS,
        FilterOperator.NOT_CONTAINS,
        FilterOperator.STARTS_WITH,
        FilterOperator.ENDS_WITH,
    },
)

_COMPARISON_OPERATORS: dict[FilterOperator, str] = {
    FilterOperator.NOT_EQUALS: "$ne",
    FilterOperator.GREATER_THAN: "$gt",
    FilterOperator.GREATER_OR_EQUAL: "$gte",
    FilterOperator.LESS_THAN: "$lt",
    FilterOperator.LESS_OR_EQUAL: "$lte",
}

# ----- FUNCTIONS ----- #


def resolve_path(key: str, fixed_keys: frozenset[str]) -> str:
    """
    Resolve the document path a grid key addresses, sending unknown keys into the dynamic value sub document.

    :param key: Key the grid column was generated with.
    :param fixed_keys: Keys that exist as real attributes of the document.
    :return: The path the query has to address.
    """
    if key in fixed_keys:
        return key

    if key.startswith(f"{DYNAMIC_VALUE_ROOT}{NESTED_PATH_SEPARATOR}"):
        return key

    return f"{DYNAMIC_VALUE_ROOT}{NESTED_PATH_SEPARATOR}{key}"


def build_text_search_filter(search: str, paths: list[str]) -> dict[str, Any]:
    """
    Build the restriction behind the free text search box, matching the term against every searchable path.

    A substring anywhere in a value cannot be answered from an index, so this restriction is always decided by
    reading documents. What can be decided is how much work each document costs: the alternatives of an "or"
    are tested in the order they are written and the first one that holds ends the test, so the paths that sit
    directly on the document are tested before the paths that live inside a nested list. A nested path has to
    walk every element of that list, which on an event with a handful of entities and their files is an order
    of magnitude more comparisons than reading one attribute.

    The set of paths is untouched by the ordering, so the very same documents match either way.

    :param search: Term the user typed into the search box.
    :param paths: Document paths the term is matched against.
    :return: The restriction, or an empty mapping when there is nothing to search for.
    """
    term = search.strip()
    if not term or not paths:
        return {}

    pattern = re.compile(re.escape(term), re.IGNORECASE)
    ordered = sorted(dict.fromkeys(paths), key=lambda path: path.count(NESTED_PATH_SEPARATOR))

    return {"$or": [{path: pattern} for path in ordered]}


def build_mongo_filter(conditions: list[FilterCondition], fixed_keys: frozenset[str]) -> dict[str, Any]:
    """
    Translate the structured filter conditions of the grid into a document store restriction.

    :param conditions: Field level restrictions requested by the client.
    :param fixed_keys: Keys that exist as real attributes of the document.
    :return: The restriction, or an empty mapping when no condition was requested.
    """
    clauses: list[dict[str, Any]] = []
    for condition in conditions:
        clause = _build_clause(condition=condition, fixed_keys=fixed_keys)
        if clause:
            clauses.append(clause)

    if not clauses:
        return {}

    if len(clauses) == 1:
        return clauses[0]

    return {"$and": clauses}


def build_mongo_sort(specifications: list[SortSpecification], fixed_keys: frozenset[str]) -> list[tuple[str, int]]:
    """
    Translate the ordering requested by the grid into the sort argument of the document store.

    :param specifications: Ordering instructions requested by the client.
    :param fixed_keys: Keys that exist as real attributes of the document.
    :return: The ordering as a list of path and direction pairs.
    """
    return [
        (
            resolve_path(key=specification.key, fixed_keys=fixed_keys),
            ASCENDING if specification.direction is SortDirection.ASC else DESCENDING,
        )
        for specification in specifications
    ]


def merge_filters(*filters: dict[str, Any]) -> dict[str, Any]:
    """
    Combine several restrictions into a single one that documents have to satisfy as a whole.

    :param filters: Restrictions that were built independently of each other.
    :return: The combined restriction, or an empty mapping when nothing was restricted.
    """
    present = [candidate for candidate in filters if candidate]
    if not present:
        return {}

    if len(present) == 1:
        return present[0]

    return {"$and": present}


def _build_clause(condition: FilterCondition, fixed_keys: frozenset[str]) -> dict[str, Any]:
    """
    Translate a single filter condition into the restriction of one document path.

    :param condition: Field level restriction requested by the client.
    :param fixed_keys: Keys that exist as real attributes of the document.
    :return: The restriction of the addressed path, or an empty mapping when the condition carries no value.
    """
    path = resolve_path(key=condition.key, fixed_keys=fixed_keys)
    operator = condition.operator
    value = condition.value

    if operator is FilterOperator.IS_EMPTY:
        return {path: {"$in": EMPTY_VALUES}}

    if operator is FilterOperator.IS_NOT_EMPTY:
        return {path: {"$nin": EMPTY_VALUES}}

    if operator in {FilterOperator.IN, FilterOperator.NOT_IN}:
        if not condition.values:
            return {}
        comparison = "$in" if operator is FilterOperator.IN else "$nin"
        return {path: {comparison: list(condition.values)}}

    if operator is FilterOperator.BETWEEN:
        if len(condition.values) < 2:
            return {}
        return {path: {"$gte": condition.values[0], "$lte": condition.values[1]}}

    if value is None:
        return {}

    if operator in _TEXT_OPERATORS:
        return _build_text_clause(path=path, operator=operator, value=value)

    comparison_operator = _COMPARISON_OPERATORS.get(operator)
    if comparison_operator is not None:
        return {path: {comparison_operator: value}}

    return {path: value}


def _build_text_clause(path: str, operator: FilterOperator, value: Any) -> dict[str, Any]:
    """
    Translate a text shaped condition into a case insensitive regular expression restriction.

    :param path: Document path the restriction applies to.
    :param operator: Text comparison requested by the client.
    :param value: Value the path is compared against.
    :return: The restriction of the addressed path.
    """
    escaped = re.escape(str(value))
    if operator is FilterOperator.STARTS_WITH:
        escaped = f"^{escaped}"
    elif operator is FilterOperator.ENDS_WITH:
        escaped = f"{escaped}$"

    pattern = re.compile(escaped, re.IGNORECASE)
    if operator is FilterOperator.NOT_CONTAINS:
        return {path: {"$not": pattern}}

    return {path: pattern}
