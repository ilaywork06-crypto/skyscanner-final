"""
Time helpers that keep every timestamp in the system timezone aware and expressed in UTC.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime, timezone

# ----- FUNCTIONS ----- #


def utc_now() -> datetime:
    """
    Read the current moment as a timezone aware UTC timestamp.

    :return: The current UTC moment.
    """
    return datetime.now(tz=timezone.utc)


def ensure_utc(value: datetime | None) -> datetime | None:
    """
    Attach the UTC timezone to a naive timestamp and convert an aware timestamp into UTC.

    :param value: Timestamp that may be naive, aware or missing.
    :return: The same moment expressed in UTC, or nothing when no timestamp was given.
    """
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)
