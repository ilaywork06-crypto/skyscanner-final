"""
The fixed vocabulary of the notification service - its name, the collections it reads and the batch it works with.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- CONSTS ----- #

SERVICE_NAME: str = "notification-service"
SERVICE_VERSION: str = "0.1.0"
SERVICE_DESCRIPTION: str = "Turns the pending notifications of the inventory into mails for the subscribers"

OUTBOX_COLLECTION: str = "notification_outbox"
SUBSCRIPTIONS_COLLECTION: str = "subscriptions"

BATCH_SIZE: int = 50
MAX_DELIVERY_ATTEMPTS: int = 5
MAIL_SUBJECT_TEMPLATE: str = "[Skyscanner] {trigger} - {event_name}"
