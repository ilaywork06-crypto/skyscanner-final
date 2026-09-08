"""
The one time rewrites that carry documents written by an earlier deployment onto the shape the service reads.

:date: 2026-08-24
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.logging_utils import get_logger
from skyscanner_common.mongo import MongoProvider
from skyscanner_models.enums import OptionalEventField

from events_service.constants import (
    EVENTS_COLLECTION,
    PLATFORMS_COLLECTION,
    EVENT_TYPE_KIND,
    INDUSTRIES_COLLECTION,
    PLATFORM_TYPE_KIND,
    TYPES_COLLECTION,
)

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)

# What an event type declared before the built in fields were switchable asked for. Everything except the
# experiment result, because that one is the reason the switch exists: it only means something on a type that
# describes an experiment, and every type used to show it.
LEGACY_TYPE_FIELDS: list[str] = [
    OptionalEventField.EVENT_DATE.value,
    OptionalEventField.NOTES.value,
]

# ----- FUNCTIONS ----- #


async def migrate_documents(provider: MongoProvider) -> None:
    """
    Rewrite the stored documents that an earlier vocabulary of the service left behind.

    Every step is written so that running it twice changes nothing the second time, because it runs on every
    start rather than being remembered somewhere: a document already carrying the new shape matches none of
    the restrictions below.

    :param provider: Owner of the shared motor client.
    """
    await _rename_entity_origins(provider=provider)
    await _widen_platforms(provider=provider)
    await _widen_declaration_industries(provider=provider)
    await _move_platforms_out_of_the_types(provider=provider)


async def _rename_entity_origins(provider: MongoProvider) -> None:
    """
    Carry the origin of every entity, and the vocabulary behind it, onto the name module.

    :param provider: Owner of the shared motor client.
    """
    events = provider.collection(EVENTS_COLLECTION)
    renamed = await events.update_many(
        {"objects.origin": {"$exists": True}},
        [
            {
                "$set": {
                    "objects": {
                        "$map": {
                            "input": "$objects",
                            "as": "entity",
                            "in": {
                                "$mergeObjects": [
                                    {
                                        "$arrayToObject": {
                                            "$filter": {
                                                "input": {"$objectToArray": "$$entity"},
                                                "as": "pair",
                                                "cond": {"$ne": ["$$pair.k", "origin"]},
                                            },
                                        },
                                    },
                                    {"module": "$$entity.origin"},
                                ],
                            },
                        },
                    },
                },
            },
        ],
    )

    industries = provider.collection(INDUSTRIES_COLLECTION)
    vocabularies = await industries.update_many(
        {"entity_origins": {"$exists": True}},
        {"$rename": {"entity_origins": "modules"}},
    )

    if renamed.modified_count or vocabularies.modified_count:
        LOGGER.info(
            "Renamed the origin of %s events and the vocabulary of %s industries to module",
            renamed.modified_count,
            vocabularies.modified_count,
        )


async def _widen_platforms(provider: MongoProvider) -> None:
    """
    Turn the single platform of every event into the list of platforms it may now name.

    The platform used to be free text, so the text that was typed is declared as a platform of its own before
    the events start pointing at it - otherwise every stored event would name a platform nothing declares.

    :param provider: Owner of the shared motor client.
    """
    events = provider.collection(EVENTS_COLLECTION)
    stored = await events.distinct("platform", {"platform": {"$nin": [None, ""]}})
    names = sorted({str(value) for value in stored if isinstance(value, str) and value})

    types = provider.collection(TYPES_COLLECTION)
    for name in names:
        industries = await events.distinct("industry", {"platform": name})
        await types.update_one(
            {"kind": PLATFORM_TYPE_KIND, "key": name},
            {
                "$setOnInsert": {
                    "_id": f"platform-{name}",
                    "name": name,
                    "description": "Declared from the platforms the stored events already named",
                    "icon": None,
                    "industries": sorted({str(value) for value in industries if isinstance(value, str)}),
                    "fields": [],
                    "order": 100,
                    "deleted": False,
                    "created_at": utc_now(),
                },
            },
            upsert=True,
        )

    result = await events.update_many(
        {"platform": {"$exists": True}},
        [
            {"$set": {"platforms": {"$cond": [{"$in": ["$platform", [None, ""]]}, [], ["$platform"]]}}},
            {"$unset": "platform"},
        ],
    )
    if result.modified_count:
        LOGGER.info(
            "Carried %s events onto a list of platforms and declared %s of them",
            result.modified_count,
            len(names),
        )


async def _move_platforms_out_of_the_types(provider: MongoProvider) -> None:
    """
    Carry every declared platform out of the types collection and into one of its own.

    A platform was filed with the types because it is written down like one - a key, a label and the
    industries it belongs to. What a thing is written like is not what it is: a platform is a piece of
    equipment an event ran on rather than a shape an event takes, and filing it with the types is what buried
    it two levels inside a page about something else. It has its own collection and its own page now.

    The declarations are copied rather than moved, and the ones left behind are marked as removed. A copy
    that fails halfway therefore leaves a store where the platforms are still readable at their old address
    rather than one where they are readable at neither, and running this a second time changes nothing.

    :param provider: Owner of the shared motor client.
    """
    types = provider.collection(TYPES_COLLECTION)
    platforms = provider.collection(PLATFORMS_COLLECTION)
    carried = 0

    async for stored in types.find({"kind": PLATFORM_TYPE_KIND, "deleted": {"$ne": True}}):
        await platforms.update_one(
            {"_id": stored["_id"]},
            {
                "$setOnInsert": {
                    "key": stored.get("key", ""),
                    "name": stored.get("name", ""),
                    "description": stored.get("description", ""),
                    "industries": list(stored.get("industries", [])),
                    "order": int(stored.get("order", 100)),
                    "deleted": False,
                    "created_at": stored.get("created_at", utc_now()),
                },
            },
            upsert=True,
        )
        carried += 1

    if carried:
        # The originals stay in the store, marked as removed like everything else that is taken out of use,
        # so a deployment that has to go back to the previous version finds its platforms where it left them.
        await types.update_many(
            {"kind": PLATFORM_TYPE_KIND, "deleted": {"$ne": True}},
            {"$set": {"deleted": True, "deleted_at": utc_now(), "deleted_by": "migration"}},
        )
        LOGGER.info("Carried %d platforms out of the types and into their own collection", carried)


async def _widen_declaration_industries(provider: MongoProvider) -> None:
    """
    Turn the single industry of every declared type into the list of industries it may now belong to.

    :param provider: Owner of the shared motor client.
    """
    types = provider.collection(TYPES_COLLECTION)
    result = await types.update_many(
        {"industry": {"$exists": True}},
        [
            {"$set": {"industries": {"$cond": [{"$eq": ["$industry", None]}, [], ["$industry"]]}}},
            {"$unset": "industry"},
        ],
    )

    # An event type declared before its built in fields were switchable showed all of them but the experiment
    # result, so that is what those types keep asking for.
    filled = await types.update_many(
        {"kind": EVENT_TYPE_KIND, "fields": {"$exists": False}},
        {"$set": {"fields": LEGACY_TYPE_FIELDS}},
    )

    if result.modified_count or filled.modified_count:
        LOGGER.info(
            "Carried %s declarations onto a list of industries and filled the fields of %s event types",
            result.modified_count,
            filled.modified_count,
        )
