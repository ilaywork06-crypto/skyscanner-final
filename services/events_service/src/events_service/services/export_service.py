"""
The export of the current table view, handing the user the very rows they filtered as a sheet or as raw data.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import csv
import io
import json
import re
from datetime import datetime
from typing import Any

from pydantic_core import to_jsonable_python

from ag_grid_lib.columns import DYNAMIC_FIELD_PREFIX
from skyscanner_common.datetime_utils import utc_now
from skyscanner_models.common import Artifact
from skyscanner_models.enums import EntityStatus
from skyscanner_models.query import SearchQuery
from skyscanner_models.storage import ArchiveEntry, ArchiveRequest

from events_service.documents import EntityDocument, EventDocument
from events_service.repositories.event_repository import EventRepository
from events_service.services.grid_service import event_row

# ----- CONSTS ----- #

CSV_MEDIA_TYPE: str = "text/csv"
JSON_MEDIA_TYPE: str = "application/json"
JSON_FORMAT: str = "json"
EXPORT_LIMIT: int = 10000
LIST_JOIN: str = ", "
STAMP_FORMAT: str = "%Y%m%dT%H%M%SZ"
ARCHIVE_COLLECTION_NAME: str = "skyscanner-files"
UNSAFE_PATH_CHARACTERS: re.Pattern[str] = re.compile(r"[^A-Za-z0-9._-]+")

# The two shapes the sheet may take. The summary keeps one row per event and folds its entities into a few
# columns, which is what a reader of the inventory expects; the row per entity is for the reader who came for
# the telemetries themselves and accepts the event columns being repeated on every one of them.
ENTITY_MODE_SUMMARY: str = "summary"
ENTITY_MODE_ROWS: str = "rows"

# Everything read off the entities is written under one of these two prefixes, which keeps those columns apart
# from a dynamic event field that happens to be called name or status. The plural one carries what was counted
# over the whole set of entities of an event, the singular one carries the attributes of a single entity, and
# the difference between the two is exactly the difference between the two modes of the sheet.
ENTITY_SUMMARY_COLUMN_PREFIX: str = "entities_"
ENTITY_COLUMN_PREFIX: str = "entity_"
ENTITIES_KEY: str = "entities"

# ----- CLASSES ----- #


class ExportService:
    """
    Owner of the export, walking the whole result of a query instead of a single page of it.
    """

    def __init__(self, repository: EventRepository) -> None:
        """
        Bind the service to the repository the exported rows are read from.

        :param repository: Persistence of the events.
        """
        self._repository = repository

    async def export_events(
        self,
        query: SearchQuery,
        columns: list[str],
        export_format: str,
        event_ids: list[str] | None = None,
        entity_mode: str = ENTITY_MODE_SUMMARY,
    ) -> tuple[str, str, str]:
        """
        Materialise the events of the current view, and the entities nested inside them, in the asked format.

        An event is only half of what the user is looking at: the telemetries, logs and videos hanging off it
        carry their own status, origin, files and dynamic values, and an export that drops them hands over a
        sheet that answers none of the questions the entities were uploaded for. The two formats carry them
        differently, because a document nests and a sheet does not.

        JSON keeps the nesting the system itself has: every event object gains an entities list, and each
        entry of it describes one entity with its name, type, origin, status, code version, notes, the names
        and the amount of its files per role, its dynamic values and who created it when.

        CSV is flat, so the entities are folded into columns instead. The default summary mode keeps one row
        per event and appends the counted view of its entities - how many there are, their names, their types,
        their origins, how many files they hold together and how many of them sit in each status - which is
        what the reader of an inventory sheet wants, and which keeps the row count of the export equal to the
        amount of events. The row mode instead writes one row per entity, repeating the columns of the event
        on each of them and adding the attributes of the single entity, for the reader who came for the
        telemetries rather than for the events. The summary columns are named entities_ after the set they
        counted and the per entity ones entity_ after the single entity they describe. In both modes the
        columns the caller explicitly asked for stay exactly as they were asked for and lead the sheet, and
        the entity columns are appended behind them.

        :param query: Query the exported rows are read with, which is the view currently on screen.
        :param columns: Keys that end up as the columns of the export, all of them when empty.
        :param export_format: Either csv or json.
        :param event_ids: Events the export is narrowed to, empty to export the whole view.
        :param entity_mode: Whether a sheet summarises the entities per event or writes one row per entity.
        :return: The body of the export, its media type and the file name it is offered under.
        """
        documents = await self._repository.iterate(
            search=query,
            batch_size=EXPORT_LIMIT,
            identifiers=event_ids,
        )
        stamp = utc_now().strftime(STAMP_FORMAT)

        if export_format.lower() == JSON_FORMAT:
            body = _events_as_json(documents=documents, columns=columns)

            return body, JSON_MEDIA_TYPE, f"skyscanner-events-{stamp}.json"

        body = _events_as_csv(documents=documents, columns=columns, entity_mode=entity_mode)

        return body, CSV_MEDIA_TYPE, f"skyscanner-events-{stamp}.csv"


    async def build_archive_manifest(
        self,
        query: SearchQuery,
        event_ids: list[str] | None = None,
    ) -> ArchiveRequest:
        """
        Work out which stored files belong to a set of events and where each of them sits in an archive.

        The layout is one folder per event, and inside it the files of the event itself next to one folder
        per entity, each split by the role its files play. A reader who unpacks the archive therefore finds
        the same structure the event page shows, instead of a flat pile of names that collide.

        The archive of a single event is named after that event, because the file name is all that is left of
        the request once the download sits in a folder among the other downloads of the day. An archive that
        covers several events cannot name one of them, so it keeps the collection name; both carry the moment
        they were built, which is what tells two downloads of the same events apart.

        :param query: Query the events are read with, which is the view currently on screen.
        :param event_ids: Events the archive is narrowed to, empty to take the whole view.
        :return: The manifest the storage service builds the archive from.
        """
        documents = await self._repository.iterate(
            search=query,
            batch_size=EXPORT_LIMIT,
            identifiers=event_ids,
        )
        entries: list[ArchiveEntry] = []
        for document in documents:
            folder = _archive_folder(document=document)
            entries.extend(
                _entries_for(files=document.additional_files, folder=f"{folder}/additional_files"),
            )
            for entity in document.objects:
                entity_folder = f"{folder}/{_safe(entity.object_type_name)}/{_safe(entity.name)}"
                entries.extend(_entries_for(files=entity.raw_files, folder=f"{entity_folder}/raw_files"))
                entries.extend(_entries_for(files=entity.parsed_files, folder=f"{entity_folder}/parsed_files"))
                entries.extend(
                    _entries_for(
                        files=entity.parsed_additional_files,
                        folder=f"{entity_folder}/parsed_additional_files",
                    ),
                )

        stamp = utc_now().strftime(STAMP_FORMAT)
        name = _archive_folder(document=documents[0]) if len(documents) == 1 else ARCHIVE_COLLECTION_NAME

        return ArchiveRequest(entries=entries, archive_name=f"{name}-{stamp}.zip")


# ----- FUNCTIONS ----- #


def _events_as_json(documents: list[EventDocument], columns: list[str]) -> str:
    """
    Render the exported events as documents, keeping their entities nested the way the system stores them.

    :param documents: Events the export was read from.
    :param columns: Keys the caller asked for, all of them when empty.
    :return: The body of the export.
    """
    rows = [_flatten(row=event_row(document=document)) for document in documents]
    selected = columns or _collect_keys(rows=rows)
    payload = [
        {
            **{key: row.get(key) for key in selected},
            ENTITIES_KEY: [_entity_payload(entity=entity) for entity in document.objects],
        }
        for row, document in zip(rows, documents, strict=True)
    ]

    return json.dumps(payload, indent=2, default=str)


def _events_as_csv(documents: list[EventDocument], columns: list[str], entity_mode: str) -> str:
    """
    Render the exported events as a sheet, folding their entities into columns or into rows of their own.

    :param documents: Events the export was read from.
    :param columns: Keys the caller asked for, all of them when empty.
    :param entity_mode: Whether the entities are summarised per event or written as one row each.
    :return: The body of the export.
    """
    per_entity = entity_mode.lower() == ENTITY_MODE_ROWS
    rows: list[dict[str, Any]] = []
    # Which columns came from the entities is remembered while the rows are built rather than guessed from
    # their names afterwards: an event carries an entity_counts attribute of its own, and a guess would drag
    # that one into a selection the caller never asked it for.
    entity_keys: dict[str, None] = {}
    for document in documents:
        event = _flatten(row=event_row(document=document))
        if not per_entity:
            summary = _entity_summary(entities=document.objects)
            entity_keys.update(dict.fromkeys(summary))
            rows.append({**event, **summary})
            continue
        # An event without a single entity still belongs in the sheet, so it is written on its own rather
        # than disappearing with the rows its missing entities would have produced.
        if not document.objects:
            rows.append(event)
            continue
        for entity in document.objects:
            entity_columns = _entity_columns(entity=entity)
            entity_keys.update(dict.fromkeys(entity_columns))
            rows.append({**event, **entity_columns})

    selected = _selected_columns(columns=columns, rows=rows, entity_keys=list(entity_keys))
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=selected, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in selected})

    return buffer.getvalue()


def _selected_columns(columns: list[str], rows: list[dict[str, Any]], entity_keys: list[str]) -> list[str]:
    """
    Work out the columns of the sheet, honouring the ones the caller named before adding the entity ones.

    :param columns: Keys the caller asked for, all of them when empty.
    :param rows: Rows the sheet is written from.
    :param entity_keys: Keys the entities of the events contributed to those rows.
    :return: The columns of the sheet in the order they are written.
    """
    if not columns:
        return _collect_keys(rows=rows)

    # The caller names the columns of the table as it stands on screen, which is a table of events and knows
    # nothing about the entity columns. Appending them behind the asked for ones is therefore the only way the
    # entities reach the sheet at all, and it leaves the selection of the caller untouched.
    return columns + [key for key in entity_keys if key not in columns]


def _entity_summary(entities: list[EntityDocument]) -> dict[str, Any]:
    """
    Fold the entities of one event into the handful of columns a flat sheet can hold.

    :param entities: Entities nested inside the event.
    :return: The summary columns of the event, always under the same keys so the sheet keeps its shape.
    """
    counts: dict[EntityStatus, int] = {status: 0 for status in EntityStatus}
    file_count = 0
    for entity in entities:
        counts[entity.status] += 1
        file_count += len(entity.raw_files) + len(entity.parsed_files) + len(entity.parsed_additional_files)

    prefix = ENTITY_SUMMARY_COLUMN_PREFIX
    summary: dict[str, Any] = {
        f"{prefix}count": len(entities),
        f"{prefix}names": LIST_JOIN.join(entity.name for entity in entities),
        f"{prefix}types": LIST_JOIN.join(_unique(values=[item.object_type_name for item in entities])),
        f"{prefix}origins": LIST_JOIN.join(_unique(values=[item.origin or "" for item in entities])),
        f"{prefix}file_count": file_count,
    }
    summary.update({f"{prefix}status_{status.value}": counts[status] for status in EntityStatus})

    return summary


def _entity_columns(entity: EntityDocument) -> dict[str, Any]:
    """
    Spread one entity over the columns it takes on a row of its own.

    :param entity: Entity that is written as a row.
    :return: The entity columns of the row.
    """
    columns: dict[str, Any] = {
        f"{ENTITY_COLUMN_PREFIX}id": entity.object_id,
        f"{ENTITY_COLUMN_PREFIX}name": entity.name,
        f"{ENTITY_COLUMN_PREFIX}type": entity.object_type_name,
        f"{ENTITY_COLUMN_PREFIX}origin": entity.origin or "",
        f"{ENTITY_COLUMN_PREFIX}status": entity.status.value,
        f"{ENTITY_COLUMN_PREFIX}code_version": entity.code_version or "",
        f"{ENTITY_COLUMN_PREFIX}notes": entity.notes,
        f"{ENTITY_COLUMN_PREFIX}created_by": entity.created_by or "",
        f"{ENTITY_COLUMN_PREFIX}created_at": _moment(value=entity.created_at),
        f"{ENTITY_COLUMN_PREFIX}updated_at": _moment(value=entity.updated_at),
    }
    columns.update(_file_columns(prefix=f"{ENTITY_COLUMN_PREFIX}raw", files=entity.raw_files))
    columns.update(_file_columns(prefix=f"{ENTITY_COLUMN_PREFIX}parsed", files=entity.parsed_files))
    columns.update(
        _file_columns(prefix=f"{ENTITY_COLUMN_PREFIX}parsed_additional", files=entity.parsed_additional_files),
    )
    # The dynamic values of an entity carry the very keys the dynamic values of an event carry, so they are
    # written under a prefix of their own instead of overwriting the columns of the event they belong to.
    columns.update(
        {
            f"{ENTITY_COLUMN_PREFIX}{DYNAMIC_FIELD_PREFIX}_{key}": _stringify(value=value)
            for key, value in entity.data.items()
        },
    )

    return columns


def _file_columns(prefix: str, files: list[Artifact]) -> dict[str, Any]:
    """
    Describe one set of files of an entity as the pair of columns a sheet holds it in.

    :param prefix: Prefix naming the role the files play.
    :param files: Stored files of that role.
    :return: The names of the files and how many of them there are.
    """
    return {
        f"{prefix}_files": LIST_JOIN.join(artifact.name for artifact in files),
        f"{prefix}_file_count": len(files),
    }


def _entity_payload(entity: EntityDocument) -> dict[str, Any]:
    """
    Describe one entity as the document a reader of the JSON export expects to find under its event.

    :param entity: Entity that is described.
    :return: The document of the entity.
    """
    return {
        "entity_id": entity.object_id,
        "name": entity.name,
        "type": entity.object_type_name,
        "origin": entity.origin,
        "status": entity.status.value,
        "code_version": entity.code_version,
        "notes": entity.notes,
        "upload_source": entity.upload_source.value,
        "files": {
            "raw": _file_payload(files=entity.raw_files),
            "parsed": _file_payload(files=entity.parsed_files),
            "parsed_additional": _file_payload(files=entity.parsed_additional_files),
        },
        DYNAMIC_FIELD_PREFIX: to_jsonable_python(entity.data),
        "created_by": entity.created_by,
        "created_at": _moment(value=entity.created_at),
        "updated_at": _moment(value=entity.updated_at),
    }


def _file_payload(files: list[Artifact]) -> dict[str, Any]:
    """
    Describe one set of files of an entity as the document of the JSON export.

    :param files: Stored files of one role.
    :return: How many files the role holds and what they are called.
    """
    return {"count": len(files), "names": [artifact.name for artifact in files]}


def _moment(value: datetime | None) -> str:
    """
    Write a stored moment the way the rest of the export writes it, which is the ISO form or nothing at all.

    :param value: Moment read off an entity.
    :return: The moment as text, empty when the entity never carried one.
    """
    return value.isoformat() if value else ""


def _unique(values: list[str]) -> list[str]:
    """
    Keep the distinct values of a list in the order they first appear, dropping the empty ones.

    :param values: Values read off the entities of one event.
    :return: The distinct non empty values.
    """
    return list(dict.fromkeys(value for value in values if value))


def _archive_folder(document: EventDocument) -> str:
    """
    Build the top level folder one event takes inside an archive.

    :param document: Event the folder is built for.
    :return: The folder name, which leads with the running number so the folders sort the way the table does.
    """
    return _safe(f"event-{document.event_id}-{document.name}")


def _entries_for(files: list[Artifact], folder: str) -> list[ArchiveEntry]:
    """
    Place one set of files inside a folder of the archive, keeping their names apart when they collide.

    :param files: Stored files that are placed.
    :param folder: Folder inside the archive the files are placed in.
    :return: One entry per file.
    """
    entries: list[ArchiveEntry] = []
    seen: dict[str, int] = {}
    for artifact in files:
        name = _safe(artifact.name)
        count = seen.get(name, 0)
        seen[name] = count + 1
        placed = name if count == 0 else f"{count}-{name}"
        entries.append(ArchiveEntry(path=artifact.path, entry=f"{folder}/{placed}"))

    return entries


def _safe(value: str) -> str:
    """
    Turn a name into one that every unpacking tool accepts as a single path segment.

    :param value: Name read from an event, an entity or a file.
    :return: The name without separators or characters that break an archive entry.
    """
    cleaned = UNSAFE_PATH_CHARACTERS.sub("_", value).strip("._ ")

    return cleaned or "unnamed"


def _flatten(row: dict[str, Any]) -> dict[str, Any]:
    """
    Turn a nested row object into the flat mapping a sheet can hold.

    :param row: Row object produced for the grid.
    :return: The flat mapping of the row.
    """
    flat: dict[str, Any] = {}
    for key, value in row.items():
        if key == "data" and isinstance(value, dict):
            for dynamic_key, dynamic_value in value.items():
                flat[dynamic_key] = _stringify(value=dynamic_value)
            continue
        if key in {"metadata", "event_type"}:
            continue
        flat[key] = _stringify(value=value)

    return flat


def _stringify(value: Any) -> Any:
    """
    Turn a nested value into a single cell of a sheet.

    :param value: Value read from a row object.
    :return: The value as a scalar a sheet can hold.
    """
    if isinstance(value, list):
        return LIST_JOIN.join(_stringify(value=item) for item in value)

    if isinstance(value, dict):
        return str(value.get("name", json.dumps(value, default=str)))

    return value


def _collect_keys(rows: list[dict[str, Any]]) -> list[str]:
    """
    Collect every key that appears in at least one row, keeping the order of first appearance.

    :param rows: Flattened rows of the export.
    :return: The keys that become the columns of the export.
    """
    # The keys are collected in a mapping rather than in a list because an export of ten thousand events, each
    # of them spread over its entities, walks a lot of rows here, and a membership test against a list would
    # turn that walk into a quadratic one for no gain - a mapping keeps the insertion order just as well.
    keys: dict[str, None] = {}
    for row in rows:
        keys.update(dict.fromkeys(row))

    return list(keys)
