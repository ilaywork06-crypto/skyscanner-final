"""
Identifier helpers, so that every document in the system is addressed by the very same kind of key.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from uuid import UUID, uuid4

# ----- FUNCTIONS ----- #


def new_id() -> str:
    """
    Mint a fresh random identifier for a document.

    :return: A newly generated identifier in its canonical text form.
    """
    return str(uuid4())


def is_valid_id(value: str) -> bool:
    """
    Check whether a piece of text is a well formed document identifier.

    :param value: Text that is expected to hold an identifier.
    :return: Whether the text can be parsed as an identifier.
    """
    try:
        UUID(value)
    except ValueError:
        return False

    return True
