"""
Carrying a renamed declaration through every document that points at it by its key.

:date: 2026-09-08
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any, Callable

from skyscanner_common.logging_utils import get_logger
from skyscanner_common.mongo import MongoProvider
from skyscanner_models.enums import FieldScope

from events_service.constants import (
    EVENTS_COLLECTION,
    FIELDS_COLLECTION,
    SUBSCRIPTIONS_COLLECTION,
    TEMPLATES_COLLECTION,
    TYPES_COLLECTION,
)

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)

# What one rename touched, by the collection it touched it in.
Tally = dict[str, int]

# The generated columns a declaration is filtered and sorted by in a saved view, per kind of declaration.
# A view names its columns rather than the values inside them, so only the columns that hold a key are read.
EVENT_TYPE_COLUMNS: frozenset[str] = frozenset({"event_type_keys", "event_type_names"})
PLATFORM_COLUMNS: frozenset[str] = frozenset({"platforms"})
ENTITY_TYPE_COLUMNS: frozenset[str] = frozenset({"object_type_key"})

# ----- CLASSES ----- #


class RenameService:
    """
    The one place a machine key is carried from its old spelling to its new one across the whole store.

    A key is not an identifier here: an event names the types it was filed under, the platforms it ran on and
    the fields it answered by their key, and it stores those keys rather than pointing at the declarations.
    That is what makes a key editable at all a question rather than a checkbox - the alternative to carrying
    the change through is a store where half the documents name something that no longer exists.

    The reading is deliberately narrow. Every rewrite starts from a query that matches only the documents
    that actually carry the old key, so renaming a type nobody ever used costs one query per collection and
    writes nothing at all.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the service to the document store every collection is rewritten through.

        :param provider: Owner of the shared motor client.
        """
        self._provider = provider

    async def rename_event_type(self, old: str, new: str, apply: bool = True) -> Tally:
        """
        Carry a renamed event type through the events, the subscriptions and the saved views naming it.

        :param old: Key the event type used to be declared under.
        :param new: Key it is declared under from now on.
        :param apply: Whether the documents are rewritten, or only counted for a caller asking what would be.
        :return: How many documents of each collection carry the key.
        """

        def rewrite(event: dict[str, Any]) -> dict[str, Any]:
            """
            Move the key wherever this event lists the types it was filed under.

            :param event: The event as it is stored.
            :return: The attributes of it that have to be written back.
            """
            keys = [new if key == old else key for key in event.get("event_type_keys", [])]

            return {"event_type_keys": keys}

        return {
            EVENTS_COLLECTION: await self._events({"event_type_keys": old}, rewrite, apply),
            SUBSCRIPTIONS_COLLECTION: await self._simple(
                SUBSCRIPTIONS_COLLECTION,
                {"event_type_key": old},
                {"event_type_key": new},
                apply,
            ),
            TEMPLATES_COLLECTION: await self._templates(EVENT_TYPE_COLUMNS, old, new, apply),
        }

    async def rename_platform(self, old: str, new: str, apply: bool = True) -> Tally:
        """
        Carry a renamed platform through the events that ran on it and the saved views naming it.

        :param old: Key the platform used to be declared under.
        :param new: Key it is declared under from now on.
        :param apply: Whether the documents are rewritten, or only counted.
        :return: How many documents of each collection carry the key.
        """

        def rewrite(event: dict[str, Any]) -> dict[str, Any]:
            """
            Move the key wherever this event lists the platforms it ran on.

            :param event: The event as it is stored.
            :return: The attributes of it that have to be written back.
            """
            return {"platforms": [new if key == old else key for key in event.get("platforms", [])]}

        return {
            EVENTS_COLLECTION: await self._events({"platforms": old}, rewrite, apply),
            TEMPLATES_COLLECTION: await self._templates(PLATFORM_COLUMNS, old, new, apply),
        }

    async def rename_entity_type(self, old: str, new: str, apply: bool = True) -> Tally:
        """
        Carry a renamed entity type through its entities, the counts of them and the fields scoped to it.

        :param old: Key the entity type used to be declared under.
        :param new: Key it is declared under from now on.
        :param apply: Whether the documents are rewritten, or only counted.
        :return: How many documents of each collection carry the key.
        """

        def rewrite(event: dict[str, Any]) -> dict[str, Any]:
            """
            Move the key on every entity of this event, and on the count kept under it.

            :param event: The event as it is stored.
            :return: The attributes of it that have to be written back.
            """
            entities = event.get("objects", [])
            for entity in entities:
                if entity.get("object_type_key") == old:
                    entity["object_type_key"] = new

            # The counts are a map keyed by the very thing being renamed, so the key itself moves.
            counts = dict(event.get("entity_counts", {}))
            if old in counts:
                counts[new] = counts.pop(old)

            return {"objects": entities, "entity_counts": counts}

        query = {"$or": [{"objects.object_type_key": old}, {f"entity_counts.{old}": {"$exists": True}}]}

        return {
            EVENTS_COLLECTION: await self._events(query, rewrite, apply),
            FIELDS_COLLECTION: await self._simple(
                FIELDS_COLLECTION,
                {"entity_type": old},
                {"entity_type": new},
                apply,
            ),
            TEMPLATES_COLLECTION: await self._templates(ENTITY_TYPE_COLUMNS, old, new, apply),
        }

    async def rename_field(self, old: str, new: str, scope: FieldScope, apply: bool = True) -> Tally:
        """
        Carry a renamed declaration through every value stored under its key.

        A dynamic value is stored twice on purpose - once in the `metadata` list the schema asks for and once
        in the flat `data` sub document that filtering and sorting are cheap over - so both spellings of it
        have to move, or a column would go on filtering by a key that nothing answers any more.

        :param old: Key the field used to be declared under.
        :param new: Key it is declared under from now on.
        :param scope: Whether the declaration describes events or the entities inside them.
        :param apply: Whether the documents are rewritten, or only counted.
        :return: How many documents of each collection carry the key.
        """
        if scope is FieldScope.EVENT:
            query: dict[str, Any] = {"$or": [{"metadata.key": old}, {f"data.{old}": {"$exists": True}}]}

            def rewrite(event: dict[str, Any]) -> dict[str, Any]:
                """
                Move the key in both places this event stores a dynamic value under it.

                :param event: The event as it is stored.
                :return: The attributes of it that have to be written back.
                """
                return {
                    "metadata": _renamed_attributes(event.get("metadata", []), old, new),
                    "data": _renamed_values(event.get("data", {}), old, new),
                }

        else:
            query = {
                "$or": [{"objects.metadata.key": old}, {f"objects.data.{old}": {"$exists": True}}],
            }

            def rewrite(event: dict[str, Any]) -> dict[str, Any]:
                """
                Move the key in both places every entity of this event stores a dynamic value under it.

                :param event: The event as it is stored.
                :return: The attributes of it that have to be written back.
                """
                entities = event.get("objects", [])
                for entity in entities:
                    entity["metadata"] = _renamed_attributes(entity.get("metadata", []), old, new)
                    entity["data"] = _renamed_values(entity.get("data", {}), old, new)

                return {"objects": entities}

        tally = {
            EVENTS_COLLECTION: await self._events(query, rewrite, apply),
            TEMPLATES_COLLECTION: await self._templates(frozenset({old}), old, new, apply, rename_column=True),
        }

        # An event type names the declared event fields it asks for, and it asks for them by key.
        if scope is FieldScope.EVENT:
            tally[TYPES_COLLECTION] = await self._type_custom_fields(old, new, apply)

        return tally

    async def relabel_type(self, type_id: str, name: str, entity: bool) -> int:
        """
        Carry a renamed label through the denormalised copies of it the events carry.

        An event stores the name of its type beside the reference to it, so that a row of the table can be
        read without looking anything up. That copy is what a table, an export and a saved view all read, so
        a label changed on the declaration alone is a label nobody sees changed.

        :param type_id: Identifier of the declaration whose label changed.
        :param name: The label it carries from now on.
        :param entity: Whether an entity type is being relabelled rather than an event type.
        :return: How many events were rewritten.
        """
        if entity:

            def rewrite(event: dict[str, Any]) -> dict[str, Any]:
                """
                Put the new label on every entity of this event that is an instance of the type.

                :param event: The event as it is stored.
                :return: The attributes of it that have to be written back.
                """
                entities = event.get("objects", [])
                for stored in entities:
                    if stored.get("object_type", {}).get("id") == type_id:
                        stored["object_type"]["name"] = name
                        stored["object_type_name"] = name

                return {"objects": entities}

            return await self._events({"objects.object_type.id": type_id}, rewrite, apply=True)

        def rewrite_event(event: dict[str, Any]) -> dict[str, Any]:
            """
            Put the new label on the reference this event keeps, and on the copy the table reads.

            :param event: The event as it is stored.
            :return: The attributes of it that have to be written back.
            """
            references = event.get("event_type", [])
            for reference in references:
                if reference.get("id") == type_id:
                    reference["name"] = name

            return {
                "event_type": references,
                "event_type_names": [reference.get("name", "") for reference in references],
            }

        return await self._events({"event_type.id": type_id}, rewrite_event, apply=True)

    async def _events(
        self,
        query: dict[str, Any],
        rewrite: Callable[[dict[str, Any]], dict[str, Any]],
        apply: bool,
    ) -> int:
        """
        Rewrite every event matching a restriction, or count them when the caller only asked what would move.

        The events are rewritten one at a time rather than with a single update, because the keys being
        carried sit inside arrays and inside maps keyed by the very thing that is changing - neither of which
        one update statement can express. A rename is a rare, deliberate act by somebody administering the
        system, and being able to answer for exactly what it touched is worth more here than being quick.

        :param query: Restriction matching only the events that carry the old key.
        :param rewrite: Builds the attributes one event has to have written back.
        :param apply: Whether the events are rewritten, or only counted.
        :return: How many events carry the key.
        """
        events = self._provider.collection(EVENTS_COLLECTION)
        if not apply:
            return int(await events.count_documents(query))

        touched = 0
        async for stored in events.find(query):
            updates = rewrite(stored)
            if updates:
                await events.update_one({"_id": stored["_id"]}, {"$set": updates})
            touched += 1

        return touched

    async def _simple(self, collection: str, query: dict[str, Any], updates: dict[str, Any], apply: bool) -> int:
        """
        Rewrite one plain attribute wherever it holds the old key.

        :param collection: Collection being rewritten.
        :param query: Restriction matching the documents that carry the old key.
        :param updates: The attribute and its new value.
        :param apply: Whether the documents are rewritten, or only counted.
        :return: How many documents carry the key.
        """
        handle = self._provider.collection(collection)
        if not apply:
            return int(await handle.count_documents(query))

        result = await handle.update_many(query, {"$set": updates})

        return int(result.modified_count)

    async def _type_custom_fields(self, old: str, new: str, apply: bool) -> int:
        """
        Carry a renamed event field through the event types that ask for it.

        :param old: Key the field used to be declared under.
        :param new: Key it is declared under from now on.
        :param apply: Whether the declarations are rewritten, or only counted.
        :return: How many declarations ask for the field.
        """
        types = self._provider.collection(TYPES_COLLECTION)
        query = {"custom_fields": old}
        if not apply:
            return int(await types.count_documents(query))

        result = await types.update_many(
            query,
            {"$set": {"custom_fields.$[asked]": new}},
            array_filters=[{"asked": old}],
        )

        return int(result.modified_count)

    async def _templates(
        self,
        columns: frozenset[str],
        old: str,
        new: str,
        apply: bool,
        rename_column: bool = False,
    ) -> int:
        """
        Carry a rename through the saved views that filter, sort or show what was renamed.

        A view is somebody's arrangement of the table, and a filter inside it names both the column it
        narrows and the values it narrows to. Renaming a platform without touching the views would leave the
        reader who works out of one looking at an empty table and no reason for it.

        :param columns: Which generated columns hold the key that is moving.
        :param old: The old spelling.
        :param new: The new spelling.
        :param apply: Whether the views are rewritten, or only counted.
        :param rename_column: Whether the column itself is named after the key, as a dynamic field's is.
        :return: How many views name the key.
        """
        templates = self._provider.collection(TEMPLATES_COLLECTION)
        fields = list(columns)
        query: dict[str, Any] = {
            "$or": [
                {"filters": {"$elemMatch": {"field": {"$in": fields}}}},
                {"sort": {"$elemMatch": {"field": {"$in": fields}}}},
                {"columns": {"$elemMatch": {"col_id": {"$in": fields}}}},
            ],
        }
        if not apply:
            return int(await templates.count_documents(query))

        touched = 0
        async for stored in templates.find(query):
            updates = _renamed_template(stored, columns, old, new, rename_column)
            if updates:
                await templates.update_one({"_id": stored["_id"]}, {"$set": updates})
                touched += 1

        return touched


# ----- FUNCTIONS ----- #


def _renamed_attributes(attributes: list[Any], old: str, new: str) -> list[Any]:
    """
    Move every stored attribute written under one key onto another.

    :param attributes: The attributes as they are stored.
    :param old: The key that is moving.
    :param new: Where it is moving to.
    :return: The same attributes with the key rewritten.
    """
    for attribute in attributes:
        if isinstance(attribute, dict) and attribute.get("key") == old:
            attribute["key"] = new

    return attributes


def _renamed_values(values: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    """
    Move one entry of the flattened values onto another key, keeping the order of the rest.

    :param values: The flattened values as they are stored.
    :param old: The key that is moving.
    :param new: Where it is moving to.
    :return: The same values under the new key.
    """
    if old not in values:
        return values

    moved = dict(values)
    moved[new] = moved.pop(old)

    return moved


def _renamed_template(
    template: dict[str, Any],
    columns: frozenset[str],
    old: str,
    new: str,
    rename_column: bool,
) -> dict[str, Any]:
    """
    Rewrite one saved view so that it goes on meaning what it meant before the rename.

    :param template: The view as it is stored.
    :param columns: Which generated columns hold the key that is moving.
    :param old: The old spelling.
    :param new: The new spelling.
    :param rename_column: Whether the column itself is named after the key.
    :return: The attributes of the view that have to be written back.
    """
    filters = template.get("filters", [])
    for condition in filters:
        if not isinstance(condition, dict):
            continue
        if rename_column and condition.get("field") == old:
            condition["field"] = new
        if condition.get("field") not in columns and not (rename_column and condition.get("field") == new):
            continue
        if condition.get("value") == old:
            condition["value"] = new
        stored = condition.get("values")
        if isinstance(stored, list):
            condition["values"] = [new if item == old else item for item in stored]

    sort = template.get("sort", [])
    for order in sort:
        if isinstance(order, dict) and rename_column and order.get("field") == old:
            order["field"] = new

    presented = template.get("columns", [])
    for column in presented:
        if isinstance(column, dict) and rename_column and column.get("col_id") == old:
            column["col_id"] = new

    return {"filters": filters, "sort": sort, "columns": presented}
