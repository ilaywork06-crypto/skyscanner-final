"""
The entry point of the notification service, starting the poll loop that mails the subscribers of the inventory.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from skyscanner_common.api import create_application
from skyscanner_common.logging_utils import configure_logging
from skyscanner_common.mongo import MongoProvider
from skyscanner_common.settings import get_mail_settings, get_mongo_settings, get_service_settings

from notification_service.api import API_PREFIX, ROUTER
from notification_service.constants import SERVICE_DESCRIPTION, SERVICE_NAME, SERVICE_VERSION
from notification_service.repositories import OutboxRepository, SubscriptionRepository
from notification_service.services import DispatchService, MailService

# ----- FUNCTIONS ----- #


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """
    Open the document store and start the poll loop before the service starts serving.

    :param application: Application the life cycle belongs to.
    :return: An iterator that yields once while the service is serving.
    """
    mail_settings = get_mail_settings()
    provider = MongoProvider(settings=get_mongo_settings())
    await provider.connect()

    dispatch = DispatchService(
        outbox_repository=OutboxRepository(provider=provider),
        subscription_repository=SubscriptionRepository(provider=provider),
        mail_service=MailService(settings=mail_settings, service_settings=get_service_settings()),
        poll_interval_seconds=mail_settings.poll_interval_seconds,
    )
    dispatch.start()

    application.state.mongo = provider
    application.state.dispatch = dispatch

    yield

    await dispatch.stop()
    await provider.close()


def create_app() -> FastAPI:
    """
    Build the application of the notification service with its routes and its error handling.

    :return: The prepared application.
    """
    configure_logging(service_name=SERVICE_NAME, level=get_service_settings().log_level)
    application = create_application(
        title="Skyscanner notification service",
        version=SERVICE_VERSION,
        description=SERVICE_DESCRIPTION,
        api_prefix=API_PREFIX,
    )
    application.router.lifespan_context = lifespan
    application.include_router(ROUTER)

    return application
