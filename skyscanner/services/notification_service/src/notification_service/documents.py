"""
The view the notification service has on the shared collections - the pending notifications and the subscriptions.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.ids import new_id
from skyscanner_models.subscription import SubscriptionTrigger

# ----- CLASSES ----- #


class OutboxDocument(BaseModel):
    """
    One pending notification written by the events service.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the pending notification")
    trigger: SubscriptionTrigger = Field(description="Change that produced the notification")
    event_id: str = Field(description="Identifier of the event the notification is about")
    event_number: int = Field(default=0, description="Running number of the event the notification is about")
    event_name: str = Field(default="", description="Name of the event the notification is about")
    industry: str = Field(default="", description="Industry key of the event the notification is about")
    event_type_keys: list[str] = Field(default_factory=list, description="Type keys of the event")
    summary: str = Field(default="", description="Short sentence rendered in the body of the mail")
    attempts: int = Field(default=0, ge=0, description="Amount of rounds that tried to deliver the notification")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the notification was written")
    processed_at: datetime | None = Field(default=None, description="UTC moment the notification was sent")


class SubscriptionDocument(BaseModel):
    """
    One stored subscription, telling the service who wants to hear about which target.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id", description="Identifier of the subscription")
    owner: str = Field(default="anonymous", description="User the subscription belongs to")
    email: str = Field(description="Mail address the notifications are sent to")
    industry: str | None = Field(default=None, description="Industry followed by the subscription")
    event_id: str | None = Field(default=None, description="Single event followed by the subscription")
    event_type_key: str | None = Field(default=None, description="Event type followed by the subscription")
    triggers: list[SubscriptionTrigger] = Field(default_factory=list, description="Changes that make it fire")
    active: bool = Field(default=True, description="Whether the subscription currently sends mails")
    created_at: datetime = Field(default_factory=utc_now, description="UTC moment the subscription was created")
    last_notified_at: datetime | None = Field(default=None, description="UTC moment the last mail was sent")
