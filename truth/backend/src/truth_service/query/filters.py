"""
Turning the question a table is asking into the query the document store answers.

Every restriction here is meant to be answerable out of an index, because the register is expected to hold
far more assumptions than anything can be read through. Three rules follow from that, and they are the whole
design:

Equality, membership and magnitude are compared exactly. The vocabulary a set filter offers is read back out
of the register itself, so the value a caller sends is the value that was stored, and an exact comparison is
both the right answer and the one an index can give.

The three restrictions that cannot be exact - contains, starts with and ends with - are written as case
insensitive patterns. Only the anchored one of those can use an index, and a register that is being narrowed
by a typed fragment is doing the one slow thing this offers. It is offered anyway, because it is what a
person means when they type into a column.

Free text is not a pattern at all. It is answered by the text index over the blob every searchable attribute
of an assumption was folded into when it was written, which is a lookup rather than a pass over the register.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

import re
from datetime import datetime
from typing import Any

from pydantic import JsonValue

from skyscanner_models.enums import SortDirection
from skyscanner_models.query import FilterCondition, FilterOperator, SortSpecification

from truth_service.constants import IDENTIFIER_FIELD, LATEST_FIELD, VALUES_PREFIX

# ----- CONSTS ----- #

ASCENDING: int = 1
DESCENDING: int = -1

# What a caller calls an attribute of the assumption itself, and what it is stored under. Anything not named
# here was declared by a schema, and a declared attribute lives under the values of the assumption.
FIELD_ALIASES: dict[str, str] = {
    "id": IDENTIFIER_FIELD,
    "industries": "industries.name",
    "industry_ids": "industries.id",
    "schemas": "schemas.name",
    "schema_ids": "schemas.id",
}

# The attributes an assumption carries whatever its schemas declare.
OWN_FIELDS: frozenset[str] = frozenset(
    {
        IDENTIFIER_FIELD,
        "name",
        "assumption_text",
        "proposing_party",
        "tags",
        "validation_responsible_parties",
        "revision",
        "revision_reason",
        "creator",
        "created_at",
        "archived",
        "deleted",
        "lineage",
    }
)

# The attributes that hold a moment rather than a word, whose comparisons are made against real timestamps.
DATE_FIELDS: frozenset[str] = frozenset({"created_at", "deleted_at"})

# What an ordering falls back to, which is the register newest first.
DEFAULT_SORT: list[tuple[str, int]] = [("created_at", DESCENDING), (IDENTIFIER_FIELD, ASCENDING)]

# ----- FUNCTIONS ----- #


def resolve_field(key: str) -> str:
    """
    Work out where one attribute of a row is actually stored.

    :param key: Attribute as the table addresses it.
    :return: The path the document store holds that attribute under.
    """
    if key in FIELD_ALIASES:
        return FIELD_ALIASES[key]

    if key in OWN_FIELDS:
        return key

    return f"{VALUES_PREFIX}{key}"


def coerce(field: str, value: JsonValue) -> Any:
    """
    Read a value sent as text into whatever the attribute it is compared against is stored as.

    A table sends what was typed into it, which is text. Comparing text against a stored number answers
    nothing at all - and answers it silently - so a comparison against a numeric or a dated attribute reads
    its bound before it is made.

    :param field: Path the value is compared against.
    :param value: Value as the caller sent it.
    :return: The value in the shape the stored attribute is comparable with.
    """
    if field in DATE_FIELDS and isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value

    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                number = float(text)
            except ValueError:
                return value

            return int(number) if number.is_integer() and "." not in text else number

    return value


def pattern(value: JsonValue, anchor_start: bool = False, anchor_end: bool = False) -> re.Pattern[str]:
    """
    Build the case insensitive pattern one of the three inexact restrictions is made with.

    The fragment is escaped, so that a reader typing a bracket or a full stop into a column filter narrows
    the register by that character rather than by whatever it happens to mean to a pattern engine.

    :param value: Fragment the caller is narrowing by.
    :param anchor_start: Whether the fragment has to sit at the beginning of the value.
    :param anchor_end: Whether the fragment has to sit at the end of the value.
    :return: The compiled pattern.
    """
    fragment = re.escape(str(value if value is not None else ""))
    prefix = "^" if anchor_start else ""
    suffix = "$" if anchor_end else ""

    return re.compile(f"{prefix}{fragment}{suffix}", re.IGNORECASE)


def empty_clauses(field: str) -> list[dict[str, Any]]:
    """
    Spell out every way one attribute can be said to hold nothing.

    An attribute is empty when it was never written, when it was written as nothing, when it holds the empty
    word or when it holds the empty list. A register whose columns come from its schemas has all four,
    because a row written before an attribute was declared simply has no such key.

    :param field: Path of the attribute.
    :return: The alternatives that together mean the attribute holds nothing.
    """
    return [{field: {"$exists": False}}, {field: None}, {field: ""}, {field: []}]


def build_condition(condition: FilterCondition) -> dict[str, Any]:
    """
    Turn one restriction of a table into one restriction of the document store.

    :param condition: Restriction as the table stated it.
    :return: The same restriction as the document store reads it.
    """
    field = resolve_field(condition.key)
    operator = condition.operator

    if operator is FilterOperator.EQUALS:
        return {field: coerce(field, condition.value)}
    if operator is FilterOperator.NOT_EQUALS:
        return {field: {"$ne": coerce(field, condition.value)}}
    if operator is FilterOperator.IN:
        return {field: {"$in": [coerce(field, value) for value in condition.values]}}
    if operator is FilterOperator.NOT_IN:
        return {field: {"$nin": [coerce(field, value) for value in condition.values]}}
    if operator is FilterOperator.CONTAINS:
        return {field: pattern(condition.value)}
    if operator is FilterOperator.NOT_CONTAINS:
        return {field: {"$not": pattern(condition.value)}}
    if operator is FilterOperator.STARTS_WITH:
        return {field: pattern(condition.value, anchor_start=True)}
    if operator is FilterOperator.ENDS_WITH:
        return {field: pattern(condition.value, anchor_end=True)}
    if operator is FilterOperator.IS_EMPTY:
        return {"$or": empty_clauses(field)}
    if operator is FilterOperator.IS_NOT_EMPTY:
        return {"$nor": empty_clauses(field)}
    if operator is FilterOperator.BETWEEN:
        return build_between(field=field, condition=condition)

    return build_ordered(field=field, operator=operator, value=condition.value)


def build_between(field: str, condition: FilterCondition) -> dict[str, Any]:
    """
    Turn a restriction to a span into the pair of bounds the document store reads.

    :param field: Path of the attribute being bounded.
    :param condition: Restriction carrying the two bounds among its values.
    :return: The restriction, or one that matches everything when the bounds were not a pair.
    """
    if len(condition.values) < 2:
        return {}

    low, high = condition.values[0], condition.values[1]

    return {field: {"$gte": coerce(field, low), "$lte": coerce(field, high)}}


def build_ordered(field: str, operator: FilterOperator, value: JsonValue) -> dict[str, Any]:
    """
    Turn a comparison of magnitude into the one operator the document store spells it with.

    :param field: Path of the attribute being compared.
    :param operator: Comparison the table asked for.
    :param value: Bound the attribute is compared against.
    :return: The restriction, or one that matches everything for a comparison this does not know.
    """
    operators: dict[FilterOperator, str] = {
        FilterOperator.GREATER_THAN: "$gt",
        FilterOperator.GREATER_OR_EQUAL: "$gte",
        FilterOperator.LESS_THAN: "$lt",
        FilterOperator.LESS_OR_EQUAL: "$lte",
    }
    spelled = operators.get(operator)
    if spelled is None:
        return {}

    return {field: {spelled: coerce(field, value)}}


def build_query(
    search: str | None = None,
    industry: str | None = None,
    schema_key: str | None = None,
    filters: list[FilterCondition] | None = None,
    latest_only: bool = True,
) -> dict[str, Any]:
    """
    Assemble everything a table is asking into the one restriction the register is read through.

    :param search: Free text matched against the indexed blob of every assumption.
    :param industry: Industry, by identifier or by name, the answer is narrowed to.
    :param schema_key: Declaration, by identifier or by name, the answer is narrowed to.
    :param filters: Structured restrictions over the attributes of the assumptions.
    :param latest_only: Whether only the current revision of each assumption answers.
    :return: The restriction the document store is read with.
    """
    clauses: list[dict[str, Any]] = []

    if latest_only:
        clauses.append({LATEST_FIELD: True})

    if industry:
        clauses.append({"$or": [{"industries.id": industry}, {"industries.name": industry}]})

    if schema_key:
        clauses.append({"$or": [{"schemas.id": schema_key}, {"schemas.name": schema_key}]})

    for condition in filters or []:
        built = build_condition(condition)
        if built:
            clauses.append(built)

    query: dict[str, Any] = {}
    if len(clauses) == 1:
        query = dict(clauses[0])
    elif clauses:
        query = {"$and": clauses}

    # The free text sits beside the restrictions rather than among them, which is what lets the text index
    # answer it while the indexes over the attributes answer the rest.
    if search and search.strip():
        query["$text"] = {"$search": search.strip()}

    return query


def build_sort(specifications: list[SortSpecification] | None) -> list[tuple[str, int]]:
    """
    Turn the ordering a table is running into the ordering the document store applies.

    The identifier is always appended, so that two assumptions sharing whatever they were ordered by keep a
    settled order between them. Without it the second page of an answer can repeat a row of the first.

    :param specifications: Ordering as the table stated it.
    :return: The ordering the document store applies, newest first when nothing was asked for.
    """
    if not specifications:
        return list(DEFAULT_SORT)

    ordering: list[tuple[str, int]] = [
        (
            resolve_field(specification.key),
            DESCENDING if specification.direction is SortDirection.DESC else ASCENDING,
        )
        for specification in specifications
    ]
    ordering.append((IDENTIFIER_FIELD, ASCENDING))

    return ordering
