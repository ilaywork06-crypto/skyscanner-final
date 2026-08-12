"""
The persistence layer of the events service, the only place that talks to the document store.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from events_service.repositories.base_repository import BaseRepository
from events_service.repositories.counter_repository import CounterRepository
from events_service.repositories.event_repository import EventRepository
from events_service.repositories.field_repository import FieldRepository
from events_service.repositories.outbox_repository import OutboxRepository
from events_service.repositories.subscription_repository import SubscriptionRepository
from events_service.repositories.industry_repository import IndustryRepository
from events_service.repositories.template_repository import TemplateRepository
from events_service.repositories.type_repository import TypeRepository
