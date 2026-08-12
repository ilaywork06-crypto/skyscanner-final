"""
Asynchronous access to the document store, owning the single motor client shared by all repositories of a service.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from skyscanner_common.errors import SkyscannerError
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.settings import MongoSettings

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)
PING_COMMAND: str = "ping"

# ----- CLASSES ----- #


class MongoProvider:
    """
    Owner of the motor client, handing out typed collection handles and taking care of the connection life cycle.
    """

    def __init__(self, settings: MongoSettings) -> None:
        """
        Store the connection settings without opening a socket yet.

        :param settings: Connection settings of the document store.
        """
        self._settings = settings
        self._client: AsyncIOMotorClient[dict[str, Any]] | None = None

    async def connect(self) -> None:
        """
        Open the motor client and verify that the document store answers.

        :raises SkyscannerError: When the document store cannot be reached.
        """
        if self._client is not None:
            return

        client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(
            self._settings.uri,
            maxPoolSize=self._settings.max_pool_size,
            serverSelectionTimeoutMS=self._settings.server_selection_timeout_ms,
            uuidRepresentation="standard",
            tz_aware=True,
        )

        try:
            await client.admin.command(PING_COMMAND)
        except PyMongoError as error:
            client.close()
            raise SkyscannerError(
                message="The document store did not answer the connection check",
                details={"uri": self._settings.uri},
            ) from error

        self._client = client
        LOGGER.info("Connected to the document store database %s", self._settings.database)

    async def close(self) -> None:
        """
        Close the motor client and forget it, so that a later connect opens a fresh one.
        """
        if self._client is None:
            return

        self._client.close()
        self._client = None
        LOGGER.info("Closed the connection to the document store")

    async def ping(self) -> bool:
        """
        Check whether the document store currently answers, used by the health endpoint.

        :return: Whether the document store answered the check.
        """
        if self._client is None:
            return False

        try:
            await self._client.admin.command(PING_COMMAND)
        except PyMongoError:
            return False

        return True

    @property
    def database(self) -> AsyncIOMotorDatabase[dict[str, Any]]:
        """
        Hand back the database handle the service works against.

        :return: The database handle of the configured database.
        :raises SkyscannerError: When the provider was not connected yet.
        """
        if self._client is None:
            raise SkyscannerError(message="The document store provider was used before it was connected")

        return self._client[self._settings.database]

    def collection(self, name: str) -> AsyncIOMotorCollection[dict[str, Any]]:
        """
        Hand back the handle of a single collection inside the configured database.

        :param name: Name of the collection.
        :return: The collection handle.
        :raises SkyscannerError: When the provider was not connected yet.
        """
        return self.database[name]
