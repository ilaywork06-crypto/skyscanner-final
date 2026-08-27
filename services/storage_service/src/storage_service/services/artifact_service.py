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
from skyscanner_common.errors import NotFoundError
from skyscanner_common.ids import new_id
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.object_storage import ChunkReader, ObjectStorageClient, build_object_key
from skyscanner_common.settings import StorageSettings, get_storage_settings
from skyscanner_common.text import file_suffix
from skyscanner_models.common import Artifact
from skyscanner_models.enums import ArtifactKind
from skyscanner_models.storage import ArchiveRequest, DownloadLinkResponse, StorageObjectResponse

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

    def stream(self, path: str) -> AsyncIterator[bytes]:
        """
        Read a stored file back in chunks, so that a large file never sits in memory as a whole.

        :param path: Key the file is stored under.
        :return: An iterator over the chunks of the stored file.
        """
        return self._storage.stream(path=path)

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
