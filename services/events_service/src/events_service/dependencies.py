"""
The dependency wiring of the events service, building the repositories and the services one request needs.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated, Callable, cast

from fastapi import Depends, Request

from ag_grid_lib.introspection import SchemaIntrospector
from skyscanner_common.errors import PermissionDeniedError
from skyscanner_common.identity import build_user_context
from skyscanner_common.mongo import MongoProvider
from skyscanner_common.settings import get_auth_settings
from skyscanner_models.common import UserContext
from skyscanner_models.enums import Permission

from events_service.constants import EVENTS_COLLECTION
from events_service.repositories.base_repository import NOT_DELETED
from events_service.repositories.counter_repository import CounterRepository
from events_service.repositories.event_repository import EventRepository
from events_service.repositories.field_repository import FieldRepository
from events_service.repositories.outbox_repository import OutboxRepository
from events_service.repositories.revision_repository import RevisionRepository
from events_service.repositories.subscription_repository import SubscriptionRepository
from events_service.repositories.industry_repository import IndustryRepository
from events_service.repositories.template_repository import TemplateRepository
from events_service.repositories.type_repository import TypeRepository
from events_service.services.entity_service import EntityService
from events_service.services.event_service import EventService
from events_service.services.export_service import ExportService
from events_service.services.field_service import FieldService
from events_service.services.grid_service import GridService
from events_service.services.revision_service import RevisionService
from events_service.services.subscription_service import SubscriptionService
from events_service.services.industry_service import IndustryService
from events_service.services.template_service import TemplateService
from events_service.services.type_service import TypeService

# ----- FUNCTIONS ----- #


def get_mongo_provider(request: Request) -> MongoProvider:
    """
    Fetch the shared document store provider that was opened when the service started.

    :param request: Incoming request carrying the application state.
    :return: The shared document store provider.
    """
    return cast(MongoProvider, request.app.state.mongo)


def get_user_context(request: Request) -> UserContext:
    """
    Build the caller identity out of the headers the authenticating reverse proxy injected.

    :param request: Incoming request carrying the identity headers.
    :return: The identity the request is handled on behalf of.
    """
    return build_user_context(headers=request.headers, settings=get_auth_settings())


def require_permission(permission: Permission) -> Callable[[UserContext], UserContext]:
    """
    Build a dependency that lets a request through only when the caller holds one capability.

    :param permission: Capability the endpoint asks for.
    :return: The dependency guarding the endpoint.
    """

    def guard(user: Annotated[UserContext, Depends(get_user_context)]) -> UserContext:
        """
        Verify that the caller holds the capability the endpoint asks for.

        :param user: Identity the request is handled on behalf of.
        :return: The very same identity, so that endpoints can read the caller from the guard.
        :raises PermissionDeniedError: When the caller does not hold the capability.
        """
        if permission not in user.permissions:
            raise PermissionDeniedError(
                message="The identity is not allowed to perform this action",
                details={"permission": permission.value},
            )

        return user

    return guard


ProviderDependency = Annotated[MongoProvider, Depends(get_mongo_provider)]
CurrentUser = Annotated[UserContext, Depends(get_user_context)]


def get_event_repository(provider: ProviderDependency) -> EventRepository:
    """
    Build the repository of the events for one request.

    :param provider: Owner of the shared motor client.
    :return: The repository of the events.
    """
    return EventRepository(provider=provider)


def get_field_repository(provider: ProviderDependency) -> FieldRepository:
    """
    Build the repository of the field declarations for one request.

    :param provider: Owner of the shared motor client.
    :return: The repository of the field declarations.
    """
    return FieldRepository(provider=provider)


def get_type_repository(provider: ProviderDependency) -> TypeRepository:
    """
    Build the repository of the type declarations for one request.

    :param provider: Owner of the shared motor client.
    :return: The repository of the type declarations.
    """
    return TypeRepository(provider=provider)


def get_industry_repository(provider: ProviderDependency) -> IndustryRepository:
    """
    Build the repository of the industries for one request.

    :param provider: Owner of the shared motor client.
    :return: The repository of the industries.
    """
    return IndustryRepository(provider=provider)


def get_template_repository(provider: ProviderDependency) -> TemplateRepository:
    """
    Build the repository of the templates for one request.

    :param provider: Owner of the shared motor client.
    :return: The repository of the templates.
    """
    return TemplateRepository(provider=provider)


def get_subscription_repository(provider: ProviderDependency) -> SubscriptionRepository:
    """
    Build the repository of the subscriptions for one request.

    :param provider: Owner of the shared motor client.
    :return: The repository of the subscriptions.
    """
    return SubscriptionRepository(provider=provider)


def get_outbox_repository(provider: ProviderDependency) -> OutboxRepository:
    """
    Build the repository of the pending notifications for one request.

    :param provider: Owner of the shared motor client.
    :return: The repository of the pending notifications.
    """
    return OutboxRepository(provider=provider)


def get_counter_repository(provider: ProviderDependency) -> CounterRepository:
    """
    Build the repository of the running numbers for one request.

    :param provider: Owner of the shared motor client.
    :return: The repository of the running numbers.
    """
    return CounterRepository(provider=provider)


def get_revision_repository(provider: ProviderDependency) -> RevisionRepository:
    """
    Build the repository of the edit history for one request.

    :param provider: Owner of the shared motor client.
    :return: The repository of the recorded edits.
    """
    return RevisionRepository(provider=provider)


EventRepositoryDependency = Annotated[EventRepository, Depends(get_event_repository)]
FieldRepositoryDependency = Annotated[FieldRepository, Depends(get_field_repository)]
TypeRepositoryDependency = Annotated[TypeRepository, Depends(get_type_repository)]
IndustryRepositoryDependency = Annotated[IndustryRepository, Depends(get_industry_repository)]
TemplateRepositoryDependency = Annotated[TemplateRepository, Depends(get_template_repository)]
SubscriptionRepositoryDependency = Annotated[SubscriptionRepository, Depends(get_subscription_repository)]
OutboxRepositoryDependency = Annotated[OutboxRepository, Depends(get_outbox_repository)]
CounterRepositoryDependency = Annotated[CounterRepository, Depends(get_counter_repository)]
RevisionRepositoryDependency = Annotated[RevisionRepository, Depends(get_revision_repository)]


def get_revision_service(repository: RevisionRepositoryDependency) -> RevisionService:
    """
    Build the owner of the edit history for one request.

    :param repository: Persistence of the recorded edits.
    :return: The service that owns the edit history.
    """
    return RevisionService(repository=repository)


RevisionServiceDependency = Annotated[RevisionService, Depends(get_revision_service)]


def get_field_service(repository: FieldRepositoryDependency) -> FieldService:
    """
    Build the owner of the dynamic schema for one request.

    :param repository: Persistence of the field declarations.
    :return: The service that owns the dynamic schema.
    """
    return FieldService(repository=repository)


def get_type_service(repository: TypeRepositoryDependency) -> TypeService:
    """
    Build the owner of the declared types for one request.

    :param repository: Persistence of the type declarations.
    :return: The service that owns the declared types.
    """
    return TypeService(repository=repository)


def get_industry_service(
    repository: IndustryRepositoryDependency,
    event_repository: EventRepositoryDependency,
) -> IndustryService:
    """
    Build the owner of the industries for one request.

    :param repository: Persistence of the industries.
    :param event_repository: Persistence of the events, used for the counters of the tabs.
    :return: The service that owns the industries.
    """
    return IndustryService(repository=repository, event_repository=event_repository)


FieldServiceDependency = Annotated[FieldService, Depends(get_field_service)]
TypeServiceDependency = Annotated[TypeService, Depends(get_type_service)]
IndustryServiceDependency = Annotated[IndustryService, Depends(get_industry_service)]


def get_entity_service(
    event_repository: EventRepositoryDependency,
    outbox_repository: OutboxRepositoryDependency,
    type_service: TypeServiceDependency,
    field_service: FieldServiceDependency,
    revision_service: RevisionServiceDependency,
    industry_service: IndustryServiceDependency,
) -> EntityService:
    """
    Build the owner of the entities of an event for one request.

    :param event_repository: Persistence of the events the entities live inside.
    :param outbox_repository: Persistence of the pending notifications.
    :param type_service: Resolver of the declared entity types.
    :param field_service: Owner of the dynamic schema of the entities.
    :param revision_service: Owner of the edit history.
    :param industry_service: Owner of the industries, which declare the vocabulary of the origins.
    :return: The service that owns the entities.
    """
    return EntityService(
        event_repository=event_repository,
        outbox_repository=outbox_repository,
        type_service=type_service,
        field_service=field_service,
        revision_service=revision_service,
        industry_service=industry_service,
    )


EntityServiceDependency = Annotated[EntityService, Depends(get_entity_service)]


def get_event_service(
    repository: EventRepositoryDependency,
    counter_repository: CounterRepositoryDependency,
    outbox_repository: OutboxRepositoryDependency,
    type_service: TypeServiceDependency,
    field_service: FieldServiceDependency,
    entity_service: EntityServiceDependency,
    revision_service: RevisionServiceDependency,
) -> EventService:
    """
    Build the owner of the inventory for one request.

    :param repository: Persistence of the events.
    :param counter_repository: Source of the running event numbers.
    :param outbox_repository: Persistence of the pending notifications.
    :param type_service: Resolver of the declared event types.
    :param field_service: Owner of the dynamic schema of the events.
    :param entity_service: Owner of the entities nested inside an event.
    :param revision_service: Owner of the edit history.
    :return: The service that owns the inventory.
    """
    return EventService(
        repository=repository,
        counter_repository=counter_repository,
        outbox_repository=outbox_repository,
        type_service=type_service,
        field_service=field_service,
        entity_service=entity_service,
        revision_service=revision_service,
    )


def get_grid_service(
    provider: ProviderDependency,
    event_repository: EventRepositoryDependency,
    field_service: FieldServiceDependency,
) -> GridService:
    """
    Build the generator of the tables for one request.

    :param provider: Owner of the shared motor client, used to inspect the stored documents.
    :param event_repository: Persistence of the events the rows are read from.
    :param field_service: Owner of the declared dynamic schema.
    :return: The service that generates the tables.
    """
    return GridService(
        event_repository=event_repository,
        field_service=field_service,
        introspector=SchemaIntrospector(
            collection=provider.collection(EVENTS_COLLECTION),
            base_filter=NOT_DELETED,
        ),
    )


def get_template_service(repository: TemplateRepositoryDependency) -> TemplateService:
    """
    Build the owner of the saved table layouts for one request.

    :param repository: Persistence of the templates.
    :return: The service that owns the templates.
    """
    return TemplateService(repository=repository)


def get_subscription_service(repository: SubscriptionRepositoryDependency) -> SubscriptionService:
    """
    Build the owner of the mail subscriptions for one request.

    :param repository: Persistence of the subscriptions.
    :return: The service that owns the subscriptions.
    """
    return SubscriptionService(repository=repository)


def get_export_service(repository: EventRepositoryDependency) -> ExportService:
    """
    Build the owner of the export for one request.

    :param repository: Persistence of the events.
    :return: The service that owns the export.
    """
    return ExportService(repository=repository)


EventServiceDependency = Annotated[EventService, Depends(get_event_service)]
GridServiceDependency = Annotated[GridService, Depends(get_grid_service)]
TemplateServiceDependency = Annotated[TemplateService, Depends(get_template_service)]
SubscriptionServiceDependency = Annotated[SubscriptionService, Depends(get_subscription_service)]
ExportServiceDependency = Annotated[ExportService, Depends(get_export_service)]
