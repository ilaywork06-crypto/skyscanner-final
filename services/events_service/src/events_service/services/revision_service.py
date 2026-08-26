"""
The edit history - turning one change into a record of who made it, why, and what every value was before.

:date: 2026-08-12
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any, Mapping

from pydantic_core import to_jsonable_python

from skyscanner_common.text import humanize_key
from skyscanner_models.common import UserContext
from skyscanner_models.enums import RevisionTarget
from skyscanner_models.revision import FieldChange, RevisionResponse

from events_service.documents import EntityDocument, EventDocument, RevisionDocument
from events_service.repositories.revision_repository import RevisionRepository

# ----- CONSTS ----- #

DYNAMIC_PREFIX: str = "data"

# Attributes worth remembering the previous value of. The stored documents also carry bookkeeping such as the
# denormalised type names and the update stamps, which say nothing a reader of the history wants to know.
TRACKED_EVENT_KEYS: tuple[str, ...] = (
    "name",
    "reference_id",
    "industry",
    "platforms",
    "status",
    "experiment_result",
    "event_date",
    "notes",
    "event_type_names",
    "additional_files",
)

TRACKED_ENTITY_KEYS: tuple[str, ...] = (
    "name",
    "module",
    "code_version",
    "status",
    "notes",
    "requested_at",
    "received_at",
    "raw_files",
    "parsed_files",
    "parsed_additional_files",
)

FILE_KEYS: frozenset[str] = frozenset(
    {"additional_files", "raw_files", "parsed_files", "parsed_additional_files"},
)

# ----- CLASSES ----- #


class RevisionService:
    """
    Owner of the edit history, writing one record per change and reading it back for the history view.
    """

    def __init__(self, repository: RevisionRepository) -> None:
        """
        Bind the service to the persistence of the recorded edits.

        :param repository: Persistence of the revisions.
        """
        self._repository = repository

    async def record_event_change(
        self,
        before: EventDocument,
        after: EventDocument,
        reason: str,
        user: UserContext,
    ) -> RevisionResponse | None:
        """
        Record what one edit of an event moved, skipping the record when nothing actually changed.

        :param before: State of the event before the edit.
        :param after: State of the event after the edit.
        :param reason: Why the change was made.
        :param user: Identity that made the change.
        :return: The recorded revision, or nothing when the edit left every value as it was.
        """
        changes = build_changes(
            before=flatten_event(document=before),
            after=flatten_event(document=after),
        )
        if not changes:
            return None

        return await self._store(
            target=RevisionTarget.EVENT,
            event_id=after.id,
            entity_id=None,
            entity_name="",
            changes=changes,
            reason=reason,
            user=user,
        )

    async def record_entity_change(
        self,
        event_id: str,
        before: EntityDocument,
        after: EntityDocument,
        reason: str,
        user: UserContext,
    ) -> RevisionResponse | None:
        """
        Record what one edit of an entity moved, skipping the record when nothing actually changed.

        :param event_id: Identifier of the event the entity belongs to.
        :param before: State of the entity before the edit.
        :param after: State of the entity after the edit.
        :param reason: Why the change was made.
        :param user: Identity that made the change.
        :return: The recorded revision, or nothing when the edit left every value as it was.
        """
        changes = build_changes(
            before=flatten_entity(document=before),
            after=flatten_entity(document=after),
        )
        if not changes:
            return None

        return await self._store(
            target=RevisionTarget.ENTITY,
            event_id=event_id,
            entity_id=after.id,
            entity_name=after.name,
            changes=changes,
            reason=reason,
            user=user,
        )

    async def record_entity_addition(
        self,
        event_id: str,
        entity: EntityDocument,
        user: UserContext,
    ) -> RevisionResponse:
        """
        Record that an entity was attached to an event that already existed.

        Attaching an entity is an edit of the event like any other, so the history has to say when it
        happened and who did it. There is no previous state to compare against, so every attribute the
        entity arrived with is reported as a value that was not there before rather than as a value that
        moved, which is exactly how the history renders an attribute that used to be empty.

        :param event_id: Identifier of the event the entity was attached to.
        :param entity: Entity as it was stored.
        :param user: Identity that attached the entity.
        :return: The recorded revision.
        """
        changes = build_changes(before={}, after=flatten_entity(document=entity))

        return await self._store(
            target=RevisionTarget.ENTITY,
            event_id=event_id,
            entity_id=entity.id,
            entity_name=entity.name,
            changes=changes,
            reason="The entity was attached to the event",
            user=user,
        )

    async def record_entity_removal(
        self,
        event_id: str,
        entity: EntityDocument,
        user: UserContext,
    ) -> RevisionResponse:
        """
        Record that an entity was removed from an event, keeping what it held at that moment.

        The entity itself is gone once the removal is written, so the record is what is left of it: every
        attribute it carried is reported as a value that no longer has an entity to belong to.

        :param event_id: Identifier of the event the entity was removed from.
        :param entity: Entity as it stood before the removal.
        :param user: Identity that removed the entity.
        :return: The recorded revision.
        """
        changes = build_changes(before=flatten_entity(document=entity), after={})

        return await self._store(
            target=RevisionTarget.ENTITY,
            event_id=event_id,
            entity_id=entity.id,
            entity_name=entity.name,
            changes=changes,
            reason="The entity was removed from the event",
            user=user,
        )

    async def list_history(
        self,
        event_id: str,
        entity_id: str | None = None,
        include_entities: bool = False,
    ) -> list[RevisionResponse]:
        """
        Read the recorded edits of one event or of one of its entities.

        :param event_id: Identifier of the event the history is read for.
        :param entity_id: Identifier of one entity, empty for the event itself.
        :param include_entities: Whether the edits of the nested entities are read as well.
        :return: The matching edits, newest first.
        """
        documents = await self._repository.list_history(
            event_id=event_id,
            entity_id=entity_id,
            include_entities=include_entities,
        )

        return [document.to_response() for document in documents]

    async def _store(
        self,
        target: RevisionTarget,
        event_id: str,
        entity_id: str | None,
        entity_name: str,
        changes: list[FieldChange],
        reason: str,
        user: UserContext,
    ) -> RevisionResponse:
        """
        Write one revision, giving it the next running number of its target.

        Whether an edit is worth a record is decided by the caller: an edit that moved nothing is not
        recorded at all, while attaching or removing an entity is recorded even when the entity was bare.

        :param target: Whether the edit changed an event or an entity.
        :param event_id: Identifier of the event the edit belongs to.
        :param entity_id: Identifier of the entity, empty for an event edit.
        :param entity_name: Name of the entity at the moment of the edit.
        :param changes: Attributes the edit moved.
        :param reason: Why the change was made.
        :param user: Identity that made the change.
        :return: The recorded revision.
        """
        version = await self._repository.next_version(event_id=event_id, entity_id=entity_id)
        document = RevisionDocument(
            target=target,
            event_id=event_id,
            entity_id=entity_id,
            entity_name=entity_name,
            version=version,
            reason=reason,
            changed_by=user.username,
            changes=changes,
        )
        await self._repository.insert(document=document)

        return document.to_response()


# ----- FUNCTIONS ----- #


def build_changes(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[FieldChange]:
    """
    Compare two flattened states and describe every attribute that moved between them.

    :param before: Flattened state before the edit.
    :param after: Flattened state after the edit.
    :return: One entry per attribute whose value changed.
    """
    changes: list[FieldChange] = []
    for key in sorted(set(before) | set(after)):
        old_value = before.get(key)
        new_value = after.get(key)
        if old_value == new_value:
            continue

        changes.append(
            FieldChange(
                key=key,
                label=_label_of(key=key),
                before=to_jsonable_python(old_value),
                after=to_jsonable_python(new_value),
            ),
        )

    return changes


def event_update_changes(document: EventDocument, updates: Mapping[str, Any]) -> list[FieldChange]:
    """
    Describe what an update would move on an event, before a single attribute of it is written.

    The attributes a request carries are not the attributes it changes: a caller may hand back exactly what
    is already stored. Reading the change out of the two states rather than out of the request is what lets
    the service refuse an edit that edits nothing, and reading it with the very same comparison the history
    uses is what keeps the two from ever disagreeing about what changed.

    :param document: Event as it is stored right now.
    :param updates: Attributes the update would write onto it.
    :return: One entry per attribute the update would move, empty when it would move nothing.
    """
    prospective = EventDocument.model_validate({**document.model_dump(by_alias=True), **updates})

    return build_changes(before=flatten_event(document=document), after=flatten_event(document=prospective))


def entity_update_changes(document: EntityDocument, updates: Mapping[str, Any]) -> list[FieldChange]:
    """
    Describe what an update would move on an entity, before a single attribute of it is written.

    :param document: Entity as it is stored right now.
    :param updates: Attributes the update would write onto it.
    :return: One entry per attribute the update would move, empty when it would move nothing.
    """
    prospective = EntityDocument.model_validate({**document.model_dump(by_alias=True), **updates})

    return build_changes(before=flatten_entity(document=document), after=flatten_entity(document=prospective))


def flatten_event(document: EventDocument) -> dict[str, Any]:
    """
    Reduce an event to the attributes the history remembers, with its dynamic values as their own entries.

    :param document: Event that is being compared.
    :return: The flattened state of the event.
    """
    return _flatten(document=document, tracked=TRACKED_EVENT_KEYS)


def flatten_entity(document: EntityDocument) -> dict[str, Any]:
    """
    Reduce an entity to the attributes the history remembers, with its dynamic values as their own entries.

    :param document: Entity that is being compared.
    :return: The flattened state of the entity.
    """
    return _flatten(document=document, tracked=TRACKED_ENTITY_KEYS)


def _flatten(document: EventDocument | EntityDocument, tracked: tuple[str, ...]) -> dict[str, Any]:
    """
    Reduce a stored document to a flat mapping of the attributes the history compares.

    Each dynamic value becomes an entry of its own, so that changing one declared field is reported as that
    single field moving rather than as the whole bag of metadata being replaced.

    :param document: Document that is being compared.
    :param tracked: Attributes that are remembered for this kind of document.
    :return: The flattened state of the document.
    """
    state: dict[str, Any] = {}
    for key in tracked:
        value = getattr(document, key, None)
        state[key] = _readable(key=key, value=value)

    for key, value in document.data.items():
        state[f"{DYNAMIC_PREFIX}.{key}"] = value

    return state


def _readable(key: str, value: Any) -> Any:
    """
    Turn one stored attribute into the shape the history compares and shows.

    A list of files is compared by the names it holds: the stored records also carry checksums and sizes,
    which would report a file as changed when nothing about it changed for a reader.

    :param key: Attribute the value belongs to.
    :param value: Value read from the document.
    :return: The comparable shape of the value.
    """
    if key in FILE_KEYS and isinstance(value, list):
        return [getattr(item, "name", str(item)) for item in value]

    return to_jsonable_python(value)


def _label_of(key: str) -> str:
    """
    Build the label a changed attribute is shown under.

    :param key: Key of the changed attribute.
    :return: The label the user reads.
    """
    if key.startswith(f"{DYNAMIC_PREFIX}."):
        return humanize_key(key.split(".", maxsplit=1)[1])

    return humanize_key(key)
