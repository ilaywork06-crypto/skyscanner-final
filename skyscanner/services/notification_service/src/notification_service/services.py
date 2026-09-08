"""
The business layer of the notification service - writing the mail of a notification and running the poll loop.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import asyncio
from email.message import EmailMessage

import aiosmtplib

from skyscanner_common.logging_utils import get_logger
from skyscanner_common.settings import MailSettings, ServiceSettings

from notification_service.constants import MAIL_SUBJECT_TEMPLATE, MAX_DELIVERY_ATTEMPTS
from notification_service.documents import OutboxDocument, SubscriptionDocument
from notification_service.repositories import OutboxRepository, SubscriptionRepository

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)
TRIGGER_LABELS: dict[str, str] = {
    "event_created": "A new event was uploaded",
    "event_updated": "An event was updated",
    "entity_added": "An entity was added",
    "entity_parsed": "An entity was parsed",
}

# ----- CLASSES ----- #


class MailService:
    """
    Writer of the mails, holding the only place in the system that talks to the mail relay.
    """

    def __init__(self, settings: MailSettings, service_settings: ServiceSettings) -> None:
        """
        Bind the service to the mail relay and to the links it puts into the body of a mail.

        :param settings: Connection settings of the mail relay.
        :param service_settings: Settings holding the addresses the mails link to.
        """
        self._settings = settings
        self._service_settings = service_settings

    async def send(self, notification: OutboxDocument, subscription: SubscriptionDocument) -> None:
        """
        Write and hand one mail to the relay.

        :param notification: Pending notification the mail is about.
        :param subscription: Subscription the mail is sent for.
        :raises SMTPException: When the relay refused the message.
        """
        message = EmailMessage()
        message["From"] = self._settings.sender
        message["To"] = subscription.email
        message["Subject"] = MAIL_SUBJECT_TEMPLATE.format(
            trigger=TRIGGER_LABELS.get(notification.trigger.value, notification.trigger.value),
            event_name=notification.event_name,
        )
        message.set_content(_build_body(notification=notification))

        await aiosmtplib.send(
            message,
            hostname=self._settings.host,
            port=self._settings.port,
            username=self._settings.username or None,
            password=self._settings.password or None,
            start_tls=self._settings.use_tls or None,
        )


class DispatchService:
    """
    Owner of the poll loop, turning each pending notification into the mails its subscribers asked for.
    """

    def __init__(
        self,
        outbox_repository: OutboxRepository,
        subscription_repository: SubscriptionRepository,
        mail_service: MailService,
        poll_interval_seconds: int,
    ) -> None:
        """
        Bind the service to the repositories, to the mail writer and to the pace of the poll loop.

        :param outbox_repository: Reader of the pending notifications.
        :param subscription_repository: Reader of the matching subscriptions.
        :param mail_service: Writer of the mails.
        :param poll_interval_seconds: Pause between two rounds of the poll loop.
        """
        self._outbox_repository = outbox_repository
        self._subscription_repository = subscription_repository
        self._mail_service = mail_service
        self._poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def dispatch_once(self) -> int:
        """
        Work through one batch of pending notifications and send every mail they ask for.

        :return: The amount of mails that went out.
        """
        sent = 0
        for notification in await self._outbox_repository.pending():
            subscriptions = await self._subscription_repository.matching(notification=notification)
            failed = False
            for subscription in subscriptions:
                try:
                    await self._mail_service.send(notification=notification, subscription=subscription)
                except (aiosmtplib.SMTPException, OSError) as error:
                    LOGGER.warning("Could not mail %s: %s", subscription.email, error)
                    failed = True
                    continue
                await self._subscription_repository.mark_notified(identifier=subscription.id)
                sent += 1

            if failed and notification.attempts + 1 < MAX_DELIVERY_ATTEMPTS:
                await self._outbox_repository.record_failure(identifier=notification.id)
                continue

            if failed:
                LOGGER.error(
                    "Giving up on the notification about %s after %d rounds",
                    notification.event_name,
                    MAX_DELIVERY_ATTEMPTS,
                )
            await self._outbox_repository.mark_processed(identifier=notification.id)

        return sent

    def start(self) -> None:
        """
        Start the background loop that keeps working through the pending notifications.
        """
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """
        Stop the background loop and wait until it left its current round.
        """
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            LOGGER.info("The dispatch loop was stopped")
        self._task = None

    async def _run(self) -> None:
        """
        Keep working through the pending notifications until the loop is cancelled.
        """
        while True:
            try:
                sent = await self.dispatch_once()
                if sent:
                    LOGGER.info("Sent %d notification mails", sent)
            except Exception as error:  # pylint: disable=broad-except
                LOGGER.exception("The dispatch round failed: %s", error)

            await asyncio.sleep(self._poll_interval_seconds)


# ----- FUNCTIONS ----- #


def _build_body(notification: OutboxDocument) -> str:
    """
    Write the plain text body of the mail one notification produces.

    :param notification: Pending notification the mail is about.
    :return: The body of the mail.
    """
    label = TRIGGER_LABELS.get(notification.trigger.value, notification.trigger.value)

    return (
        f"{label}.\n\n"
        f"Event: {notification.event_name} (#{notification.event_number})\n"
        f"Industry: {notification.industry}\n"
        f"Types: {', '.join(notification.event_type_keys) or 'none'}\n\n"
        f"{notification.summary}\n\n"
        f"Open the event at /events/{notification.event_id}\n"
    )
