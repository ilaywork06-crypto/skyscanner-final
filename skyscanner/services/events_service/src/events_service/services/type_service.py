"""
The rules around the declared event types and entity types the create wizard and the event page work with.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from skyscanner_common.errors import ConflictError, NotFoundError, ValidationError
from skyscanner_models.common import RenameResult, UserContext
from skyscanner_models.entity import EntityTypeCreateRequest, EntityTypeResponse, EntityTypeUpdateRequest
from skyscanner_models.event import EventTypeCreateRequest, EventTypeResponse, EventTypeUpdateRequest

from events_service.constants import ENTITY_TYPE_KIND, EVENT_TYPE_KIND
from events_service.documents import TypeDocument
from events_service.repositories.type_repository import TypeRepository
from events_service.services.rename_service import RenameService

# ----- CLASSES ----- #


class TypeService:
    """
    Owner of the declared types, resolving the keys the client sends into the references stored in the documents.
    """

    def __init__(self, repository: TypeRepository, renames: RenameService) -> None:
        """
        Bind the service to the type declarations and to the rewriter that carries a changed key through.

        :param repository: Persistence of the type declarations.
        :param renames: Owner of the rewrites a changed key or label costs elsewhere in the store.
        """
        self._repository = repository
        self._renames = renames

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

    async def update_event_type(self, type_id: str, request: EventTypeUpdateRequest) -> EventTypeResponse:
        """
        Change a stored event type, leaving every attribute the caller omitted untouched.

        :param type_id: Identifier of the event type that is changed.
        :param request: Attributes the caller wants to change.
        :return: The changed event type.
        :raises NotFoundError: When the identifier is unknown.
        """
        updates = request.model_dump(exclude_unset=True)
        stored = await self._require(type_id=type_id)
        await self._move_key(document=stored, updates=updates, entity=False)
        document = await self._update(type_id=type_id, updates=updates)
        await self._move_label(document=stored, updates=updates, entity=False)

        return document.to_event_type()

    async def update_entity_type(self, type_id: str, request: EntityTypeUpdateRequest) -> EntityTypeResponse:
        """
        Change a stored entity type, leaving every attribute the caller omitted untouched.

        :param type_id: Identifier of the entity type that is changed.
        :param request: Attributes the caller wants to change.
        :return: The changed entity type.
        :raises NotFoundError: When the identifier is unknown.
        """
        updates = request.model_dump(exclude_unset=True)
        stored = await self._require(type_id=type_id)
        await self._move_key(document=stored, updates=updates, entity=True)
        document = await self._update(type_id=type_id, updates=updates)
        await self._move_label(document=stored, updates=updates, entity=True)

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

    async def preview_rename(self, type_id: str, key: str) -> RenameResult:
        """
        Say what renaming a declared type would touch, without touching any of it.

        A key is stored by value on every event filed under the type, so changing one is a write across the
        store rather than an edit to a single document. Whoever is about to do that is shown the size of it
        first, which is the difference between an informed change and a surprise.

        :param type_id: Identifier of the type that would be renamed.
        :param key: Key it would be renamed to.
        :return: How many documents of each collection carry the current key.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._require(type_id=type_id)
        affected = await self._rename(document=document, key=key, entity=document.kind == ENTITY_TYPE_KIND, apply=False)

        return RenameResult(key=key, previous_key=document.key, affected=affected)

    async def _require(self, type_id: str) -> TypeDocument:
        """
        Read a type declaration by its identifier, refusing one that does not exist.

        :param type_id: Identifier of the type.
        :return: The stored declaration.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._repository.find_by_id(identifier=type_id)
        if document is None:
            raise NotFoundError(message="The type does not exist", details={"id": type_id})

        return document

    async def _move_key(self, document: TypeDocument, updates: dict[str, Any], entity: bool) -> dict[str, int]:
        """
        Carry a changed key through every document naming it, or do nothing when the key is not what changed.

        The rewrite runs before the declaration itself is written, so a key that turns out to be taken is
        refused with the store exactly as it was rather than half moved.

        :param document: The declaration as it stands before the change.
        :param updates: Attributes the caller wants to change, from which a key of no change is dropped.
        :param entity: Whether an entity type is being renamed rather than an event type.
        :return: How many documents of each collection were rewritten.
        :raises ConflictError: When the new key is already taken by another declaration of the same kind.
        :raises ValidationError: When the new key is empty.
        """
        key = updates.get("key")
        if key is None or key == document.key:
            updates.pop("key", None)

            return {}

        if not isinstance(key, str) or not key.strip():
            raise ValidationError(message="A type needs a key", details={"id": document.id})

        taken = await self._repository.find_by_key(kind=document.kind, key=key)
        if taken is not None and taken.id != document.id:
            raise ConflictError(
                message="A type with this key is already declared",
                details={"kind": document.kind, "key": key},
            )

        return await self._rename(document=document, key=key, entity=entity, apply=True)

    async def _rename(self, document: TypeDocument, key: str, entity: bool, apply: bool) -> dict[str, int]:
        """
        Run the rewrite one kind of declaration asks for, or count what it would rewrite.

        :param document: The declaration as it stands before the change.
        :param key: Key it is moving to.
        :param entity: Whether an entity type is being renamed rather than an event type.
        :param apply: Whether the documents are rewritten, or only counted.
        :return: How many documents of each collection carry the key.
        """
        if entity:
            return await self._renames.rename_entity_type(old=document.key, new=key, apply=apply)

        return await self._renames.rename_event_type(old=document.key, new=key, apply=apply)

    async def _move_label(self, document: TypeDocument, updates: dict[str, Any], entity: bool) -> None:
        """
        Carry a changed label through the copies of it the events already carry.

        An event stores the name of its type beside the reference to it so that a row reads without a lookup,
        which means a label changed on the declaration alone is a label the table goes on showing the old
        spelling of forever.

        :param document: The declaration as it stood before the change.
        :param updates: Attributes the caller asked to change.
        :param entity: Whether an entity type was relabelled rather than an event type.
        """
        name = updates.get("name")
        if not isinstance(name, str) or name == document.name:
            return

        await self._renames.relabel_type(type_id=document.id, name=name, entity=entity)

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
