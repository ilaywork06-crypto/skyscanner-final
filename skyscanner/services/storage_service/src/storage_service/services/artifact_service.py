"""
The rules around the stored files - where a file lands in the bucket and how it is read back afterwards.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import asyncio
import tempfile
import zipfile
from dataclasses import dataclass
from typing import AsyncIterator

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.errors import NotFoundError, ValidationError
from skyscanner_common.ids import new_id
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.object_storage import (
    MAXIMUM_PARTS,
    MINIMUM_PART_BYTES,
    ChunkReader,
    ObjectStorageClient,
    build_object_key,
)
from skyscanner_common.settings import StorageSettings, get_storage_settings
from skyscanner_common.text import file_suffix
from skyscanner_models.common import Artifact
from skyscanner_models.enums import ArtifactKind
from skyscanner_models.storage import (
    ArchiveRequest,
    DownloadLinkResponse,
    StorageObjectResponse,
    UploadBeginRequest,
    UploadBeginResponse,
    UploadCompleteRequest,
    UploadPart,
    UploadStatusResponse,
)

from storage_service.constants import DEFAULT_CONTENT_TYPE, DEFAULT_OWNER_KIND, UNKNOWN_OWNER

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)

# Where the archive stops living in memory and moves to disk, and how much of it is handed over at a time.
ARCHIVE_SPOOL_BYTES: int = 64 * 1024 * 1024
ARCHIVE_CHUNK_BYTES: int = 1024 * 1024

# ----- CLASSES ----- #


@dataclass(frozen=True)
class UploadPayload:
    """
    One file as it arrived from the browser, offered as a source of bytes rather than as the bytes themselves.

    A file used to be read into memory in full before anything was written, which made the memory one upload
    costs the size of the files it carried - and a browser dropping a few gigabytes of telemetry onto the
    system was exactly the request that ended it. The web layer hands over the way to read the file instead,
    and the bucket is fed from it piece by piece.
    """

    file_name: str
    read: ChunkReader
    content_type: str


class ArtifactService:
    """
    Owner of the stored files, turning an upload into the artifact record the inventory keeps.
    """

    def __init__(self, storage: ObjectStorageClient, settings: StorageSettings | None = None) -> None:
        """
        Bind the service to the client of the bucket.

        :param storage: Client of the object storage.
        :param settings: Settings of the bucket, read from the environment when the caller names none.
        """
        self._storage = storage
        self._settings = settings or get_storage_settings()

    async def upload(
        self,
        payloads: list[UploadPayload],
        owner_kind: str = DEFAULT_OWNER_KIND,
        owner_id: str | None = None,
        kind: ArtifactKind = ArtifactKind.ADDITIONAL,
        folder: str | None = None,
        descriptor: str = "",
        uploaded_by: str | None = None,
    ) -> list[Artifact]:
        """
        Write every uploaded file into the bucket and describe it as an artifact record.

        :param payloads: Files as they arrived from the browser.
        :param owner_kind: Top level folder of the key, telling events and entities apart.
        :param owner_id: Identifier of the owner the files belong to, if it is known already.
        :param kind: Role the files play for their owner.
        :param folder: Virtual folder used to group the files in the table.
        :param descriptor: Free text describing what the files hold.
        :param uploaded_by: Caller the files are written on behalf of, empty when nobody was resolved.
        :return: The artifact records of the written files.
        :raises StorageError: When the object storage refused a write.
        """
        limit = asyncio.Semaphore(self._settings.upload_concurrency)

        async def write(payload: UploadPayload) -> Artifact:
            """
            Write one of the picked files, waiting for a place among the ones already being written.

            :param payload: File as it arrived from the browser.
            :return: The artifact record of the written file.
            """
            async with limit:
                return await self._write_one(
                    payload=payload,
                    owner_kind=owner_kind,
                    owner_id=owner_id,
                    kind=kind,
                    folder=folder,
                    descriptor=descriptor,
                    uploaded_by=uploaded_by,
                )

        # The order of the answer follows the order the files were picked in, whatever order they landed in.
        return list(await asyncio.gather(*(write(payload) for payload in payloads)))

    async def _write_one(
        self,
        payload: UploadPayload,
        owner_kind: str,
        owner_id: str | None,
        kind: ArtifactKind,
        folder: str | None,
        descriptor: str,
        uploaded_by: str | None,
    ) -> Artifact:
        """
        Write a single uploaded file into the bucket and describe it as an artifact record.

        :param payload: File as it arrived from the browser.
        :param owner_kind: Top level folder of the key, telling events and entities apart.
        :param owner_id: Identifier of the owner the file belongs to, if it is known already.
        :param kind: Role the file plays for its owner.
        :param folder: Virtual folder used to group the files in the table.
        :param descriptor: Free text describing what the file holds.
        :param uploaded_by: Caller the file is written on behalf of, empty when nobody was resolved.
        :return: The artifact record of the written file.
        :raises StorageError: When the object storage refused the write.
        """
        content_type = payload.content_type or DEFAULT_CONTENT_TYPE
        path = build_object_key(
            prefix=owner_kind,
            identifier=owner_id or UNKNOWN_OWNER,
            file_name=f"{new_id()}_{payload.file_name}",
        )
        checksum, size = await self._storage.upload_stream(
            path=path,
            reader=payload.read,
            content_type=content_type,
            metadata={"original_name": payload.file_name, "kind": kind.value},
        )

        return Artifact(
            id=new_id(),
            name=payload.file_name,
            path=path,
            descriptor=descriptor,
            kind=kind,
            suffix=file_suffix(file_name=payload.file_name),
            folder=folder,
            source=f"upload://{owner_kind}/{owner_id or UNKNOWN_OWNER}",
            size_bytes=size,
            content_type=content_type,
            checksum=checksum,
            uploaded_by=uploaded_by,
            created_at=utc_now(),
        )

    async def begin_upload(self, request: UploadBeginRequest) -> UploadBeginResponse:
        """
        Open an upload the browser drives itself, and tell it where to write and how large a part is.

        The one request per file shape is what a very large file cannot survive: a connection that drops
        after thirty of forty gigabytes costs all thirty, and nothing about the protocol lets the browser
        pick the wait back up. An upload opened here is written part by part instead - each part its own
        request, each one retried on its own, and the whole thing resumable from whatever landed.

        :param request: What the file is called and who it will belong to.
        :return: The identifier of the opened upload, the key it will land under and the size of one part.
        :raises StorageError: When the object storage refused to open the upload.
        """
        path = build_object_key(
            prefix=request.owner_kind,
            identifier=request.owner_id or UNKNOWN_OWNER,
            file_name=f"{new_id()}_{request.file_name}",
        )
        upload_id = await self._storage.begin_multipart(
            path=path,
            content_type=request.content_type or DEFAULT_CONTENT_TYPE,
            metadata={"original_name": request.file_name, "kind": request.kind.value},
        )

        return UploadBeginResponse(
            upload_id=upload_id,
            path=path,
            part_size=self._part_size,
            max_parts=MAXIMUM_PARTS,
        )

    async def write_upload_part(self, path: str, upload_id: str, number: int, chunk: bytes) -> UploadPart:
        """
        Write one part of an upload the browser is driving.

        :param path: Key the file is being stored under.
        :param upload_id: Identifier of the opened upload.
        :param number: One based position of the part inside the file.
        :param chunk: Bytes the part carries.
        :return: The part as the bucket recorded it.
        :raises ValidationError: When the part is numbered outside what the protocol allows.
        :raises StorageError: When the object storage refused the part.
        """
        if number < 1 or number > MAXIMUM_PARTS:
            raise ValidationError(
                message="The part is numbered outside the upload",
                details={"part": str(number), "most": str(MAXIMUM_PARTS)},
            )

        etag = await self._storage.write_part(path=path, upload_id=upload_id, number=number, chunk=chunk)

        return UploadPart(number=number, etag=etag, size_bytes=len(chunk))

    async def upload_status(self, path: str, upload_id: str) -> UploadStatusResponse:
        """
        Read back which parts of an upload already landed, which is what a browser resumes from.

        :param path: Key the file is being stored under.
        :param upload_id: Identifier of the opened upload.
        :return: Every part the bucket is already holding.
        :raises NotFoundError: When the upload is not open any more.
        :raises StorageError: When the object storage refused the listing.
        """
        stored = await self._storage.stored_parts(path=path, upload_id=upload_id)

        return UploadStatusResponse(
            upload_id=upload_id,
            path=path,
            parts=[UploadPart(number=number, etag=etag, size_bytes=size) for number, etag, size in stored],
        )

    async def complete_upload(
        self,
        upload_id: str,
        request: UploadCompleteRequest,
        uploaded_by: str | None = None,
    ) -> Artifact:
        """
        Join the parts of a driven upload into one stored file and describe it as an artifact record.

        The size is read back off the bucket rather than believed from the browser, because the parts were
        written across many requests and the only account of what actually landed is the one the bucket
        keeps. That reading is also what refuses an upload whose parts never all arrived.

        :param upload_id: Identifier of the opened upload.
        :param request: The parts of the file together with everything describing it.
        :param uploaded_by: Caller the file is written on behalf of, empty when nobody was resolved.
        :return: The artifact record of the finished file.
        :raises ValidationError: When the upload names no parts at all.
        :raises StorageError: When the object storage refused to finish the upload.
        """
        if not request.parts:
            raise ValidationError(
                message="The upload carries no parts",
                details={"upload_id": upload_id, "path": request.path},
            )

        checksum = await self._storage.complete_multipart(
            path=request.path,
            upload_id=upload_id,
            parts=[(part.number, part.etag) for part in request.parts],
        )
        stored = await self._storage.head(path=request.path)
        content_type = request.content_type or DEFAULT_CONTENT_TYPE

        return Artifact(
            id=new_id(),
            name=request.file_name,
            path=request.path,
            descriptor=request.descriptor,
            kind=request.kind,
            suffix=file_suffix(file_name=request.file_name),
            folder=request.folder,
            source=f"upload://{request.owner_kind}/{request.owner_id or UNKNOWN_OWNER}",
            size_bytes=int(stored.get("ContentLength", 0)),
            content_type=content_type,
            checksum=checksum,
            uploaded_by=uploaded_by,
            created_at=utc_now(),
        )

    async def abort_upload(self, path: str, upload_id: str) -> None:
        """
        Give up an upload the browser was driving, so the parts already written leave the bucket.

        :param path: Key the file was being stored under.
        :param upload_id: Identifier of the opened upload.
        """
        await self._storage.abort_multipart(path=path, upload_id=upload_id)

    @property
    def _part_size(self) -> int:
        """
        How many bytes one part of a driven upload carries, never below what the protocol allows.

        :return: The size of one part in bytes.
        """
        return max(self._settings.multipart_chunk_bytes, MINIMUM_PART_BYTES)

    async def download_link(self, path: str, name: str | None = None) -> DownloadLinkResponse:
        """
        Mint a temporary link that lets the browser read one stored file straight from the bucket.

        :param path: Key the file is stored under.
        :param name: Name the browser should save the download as.
        :return: The link together with the moment it stops working.
        :raises NotFoundError: When the bucket does not hold the key.
        :raises StorageError: When the link could not be minted.
        """
        metadata = await self._storage.head(path=path)
        file_name = name or path.rsplit("/", maxsplit=1)[-1]
        url, ttl = await self._storage.presigned_url(path=path, file_name=file_name)

        return DownloadLinkResponse(
            url=url,
            name=file_name,
            content_type=str(metadata.get("ContentType", DEFAULT_CONTENT_TYPE)),
            expires_at=utc_now() + ttl,
        )

    async def describe(self, path: str) -> StorageObjectResponse:
        """
        Read the metadata the bucket keeps for one stored file.

        :param path: Key the file is stored under.
        :return: The metadata of the stored file.
        :raises NotFoundError: When the bucket does not hold the key.
        :raises StorageError: When the object storage refused the lookup.
        """
        metadata = await self._storage.head(path=path)

        return StorageObjectResponse(
            path=path,
            size_bytes=int(metadata.get("ContentLength", 0)),
            content_type=str(metadata.get("ContentType", DEFAULT_CONTENT_TYPE)),
            checksum=str(metadata.get("ETag", "")).strip('"') or None,
            last_modified=metadata.get("LastModified"),
        )

    def stream(self, path: str, start: int | None = None, end: int | None = None) -> AsyncIterator[bytes]:
        """
        Read a stored file back in chunks, so that a large file never sits in memory as a whole.

        :param path: Key the file is stored under.
        :param start: First byte that is wanted, counted from zero, or nothing for the beginning.
        :param end: Last byte that is wanted, included, or nothing for the end of the file.
        :return: An iterator over the chunks of the requested window.
        """
        return self._storage.stream(path=path, start=start, end=end)

    async def delete(self, path: str) -> None:
        """
        Remove one stored file from the bucket.

        :param path: Key the file is stored under.
        :raises StorageError: When the object storage refused the deletion.
        """
        await self._storage.delete(path=path)

    async def build_archive(self, request: ArchiveRequest) -> AsyncIterator[bytes]:
        """
        Pack a set of stored files into one archive, laid out the way the manifest describes.

        The archive is assembled into a spooled temporary file rather than into memory: a request for the
        files of a hundred events is exactly the request that would otherwise exhaust the process, and the
        spool moves to disk once it outgrows its buffer. A file the bucket no longer holds is skipped, so
        one missing object costs its own entry rather than the whole download.

        :param request: Files the archive holds and the path each of them takes inside it.
        :return: An iterator over the chunks of the finished archive.
        """
        spool = tempfile.SpooledTemporaryFile(max_size=ARCHIVE_SPOOL_BYTES)
        try:
            with zipfile.ZipFile(spool, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
                for item in request.entries:
                    await self._write_entry(archive=archive, path=item.path, entry=item.entry)

            spool.seek(0)
            while True:
                chunk = spool.read(ARCHIVE_CHUNK_BYTES)
                if not chunk:
                    break
                yield chunk
        finally:
            spool.close()

    async def _write_entry(self, archive: zipfile.ZipFile, path: str, entry: str) -> None:
        """
        Copy one stored file into the archive without ever holding the whole of it in memory.

        A file the bucket no longer holds is skipped, so one missing object costs its own entry rather than
        the whole download.

        :param archive: Archive the file is written into.
        :param path: Key the file is stored under.
        :param entry: Path the file takes inside the archive.
        """
        try:
            stream = self._storage.stream(path=path)
            # The entry is opened only once the bucket has answered, so a missing object leaves no empty
            # entry of its own name behind in the archive.
            first = await anext(stream, None)
        except NotFoundError:
            LOGGER.warning("The bucket no longer holds %s, leaving it out of the archive", path)

            return

        with archive.open(entry, mode="w") as target:
            if first is not None:
                target.write(first)
            async for chunk in stream:
                target.write(chunk)
