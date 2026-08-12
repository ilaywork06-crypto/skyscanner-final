"""
The rules around the stored files - where a file lands in the bucket and how it is read back afterwards.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import tempfile
import zipfile
from dataclasses import dataclass
from typing import AsyncIterator

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.errors import NotFoundError
from skyscanner_common.ids import new_id
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.object_storage import ObjectStorageClient, build_object_key
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
    One file as it arrived from the browser, already read into memory by the web layer.
    """

    file_name: str
    content: bytes
    content_type: str


class ArtifactService:
    """
    Owner of the stored files, turning an upload into the artifact record the inventory keeps.
    """

    def __init__(self, storage: ObjectStorageClient) -> None:
        """
        Bind the service to the client of the bucket.

        :param storage: Client of the object storage.
        """
        self._storage = storage

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
        artifacts: list[Artifact] = []
        for payload in payloads:
            path = build_object_key(
                prefix=owner_kind,
                identifier=owner_id or UNKNOWN_OWNER,
                file_name=f"{new_id()}_{payload.file_name}",
            )
            checksum = await self._storage.upload(
                path=path,
                payload=payload.content,
                content_type=payload.content_type or DEFAULT_CONTENT_TYPE,
                metadata={"original_name": payload.file_name, "kind": kind.value},
            )
            artifacts.append(
                Artifact(
                    id=new_id(),
                    name=payload.file_name,
                    path=path,
                    descriptor=descriptor,
                    kind=kind,
                    suffix=file_suffix(file_name=payload.file_name),
                    folder=folder,
                    source=f"upload://{owner_kind}/{owner_id or UNKNOWN_OWNER}",
                    size_bytes=len(payload.content),
                    content_type=payload.content_type or DEFAULT_CONTENT_TYPE,
                    checksum=checksum,
                    uploaded_by=uploaded_by,
                    created_at=utc_now(),
                ),
            )

        return artifacts

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
                    try:
                        payload = await self._storage.download(path=item.path)
                    except NotFoundError:
                        LOGGER.warning("The bucket no longer holds %s, leaving it out of the archive", item.path)
                        continue
                    archive.writestr(item.entry, payload)

            spool.seek(0)
            while True:
                chunk = spool.read(ARCHIVE_CHUNK_BYTES)
                if not chunk:
                    break
                yield chunk
        finally:
            spool.close()
