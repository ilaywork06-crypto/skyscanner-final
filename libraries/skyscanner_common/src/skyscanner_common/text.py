"""
Small text helpers used when keys are derived from labels and when file names are split into their parts.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import re
import unicodedata
from urllib.parse import quote

# ----- CONSTS ----- #

NON_KEY_CHARACTERS: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
NON_KEY_SEPARATORS: re.Pattern[str] = re.compile(r"[_.\-\s]+")
SUFFIX_SEPARATOR: str = "."

# What a single path segment may never carry, whatever alphabet the rest of it is written in. A separator
# would silently move the file into a folder of its own - or out of the one it belongs to - and a control
# character is refused outright by archive tools and by the header of a download. Everything else is kept:
# a name is written in the alphabet its owner works in, and a system that only accepts ASCII simply loses
# the name it was given.
PATH_SEPARATORS: re.Pattern[str] = re.compile(r"[\\/]+")
CONTROL_CHARACTERS: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]+")
COLLAPSED_WHITESPACE: re.Pattern[str] = re.compile(r"\s+")

# A dot or a space at either edge of a segment is dropped by some file systems and turns "..", the way out of
# a folder, into a segment of its own, so neither is ever left standing there.
TRIMMED_EDGES: str = ". "

# Most file systems measure a segment in bytes rather than in letters, and a Hebrew letter costs two of them
# in UTF-8, so the cap is applied to the encoded form rather than to the length of the text.
MAX_SEGMENT_BYTES: int = 180

SEGMENT_REPLACEMENT: str = "_"
FALLBACK_SEGMENT: str = "unnamed"

# The alphabet a bucket accepts inside the value of a stored metadata attribute, which travels as a header.
NON_ASCII_METADATA: re.Pattern[str] = re.compile(r"[^\x20-\x7e]")

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


def safe_path_segment(
    value: str,
    fallback: str = FALLBACK_SEGMENT,
    max_bytes: int = MAX_SEGMENT_BYTES,
) -> str:
    """
    Turn a name into one segment of a path, keeping every letter that is safe to keep.

    A file is named in the alphabet its owner works in - Hebrew, Cyrillic, an accent, a space - and none of
    that is a reason to rename it. Only what would change where the file ends up, or break the tool reading
    it, is replaced: the separators, the control characters and the two edges a file system trims by itself.
    The name is normalised first so that two spellings of the same letter cannot become two different files.

    :param value: Name read from an upload, an event, an entity or a stored file.
    :param fallback: Name used when nothing usable is left of the value.
    :param max_bytes: Largest size the encoded segment may take.
    :return: The name as a single safe path segment.
    """
    normalised = unicodedata.normalize("NFC", value)
    without_separators = PATH_SEPARATORS.sub(SEGMENT_REPLACEMENT, normalised)
    without_controls = CONTROL_CHARACTERS.sub(SEGMENT_REPLACEMENT, without_separators)
    collapsed = COLLAPSED_WHITESPACE.sub(" ", without_controls).strip(TRIMMED_EDGES)

    return _truncate_segment(value=collapsed, max_bytes=max_bytes) or fallback


def ascii_metadata_value(value: str) -> str:
    """
    Render a value so that it survives being stored as an attribute next to an object in the bucket.

    Those attributes travel as headers, which carry plain ASCII and nothing else, so a name written in any
    other alphabet is refused by the bucket rather than stored beside the file. Percent encoding it keeps the
    whole name readable and reversible instead of replacing the letters the bucket cannot spell.

    :param value: Value that is stored next to the object.
    :return: The value in a form the bucket accepts.
    """
    if not NON_ASCII_METADATA.search(value):
        return value

    return quote(value, safe="")


def _truncate_segment(value: str, max_bytes: int) -> str:
    """
    Cut a segment down to the size a file system allows, keeping the extension it ends with.

    :param value: Segment that may be too long.
    :param max_bytes: Largest size the encoded segment may take.
    :return: The segment within the allowed size.
    """
    if len(value.encode("utf-8")) <= max_bytes:
        return value

    suffix = file_suffix(file_name=value)
    tail = f"{SUFFIX_SEPARATOR}{suffix}" if suffix else ""
    stem = value[: -len(tail)] if tail else value
    room = max_bytes - len(tail.encode("utf-8"))

    return _cut_to_bytes(value=stem, max_bytes=room).strip(TRIMMED_EDGES) + tail


def _cut_to_bytes(value: str, max_bytes: int) -> str:
    """
    Cut a piece of text to a size measured in encoded bytes without ever splitting a letter in half.

    :param value: Text that is cut.
    :param max_bytes: Largest size the encoded text may take.
    :return: The longest prefix of the text that fits.
    """
    encoded = value.encode("utf-8")[: max(max_bytes, 0)]

    return encoded.decode("utf-8", errors="ignore")
