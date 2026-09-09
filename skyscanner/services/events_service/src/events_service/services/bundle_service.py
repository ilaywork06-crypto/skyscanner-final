"""
The bundle: an inventory written out whole, and read back in whole somewhere else.

:date: 2026-09-09
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import hashlib
import io
import json
import zipfile
from typing import Any, Iterable

from pydantic_core import to_jsonable_python

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.ids import new_id
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.text import file_suffix
from skyscanner_models.common import Artifact, UserContext
from skyscanner_models.query import SearchQuery
from skyscanner_models.storage import ArchiveDocument, ArchiveEntry, ArchiveRequest

from events_service.constants import (
    ENTITY_TYPE_KIND,
    EVENT_ID_COUNTER,
    EVENT_TYPE_KIND,
)
from events_service.documents import (
    EventDocument,
    FieldDocument,
    IndustryDocument,
    PlatformDocument,
    TypeDocument,
)
from events_service.repositories.counter_repository import CounterRepository
from events_service.repositories.event_repository import EventRepository
from events_service.repositories.field_repository import FieldRepository
from events_service.repositories.industry_repository import IndustryRepository
from events_service.repositories.platform_repository import PlatformRepository
from events_service.repositories.type_repository import TypeRepository
from events_service.services.storage_client import StorageClient, StoredFile

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)

# What marks an archive as one of these rather than as the plain folder of files the other export writes.
BUNDLE_FORMAT: str = "skyscanner.inventory.bundle"

# The revision of the manifest below, so that a bundle written today stays recognisable when it grows.
BUNDLE_VERSION: int = 1

# Where the description of everything in the archive sits, and where the bytes of the files sit beside it.
MANIFEST_ENTRY: str = "manifest.json"
FILES_FOLDER: str = "files"

# How many events one export walks. The same ceiling the sheet export uses, for the same reason.
BUNDLE_LIMIT: int = 10000

# How much of a bundle is accepted at all. A zip is read into a spooled file rather than into memory, but an
# import still has to hold one file at a time to hand it to the bucket, and a bundle larger than this is one
# somebody should be splitting rather than one this should be trying to swallow.
MAX_BUNDLE_BYTES: int = 8 * 1024 * 1024 * 1024

# How long the hash naming a file inside the archive is cut to. A bucket key is long and holds folders, so it
# cannot be an entry name; its hash can, and sixteen hexadecimal characters is far past what a single archive
# could collide in.
PATH_HASH_LENGTH: int = 16

# ----- CLASSES ----- #


class BundleSummary:
    """
    What a restore actually wrote, which is what the dialog on the other end reports.
    """

    def __init__(self) -> None:
        """
        Start a summary with nothing written and nothing refused.
        """
        self.events_created: int = 0
        self.events_skipped: int = 0
        self.industries_created: int = 0
        self.types_created: int = 0
        self.platforms_created: int = 0
        self.fields_created: int = 0
        self.files_restored: int = 0
        self.failures: list[str] = []

    def as_payload(self) -> dict[str, Any]:
        """
        Render the summary as the answer of the import endpoint.

        :return: The counts and the failures, as the client reads them.
        """
        return {
            "events_created": self.events_created,
            "events_skipped": self.events_skipped,
            "industries_created": self.industries_created,
            "types_created": self.types_created,
            "platforms_created": self.platforms_created,
            "fields_created": self.fields_created,
            "files_restored": self.files_restored,
            "failures": self.failures,
        }


class BundleService:
    """
    Owner of the bundle at both of its ends: writing the inventory out, and reading one back in.

    The two exports of this service answer two different questions and are deliberately different things.
    The sheet carries the columns that were on screen, flattened into the cells a sheet holds them in, which
    is what makes it something to read and useless for putting anything back: a flattened value has lost
    whether it was a number or the word for one, a hidden column has lost its values entirely, and a renamed
    header no longer says which key it came from.

    A bundle is the other thing. It carries the events exactly as they are stored - their entities, their
    dynamic values, their file records - and it carries the declarations those documents name by key: the
    industries, the types, the platforms and the fields. Without those a restored event names an industry
    that does not exist, is filed under a type nothing declares, and answers fields no form offers, which is
    a row in a table rather than an event in an inventory.

    And it carries the bytes. A file record is a name and a bucket key, and a bucket key from another
    installation names nothing at all, so the archive holds the file itself and the restore writes it into
    the bucket it is being restored into and rewrites the record to point at where it actually landed.
    """

    def __init__(
        self,
        events: EventRepository,
        industries: IndustryRepository,
        types: TypeRepository,
        platforms: PlatformRepository,
        fields: FieldRepository,
        counters: CounterRepository,
        storage: StorageClient,
    ) -> None:
        """
        Bind the service to every collection a bundle spans and to the service that holds the files.

        :param events: Persistence of the events.
        :param industries: Persistence of the industries.
        :param types: Persistence of the event and entity type declarations.
        :param platforms: Persistence of the platform declarations.
        :param fields: Persistence of the dynamic field declarations.
        :param counters: Keeper of the running event number.
        :param storage: The only way to the bucket from here, which is a service of its own.
        """
        self._events = events
        self._industries = industries
        self._types = types
        self._platforms = platforms
        self._fields = fields
        self._counters = counters
        self._storage = storage

    async def build_bundle(self, query: SearchQuery, event_ids: list[str] | None = None) -> ArchiveRequest:
        """
        Describe the archive that carries the current view whole, files and declarations included.

        The manifest is written here and the archive is built by the storage service, because only this
        service knows what an event is and only that one may read the bucket. The manifest travels as a
        document of the archive rather than as a second download, so a bundle is one file.

        Only the declarations the exported events actually name are carried. A bundle of one industry's
        events that dragged every field declaration of every other industry along with it would restore into
        a system holding columns nobody asked for, and would do it silently.

        :param query: Query the exported events are read with, which is the view currently on screen.
        :param event_ids: Events the bundle is narrowed to, empty to take the whole view.
        :return: The manifest of the archive, ready for the storage service to build.
        """
        documents = await self._events.iterate(search=query, batch_size=BUNDLE_LIMIT, identifiers=event_ids)
        files = _collect_files(documents=documents)

        manifest = {
            "format": BUNDLE_FORMAT,
            "version": BUNDLE_VERSION,
            "created_at": utc_now().isoformat(),
            "industries": await self._referenced_industries(documents=documents),
            "types": await self._referenced_types(documents=documents),
            "platforms": await self._referenced_platforms(documents=documents),
            "fields": await self._referenced_fields(documents=documents),
            "events": [to_jsonable_python(document.model_dump(by_alias=True)) for document in documents],
            # The bucket key of a file is what an event points at and what the archive has to be looked up
            # by, so the map is written the way the restore reads it: from the key it found on a record to
            # the entry the bytes are actually in.
            "files": {path: entry for path, (entry, _) in files.items()},
        }

        stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")

        return ArchiveRequest(
            entries=[ArchiveEntry(path=path, entry=entry) for path, (entry, _) in files.items()],
            documents=[
                ArchiveDocument(entry=MANIFEST_ENTRY, content=json.dumps(manifest, indent=2, default=str)),
            ],
            archive_name=f"skyscanner-bundle-{stamp}.zip",
        )

    async def restore_bundle(self, payload: bytes, user: UserContext) -> dict[str, Any]:
        """
        Read a bundle back in, writing everything in it that is not already here.

        The order is not a preference. An event names its industry, its types, its platforms and its fields
        by key, and a key that has not been declared yet is a column no form offers and a chip no page can
        colour - so the declarations are written first and the events afterwards.

        One event that fails does not stop the rest. A bundle is a great many independent writes and the
        only two honest behaviours are to stop at the first refusal and leave a half restored inventory
        unexplained, or to write everything that can be written and say exactly what could not. This does
        the second, and the summary names every failure.

        :param payload: The bundle, as the bytes of the uploaded archive.
        :param user: Identity the restore is performed on behalf of and its files attributed to.
        :return: What was written, what was left alone and what could not be written.
        :raises ValueError: When the upload is not a readable bundle at all.
        """
        summary = BundleSummary()

        try:
            archive = zipfile.ZipFile(io.BytesIO(payload))
        except zipfile.BadZipFile as error:
            raise ValueError("The uploaded file is not an archive") from error

        with archive:
            manifest = _read_manifest(archive=archive)

            await self._restore_industries(manifest=manifest, summary=summary)
            await self._restore_platforms(manifest=manifest, summary=summary)
            await self._restore_types(manifest=manifest, summary=summary)
            await self._restore_fields(manifest=manifest, summary=summary)

            restored_files = await self._restore_files(
                archive=archive,
                manifest=manifest,
                user=user,
                summary=summary,
            )
            await self._restore_events(manifest=manifest, files=restored_files, summary=summary)

        return summary.as_payload()

    async def _referenced_industries(self, documents: list[EventDocument]) -> list[dict[str, Any]]:
        """
        Read the industries the exported events are filed under.

        :param documents: Events the bundle carries.
        :return: The industry declarations, as documents.
        """
        keys = {document.industry for document in documents if document.industry}
        found = [await self._industries.find_by_key(key=key) for key in sorted(keys)]

        return [to_jsonable_python(item.model_dump(by_alias=True)) for item in found if item is not None]

    async def _referenced_platforms(self, documents: list[EventDocument]) -> list[dict[str, Any]]:
        """
        Read the platforms the exported events ran on.

        :param documents: Events the bundle carries.
        :return: The platform declarations, as documents.
        """
        keys = {key for document in documents for key in document.platforms if key}
        found = [await self._platforms.find_by_key(key=key) for key in sorted(keys)]

        return [to_jsonable_python(item.model_dump(by_alias=True)) for item in found if item is not None]

    async def _referenced_types(self, documents: list[EventDocument]) -> list[dict[str, Any]]:
        """
        Read the event and entity types the exported events and their entities are instances of.

        :param documents: Events the bundle carries.
        :return: The type declarations, as documents.
        """
        event_keys = {key for document in documents for key in document.event_type_keys if key}
        entity_keys = {
            entity.object_type_key
            for document in documents
            for entity in document.live_objects
            if entity.object_type_key
        }

        found: list[TypeDocument | None] = []
        for key in sorted(event_keys):
            found.append(await self._types.find_by_key(kind=EVENT_TYPE_KIND, key=key))
        for key in sorted(entity_keys):
            found.append(await self._types.find_by_key(kind=ENTITY_TYPE_KIND, key=key))

        return [to_jsonable_python(item.model_dump(by_alias=True)) for item in found if item is not None]

    async def _referenced_fields(self, documents: list[EventDocument]) -> list[dict[str, Any]]:
        """
        Read the dynamic field declarations the exported events and their entities answer.

        A field is looked up by the key an event actually carries a value under, so a declaration nobody in
        this view ever filled in is left behind. That is deliberate: a bundle describes the events it holds,
        not the schema of the system it came from.

        :param documents: Events the bundle carries.
        :return: The field declarations, as documents.
        """
        keys = {key for document in documents for key in document.data}
        keys.update(key for document in documents for entity in document.live_objects for key in entity.data)

        declared = await self._fields.find_many(query={"key": {"$in": sorted(keys)}}) if keys else []

        return [to_jsonable_python(item.model_dump(by_alias=True)) for item in declared]

    async def _restore_industries(self, manifest: dict[str, Any], summary: BundleSummary) -> None:
        """
        Declare the industries of the bundle that this system does not have.

        :param manifest: What the bundle says it holds.
        :param summary: Tally the restore is reported through.
        """
        for raw in _documents_of(manifest, "industries"):
            try:
                document = IndustryDocument.model_validate(raw)
                if await self._industries.find_by_key(key=document.key) is not None:
                    continue
                await self._industries.insert(document)
                summary.industries_created += 1
            except Exception as error:  # pylint: disable=broad-exception-caught
                summary.failures.append(f"industry {raw.get('key', '?')}: {error}")

    async def _restore_platforms(self, manifest: dict[str, Any], summary: BundleSummary) -> None:
        """
        Declare the platforms of the bundle that this system does not have.

        :param manifest: What the bundle says it holds.
        :param summary: Tally the restore is reported through.
        """
        for raw in _documents_of(manifest, "platforms"):
            try:
                document = PlatformDocument.model_validate(raw)
                if await self._platforms.find_by_key(key=document.key) is not None:
                    continue
                await self._platforms.insert(document)
                summary.platforms_created += 1
            except Exception as error:  # pylint: disable=broad-exception-caught
                summary.failures.append(f"platform {raw.get('key', '?')}: {error}")

    async def _restore_types(self, manifest: dict[str, Any], summary: BundleSummary) -> None:
        """
        Declare the event and entity types of the bundle that this system does not have.

        :param manifest: What the bundle says it holds.
        :param summary: Tally the restore is reported through.
        """
        for raw in _documents_of(manifest, "types"):
            try:
                document = TypeDocument.model_validate(raw)
                if await self._types.find_by_key(kind=document.kind, key=document.key) is not None:
                    continue
                await self._types.insert(document)
                summary.types_created += 1
            except Exception as error:  # pylint: disable=broad-exception-caught
                summary.failures.append(f"type {raw.get('key', '?')}: {error}")

    async def _restore_fields(self, manifest: dict[str, Any], summary: BundleSummary) -> None:
        """
        Declare the dynamic fields of the bundle that this system does not have.

        A field is the one declaration whose key is not unique on its own: the same key is declared once for
        the events of an industry and again for its entities, and the two are different columns holding
        different things. It is therefore looked up by everything that makes it what it is.

        :param manifest: What the bundle says it holds.
        :param summary: Tally the restore is reported through.
        """
        for raw in _documents_of(manifest, "fields"):
            try:
                document = FieldDocument.model_validate(raw)
                existing = await self._fields.find_by_key(
                    key=document.key,
                    scope=document.scope,
                    industry=document.industry,
                    entity_type=document.entity_type,
                )
                if existing is not None:
                    continue
                await self._fields.insert(document)
                summary.fields_created += 1
            except Exception as error:  # pylint: disable=broad-exception-caught
                summary.failures.append(f"field {raw.get('key', '?')}: {error}")

    async def _restore_files(
        self,
        archive: zipfile.ZipFile,
        manifest: dict[str, Any],
        user: UserContext,
        summary: BundleSummary,
    ) -> dict[str, StoredFile]:
        """
        Write every file of the bundle into this system's bucket and say where each of them landed.

        A bucket key from another installation names nothing here, so nothing about the old key is kept
        beyond using it to find the bytes in the archive and to recognise the same file on every record that
        pointed at it. A file referenced by three entities is written once and all three are pointed at the
        one copy, which is exactly what the old key meant.

        :param archive: The bundle, opened.
        :param manifest: What the bundle says it holds.
        :param user: Identity the restore is performed on behalf of and its files attributed to.
        :param summary: Tally the restore is reported through.
        :return: Where each file of the bundle now lives, by the key it used to live under.
        """
        wanted = manifest.get("files")
        if not isinstance(wanted, dict):
            return {}

        names = set(archive.namelist())
        names_by_path = _names_by_path(manifest=manifest)
        restored: dict[str, StoredFile] = {}

        for old_path, entry in wanted.items():
            if not isinstance(old_path, str) or not isinstance(entry, str) or entry not in names:
                summary.failures.append(f"file {old_path}: not in the archive")
                continue

            try:
                content = archive.read(entry)
                stored = await self._storage.upload(
                    file_name=names_by_path.get(old_path) or entry.rsplit("/", maxsplit=1)[-1],
                    content=content,
                    user=user,
                )
                restored[old_path] = stored
                summary.files_restored += 1
            except Exception as error:  # pylint: disable=broad-exception-caught
                summary.failures.append(f"file {old_path}: {error}")

        return restored

    async def _restore_events(
        self,
        manifest: dict[str, Any],
        files: dict[str, StoredFile],
        summary: BundleSummary,
    ) -> None:
        """
        Write the events of the bundle, pointed at the files that were just restored.

        An event keeps its identifier and its running number when nothing here is already using either, so a
        restore into an empty system reproduces the inventory exactly as it was - the same numbers on the
        same rows, which is what makes a link somebody wrote down still lead where it led. Restoring into a
        system that already holds that number is a merge rather than a restore, and there the event is given
        one of its own; there is nothing else it could be given.

        :param manifest: What the bundle says it holds.
        :param files: Where each file of the bundle now lives, by the key it used to live under.
        :param summary: Tally the restore is reported through.
        """
        highest = 0

        for raw in _documents_of(manifest, "events"):
            try:
                document = EventDocument.model_validate(raw)
            except Exception as error:  # pylint: disable=broad-exception-caught
                summary.failures.append(f"event {raw.get('name', '?')}: {error}")
                continue

            try:
                if await self._events.find_by_id(document.id) is not None:
                    summary.events_skipped += 1
                    continue

                _repoint_files(document=document, files=files)
                document.event_id = await self._free_event_number(wanted=document.event_id)
                highest = max(highest, document.event_id)

                await self._events.insert(document)
                summary.events_created += 1
            except Exception as error:  # pylint: disable=broad-exception-caught
                summary.failures.append(f"event {document.name or document.id}: {error}")

        # The counter is lifted past everything that was just restored, so the next event created by hand
        # gets a number of its own rather than one a restored event is already using.
        if highest:
            await self._counters.set_minimum(name=EVENT_ID_COUNTER, minimum=highest)

    async def _free_event_number(self, wanted: int) -> int:
        """
        Keep the running number an event came in with, unless this system already gave it to something else.

        :param wanted: The number the event carried in the bundle.
        :return: That number, or a fresh one when it is taken.
        """
        if wanted > 0 and await self._events.find_one({"event_id": wanted}) is None:
            return wanted

        return await self._counters.next_value(name=EVENT_ID_COUNTER)


# ----- FUNCTIONS ----- #


def _collect_files(documents: list[EventDocument]) -> dict[str, tuple[str, Artifact]]:
    """
    Work out which stored files the exported events point at and what each of them is called in the archive.

    A file is collected by its bucket key rather than by the record that names it, so a file referenced by
    an event and by two of its entities is carried once. The entry is named after a hash of that key,
    because the key holds folders and an entry name cannot.

    :param documents: Events the bundle carries.
    :return: One entry per distinct file, by the key it is stored under.
    """
    collected: dict[str, tuple[str, Artifact]] = {}

    for document in documents:
        for artifact in _artifacts_of(document):
            if artifact.path in collected:
                continue
            digest = hashlib.sha1(artifact.path.encode("utf-8")).hexdigest()[:PATH_HASH_LENGTH]
            suffix = file_suffix(artifact.name)
            entry = f"{FILES_FOLDER}/{digest}{f'.{suffix}' if suffix else ''}"
            collected[artifact.path] = (entry, artifact)

    return collected


def _artifacts_of(document: EventDocument) -> Iterable[Artifact]:
    """
    Walk every file record of one event, its own and those of every entity nested inside it.

    :param document: Event the records are read from.
    :return: Every artifact the event points at.
    """
    yield from document.additional_files
    for entity in document.objects:
        yield from entity.raw_files
        yield from entity.parsed_files
        yield from entity.parsed_additional_files


def _repoint_files(document: EventDocument, files: dict[str, StoredFile]) -> None:
    """
    Point every file record of a restored event at the copy that was just written into this system's bucket.

    A record whose bytes could not be restored is left pointing at the key it came in with. That key names
    nothing here, so the file cannot be opened - but the record still says the file existed, what it was
    called and how large it was, which is a truer account of the event than quietly dropping it.

    :param document: Event whose records are repointed.
    :param files: Where each file of the bundle now lives, by the key it used to live under.
    """
    for artifact in _artifacts_of(document):
        stored = files.get(artifact.path)
        if stored is None:
            continue

        artifact.id = new_id()
        artifact.path = stored.path
        artifact.size_bytes = stored.size_bytes
        artifact.checksum = stored.checksum
        artifact.content_type = stored.content_type or artifact.content_type


def _names_by_path(manifest: dict[str, Any]) -> dict[str, str]:
    """
    Work out what each file of a bundle was called, by the key it was stored under.

    The name lives on the file records rather than in the file map, because that is where it lives in the
    inventory itself; the map holds only where the bytes are. It is gathered in one pass rather than
    searched for per file: a bundle of ten thousand events holds tens of thousands of records, and a scan
    per file would turn a restore into a walk of the manifest for every byte it writes.

    :param manifest: What the bundle says it holds.
    :return: The name of each file, by the key it was stored under.
    """
    names: dict[str, str] = {}
    for event in _documents_of(manifest, "events"):
        for record in _raw_artifacts_of(event):
            path = record.get("path")
            name = record.get("name")
            if isinstance(path, str) and isinstance(name, str) and path not in names:
                names[path] = name

    return names


def _raw_artifacts_of(event: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """
    Walk the file records of one event as the manifest wrote them, before anything has been validated.

    :param event: Event as it sits in the manifest.
    :return: Every file record the event carries.
    """
    for record in event.get("additional_files") or []:
        if isinstance(record, dict):
            yield record

    for entity in event.get("objects") or []:
        if not isinstance(entity, dict):
            continue
        for key in ("raw_files", "parsed_files", "parsed_additional_files"):
            for record in entity.get(key) or []:
                if isinstance(record, dict):
                    yield record


def _read_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    """
    Read the description of the archive, and say plainly when the archive is not a bundle.

    The format marker is checked rather than assumed, because the alternative is an import that accepts any
    zip at all, reports that it held nothing, and leaves the person who picked it to work out that they
    picked the folder of loose files the other export writes.

    :param archive: The uploaded archive, opened.
    :return: What the bundle says it holds.
    :raises ValueError: When the archive carries no manifest, or one of another format.
    """
    if MANIFEST_ENTRY not in archive.namelist():
        raise ValueError("The archive carries no manifest, so it is not a bundle")

    try:
        manifest = json.loads(archive.read(MANIFEST_ENTRY))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("The manifest of the archive could not be read") from error

    if not isinstance(manifest, dict) or manifest.get("format") != BUNDLE_FORMAT:
        raise ValueError("The archive is not a bundle this inventory can read")

    return manifest


def _documents_of(manifest: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """
    Read one list of documents out of a manifest, tolerating a bundle that was edited by hand.

    :param manifest: What the bundle says it holds.
    :param key: Which list is read.
    :return: The documents of that list, with anything that is not one left out.
    """
    values = manifest.get(key)
    if not isinstance(values, list):
        return []

    return [value for value in values if isinstance(value, dict)]
