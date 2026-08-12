"""
Small text helpers used when keys are derived from labels and when file names are split into their parts.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import re

# ----- CONSTS ----- #

NON_KEY_CHARACTERS: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
NON_KEY_SEPARATORS: re.Pattern[str] = re.compile(r"[_.\-\s]+")
SUFFIX_SEPARATOR: str = "."

# ----- FUNCTIONS ----- #


def slugify(value: str) -> str:
    """
    Turn a human readable label into a lower snake case machine key.

    :param value: Label supplied by the user.
    :return: The machine key derived from the label.
    """
    return NON_KEY_CHARACTERS.sub("_", value.strip().lower()).strip("_")


def humanize_key(value: str) -> str:
    """
    Turn a machine key back into the label a person reads, which is the inverse of slugify.

    :param value: Machine key stored for a field or an attribute.
    :return: The readable label of the key.
    """
    parts = [part for part in NON_KEY_SEPARATORS.split(value) if part]

    return " ".join(part[:1].upper() + part[1:] for part in parts)


def file_suffix(file_name: str) -> str:
    """
    Read the extension of a file name without its leading separator.

    :param file_name: Name of the uploaded file.
    :return: The lower case extension, or an empty text when the name carries none.
    """
    if SUFFIX_SEPARATOR not in file_name:
        return ""

    return file_name.rsplit(SUFFIX_SEPARATOR, maxsplit=1)[-1].lower()


def split_list(value: str, separator: str = ",") -> list[str]:
    """
    Split a separated piece of text into the list of its non empty trimmed parts.

    :param value: Text holding several values.
    :param separator: Character the values are separated by.
    :return: The trimmed parts of the text.
    """
    return [part.strip() for part in value.split(separator) if part.strip()]
