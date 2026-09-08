"""
The entry point of the storage service, opening the bucket before the first upload reaches an endpoint.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from skyscanner_common.api import create_application
from skyscanner_common.logging_utils import configure_logging
from skyscanner_common.object_storage import ObjectStorageClient
from skyscanner_common.settings import get_service_settings, get_storage_settings

from storage_service.api.router import API_PREFIX, build_api_router
from storage_service.constants import SERVICE_DESCRIPTION, SERVICE_NAME, SERVICE_VERSION

# ----- FUNCTIONS ----- #


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """
    Open the bucket before the service starts serving and close it when it stops.

    :param application: Application the life cycle belongs to.
    :return: An iterator that yields once while the service is serving.
    """
    storage = ObjectStorageClient(settings=get_storage_settings())
    await storage.start()
    application.state.storage = storage

    yield

    await storage.stop()


def create_app() -> FastAPI:
    """
    Build the application of the storage service with its routes, its CORS policy and its error handling.

    :return: The prepared application.
    """
    configure_logging(service_name=SERVICE_NAME, level=get_service_settings().log_level)
    application = create_application(
        title="Skyscanner storage service",
        version=SERVICE_VERSION,
        description=SERVICE_DESCRIPTION,
        api_prefix=API_PREFIX,
    )
    application.router.lifespan_context = lifespan
    application.include_router(build_api_router())

    return application
