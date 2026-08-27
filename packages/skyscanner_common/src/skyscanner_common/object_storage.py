"""
Asynchronous access to the bucket that keeps every uploaded file, covering uploads, reads, links and deletions.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import asyncio
import re
from contextlib import AsyncExitStack
from datetime import timedelta
from typing import Any, AsyncIterator, Awaitable, Callable
from urllib.parse import quote

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.errors import NotFoundError, StorageError
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.settings import StorageSettings
from skyscanner_common.text import ascii_metadata_value, safe_path_segment

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)
S3_SERVICE_NAME: str = "s3"
DEFAULT_CONTENT_TYPE: str = "application/octet-stream"
STREAM_CHUNK_SIZE: int = 1024 * 1024
NOT_FOUND_CODES: frozenset[str] = frozenset({"404", "NoSuchKey", "NoSuchBucket", "NotFound"})

# How a caller hands the bytes of one file over: the same shape an upload of the web framework offers, so
# nothing has to be read into memory before the write begins.
ChunkReader = Callable[[int], Awaitable[bytes]]

# The floor the protocol sets for every part of a multipart upload but the last one.
MINIMUM_PART_BYTES: int = 5 * 1024 * 1024

# The ceiling the protocol sets on the amount of parts one upload may be split into.
MAXIMUM_PARTS: int = 10_000

PART_NUMBER_KEY: str = "PartNumber"
ETAG_KEY: str = "ETag"

# A quote or a control character ends the quoted file name of the header early and lets the rest of the name
# be read as further parameters, and a name outside latin-1 cannot be put in the header at all, so the plain
# form is reduced to what always survives and the real name travels beside it in the encoded form of RFC 5987.
UNSAFE_HEADER_CHARACTERS: re.Pattern[str] = re.compile(r'[^\x20-\x7e]|["\\]')
FALLBACK_HEADER_CHARACTER: str = "_"
FALLBACK_FILE_NAME: str = "download"

# ----- CLASSES ----- #


class ObjectStorageClient:
    """
    A long lived client of the object storage, opened at service start up and closed at service shut down.
    """

    def __init__(self, settings: StorageSettings) -> None:
        """
        Store the bucket settings without opening a connection yet.

        :param settings: Connection settings of the object storage.
        """
        self._settings = settings
        self._exit_stack = AsyncExitStack()
        self._client: Any = None

    async def start(self) -> None:
        """
        Open the underlying client and make sure the configured bucket exists.

        :raises StorageError: When the object storage cannot be reached.
        """
        if self._client is not None:
            return

        session = aioboto3.Session(
            aws_access_key_id=self._settings.access_key_id,
            aws_secret_access_key=self._settings.secret_access_key,
            region_name=self._settings.region,
        )
        try:
            self._client = await self._exit_stack.enter_async_context(
                session.client(S3_SERVICE_NAME, endpoint_url=self._settings.endpoint_url),
            )
            await self._ensure_bucket()
        except (BotoCoreError, ClientError) as error:
            await self.stop()
            raise StorageError(
                message="The object storage could not be reached",
                details={"bucket": self._settings.bucket},
            ) from error

        LOGGER.info("Connected to the object storage bucket %s", self._settings.bucket)

    async def stop(self) -> None:
        """
        Close the underlying client and release every resource it holds.
        """
        await self._exit_stack.aclose()
        self._exit_stack = AsyncExitStack()
        self._client = None

    async def ping(self) -> bool:
        """
        Check whether the bucket currently answers, used by the health endpoint.

        :return: Whether the bucket answered the check.
        """
        if self._client is None:
            return False

        try:
            await self._client.head_bucket(Bucket=self._settings.bucket)
        except (BotoCoreError, ClientError):
            return False

        return True

    async def upload(
        self,
        path: str,
        payload: bytes,
        content_type: str = DEFAULT_CONTENT_TYPE,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Write a payload into the bucket under the given key.

        :param path: Key the payload is stored under.
        :param payload: Bytes that are written.
        :param content_type: MIME type recorded together with the object.
        :param metadata: Extra key and value pairs stored next to the object.
        :return: The checksum reported by the object storage.
        :raises StorageError: When the object storage refused the write.
        """
        client = self._require_client()
        try:
            response = await client.put_object(
                Bucket=self._settings.bucket,
                Key=path,
                Body=payload,
                ContentType=content_type,
                Metadata=_encode_metadata(metadata),
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageError(message="The file could not be written", details={"path": path}) from error

        return str(response.get("ETag", "")).strip('"')

    async def upload_stream(
        self,
        path: str,
        reader: ChunkReader,
        content_type: str = DEFAULT_CONTENT_TYPE,
        metadata: dict[str, str] | None = None,
    ) -> tuple[str, int]:
        """
        Write a file into the bucket by reading it in pieces, never holding the whole of it in memory.

        A small file is one ordinary write. Anything past the configured threshold is written as a multipart
        upload instead: the bucket takes it part by part, several parts travel at once, and the process only
        ever holds as many parts as it is allowed to have in the air - which is what makes the size of the
        file stop being the size of the memory it costs. A failure aborts the upload rather than leaving the
        parts of half a file lying in the bucket.

        :param path: Key the file is stored under.
        :param reader: Source of the bytes, asked for at most the given amount at a time.
        :param content_type: MIME type recorded together with the object.
        :param metadata: Extra key and value pairs stored next to the object.
        :return: The checksum reported by the object storage and the amount of bytes that were written.
        :raises StorageError: When the object storage refused the write.
        """
        threshold = self._settings.multipart_threshold_bytes
        head = await _read_up_to(reader=reader, amount=threshold + 1)
        if len(head) <= threshold:
            checksum = await self.upload(
                path=path,
                payload=head,
                content_type=content_type,
                metadata=metadata,
            )

            return checksum, len(head)

        return await self._upload_multipart(
            path=path,
            buffered=head,
            reader=reader,
            content_type=content_type,
            metadata=metadata,
        )

    async def download(self, path: str) -> bytes:
        """
        Read a whole object back from the bucket.

        :param path: Key the object is stored under.
        :return: The bytes of the stored object.
        :raises NotFoundError: When the bucket does not hold the key.
        :raises StorageError: When the object storage refused the read.
        """
        client = self._require_client()
        try:
            response = await client.get_object(Bucket=self._settings.bucket, Key=path)
            payload: bytes = await response["Body"].read()
        except ClientError as error:
            if _is_missing(error):
                raise NotFoundError(message="The file is not stored", details={"path": path}) from error
            raise StorageError(message="The file could not be read", details={"path": path}) from error
        except BotoCoreError as error:
            raise StorageError(message="The file could not be read", details={"path": path}) from error

        return payload

    async def stream(self, path: str) -> AsyncIterator[bytes]:
        """
        Read an object back in chunks, so that large files never sit in memory as a whole.

        :param path: Key the object is stored under.
        :return: An iterator over the chunks of the stored object.
        :raises NotFoundError: When the bucket does not hold the key.
        :raises StorageError: When the object storage refused the read.
        """
        client = self._require_client()
        try:
            response = await client.get_object(Bucket=self._settings.bucket, Key=path)
        except ClientError as error:
            if _is_missing(error):
                raise NotFoundError(message="The file is not stored", details={"path": path}) from error
            raise StorageError(message="The file could not be read", details={"path": path}) from error
        except BotoCoreError as error:
            raise StorageError(message="The file could not be read", details={"path": path}) from error

        stream = response["Body"]
        while True:
            chunk: bytes = await stream.read(STREAM_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk

    async def head(self, path: str) -> dict[str, Any]:
        """
        Read the metadata the bucket keeps for one object.

        :param path: Key the object is stored under.
        :return: The raw metadata answer of the object storage.
        :raises NotFoundError: When the bucket does not hold the key.
        :raises StorageError: When the object storage refused the lookup.
        """
        client = self._require_client()
        try:
            response: dict[str, Any] = await client.head_object(Bucket=self._settings.bucket, Key=path)
        except ClientError as error:
            if _is_missing(error):
                raise NotFoundError(message="The file is not stored", details={"path": path}) from error
            raise StorageError(message="The file could not be inspected", details={"path": path}) from error
        except BotoCoreError as error:
            raise StorageError(message="The file could not be inspected", details={"path": path}) from error

        return response

    async def delete(self, path: str) -> None:
        """
        Remove one object from the bucket.

        :param path: Key the object is stored under.
        :raises StorageError: When the object storage refused the deletion.
        """
        client = self._require_client()
        try:
            await client.delete_object(Bucket=self._settings.bucket, Key=path)
        except (BotoCoreError, ClientError) as error:
            raise StorageError(message="The file could not be removed", details={"path": path}) from error

    async def presigned_url(
        self,
        path: str,
        file_name: str | None = None,
        inline: bool = False,
    ) -> tuple[str, timedelta]:
        """
        Mint a temporary link that lets the browser read one object straight from the bucket.

        :param path: Key the object is stored under.
        :param file_name: Name the browser should save the download as.
        :param inline: Whether the browser should render the object instead of saving it.
        :return: The link together with the period it stays valid for.
        :raises StorageError: When the link could not be minted.
        """
        client = self._require_client()
        parameters: dict[str, str] = {"Bucket": self._settings.bucket, "Key": path}
        if file_name is not None:
            parameters["ResponseContentDisposition"] = content_disposition(
                disposition="inline" if inline else "attachment",
                file_name=file_name,
            )

        try:
            url: str = await client.generate_presigned_url(
                ClientMethod="get_object",
                Params=parameters,
                ExpiresIn=self._settings.presigned_url_ttl_seconds,
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageError(message="The download link could not be created", details={"path": path}) from error

        return url, timedelta(seconds=self._settings.presigned_url_ttl_seconds)

    async def _upload_multipart(
        self,
        path: str,
        buffered: bytes,
        reader: ChunkReader,
        content_type: str,
        metadata: dict[str, str] | None,
    ) -> tuple[str, int]:
        """
        Write one file to the bucket part by part, with several parts of it travelling at the same time.

        :param path: Key the file is stored under.
        :param buffered: Bytes that were already read while the size of the file was being decided.
        :param reader: Source of the rest of the bytes.
        :param content_type: MIME type recorded together with the object.
        :param metadata: Extra key and value pairs stored next to the object.
        :return: The checksum reported by the object storage and the amount of bytes that were written.
        :raises StorageError: When the object storage refused any part of the write.
        """
        client = self._require_client()
        part_size = max(self._settings.multipart_chunk_bytes, MINIMUM_PART_BYTES)
        concurrency = self._settings.multipart_concurrency

        try:
            started = await client.create_multipart_upload(
                Bucket=self._settings.bucket,
                Key=path,
                ContentType=content_type,
                Metadata=_encode_metadata(metadata),
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageError(message="The file could not be written", details={"path": path}) from error

        upload_id = str(started["UploadId"])
        written = 0
        parts: list[dict[str, Any]] = []
        in_flight: list[asyncio.Task[dict[str, Any]]] = []

        try:
            async for number, chunk in _numbered_parts(buffered=buffered, reader=reader, part_size=part_size):
                written += len(chunk)
                in_flight.append(
                    asyncio.ensure_future(
                        self._upload_part(path=path, upload_id=upload_id, number=number, chunk=chunk),
                    ),
                )
                # The bytes of every part in the air are held in memory until the bucket has taken them, so
                # the next part is only read once the oldest wave of them has landed.
                if len(in_flight) >= concurrency:
                    parts.extend(await asyncio.gather(*in_flight))
                    in_flight = []

            parts.extend(await asyncio.gather(*in_flight))
            in_flight = []
            parts.sort(key=lambda part: int(part[PART_NUMBER_KEY]))
            completed = await client.complete_multipart_upload(
                Bucket=self._settings.bucket,
                Key=path,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
        except (BotoCoreError, ClientError, StorageError) as error:
            for task in in_flight:
                task.cancel()
            await self._abort_multipart(path=path, upload_id=upload_id)
            raise StorageError(message="The file could not be written", details={"path": path}) from error

        LOGGER.info("Wrote %s to the bucket as %d parts", path, len(parts))

        return str(completed.get(ETAG_KEY, "")).strip('"'), written

    async def _upload_part(self, path: str, upload_id: str, number: int, chunk: bytes) -> dict[str, Any]:
        """
        Write a single part of a multipart upload and describe it the way completing the upload asks for.

        :param path: Key the file is stored under.
        :param upload_id: Identifier the bucket gave the started upload.
        :param number: One based position of the part inside the file.
        :param chunk: Bytes the part carries.
        :return: The part number together with the checksum the bucket reported for it.
        :raises StorageError: When the object storage refused the part.
        """
        client = self._require_client()
        try:
            response = await client.upload_part(
                Bucket=self._settings.bucket,
                Key=path,
                UploadId=upload_id,
                PartNumber=number,
                Body=chunk,
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageError(
                message="The file could not be written",
                details={"path": path, "part": str(number)},
            ) from error

        return {PART_NUMBER_KEY: number, ETAG_KEY: response[ETAG_KEY]}

    async def _abort_multipart(self, path: str, upload_id: str) -> None:
        """
        Give up a started multipart upload so that the parts already written do not stay in the bucket.

        The upload has already failed by the time this runs, so a bucket that refuses the abort as well is
        logged rather than raised: the failure the caller has to hear about is the one that came first.

        :param path: Key the file was being stored under.
        :param upload_id: Identifier the bucket gave the started upload.
        """
        try:
            await self._require_client().abort_multipart_upload(
                Bucket=self._settings.bucket,
                Key=path,
                UploadId=upload_id,
            )
        except (BotoCoreError, ClientError, StorageError):
            LOGGER.warning("The unfinished upload of %s could not be given up", path)

    async def _ensure_bucket(self) -> None:
        """
        Create the configured bucket when the object storage does not hold it yet.

        :raises ClientError: When the bucket exists but cannot be inspected or created.
        """
        client = self._require_client()
        try:
            await client.head_bucket(Bucket=self._settings.bucket)
        except ClientError as error:
            if not _is_missing(error):
                raise
            await client.create_bucket(Bucket=self._settings.bucket)
            LOGGER.info("Created the object storage bucket %s", self._settings.bucket)

    def _require_client(self) -> Any:
        """
        Fetch the underlying client and refuse to work before the connection was opened.

        :return: The underlying object storage client.
        :raises StorageError: When the client was used before it was started.
        """
        if self._client is None:
            raise StorageError(message="The object storage client was used before it was started")

        return self._client


# ----- FUNCTIONS ----- #


def build_object_key(prefix: str, identifier: str, file_name: str) -> str:
    """
    Build the key an uploaded file is stored under, keeping the files of one owner together in the bucket.

    The name keeps whatever alphabet it was written in - a bucket stores its keys as UTF-8 and has never
    cared which letters they are made of - and only what would move the file into a folder of its own is
    taken out of it.

    :param prefix: Top level folder of the key, usually the kind of owner.
    :param identifier: Identifier of the owner the file belongs to.
    :param file_name: Original name of the uploaded file.
    :return: The key the file has to be stored under.
    """
    stamp = utc_now().strftime("%Y/%m/%d")

    return f"{prefix}/{identifier}/{stamp}/{safe_path_segment(file_name)}"


async def _read_up_to(reader: ChunkReader, amount: int) -> bytes:
    """
    Ask a source for a fixed amount of bytes, stopping early only when it has nothing left to give.

    A single read is allowed to answer with less than it was asked for, which is exactly what makes the
    difference between a file that ended and a file that arrived in small pieces, so the reads are repeated
    until either the amount is full or the source is empty.

    :param reader: Source of the bytes.
    :param amount: Largest amount of bytes that is collected.
    :return: The collected bytes, shorter than the amount only when the source ran out.
    """
    collected = bytearray()
    while len(collected) < amount:
        block = await reader(amount - len(collected))
        if not block:
            break
        collected.extend(block)

    return bytes(collected)


async def _numbered_parts(buffered: bytes, reader: ChunkReader, part_size: int) -> AsyncIterator[tuple[int, bytes]]:
    """
    Cut a file into the numbered parts a multipart upload is made of.

    :param buffered: Bytes that were already read out of the source.
    :param reader: Source of the rest of the bytes.
    :param part_size: Size every part but the last one carries.
    :return: An iterator over the position and the bytes of each part.
    :raises StorageError: When the file needs more parts than one upload may be split into.
    """
    pending = bytearray(buffered)
    number = 0
    exhausted = False

    while True:
        while not exhausted and len(pending) < part_size:
            block = await reader(part_size)
            if not block:
                exhausted = True
                break
            pending.extend(block)

        if not pending:
            return

        number += 1
        if number > MAXIMUM_PARTS:
            raise StorageError(
                message="The file is too large to be written in one upload",
                details={"parts": str(MAXIMUM_PARTS)},
            )

        yield number, bytes(pending[:part_size])
        del pending[:part_size]


def _encode_metadata(metadata: dict[str, str] | None) -> dict[str, str]:
    """
    Render every stored attribute so that the bucket accepts it whatever alphabet it was written in.

    :param metadata: Attributes the caller wants stored next to the object.
    :return: The attributes in the form the bucket accepts.
    """
    return {key: ascii_metadata_value(value) for key, value in (metadata or {}).items()}


def content_disposition(disposition: str, file_name: str) -> str:
    """
    Build the disposition header of an answer so that any file name survives it, quoted or not ASCII.

    Every caller that offers a stored file under its own name needs this, which is why it sits beside the
    bucket rather than in one of the services: a name carrying a quote or a Hebrew letter otherwise either
    truncates the header or cannot be encoded into it at all.

    :param disposition: Whether the browser renders the file or saves it.
    :param file_name: Name the file is offered under.
    :return: The value of the disposition header.
    """
    fallback = UNSAFE_HEADER_CHARACTERS.sub(FALLBACK_HEADER_CHARACTER, file_name).strip() or FALLBACK_FILE_NAME
    encoded = quote(file_name, safe="")

    return f"{disposition}; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"


def _is_missing(error: ClientError) -> bool:
    """
    Decide whether a client error reports a missing key or bucket rather than a real failure.

    :param error: Error raised by the object storage client.
    :return: Whether the error means that the addressed object does not exist.
    """
    response: dict[str, Any] = getattr(error, "response", {})
    code = str(response.get("Error", {}).get("Code", ""))
    status = str(response.get("ResponseMetadata", {}).get("HTTPStatusCode", ""))

    return code in NOT_FOUND_CODES or status == "404"
