"""
Asynchronous access to the bucket that keeps every uploaded file, covering uploads, reads, links and deletions.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import re
from contextlib import AsyncExitStack
from datetime import timedelta
from typing import Any, AsyncIterator
from urllib.parse import quote

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.errors import NotFoundError, StorageError
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.settings import StorageSettings

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)
S3_SERVICE_NAME: str = "s3"
DEFAULT_CONTENT_TYPE: str = "application/octet-stream"
STREAM_CHUNK_SIZE: int = 1024 * 1024
NOT_FOUND_CODES: frozenset[str] = frozenset({"404", "NoSuchKey", "NoSuchBucket", "NotFound"})

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
                Metadata=metadata or {},
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageError(message="The file could not be written", details={"path": path}) from error

        return str(response.get("ETag", "")).strip('"')

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

    :param prefix: Top level folder of the key, usually the kind of owner.
    :param identifier: Identifier of the owner the file belongs to.
    :param file_name: Original name of the uploaded file.
    :return: The key the file has to be stored under.
    """
    stamp = utc_now().strftime("%Y/%m/%d")

    return f"{prefix}/{identifier}/{stamp}/{file_name}"


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
