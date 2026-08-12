"""
Persistence of the events and of the entities nested inside them, including the queries behind the inventory table.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import asyncio
import json
import time
from collections import OrderedDict
from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel

from ag_grid_lib.datasource import (
    DYNAMIC_VALUE_ROOT,
    build_mongo_filter,
    build_mongo_sort,
    build_text_search_filter,
    merge_filters,
)
from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.mongo import MongoProvider
from skyscanner_models.enums import EntityStatus, ParseState
from skyscanner_models.query import SearchQuery

from events_service.constants import EVENTS_COLLECTION, EVENT_SEARCH_PATHS, FIXED_EVENT_KEYS
from events_service.documents import EntityDocument, EventDocument
from events_service.repositories.base_repository import IDENTIFIER_FIELD, BaseRepository

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)

OBJECTS_FIELD: str = "objects"
INDUSTRY_FIELD: str = "industry"
PARSED_STATUSES: list[str] = [EntityStatus.PARSED.value]
DEFAULT_SORT: list[tuple[str, int]] = [("created_at", DESCENDING)]

# The entities of an event are by far the heaviest part of the document - an event of the seeded inventory is
# around four kilobytes and roughly three quarters of that is the nested entities with their file records.
# Neither a page of the table nor a sheet of the export renders them, so leaving them behind cuts the bytes
# read, the BSON decoded and the models validated by the same three quarters.
WITHOUT_ENTITIES: dict[str, Any] = {OBJECTS_FIELD: 0}

# The totals behind the table are memoised because the grid asks for the very same restriction once per block
# while the user scrolls, and counting a free text restriction means reading every document. The memory is
# dropped as soon as this process writes an event, so the only staleness it can show is a write made by
# another replica inside the time to live.
TOTAL_CACHE_TTL_SECONDS: float = 15.0
TOTAL_CACHE_ENTRIES: int = 512
INDUSTRY_COUNTS_KEY: str = "__industry_counts__"

# The dynamic values a script wrote without declaring them are unbounded in number, so only the declared ones
# are indexed, and even those are capped well below the sixty four indexes a collection may carry.
MAX_DYNAMIC_INDEXES: int = 32
DYNAMIC_INDEX_PREFIX: str = "dynamic_"

_TOTALS: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()

# ----- CLASSES ----- #


class EventRepository(BaseRepository[EventDocument]):
    """
    The single door to the events collection, translating the table query into a document store query.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the events collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=EVENTS_COLLECTION, document_type=EventDocument)

    async def ensure_indexes(self) -> None:
        """
        Create the indexes that keep the inventory table responsive on a large collection.

        Every index that is not a uniqueness rule is compound and ends in the attribute the table orders by.
        A single attribute index lets the document store find the matching events but not hand them over in
        order, so it has to read every match and sort them afterwards; ending the index in the ordering makes
        the very same query walk the index and stop after one page, no matter how many events match.
        """
        await self.create_indexes(
            [
                IndexModel([("event_id", ASCENDING)], unique=True, name="event_id_unique"),
                # The identifier the user knows an event by names exactly one event, so it is unique. The
                # index is partial because most events carry no reference at all, and an ordinary unique
                # index would let only one of them hold the empty value.
                IndexModel(
                    [("reference_id", ASCENDING)],
                    unique=True,
                    partialFilterExpression={"reference_id": {"$gt": ""}},
                    name="reference_id_unique",
                ),
                IndexModel([("created_at", DESCENDING)], name="created_at"),
                IndexModel([("updated_at", DESCENDING)], name="updated_at"),
                IndexModel([("event_date", DESCENDING)], name="event_date"),
                IndexModel([("name", ASCENDING)], name="name"),
                IndexModel([(INDUSTRY_FIELD, ASCENDING), ("created_at", DESCENDING)], name="industry_created"),
                IndexModel([(INDUSTRY_FIELD, ASCENDING), ("event_date", DESCENDING)], name="industry_event_date"),
                # The industry tab plus the status filter is the combination the table is used with most, so
                # it gets an index of its own rather than being served by narrowing on the industry alone.
                IndexModel(
                    [(INDUSTRY_FIELD, ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
                    name="industry_status_created",
                ),
                IndexModel([("status", ASCENDING), ("created_at", DESCENDING)], name="status_created"),
                IndexModel(
                    [("experiment_result", ASCENDING), ("created_at", DESCENDING)],
                    name="experiment_result_created",
                ),
                IndexModel([("event_type_keys", ASCENDING), ("created_at", DESCENDING)], name="event_type_created"),
                IndexModel([("platform", ASCENDING), ("created_at", DESCENDING)], name="platform_created"),
            ],
        )

    async def ensure_dynamic_indexes(self, keys: list[str]) -> None:
        """
        Index the declared dynamic values so that ordering the table by one of them stays a paged read.

        Without an index the document store has to read every matching event into memory and sort it there,
        which is work that grows with the inventory rather than with the page. The indexes are deliberately
        not sparse: a sparse index holds no entry for an event that never carried the value, and the planner
        refuses to order by an index that would silently drop those events from the answer.

        :param keys: Keys of the declared dynamic values, of which the first ones are indexed.
        """
        wanted = sorted({key for key in keys if key})[:MAX_DYNAMIC_INDEXES]
        if not wanted:
            return

        await self.create_indexes(
            [
                IndexModel(
                    [(f"{DYNAMIC_VALUE_ROOT}.{key}", ASCENDING)],
                    name=f"{DYNAMIC_INDEX_PREFIX}{key}",
                )
                for key in wanted
            ],
        )
        LOGGER.info("Indexed %s declared dynamic values of the events", len(wanted))

    async def drop_legacy_indexes(self) -> None:
        """
        Remove the indexes an earlier deployment created that a compound index has since taken over.

        An index that only names the attribute a filter addresses cannot serve the ordering of the table as
        well, so each of them was replaced by a compound index that starts with the very same attribute. The
        old ones answer nothing the new ones do not, and every index left behind is paid for on every write.
        """
        await self.drop_index_if_present(name="reference_id")
        await self.drop_index_if_present(name="status")
        await self.drop_index_if_present(name="experiment_result")
        await self.drop_index_if_present(name="event_type_keys")

    async def find_by_reference(self, reference_id: str, excluding: str | None = None) -> EventDocument | None:
        """
        Read the event that carries one user supplied reference, if any event carries it.

        :param reference_id: Reference the user knows the event by.
        :param excluding: Event that is allowed to hold the reference, which is the one being changed.
        :return: The event holding the reference, or nothing when it is free.
        """
        query: dict[str, Any] = {"reference_id": reference_id}
        if excluding is not None:
            query[IDENTIFIER_FIELD] = {"$ne": excluding}

        return await self.find_one(query=query)

    def build_query(self, search: SearchQuery) -> dict[str, Any]:
        """
        Translate the toolbar and the grid filter model into the restriction the inventory query runs with.

        :param search: Query requested by the client.
        :return: The restriction matching documents have to satisfy.
        """
        clauses: list[dict[str, Any]] = []
        if search.industry:
            clauses.append({INDUSTRY_FIELD: search.industry})

        if search.search:
            clauses.append(build_text_search_filter(search=search.search, paths=EVENT_SEARCH_PATHS))

        clauses.append(build_mongo_filter(conditions=search.filters, fixed_keys=FIXED_EVENT_KEYS))
        clauses.append(_parse_state_clause(parse_state=search.parse_state))

        return merge_filters(*clauses)

    async def search(self, search: SearchQuery, include_entities: bool = False) -> tuple[list[EventDocument], int]:
        """
        Read one page of the inventory together with the total amount of matching events.

        The page and the total are asked for at the same time rather than one after the other, because the
        two are independent queries and the total is the slower of them whenever the restriction cannot be
        served by an index.

        The entities of an event are left out by default: a row of the table is built from the summary
        projection, which carries the counters of the entities but not the entities themselves. A caller that
        really needs them has to ask for them, otherwise it would silently read an event with an empty
        entity list.

        :param search: Query requested by the client.
        :param include_entities: Whether the entities nested inside the events are read as well.
        :return: The events of the requested page and the total amount of matching events.
        """
        query = self.build_query(search=search)
        sort = build_mongo_sort(specifications=search.sort, fixed_keys=FIXED_EVENT_KEYS) or DEFAULT_SORT

        documents, total = await asyncio.gather(
            self.find_many(
                query=query,
                sort=sort,
                skip=(search.page - 1) * search.page_size,
                limit=search.page_size,
                projection=None if include_entities else WITHOUT_ENTITIES,
            ),
            self.count_matching(query=query),
        )

        return documents, total

    async def count_matching(self, query: dict[str, Any]) -> int:
        """
        Work out how many events a restriction matches, without paying a scan for every page of the table.

        An unrestricted table asks the same question as "how big is the collection", which the document store
        answers out of its own metadata. Every other restriction is counted once and remembered for a few
        seconds, because the grid asks for the identical restriction again for every block it scrolls through.

        :param query: Restriction the events have to satisfy.
        :return: The amount of matching events.
        """
        if not query:
            return await self.estimated_count()

        fingerprint = _fingerprint(query=query)
        remembered = _recall(fingerprint=fingerprint)
        if remembered is not None:
            return int(remembered)

        total = await self.count(query=query)
        _remember(fingerprint=fingerprint, value=total)

        return total

    async def iterate(
        self,
        search: SearchQuery,
        batch_size: int,
        identifiers: list[str] | None = None,
        include_entities: bool = True,
    ) -> list[EventDocument]:
        """
        Read every event matching a query, used by the export endpoint that has to walk the whole result.

        :param search: Query requested by the client.
        :param batch_size: Largest amount of documents that is materialised at once.
        :param identifiers: Events the result is narrowed to, empty to keep every match of the query.
        :param include_entities: Whether the entities nested inside the events are read as well.
        :return: Every event matching the query.
        """
        query = self.build_query(search=search)
        if identifiers:
            query = merge_filters(query, {IDENTIFIER_FIELD: {"$in": identifiers}})
        sort = build_mongo_sort(specifications=search.sort, fixed_keys=FIXED_EVENT_KEYS) or DEFAULT_SORT

        return await self.find_many(
            query=query,
            sort=sort,
            limit=batch_size,
            projection=None if include_entities else WITHOUT_ENTITIES,
        )

    async def counts_by_industry(self) -> dict[str, int]:
        """
        Count the events of every industry, used to decorate the industry tabs and the industry overview.

        The industry keys are read out of the index rather than out of the documents, and each of them is then
        counted through the same index. Both steps are answered from index keys alone, so the whole round
        never reads a single event, where grouping over the collection had to read all of them.

        :return: The amount of events per industry key.
        """
        remembered = _recall(fingerprint=INDUSTRY_COUNTS_KEY)
        if remembered is not None:
            return dict(remembered)

        keys = [str(value) for value in await self.collection.distinct(INDUSTRY_FIELD) if isinstance(value, str)]
        totals = await asyncio.gather(*(self.count(query={INDUSTRY_FIELD: key}) for key in keys))
        counts = dict(zip(keys, totals))
        _remember(fingerprint=INDUSTRY_COUNTS_KEY, value=counts)

        return counts

    async def add_entity(self, event_id: str, entity: EntityDocument) -> bool:
        """
        Append one entity to the objects list of an event and refresh the counters of the event.

        :param event_id: Identifier of the event the entity is added to.
        :param entity: Entity that is appended.
        :return: Whether the event was found and changed.
        """
        result = await self.collection.update_one(
            {IDENTIFIER_FIELD: event_id},
            {
                "$push": {OBJECTS_FIELD: entity.model_dump()},
                "$inc": {f"entity_counts.{entity.object_type_key}": 1},
                "$set": {"updated_at": utc_now()},
            },
        )
        self._on_write()

        return bool(result.matched_count)

    async def update_entity(self, event_id: str, entity_id: str, updates: dict[str, Any]) -> bool:
        """
        Change a subset of the attributes of one entity nested inside an event.

        :param event_id: Identifier of the event the entity belongs to.
        :param entity_id: Identifier of the entity that is changed.
        :param updates: Attributes of the entity and their new values.
        :return: Whether the entity was found and changed.
        """
        if not updates:
            return False

        prefixed = {f"{OBJECTS_FIELD}.$[entity].{key}": value for key, value in updates.items()}
        prefixed["updated_at"] = utc_now()
        result = await self.collection.update_one(
            {IDENTIFIER_FIELD: event_id},
            {"$set": prefixed},
            array_filters=[{"entity.id": entity_id}],
        )
        self._on_write()

        return bool(result.matched_count)

    async def remove_entity(self, event_id: str, entity_id: str, entity_type_key: str) -> bool:
        """
        Remove one entity from the objects list of an event and refresh the counters of the event.

        :param event_id: Identifier of the event the entity belongs to.
        :param entity_id: Identifier of the entity that is removed.
        :param entity_type_key: Type key of the removed entity, needed to lower the right counter.
        :return: Whether the event was found and changed.
        """
        result = await self.collection.update_one(
            {IDENTIFIER_FIELD: event_id},
            {
                "$pull": {OBJECTS_FIELD: {"id": entity_id}},
                "$inc": {f"entity_counts.{entity_type_key}": -1},
                "$set": {"updated_at": utc_now()},
            },
        )
        self._on_write()

        return bool(result.matched_count)

    def _on_write(self) -> None:
        """
        Forget every remembered total, because a write may have moved any of them.
        """
        _TOTALS.clear()


# ----- FUNCTIONS ----- #


def _fingerprint(query: dict[str, Any]) -> str:
    """
    Turn a restriction into a stable text key the remembered totals can be looked up under.

    :param query: Restriction the events have to satisfy.
    :return: The key of the restriction, identical for two restrictions that ask the same question.
    """
    return json.dumps(query, sort_keys=True, default=repr)


def _recall(fingerprint: str) -> Any:
    """
    Read a remembered total, treating one that sat around for too long as absent.

    :param fingerprint: Key the total was remembered under.
    :return: The remembered value, or nothing when it was never taken or has expired.
    """
    remembered = _TOTALS.get(fingerprint)
    if remembered is None:
        return None

    taken_at, value = remembered
    if time.monotonic() - taken_at > TOTAL_CACHE_TTL_SECONDS:
        _TOTALS.pop(fingerprint, None)
        return None

    return value


def _remember(fingerprint: str, value: Any) -> None:
    """
    Remember one total, dropping the oldest entry once the memory reached its size.

    :param fingerprint: Key the total is remembered under.
    :param value: Value that is remembered.
    """
    _TOTALS[fingerprint] = (time.monotonic(), value)
    _TOTALS.move_to_end(fingerprint)
    while len(_TOTALS) > TOTAL_CACHE_ENTRIES:
        _TOTALS.popitem(last=False)


def _parse_state_clause(parse_state: ParseState) -> dict[str, Any]:
    """
    Translate the parsed and not parsed selector of the toolbar into a restriction on the nested entities.

    An event counts as parsed once it carries at least one entity and none of its entities is still waiting.
    The emptiness test matters: without it an event with no entities at all satisfies "no unparsed entity"
    and is reported as parsed, which is the opposite of the truth - nothing about it has been parsed yet.
    The two branches are exact complements of each other, so every event answers to one of them.

    
    :param parse_state: Selection made in the show selector of the toolbar.
    :return: The restriction, or an empty mapping when everything should be shown.
    """
    has_entities = {f"{OBJECTS_FIELD}.0": {"$exists": True}}
    no_entities = {f"{OBJECTS_FIELD}.0": {"$exists": False}}
    unparsed_match = {"$elemMatch": {"status": {"$nin": PARSED_STATUSES}}}
    holds_unparsed = {OBJECTS_FIELD: unparsed_match}
    holds_none_unparsed = {OBJECTS_FIELD: {"$not": unparsed_match}}

    if parse_state is ParseState.PARSED:
        return {"$and": [has_entities, holds_none_unparsed]}

    if parse_state is ParseState.NOT_PARSED:
        return {"$or": [no_entities, holds_unparsed]}

    return {}
