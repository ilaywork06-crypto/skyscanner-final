"""
The start up work of the events service, creating every index the collections are queried through.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from skyscanner_common.mongo import MongoProvider
from skyscanner_models.enums import FieldScope

from events_service.migrations import migrate_documents
from events_service.repositories.event_repository import EventRepository
from events_service.repositories.field_repository import FieldRepository
from events_service.repositories.outbox_repository import OutboxRepository
from events_service.repositories.revision_repository import RevisionRepository
from events_service.repositories.subscription_repository import SubscriptionRepository
from events_service.repositories.industry_repository import IndustryRepository
from events_service.repositories.template_repository import TemplateRepository
from events_service.repositories.type_repository import TypeRepository

# ----- FUNCTIONS ----- #


async def prepare_database(provider: MongoProvider) -> None:
    """
    Carry the stored documents onto the current shape and create every index the service relies on.

    :param provider: Owner of the shared motor client.
    """
    # The documents come first: an index is built over whatever the collections hold, so a rewrite that runs
    # after the indexes would leave them describing attributes that no document carries any more.
    await migrate_documents(provider=provider)

    # The rule behind this index changed, so a database created before the change has to have the old one
    # taken down before the new one can be put in its place.
    subscriptions = SubscriptionRepository(provider=provider)
    events = EventRepository(provider=provider)
    fields = FieldRepository(provider=provider)
    await subscriptions.drop_legacy_indexes()
    await events.drop_legacy_indexes()

    repositories = (
        events,
        fields,
        TypeRepository(provider=provider),
        IndustryRepository(provider=provider),
        TemplateRepository(provider=provider),
        subscriptions,
        OutboxRepository(provider=provider),
        RevisionRepository(provider=provider),
    )
    for repository in repositories:
        await repository.ensure_indexes()

    await _index_declared_dynamic_values(events=events, fields=fields)


async def _index_declared_dynamic_values(events: EventRepository, fields: FieldRepository) -> None:
    """
    Give every dynamic value an industry declared an index on the events collection.

    A declared field becomes a column of the inventory table that the user may order and filter by, and a
    column that is ordered by without an index makes the document store read every matching event and sort it
    in memory. The declarations are read here rather than being written into the repository because the schema
    is data: which columns exist is decided on the schema page and not in this file. A field declared while the
    service is already running is therefore indexed at the next start, which is the same moment every other
    index of the service is settled at.

    :param events: Persistence of the events, which is the collection the indexes are created on.
    :param fields: Persistence of the field declarations the indexed keys are read from.
    """
    declared = await fields.list_for_scope(scope=FieldScope.EVENT, include_shared=False)
    keys = [document.key for document in declared if document.sortable or document.filterable]

    await events.ensure_dynamic_indexes(keys=keys)
