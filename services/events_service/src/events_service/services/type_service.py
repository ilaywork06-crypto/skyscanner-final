"""
The rules around the declared event types and entity types the create wizard and the event page work with.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from skyscanner_common.errors import ConflictError, NotFoundError, ValidationError
from skyscanner_models.common import UserContext
from skyscanner_models.entity import EntityTypeCreateRequest, EntityTypeResponse, EntityTypeUpdateRequest
from skyscanner_models.event import EventTypeCreateRequest, EventTypeResponse, EventTypeUpdateRequest
from skyscanner_models.platform import PlatformCreateRequest, PlatformResponse, PlatformUpdateRequest

from events_service.constants import ENTITY_TYPE_KIND, EVENT_TYPE_KIND, PLATFORM_TYPE_KIND
from events_service.documents import TypeDocument
from events_service.repositories.type_repository import TypeRepository

# ----- CLASSES ----- #


class TypeService:
    """
    Owner of the declared types, resolving the keys the client sends into the references stored in the documents.
    """

    def __init__(self, repository: TypeRepository) -> None:
        """
        Bind the service to the repository of the type declarations.

        :param repository: Persistence of the type declarations.
        """
        self._repository = repository

    async def list_event_types(
        self,
        industry: str | None = None,
        offset: int = 0,
        limit: int = 0,
    ) -> list[EventTypeResponse]:
        """
        Read the event types an industry may choose from.

        :param industry: Industry whose own types are added to the shared ones.
        :param offset: Amount of types skipped before collecting.
        :param limit: Largest amount of types that is returned, zero for all of them.
        :return: The matching event types.
        """
        documents = await self._repository.list_event_types(industry=industry, offset=offset, limit=limit)

        return [document.to_event_type() for document in documents]

    async def list_entity_types(
        self,
        industry: str | None = None,
        offset: int = 0,
        limit: int = 0,
    ) -> list[EntityTypeResponse]:
        """
        Read the entity types an industry may choose from.

        :param industry: Industry whose own types are added to the shared ones.
        :param offset: Amount of types skipped before collecting.
        :param limit: Largest amount of types that is returned, zero for all of them.
        :return: The matching entity types.
        """
        documents = await self._repository.list_entity_types(industry=industry, offset=offset, limit=limit)

        return [document.to_entity_type() for document in documents]

    async def list_platforms(
        self,
        industry: str | None = None,
        offset: int = 0,
        limit: int = 0,
    ) -> list[PlatformResponse]:
        """
        Read the platforms an industry may name on its events.

        :param industry: Industry whose own platforms are added to the shared ones.
        :param offset: Amount of platforms skipped before collecting.
        :param limit: Largest amount of platforms that is returned, zero for all of them.
        :return: The matching platforms.
        """
        documents = await self._repository.list_platforms(industry=industry, offset=offset, limit=limit)

        return [document.to_platform() for document in documents]

    async def create_event_type(self, request: EventTypeCreateRequest) -> EventTypeResponse:
        """
        Declare a new event type, refusing a key that is already taken.

        :param request: Event type supplied by the user.
        :return: The stored event type.
        :raises ConflictError: When an event type with the same key is already declared.
        """
        document = await self._insert(
            kind=EVENT_TYPE_KIND,
            key=request.key,
            values=request.model_dump(exclude={"key"}),
        )

        return document.to_event_type()

    async def create_entity_type(self, request: EntityTypeCreateRequest) -> EntityTypeResponse:
        """
        Declare a new entity type, refusing a key that is already taken.

        :param request: Entity type supplied by the user.
        :return: The stored entity type.
        :raises ConflictError: When an entity type with the same key is already declared.
        """
        document = await self._insert(
            kind=ENTITY_TYPE_KIND,
            key=request.key,
            values=request.model_dump(exclude={"key"}),
        )

        return document.to_entity_type()

    async def create_platform(self, request: PlatformCreateRequest) -> PlatformResponse:
        """
        Declare a new platform, refusing a key that is already taken.

        :param request: Platform supplied by the user.
        :return: The stored platform.
        :raises ConflictError: When a platform with the same key is already declared.
        """
        document = await self._insert(
            kind=PLATFORM_TYPE_KIND,
            key=request.key,
            values=request.model_dump(exclude={"key"}),
        )

        return document.to_platform()

    async def update_platform(self, type_id: str, request: PlatformUpdateRequest) -> PlatformResponse:
        """
        Change a stored platform, leaving every attribute the caller omitted untouched.

        :param type_id: Identifier of the platform that is changed.
        :param request: Attributes the caller wants to change.
        :return: The changed platform.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._update(type_id=type_id, updates=request.model_dump(exclude_unset=True))

        return document.to_platform()

    async def resolve_platforms(self, keys: list[str], industry: str) -> list[TypeDocument]:
        """
        Resolve the platform keys chosen in the wizard, refusing one the industry may not name.

        The platforms are a declared vocabulary rather than free text, and each of them says which
        industries it belongs to, so an event can only ever name the ones its own industry was offered.

        :param keys: Machine keys the client sent.
        :param industry: Industry of the event the platforms are named on.
        :return: The stored declarations behind the keys.
        :raises NotFoundError: When one of the keys is not declared.
        :raises ValidationError: When a declared platform does not belong to the industry of the event.
        """
        resolved = await self._resolve(kind=PLATFORM_TYPE_KIND, keys=keys)
        for document in resolved:
            if document.industries and industry not in document.industries:
                raise ValidationError(
                    message="The platform is not declared for the industry of this event",
                    details={"platform": document.key, "industry": industry},
                )

        return resolved

    async def update_event_type(self, type_id: str, request: EventTypeUpdateRequest) -> EventTypeResponse:
        """
        Change a stored event type, leaving every attribute the caller omitted untouched.

        :param type_id: Identifier of the event type that is changed.
        :param request: Attributes the caller wants to change.
        :return: The changed event type.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._update(type_id=type_id, updates=request.model_dump(exclude_unset=True))

        return document.to_event_type()

    async def update_entity_type(self, type_id: str, request: EntityTypeUpdateRequest) -> EntityTypeResponse:
        """
        Change a stored entity type, leaving every attribute the caller omitted untouched.

        :param type_id: Identifier of the entity type that is changed.
        :param request: Attributes the caller wants to change.
        :return: The changed entity type.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._update(type_id=type_id, updates=request.model_dump(exclude_unset=True))

        return document.to_entity_type()

    async def delete_type(self, type_id: str, user: UserContext) -> None:
        """
        Remove a stored type declaration.

        :param type_id: Identifier of the type that is removed.
        :param user: Identity the removal is attributed to.
        :raises NotFoundError: When the identifier is unknown.
        """
        removed = await self._repository.delete(identifier=type_id, user=user.username)
        if not removed:
            raise NotFoundError(message="The type does not exist", details={"id": type_id})

    async def _insert(self, kind: str, key: str, values: dict[str, Any]) -> TypeDocument:
        """
        Write a new type declaration of one kind into the collection.

        :param kind: Whether an event type, an entity type or a platform is declared.
        :param key: Machine key of the type.
        :param values: Remaining attributes of the declaration.
        :return: The stored declaration.
        :raises ConflictError: When the kind already holds a type with the same key.
        """
        existing = await self._repository.find_by_key(kind=kind, key=key)
        if existing is not None:
            raise ConflictError(message="A type with this key is already declared", details={"kind": kind, "key": key})

        document = TypeDocument(kind=kind, key=key, **values)
        await self._repository.insert(document=document)

        return document

    async def _update(self, type_id: str, updates: dict[str, Any]) -> TypeDocument:
        """
        Change a stored type declaration and read it back.

        :param type_id: Identifier of the type that is changed.
        :param updates: Attributes and their new values.
        :return: The changed declaration.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._repository.find_by_id(identifier=type_id)
        if document is None:
            raise NotFoundError(message="The type does not exist", details={"id": type_id})

        await self._repository.update_fields(identifier=type_id, updates=updates)
        refreshed = await self._repository.find_by_id(identifier=type_id)
        if refreshed is None:
            raise NotFoundError(message="The type does not exist", details={"id": type_id})

        return refreshed

    async def resolve_event_types(self, keys: list[str]) -> list[TypeDocument]:
        """
        Resolve the event type keys chosen in the wizard into the stored declarations.

        :param keys: Machine keys the client sent.
        :return: The stored declarations behind the keys.
        :raises NotFoundError: When one of the keys is unknown.
        """
        return await self._resolve(kind=EVENT_TYPE_KIND, keys=keys)

    async def resolve_known_event_types(self, keys: list[str]) -> list[TypeDocument]:
        """
        Resolve event type keys into the declarations that still exist, passing over the ones that do not.

        A stored event names the types it was filed under, and a type may be removed long after events were
        filed under it. Reading those keys back strictly would make such an event refuse to be edited at all,
        which is a far worse answer than a form that no longer asks what the removed type used to ask.

        :param keys: Machine keys read off a stored event.
        :return: The stored declarations behind the keys that are still declared.
        """
        resolved: list[TypeDocument] = []
        for key in keys:
            document = await self._repository.find_by_key(kind=EVENT_TYPE_KIND, key=key)
            if document is not None:
                resolved.append(document)

        return resolved

    async def resolve_entity_type(self, key: str) -> TypeDocument:
        """
        Resolve a single entity type key into the stored declaration.

        :param key: Machine key the client sent.
        :return: The stored declaration behind the key.
        :raises NotFoundError: When the key is unknown.
        """
        resolved = await self._resolve(kind=ENTITY_TYPE_KIND, keys=[key])

        return resolved[0]

    async def _resolve(self, kind: str, keys: list[str]) -> list[TypeDocument]:
        """
        Resolve a list of type keys of one kind into the stored declarations.

        :param kind: Whether event types, entity types or platforms are resolved.
        :param keys: Machine keys the client sent.
        :return: The stored declarations behind the keys.
        :raises NotFoundError: When one of the keys is unknown.
        """
        resolved: list[TypeDocument] = []
        for key in keys:
            document = await self._repository.find_by_key(kind=kind, key=key)
            if document is None:
                raise NotFoundError(message="The type is not declared", details={"kind": kind, "key": key})
            resolved.append(document)

        return resolved
