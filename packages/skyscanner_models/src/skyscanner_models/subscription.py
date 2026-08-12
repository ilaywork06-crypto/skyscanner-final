"""
Payloads for the mail subscriptions that tell a user when a new event or entity reaches an industry they follow.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# ----- CLASSES ----- #


class SubscriptionTrigger(str, Enum):
    """
    The change that makes a subscription send a mail.
    """

    EVENT_CREATED = "event_created"
    EVENT_UPDATED = "event_updated"
    ENTITY_ADDED = "entity_added"
    ENTITY_PARSED = "entity_parsed"


class SubscriptionCreateRequest(BaseModel):
    """
    The payload accepted when a user starts following an industry or a single event.
    """

    model_config = ConfigDict(populate_by_name=True)

    email: str = Field(description="Mail address the notifications are sent to")
    industry: str | None = Field(default=None, description="Industry followed by the subscription")
    event_id: str | None = Field(default=None, description="Single event followed by the subscription")
    event_type_key: str | None = Field(default=None, description="Event type followed by the subscription")
    triggers: list[SubscriptionTrigger] = Field(
        default_factory=lambda: [SubscriptionTrigger.EVENT_CREATED],
        description="Changes that make the subscription fire",
    )


class SubscriptionResponse(BaseModel):
    """
    A stored subscription as it is handed back to the client.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the subscription")
    owner: str = Field(description="User the subscription belongs to")
    email: str = Field(description="Mail address the notifications are sent to")
    industry: str | None = Field(default=None, description="Industry followed by the subscription")
    event_id: str | None = Field(default=None, description="Single event followed by the subscription")
    event_type_key: str | None = Field(default=None, description="Event type followed by the subscription")
    triggers: list[SubscriptionTrigger] = Field(default_factory=list, description="Changes that make it fire")
    active: bool = Field(default=True, description="Whether the subscription currently sends mails")
    created_at: datetime = Field(description="UTC moment the subscription was created")
    last_notified_at: datetime | None = Field(default=None, description="UTC moment the last mail was sent")
