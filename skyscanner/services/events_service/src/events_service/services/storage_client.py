"""
The way to the bucket from this service, which is a request to the service that owns it.

:date: 2026-09-09
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from dataclasses import dataclass

import httpx

from skyscanner_common.logging_utils import get_logger
from skyscanner_common.settings import AuthSettings, ServiceSettings
from skyscanner_models.common import UserContext

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)

UPLOAD_PATH: str = "/artifacts"

# What a restored file is filed under in the bucket. The bucket lays its keys out by who owns the object, and
# a restored file belongs to the event it is being restored onto exactly as an uploaded one belongs to the
# event it was uploaded to.
OWNER_KIND: str = "events"

DEFAULT_CONTENT_TYPE: str = "application/octet-stream"

# A restore writes one file per request and a file may be very large, so the ceiling is generous. It is a
# ceiling rather than none at all because a request that will never answer should fail rather than hang.
UPLOAD_TIMEOUT_SECONDS: float = 600.0

# What separates the roles inside the header the reverse proxy injects them as.
ROLE_SEPARATOR: str = ","

# ----- CLASSES ----- #


@dataclass(frozen=True)
class StoredFile:
    """
    Where one restored file landed in this system's bucket, and what the bucket says about it.
    """

    path: str
    size_bytes: int
    content_type: str
    checksum: str | None


class StorageClient:
    """
    The only way from this service to the bucket, which is deliberately not a way to the bucket at all.

    The storage service is the one service that may read and write the bucket, and that boundary is what
    keeps the knowledge of what an event is here and the knowledge of how an object is keyed there. A
    restore needs to write files, so it asks rather than reaching - which costs a request per file and buys
    a system where exactly one service can lose a bucket.
    """

    def __init__(self, settings: ServiceSettings, auth: AuthSettings) -> None:
        """
        Bind the client to the address the storage service answers at.

        :param settings: Where every service of the system is reached.
        :param auth: Names of the headers an identity travels in, which this forwards rather than invents.
        """
        self._base_url = settings.storage_service_url.rstrip("/")
        self._auth = auth

    def _identity_headers(self, user: UserContext) -> dict[str, str]:
        """
        Write the caller's identity into the headers the storage service reads one out of.

        The roles travel with the name, and that is the whole point rather than a detail: the storage
        service grants nothing to a name it cannot place, so forwarding a username alone would have every
        restore refused for want of the permission the person asking for it actually holds.

        :param user: Identity the restore is being performed on behalf of.
        :return: The headers the request carries.
        """
        return {
            self._auth.user_header: user.username,
            self._auth.roles_header: ROLE_SEPARATOR.join(role.value for role in user.roles),
        }

    async def upload(self, file_name: str, content: bytes, user: UserContext) -> StoredFile:
        """
        Write one file into the bucket and say where it landed.

        :param file_name: What the file is called, which it is stored and offered under.
        :param content: The bytes of the file.
        :param user: Identity the write is performed on behalf of and attributed to.
        :return: Where the file landed and what the bucket says about it.
        :raises RuntimeError: When the storage service refused the write or answered with nothing usable.
        """
        async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{self._base_url}{UPLOAD_PATH}",
                files={"files": (file_name, content, DEFAULT_CONTENT_TYPE)},
                data={"owner_kind": OWNER_KIND},
                headers=self._identity_headers(user=user),
            )

        if response.status_code >= httpx.codes.BAD_REQUEST:
            raise RuntimeError(f"the storage service refused the file ({response.status_code})")

        artifacts = response.json().get("artifacts") or []
        if not artifacts:
            raise RuntimeError("the storage service wrote nothing")

        written = artifacts[0]

        return StoredFile(
            path=str(written.get("path", "")),
            size_bytes=int(written.get("size_bytes", 0) or 0),
            content_type=str(written.get("content_type") or DEFAULT_CONTENT_TYPE),
            checksum=written.get("checksum"),
        )
