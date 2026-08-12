"""
The rules around the events themselves - creating one out of the wizard, reading the inventory and editing later on.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from math import ceil
from typing import Any

from skyscanner_common.datetime_utils import ensure_utc, utc_now
from skyscanner_common.errors import ConflictError, NotFoundError, ValidationError
from skyscanner_common.ids import new_id
from skyscanner_models.common import UserContext
from skyscanner_models.enums import FieldScope
from skyscanner_models.event import EventCreateRequest, EventResponse, EventSummaryResponse, EventUpdateRequest
from skyscanner_models.pagination import Page
from skyscanner_models.query import SearchQuery
from skyscanner_models.subscription import SubscriptionTrigger

from events_service.constants import EVENT_ID_COUNTER
from events_service.documents import EventDocument, OutboxDocument
from events_service.repositories.counter_repository import CounterRepository
from events_service.repositories.event_repository import EventRepository
from events_service.repositories.outbox_repository import OutboxRepository
from events_service.services.entity_service import EntityService
from events_service.services.field_service import FieldService
from events_service.services.revision_service import RevisionService, event_update_changes
from events_service.services.type_service import TypeService

# ----- CLASSES ----- #


class EventService:
    """
    Owner of the inventory, turning the three steps of the create wizard into one stored document.
    """

    def __init__(
        self,
        repository: EventRepository,
        counter_repository: CounterRepository,
        outbox_repository: OutboxRepository,
        type_service: TypeService,
        field_service: FieldService,
        entity_service: EntityService,
        revision_service: RevisionService,
    ) -> None:
        """
        Bind the service to the repositories and the sibling services it needs.

        :param repository: Persistence of the events.
        :param counter_repository: Source of the running event numbers.
        :param outbox_repository: Persistence of the pending notifications.
        :param type_service: Resolver of the declared event types.
        :param field_service: Owner of the dynamic schema of the events.
        :param entity_service: Owner of the entities nested inside an event.
        :param revision_service: Owner of the edit history.
        """
        self._repository = repository
        self._counter_repository = counter_repository
        self._outbox_repository = outbox_repository
        self._type_service = type_service
        self._field_service = field_service
        self._entity_service = entity_service
        self._revision_service = revision_service

    async def search_events(self, query: SearchQuery) -> Page[EventSummaryResponse]:
        """
        Read one page of the inventory the way the toolbar and the table asked for it.

        :param query: Query requested by the client.
        :return: The page of matching events.
        """
        documents, total = await self._repository.search(search=query)

        return Page[EventSummaryResponse](
            items=[document.to_summary() for document in documents],
            total=total,
            page=query.page,
            page_size=query.page_size,
            pages=ceil(total / query.page_size) if query.page_size else 0,
        )

    async def search_documents(self, query: SearchQuery) -> tuple[list[EventDocument], int]:
        """
        Read one page of the inventory as stored documents, used by the grid and the export endpoints.

        :param query: Query requested by the client.
        :return: The documents of the page and the total amount of matching events.
        """
        return await self._repository.search(search=query)

    async def get_event(self, event_id: str) -> EventResponse:
        """
        Read a single event together with every entity nested inside it.

        :param event_id: Identifier of the event.
        :return: The detail representation of the event.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._require_event(event_id=event_id)

        return document.to_response()

    async def create_event(self, request: EventCreateRequest, user: UserContext) -> EventResponse:
        """
        Store a new event with the files, the dynamic values and the entities the wizard collected.

        :param request: Event supplied by the user.
        :param user: Identity the event is attributed to.
        :return: The stored event.
        :raises ValidationError: When no event type was chosen or a declared rule is broken.
        :raises NotFoundError: When a chosen event type or entity type is not declared.
        """
        if not request.event_type_keys:
            raise ValidationError(message="At least one event type has to be chosen")

        await self._require_free_reference(reference_id=request.reference_id.strip())

        types = await self._type_service.resolve_event_types(keys=request.event_type_keys)
        attributes, flattened = await self._field_service.build_values(
            scope=FieldScope.EVENT,
            supplied=request.metadata,
            industry=request.industry,
        )
        event_number = await self._counter_repository.next_value(name=EVENT_ID_COUNTER)

        document = EventDocument(
            id=new_id(),
            event_id=event_number,
            reference_id=request.reference_id.strip(),
            name=request.name or f"{types[0].name} {event_number}",
            event_type=[declared.to_reference() for declared in types],
            event_type_names=[declared.name for declared in types],
            event_type_keys=[declared.key for declared in types],
            industry=request.industry,
            platform=request.platform,
            status=request.status,
            experiment_result=request.experiment_result,
            event_date=ensure_utc(request.event_date),
            notes=request.notes,
            additional_files=request.additional_files,
            metadata=attributes,
            data=flattened,
            upload_source=request.upload_source,
            created_by=user.username,
        )

        for index, entity_request in enumerate(request.entities, start=1):
            entity = await self._entity_service.build_entity(
                request=entity_request,
                industry=request.industry,
                event_values=flattened,
                object_id=index,
                user=user,
            )
            document.objects.append(entity)
            document.entity_counts[entity.object_type_key] = document.entity_counts.get(entity.object_type_key, 0) + 1

        await self._repository.insert(document=document)
        await self._publish(
            document=document,
            trigger=SubscriptionTrigger.EVENT_CREATED,
            summary=f"A new {document.industry} event was uploaded by {user.username}",
        )

        return document.to_response()

    async def update_event(self, event_id: str, request: EventUpdateRequest, user: UserContext) -> EventResponse:
        """
        Change an event so that data revealed after the upload can be filled in later on.

        :param event_id: Identifier of the event that is changed.
        :param request: Attributes the caller wants to change.
        :param user: Identity the change is attributed to.
        :return: The changed event.
        :raises NotFoundError: When the identifier or a chosen event type is unknown.
        :raises ValidationError: When a value breaks a declared rule or the request changes nothing.
        """
        document = await self._require_event(event_id=event_id)
        updates: dict[str, Any] = request.model_dump(exclude_unset=True, exclude_none=True)
        # The reason belongs to the history of the change, not to the event itself.
        updates.pop("reason", None)

        if request.reference_id is not None:
            updates["reference_id"] = request.reference_id.strip()
            await self._require_free_reference(reference_id=updates["reference_id"], excluding=event_id)

        if request.event_type_keys is not None:
            types = await self._type_service.resolve_event_types(keys=request.event_type_keys)
            updates["event_type"] = [declared.to_reference().model_dump() for declared in types]
            updates["event_type_names"] = [declared.name for declared in types]
            updates["event_type_keys"] = [declared.key for declared in types]

        if request.metadata is not None:
            attributes, flattened = await self._field_service.build_values(
                scope=FieldScope.EVENT,
                supplied=request.metadata,
                industry=request.industry or document.industry,
            )
            updates["metadata"] = [attribute.model_dump() for attribute in attributes]
            updates["data"] = flattened

        if request.additional_files is not None:
            updates["additional_files"] = [artifact.model_dump() for artifact in request.additional_files]

        if request.status is not None:
            updates["status"] = request.status.value

        if request.experiment_result is not None:
            updates["experiment_result"] = request.experiment_result.value

        if request.event_date is not None:
            updates["event_date"] = ensure_utc(request.event_date)

        # The attributes a request carries are not the attributes it changes: an editor that saves a form
        # without touching it hands back exactly what is stored. Such a request is refused rather than
        # applied, because it came with a reason for a change that is not in it, and because carrying it
        # out would stamp a new author and moment on the event and mail every subscriber about nothing.
        if not event_update_changes(document=document, updates=updates):
            raise ValidationError(
                message="The request does not change anything about the event",
                details={"id": event_id, "reason": request.reason},
            )

        updates["updated_at"] = utc_now()
        updates["updated_by"] = user.username
        await self._repository.update_fields(identifier=event_id, updates=updates)

        refreshed = await self._require_event(event_id=event_id)
        await self._revision_service.record_event_change(
            before=document,
            after=refreshed,
            reason=request.reason,
            user=user,
        )
        await self._publish(
            document=refreshed,
            trigger=SubscriptionTrigger.EVENT_UPDATED,
            summary=f"The event was updated by {user.username}: {request.reason}",
        )

        return refreshed.to_response()

    async def delete_event(self, event_id: str) -> None:
        """
        Remove an event together with the entities nested inside it.

        :param event_id: Identifier of the event that is removed.
        :raises NotFoundError: When the identifier is unknown.
        """
        removed = await self._repository.delete(identifier=event_id)
        if not removed:
            raise NotFoundError(message="The event does not exist", details={"id": event_id})

    async def _require_free_reference(self, reference_id: str, excluding: str | None = None) -> None:
        """
        Refuse a reference that another event already carries.

        The generated event number identifies an event inside the system and is never chosen by anybody.
        The reference is the identifier the users themselves know an event by, so it has to name exactly
        one event or it is not an identifier at all. An empty reference is simply absent and never clashes.

        :param reference_id: Reference the caller supplied.
        :param excluding: Event that is allowed to hold the reference, which is the one being changed.
        :raises ConflictError: When another event already carries the reference.
        """
        if not reference_id:
            return

        taken = await self._repository.find_by_reference(reference_id=reference_id, excluding=excluding)
        if taken is not None:
            raise ConflictError(
                message="Another event already carries this reference",
                details={"reference_id": reference_id, "event": taken.name},
            )

    async def _require_event(self, event_id: str) -> EventDocument:
        """
        Read an event and refuse to continue when it does not exist.

        :param event_id: Identifier of the event.
        :return: The stored event.
        :raises NotFoundError: When the event does not exist.
        """
        document = await self._repository.find_by_id(identifier=event_id)
        if document is None:
            raise NotFoundError(message="The event does not exist", details={"id": event_id})

        return document

    async def _publish(self, document: EventDocument, trigger: SubscriptionTrigger, summary: str) -> None:
        """
        Write a pending notification that the mail service turns into a message.

        :param document: Event the notification is about.
        :param trigger: Change that produced the notification.
        :param summary: Short sentence rendered in the body of the mail.
        """
        await self._outbox_repository.insert(
            document=OutboxDocument(
                trigger=trigger,
                event_id=document.id,
                event_number=document.event_id,
                event_name=document.name,
                industry=document.industry,
                event_type_keys=document.event_type_keys,
                summary=summary,
            ),
        )
