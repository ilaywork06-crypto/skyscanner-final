"""
The entry point of the register, opening the document store before the first request reaches an endpoint.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from skyscanner_common.api import create_application
from skyscanner_common.logging_utils import configure_logging
from skyscanner_common.mongo import MongoProvider
from skyscanner_common.settings import get_service_settings

from truth_service.api.router import API_PREFIX, build_api_router
from truth_service.bootstrap import prepare_database
from truth_service.constants import SERVICE_NAME
from truth_service.settings import get_truth_mongo_settings, get_truth_service_settings

# ----- CONSTS ----- #

SERVICE_VERSION: str = "0.1.0"
SERVICE_DESCRIPTION: str = "The register of the working assumptions a project is planned on"

# ----- FUNCTIONS ----- #


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """
    Open the document store before the service starts serving and close it when it stops.

    :param application: Application the life cycle belongs to.
    :return: An iterator that yields once while the service is serving.
    """
    provider = MongoProvider(settings=get_truth_mongo_settings())
    await provider.connect()
    application.state.mongo = provider
    await prepare_database(provider=provider)

    yield

    await provider.close()


def create_app() -> FastAPI:
    """
    Build the application of the register with its routes, its CORS policy and its error handling.

    :return: The prepared application.
    """
    configure_logging(service_name=SERVICE_NAME, level=get_service_settings().log_level)
    application = create_application(
        title="Truth",
        version=SERVICE_VERSION,
        description=SERVICE_DESCRIPTION,
        api_prefix=API_PREFIX,
        root_path=get_truth_service_settings().root_path,
    )
    application.router.lifespan_context = lifespan
    application.include_router(build_api_router())

    return application


app = create_app()
