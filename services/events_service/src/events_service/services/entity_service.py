"""
The rules around the entities nested inside an event, from building one out of a request to changing its files.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from skyscanner_common.datetime_utils import ensure_utc, utc_now
from skyscanner_common.errors import NotFoundError, ValidationError
from skyscanner_common.ids import new_id
from skyscanner_models.common import Artifact, UserContext
from skyscanner_models.entity import EntityCreateRequest, EntityResponse, EntityUpdateRequest
from skyscanner_models.enums import EntityStatus, FieldScope
from skyscanner_models.subscription import SubscriptionTrigger

from events_service.documents import EntityDocument, EventDocument, OutboxDocument
from events_service.repositories.event_repository import EventRepository
from events_service.repositories.outbox_repository import OutboxRepository
from events_service.services.field_service import FieldService
from events_service.services.industry_service import IndustryService
from events_service.services.revision_service import RevisionService, entity_update_changes
from events_service.services.type_service import TypeService

# ----- CLASSES ----- #


class EntityService:
    """
    Owner of the entities of an event, keeping their type references, their dynamic values and their file sets.
    """

    def __init__(
        self,
        event_repository: EventRepository,
        outbox_repository: OutboxRepository,
        type_service: TypeService,
        field_service: FieldService,
        revision_service: RevisionService,
        industry_service: IndustryService,
    ) -> None:
        """
        Bind the service to the repositories and the sibling services it needs.

        :param event_repository: Persistence of the events the entities live inside.
        :param outbox_repository: Persistence of the pending notifications.
        :param type_service: Resolver of the declared entity types.
        :param field_service: Owner of the dynamic schema of the entities.
        :param revision_service: Owner of the edit history.
        :param industry_service: Owner of the industries, which declare the vocabulary of the origins.
        """
        self._event_repository = event_repository
        self._outbox_repository = outbox_repository
        self._type_service = type_service
        self._field_service = field_service
        self._revision_service = revision_service
        self._industry_service = industry_service

    async def build_entity(
        self,
        request: EntityCreateRequest,
        industry: str,
        event_values: dict[str, Any],
        object_id: int,
        user: UserContext,
    ) -> EntityDocument:
        """
        Turn a create request into the document that is stored inside the objects list of an event.

        :param request: Entity supplied by the user.
        :param industry: Industry of the event, deciding which part of the schema applies.
        :param event_values: Dynamic values of the owning event, which an entity field may depend on.
        :param object_id: Running number the entity takes inside its event.
        :param user: Identity the entity is attributed to.
        :return: The document that is stored.
        :raises NotFoundError: When the chosen entity type is not declared.
        :raises ValidationError: When a required value is missing, a value breaks a declared rule or the
            entity is declared parsed while it carries no parsed files.
        """
        entity_type = await self._type_service.resolve_entity_type(key=request.entity_type_key)
        attributes, flattened = await self._field_service.build_values(
            scope=FieldScope.ENTITY,
            supplied=request.metadata,
            industry=industry,
            entity_type=request.entity_type_key,
            context=event_values,
        )

        await self._require_known_origin(industry=industry, origin=request.origin)

        status = _resolve_status(
            requested=request.status,
            current=None,
            parsed_files=request.parsed_files,
            details={"name": request.name},
        )

        return EntityDocument(
            id=new_id(),
            object_id=object_id,
            name=request.name,
            object_type=entity_type.to_reference(),
            object_type_name=entity_type.name,
            object_type_key=entity_type.key,
            origin=request.origin,
            code_version=request.code_version,
            status=status,
            notes=request.notes,
            upload_source=request.upload_source,
            requested_at=ensure_utc(request.requested_at),
            received_at=ensure_utc(request.received_at),
            raw_files=request.raw_files,
            parsed_files=request.parsed_files,
            parsed_additional_files=request.parsed_additional_files,
            metadata=attributes,
            data=flattened,
            created_by=user.username,
        )

    async def list_entities(
        self,
        event_id: str,
        entity_type_key: str | None = None,
        offset: int = 0,
        limit: int = 0,
    ) -> list[EntityResponse]:
        """
        Read the entities of one event, optionally narrowed to a single entity type.

        :param event_id: Identifier of the event the entities belong to.
        :param entity_type_key: Type key the result is narrowed to.
        :param offset: Amount of entities skipped before collecting.
        :param limit: Largest amount of entities that is returned, zero for all of them.
        :return: The matching entities of the event.
        :raises NotFoundError: When the event does not exist.
        """
        event = await self._require_event(event_id=event_id)
        entities = event.objects
        if entity_type_key:
            entities = [entity for entity in entities if entity.object_type_key == entity_type_key]

        windowed = entities[offset:] if limit <= 0 else entities[offset : offset + limit]

        return [entity.to_response(event_id=event.id) for entity in windowed]

    async def add_entity(self, event_id: str, request: EntityCreateRequest, user: UserContext) -> EntityResponse:
        """
        Attach a new entity to an event that already exists.

        :param event_id: Identifier of the event the entity is attached to.
        :param request: Entity supplied by the user.
        :param user: Identity the entity is attributed to.
        :return: The stored entity.
        :raises NotFoundError: When the event does not exist or the entity type is not declared.
        :raises ValidationError: When a required value is missing, a value breaks a declared rule or the
            entity is declared parsed while it carries no parsed files.
        """
        event = await self._require_event(event_id=event_id)
        next_object_id = max((entity.object_id for entity in event.objects), default=0) + 1
        entity = await self.build_entity(
            request=request,
            industry=event.industry,
            event_values=event.data,
            object_id=next_object_id,
            user=user,
        )
        await self._event_repository.add_entity(event_id=event_id, entity=entity)
        # Attaching an entity changes the event, so the history has to carry it the same way it carries an
        # edit. The action is its own reason, which is why the request never asks the user for one.
        await self._revision_service.record_entity_addition(event_id=event_id, entity=entity, user=user)
        await self._publish(event=event, trigger=SubscriptionTrigger.ENTITY_ADDED, summary=f"{entity.name} was added")

        return entity.to_response(event_id=event_id)

    async def update_entity(
        self,
        event_id: str,
        entity_id: str,
        request: EntityUpdateRequest,
        user: UserContext,
    ) -> EntityResponse:
        """
        Change an entity, which is how a raw telemetry becomes a parsed one once its products were uploaded.

        :param event_id: Identifier of the event the entity belongs to.
        :param entity_id: Identifier of the entity that is changed.
        :param request: Attributes the caller wants to change.
        :param user: Identity the change is attributed to.
        :return: The changed entity.
        :raises NotFoundError: When the event or the entity does not exist.
        :raises ValidationError: When a value breaks a declared rule, the entity is declared parsed while it
            carries no parsed files, or the request changes nothing at all.
        """
        event = await self._require_event(event_id=event_id)
        current = _find_entity(event=event, entity_id=entity_id)
        await self._require_known_origin(industry=event.industry, origin=request.origin)

        updates: dict[str, Any] = request.model_dump(exclude_unset=True, exclude_none=True)
        # The reason belongs to the history of the change, not to the entity itself.
        updates.pop("reason", None)
        if request.metadata is not None:
            attributes, flattened = await self._field_service.build_values(
                scope=FieldScope.ENTITY,
                supplied=request.metadata,
                industry=event.industry,
                entity_type=current.object_type_key,
                context=event.data,
            )
            updates["metadata"] = [attribute.model_dump() for attribute in attributes]
            updates["data"] = flattened

        for artifact_field in ("raw_files", "parsed_files", "parsed_additional_files"):
            if artifact_field in updates:
                updates[artifact_field] = [artifact.model_dump() for artifact in getattr(request, artifact_field)]

        # The parsed state is a claim about the files, so it is decided together with them rather than being
        # trusted from the request on its own, exactly as it is decided when the entity is created.
        resulting_parsed = request.parsed_files if request.parsed_files is not None else current.parsed_files
        updates["status"] = _resolve_status(
            requested=request.status,
            current=current.status,
            parsed_files=resulting_parsed,
            details={"id": entity_id},
        ).value

        # An edit that moves nothing is not an edit. Refusing it here keeps the entity, its update stamp and
        # its history in agreement instead of recording an author and a moment for a change that never was.
        if not entity_update_changes(document=current, updates=updates):
            raise ValidationError(
                message="The request does not change anything about the entity",
                details={"id": entity_id, "reason": request.reason},
            )

        updates["updated_at"] = utc_now()
        updates["updated_by"] = user.username
        await self._event_repository.update_entity(event_id=event_id, entity_id=entity_id, updates=updates)

        refreshed = await self._require_event(event_id=event_id)
        updated = _find_entity(event=refreshed, entity_id=entity_id)
        await self._revision_service.record_entity_change(
            event_id=event_id,
            before=current,
            after=updated,
            reason=request.reason,
            user=user,
        )
        if updated.status is EntityStatus.PARSED and current.status is not EntityStatus.PARSED:
            await self._publish(
                event=refreshed,
                trigger=SubscriptionTrigger.ENTITY_PARSED,
                summary=f"{updated.name} reached the parsed state",
            )

        return updated.to_response(event_id=event_id)

    async def delete_entity(self, event_id: str, entity_id: str, user: UserContext) -> None:
        """
        Remove an entity from an event.

        :param event_id: Identifier of the event the entity belongs to.
        :param entity_id: Identifier of the entity that is removed.
        :param user: Identity the removal is attributed to.
        :raises NotFoundError: When the event or the entity does not exist.
        """
        event = await self._require_event(event_id=event_id)
        entity = _find_entity(event=event, entity_id=entity_id)
        await self._event_repository.remove_entity(
            event_id=event_id,
            entity_id=entity_id,
            entity_type_key=entity.object_type_key,
        )
        # The entity is gone from the event, so the only place that can still answer what it held and who
        # took it away is the history.
        await self._revision_service.record_entity_removal(event_id=event_id, entity=entity, user=user)

    async def _require_known_origin(self, industry: str, origin: str | None) -> None:
        """
        Refuse an origin that the industry did not declare, once the industry declared a vocabulary at all.

        An industry that has not named its origins accepts anything, so a system that nobody has configured
        yet keeps working exactly as it did before the vocabulary existed.

        :param industry: Industry the entity belongs to.
        :param origin: Origin the caller supplied.
        :raises ValidationError: When the industry declared a vocabulary the origin is not part of.
        """
        if not origin:
            return

        allowed = await self._industry_service.allowed_origins(key=industry)
        if allowed and origin not in allowed:
            raise ValidationError(
                message="The origin is not one of the values declared for this industry",
                details={"origin": origin, "allowed": ", ".join(allowed)},
            )

    async def _require_event(self, event_id: str) -> EventDocument:
        """
        Read an event and refuse to continue when it does not exist.

        :param event_id: Identifier of the event.
        :return: The stored event.
        :raises NotFoundError: When the event does not exist.
        """
        event = await self._event_repository.find_by_id(identifier=event_id)
        if event is None:
            raise NotFoundError(message="The event does not exist", details={"id": event_id})

        return event

    async def _publish(self, event: EventDocument, trigger: SubscriptionTrigger, summary: str) -> None:
        """
        Write a pending notification that the mail service turns into a message.

        :param event: Event the notification is about.
        :param trigger: Change that produced the notification.
        :param summary: Short sentence rendered in the body of the mail.
        """
        await self._outbox_repository.insert(
            document=OutboxDocument(
                trigger=trigger,
                event_id=event.id,
                event_number=event.event_id,
                event_name=event.name,
                industry=event.industry,
                event_type_keys=event.event_type_keys,
                summary=summary,
            ),
        )


# ----- FUNCTIONS ----- #


def _resolve_status(
    requested: EntityStatus | None,
    current: EntityStatus | None,
    parsed_files: list[Artifact],
    details: dict[str, Any],
) -> EntityStatus:
    """
    Decide the parsing state an entity ends up in, so that it always follows the parsed files it carries.

    The parsed state is not an opinion the caller holds about an entity, it is what the parsed files say
    about it, and the two are read the same way whether the entity is being created with its event, added
    to one afterwards or edited later on. An entity that carries parsed products is parsed, whatever the
    request left in the status field. An entity that carries none cannot be called parsed, so a request
    that says so is refused rather than quietly corrected, and an entity that loses its parsed files loses
    the claim with them.

    :param requested: Parsing state the caller asked for, empty when the caller did not name one.
    :param current: Parsing state the entity holds today, empty while it is being created.
    :param parsed_files: Parsed files the entity ends up carrying.
    :param details: Identification of the entity, reported with a refusal.
    :return: The parsing state the entity is stored with.
    :raises ValidationError: When the caller asks for the parsed state without any parsed file.
    """
    if parsed_files:
        return EntityStatus.PARSED

    if requested is EntityStatus.PARSED:
        raise ValidationError(
            message="An entity cannot be marked as parsed while it carries no parsed files",
            details=details,
        )

    if requested is not None:
        return requested

    return EntityStatus.RAW if current is None or current is EntityStatus.PARSED else current


def _find_entity(event: EventDocument, entity_id: str) -> EntityDocument:
    """
    Pick one entity out of the objects list of an event.

    :param event: Event the entity is looked up in.
    :param entity_id: Identifier of the entity.
    :return: The entity carrying the identifier.
    :raises NotFoundError: When the event does not hold such an entity.
    """
    for entity in event.objects:
        if entity.id == entity_id:
            return entity

    raise NotFoundError(message="The entity does not exist", details={"id": entity_id})
