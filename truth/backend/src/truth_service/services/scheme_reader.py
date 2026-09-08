"""
Reading the free form dictionaries a schema declares its attributes as, and checking a value against them.

The register stores whatever a caller hands it - the declaration is typed as a list of dictionaries and
nothing more - so a schema may have been written by this client, by a script or by a person. Reading is
therefore generous: an attribute naming itself under ``key``, ``name`` or ``field`` is the same attribute
either way, and a whole attribute written as ``{"berth_count": "int"}`` is understood as the shortest way
anybody would think to write one.

This mirrors the reader the client runs, deliberately and exactly. Two readers of one free form declaration
that disagree would let a value be written through the form and then be rejected on its way in, or the other
way about, over a spelling nobody ever promised to follow.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skyscanner_common.errors import ValidationError

# ----- CONSTS ----- #

KEY_ALIASES: tuple[str, ...] = ("key", "name", "field", "field_name", "id")
NAME_ALIASES: tuple[str, ...] = ("display_name", "displayName", "label", "title", "display", "caption")
TYPE_ALIASES: tuple[str, ...] = ("type", "field_type", "data_type", "kind")
OPTION_ALIASES: tuple[str, ...] = ("options", "choices", "enum", "values", "allowed", "allowed_values")
REQUIRED_ALIASES: tuple[str, ...] = ("required", "mandatory", "is_required")
ARRAY_ALIASES: tuple[str, ...] = ("array", "multiple", "is_list", "many", "repeated")

TRUE_WORDS: frozenset[str] = frozenset({"true", "yes", "1"})

# What each spelling of a type is understood as. The left hand side is what people and scripts write; the
# right hand side is the vocabulary this register actually has.
TYPE_BY_NAME: dict[str, str] = {
    "string": "string",
    "str": "string",
    "text": "string",
    "boolean": "boolean",
    "bool": "boolean",
    "confined_number": "confined_number",
    "confined number": "confined_number",
    "number": "confined_number",
    "int": "confined_number",
    "integer": "confined_number",
    "confined_float": "confined_float",
    "confined float": "confined_float",
    "float": "confined_float",
    "double": "confined_float",
    "decimal": "confined_float",
    "enum": "enum",
    "select": "enum",
    "choice": "enum",
    "date": "date",
    "datetime": "date",
}

FALLBACK_TYPE: str = "string"
NUMERIC_TYPES: frozenset[str] = frozenset({"confined_number", "confined_float"})
ARRAY_TYPE_NAMES: frozenset[str] = frozenset({"list", "array", "set", "tuple", "sequence"})

INNER_TYPE_PATTERN = re.compile(r"^(?:list|array|set|tuple|sequence)\s*(?:\[|<|\bof\b)\s*([a-z_ ]+)")
SUFFIXED_TYPE_PATTERN = re.compile(r"^([a-z_ ]+?)\s*\[\s*\]$")

# ----- CLASSES ----- #


class SchemeField(BaseModel):
    """
    One attribute of an assumption, as a schema declares it and as everything here reads it.
    """

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(description="What the value is stored under")
    display_name: str = Field(default="", description="What a person reads")
    type: str = Field(default=FALLBACK_TYPE, description="Kind of value the attribute holds")
    required: bool = Field(default=False, description="Whether an assumption has to carry the attribute")
    array: bool = Field(default=False, description="Whether the attribute holds several values")
    options: list[str] = Field(default_factory=list, description="Vocabulary an enumerated attribute is drawn from")
    minimum: float | None = Field(default=None, description="Smallest value a confined number may hold")
    maximum: float | None = Field(default=None, description="Largest value a confined number may hold")
    step: float | None = Field(default=None, description="Increment a confined number moves in")


# ----- FUNCTIONS ----- #


def humanize_key(key: str) -> str:
    """
    Turn a stored key into the words a person reads where no display name was written.

    :param key: Key the value is stored under.
    :return: The same key as separated, capitalised words.
    """
    words = [word for word in re.split(r"[_\-\s]+", key.strip()) if word]

    return " ".join(word[:1].upper() + word[1:] for word in words) if words else key


def read_string(raw: dict[str, JsonValue], aliases: tuple[str, ...]) -> str | None:
    """
    Read one word out of a stored dictionary, trying each spelling in turn.

    :param raw: Dictionary the attribute was stored as.
    :param aliases: Spellings the word may have been written under.
    :return: The word, or nothing when none of the spellings carried one.
    """
    for alias in aliases:
        value = raw.get(alias)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def read_flag(raw: dict[str, JsonValue], aliases: tuple[str, ...]) -> bool:
    """
    Read one flag out of a stored dictionary, accepting the several ways a flag gets written down.

    :param raw: Dictionary the attribute was stored as.
    :param aliases: Spellings the flag may have been written under.
    :return: Whether the flag was set.
    """
    for alias in aliases:
        value = raw.get(alias)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in TRUE_WORDS
        if isinstance(value, (int, float)):
            return value != 0

    return False


def read_number(raw: dict[str, JsonValue], key: str) -> float | None:
    """
    Read one number out of a stored dictionary, or nothing where none was written.

    :param raw: Dictionary the attribute was stored as.
    :param key: Key the number was written under.
    :return: The number, or nothing when the key held no number.
    """
    value = raw.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None

    return None


def read_options(raw: dict[str, JsonValue]) -> list[str]:
    """
    Read the vocabulary of an enumerated attribute, whichever key it was offered under.

    :param raw: Dictionary the attribute was stored as.
    :return: The values the attribute may hold, empty when none were offered.
    """
    for alias in OPTION_ALIASES:
        value = raw.get(alias)
        if isinstance(value, list):
            return [str(item) for item in value if item is not None and not isinstance(item, (dict, list))]

    return []


def read_type(raw: dict[str, JsonValue]) -> tuple[str, bool]:
    """
    Work out what kind of value an attribute holds and whether it holds one of them or several.

    A type is often written as a list of something - ``list[str]``, ``string[]`` - which says two separate
    things at once, so both are read out of it rather than the whole spelling being given up on.

    :param raw: Dictionary the attribute was stored as.
    :return: The kind of value and whether the attribute holds several of them.
    """
    written = read_string(raw, TYPE_ALIASES)
    declared_array = read_flag(raw, ARRAY_ALIASES)

    if written is None:
        # An attribute with a vocabulary and no stated type is an enumeration, whatever else it forgot to say.
        return ("enum" if read_options(raw) else FALLBACK_TYPE), declared_array

    lowered = written.lower().strip()

    inner = INNER_TYPE_PATTERN.match(lowered)
    if inner is not None:
        return TYPE_BY_NAME.get(inner.group(1).strip(), FALLBACK_TYPE), True

    suffixed = SUFFIXED_TYPE_PATTERN.match(lowered)
    if suffixed is not None:
        return TYPE_BY_NAME.get(suffixed.group(1).strip(), FALLBACK_TYPE), True

    if lowered in ARRAY_TYPE_NAMES:
        return FALLBACK_TYPE, True

    return TYPE_BY_NAME.get(lowered, FALLBACK_TYPE), declared_array


def build_field(key: str, display_name: str, raw: dict[str, JsonValue]) -> SchemeField:
    """
    Assemble one attribute out of what was recognised in the dictionary it was stored as.

    :param key: Key the value is stored under.
    :param display_name: What a person reads.
    :param raw: Dictionary the attribute was stored as.
    :return: The attribute as everything here reads it.
    """
    kind, array = read_type(raw)
    numeric = kind in NUMERIC_TYPES

    return SchemeField(
        key=key,
        display_name=display_name,
        type=kind,
        array=array,
        required=read_flag(raw, REQUIRED_ALIASES),
        options=read_options(raw) if kind == "enum" else [],
        minimum=read_number(raw, "min") if numeric else None,
        maximum=read_number(raw, "max") if numeric else None,
        step=read_number(raw, "step") if numeric else None,
    )


def read_field(raw: dict[str, JsonValue]) -> SchemeField | None:
    """
    Read one stored attribute, or nothing at all when there is no key to be found in it.

    A dictionary of exactly one entry is read as that entry, because a schema written as
    ``{"speed": "number"}`` names an attribute and its type in the shortest way anybody would think to write
    it, and refusing to understand that leaves the whole declaration unreadable over a spelling nobody
    promised to follow.

    :param raw: Dictionary the attribute was stored as.
    :return: The attribute, or nothing when the dictionary named none.
    """
    named = read_string(raw, KEY_ALIASES)
    entries = list(raw.items())

    if named is None and len(entries) == 1 and isinstance(entries[0][1], str):
        key, written = entries[0]

        return build_field(key=key, display_name=humanize_key(key), raw={"type": written})

    if named is None:
        return None

    return build_field(key=named, display_name=read_string(raw, NAME_ALIASES) or humanize_key(named), raw=raw)


def read_scheme(fields: list[dict[str, JsonValue]]) -> list[SchemeField]:
    """
    Read a whole stored declaration into the attributes everything here works with.

    :param fields: The dictionaries the declaration stored its attributes as.
    :return: The attributes that could be read out of it.
    """
    read: list[SchemeField] = []
    for raw in fields:
        if not isinstance(raw, dict):
            continue
        field = read_field(raw)
        if field is not None:
            read.append(field)

    return read


def merge_fields(schemes: list[list[dict[str, JsonValue]]]) -> list[dict[str, JsonValue]]:
    """
    Merge the declarations of several schemas into the one flat list an assumption is described by.

    An attribute declared by two schemas is one attribute, because an assumption carries one value under it
    either way. The first declaration of it is the one that is kept, so the order is the order the schemas
    were named in.

    :param schemes: The stored attribute lists of every schema that applies.
    :return: Every attribute named by any of them, each appearing once.
    """
    merged: list[dict[str, JsonValue]] = []
    seen: set[str] = set()

    for stored in schemes:
        for raw in stored:
            if not isinstance(raw, dict):
                continue
            field = read_field(raw)
            if field is None or field.key in seen:
                continue
            seen.add(field.key)
            merged.append(dict(raw))

    return merged


def check_values(fields: list[SchemeField], values: dict[str, JsonValue]) -> None:
    """
    Check what an assumption carries against what its schemas declared.

    Only the three things a declaration actually states are checked - that a required attribute was given,
    that an enumerated one holds a value from its own vocabulary, and that a confined number sits inside its
    bounds. An attribute the declaration says nothing definite about is left alone: the register stores what
    it is handed, and refusing a value on a rule nobody wrote would be the register inventing one.

    :param fields: The attributes the schemas of the assumption declare.
    :param values: What the assumption carries.
    :raises ValidationError: When a value contradicts what its own declaration states.
    """
    complaints: dict[str, str] = {}

    for field in fields:
        given = values.get(field.key)

        if field.required and _is_missing(given):
            complaints[field.key] = f"{field.display_name or field.key} is required"

            continue

        if _is_missing(given):
            continue

        for value in given if isinstance(given, list) else [given]:
            complaint = _check_one(field=field, value=value)
            if complaint is not None:
                complaints[field.key] = complaint

                break

    if complaints:
        raise ValidationError(message="The assumption does not satisfy the schemas it names", details=complaints)


def _is_missing(value: JsonValue) -> bool:
    """
    Decide whether an attribute was given a value at all.

    :param value: Value the assumption carries under the attribute.
    :return: Whether the attribute holds nothing.
    """
    return value is None or value == "" or value == []


def _check_one(field: SchemeField, value: Any) -> str | None:
    """
    Check one single value against the attribute it was written under.

    :param field: Attribute as its schema declares it.
    :param value: One value the assumption carries under that attribute.
    :return: What is wrong with the value, or nothing when it satisfies the declaration.
    """
    name = field.display_name or field.key

    if field.type == "enum" and field.options and str(value) not in field.options:
        return f"{name} holds a value its schema does not offer"

    if field.type not in NUMERIC_TYPES:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"{name} is declared as a number"

    if field.minimum is not None and number < field.minimum:
        return f"{name} is below the smallest value its schema allows"

    if field.maximum is not None and number > field.maximum:
        return f"{name} is above the largest value its schema allows"

    return None
