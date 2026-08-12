"""
Discovery of the shape of the stored documents, so that values written by a script still reach the table as columns.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection

from skyscanner_models.enums import FieldScope, FieldType
from skyscanner_models.field import FieldMetadata, FieldResponse

from ag_grid_lib.datasource import DYNAMIC_VALUE_ROOT

# ----- CONSTS ----- #

DEFAULT_SAMPLE_SIZE: int = 500
DEFAULT_DISTINCT_LIMIT: int = 50
DISCOVERED_ORDER: int = 900

# A random sample of a whole collection is cheap: the document store seeks straight at the documents it drew,
# as long as the sample stays below a twentieth of the collection. A random sample of a restricted collection
# is not cheap at all, because the restriction has to be answered in full before anything can be drawn out of
# it - on a large inventory that means reading every document of an industry in order to look at five hundred
# of them. The restricted case therefore takes a bounded window instead of a sample, so that the discovery
# costs the same whether the industry holds a thousand events or a million.
DEFAULT_SCAN_LIMIT: int = 500

# The same reasoning bounds the window the ready made filter options are counted over.
DEFAULT_DISTINCT_SCAN_LIMIT: int = 20_000

BSON_TYPE_MAPPING: dict[str, FieldType] = {
    "string": FieldType.STRING,
    "int": FieldType.INTEGER,
    "long": FieldType.INTEGER,
    "double": FieldType.NUMBER,
    "decimal": FieldType.NUMBER,
    "bool": FieldType.BOOLEAN,
    "date": FieldType.DATETIME,
    "object": FieldType.JSON,
    "array": FieldType.JSON,
}

# ----- CLASSES ----- #


class SchemaIntrospector:
    """
    Reader of the effective schema of a collection, pairing the declared fields with the keys found in the documents.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection[dict[str, Any]],
        sample_size: int = DEFAULT_SAMPLE_SIZE,
        scan_limit: int = DEFAULT_SCAN_LIMIT,
        distinct_scan_limit: int = DEFAULT_DISTINCT_SCAN_LIMIT,
    ):
        """
        Keep the collection that is inspected and how many documents one run may look at.

        :param collection: Collection whose documents are inspected.
        :param sample_size: Amount of documents a single unrestricted introspection run samples.
        :param scan_limit: Amount of documents a single restricted introspection run reads.
        :param distinct_scan_limit: Amount of documents the ready made filter options are counted over.
        """
        self._collection = collection
        self._sample_size = sample_size
        self._scan_limit = scan_limit
        self._distinct_scan_limit = distinct_scan_limit

    async def discover_dynamic_keys(self, scope_filter: dict[str, Any] | None = None) -> dict[str, FieldType]:
        """
        Collect the dynamic keys that appear in the inspected documents together with the type they hold.

        :param scope_filter: Restriction limiting the inspected documents, for example to a single industry.
        :return: The discovered keys mapped to the primitive type they were seen with.
        """
        pipeline: list[dict[str, Any]] = _sampling_stages(
            scope_filter=scope_filter,
            sample_size=self._sample_size,
            scan_limit=self._scan_limit,
        )
        pipeline.extend(
            [
                {"$project": {"pairs": {"$objectToArray": {"$ifNull": [f"${DYNAMIC_VALUE_ROOT}", {}]}}}},
                {"$unwind": "$pairs"},
                {"$group": {"_id": "$pairs.k", "types": {"$addToSet": {"$type": "$pairs.v"}}}},
                {"$sort": {"_id": 1}},
            ],
        )

        discovered: dict[str, FieldType] = {}
        async for document in self._collection.aggregate(pipeline):
            key = str(document["_id"])
            types = [str(candidate) for candidate in document.get("types", [])]
            discovered[key] = _pick_field_type(types)

        return discovered

    async def infer_missing_fields(
        self,
        declared_keys: set[str],
        scope: FieldScope,
        industry: str | None = None,
        scope_filter: dict[str, Any] | None = None,
    ) -> list[FieldResponse]:
        """
        Build read only field definitions for the dynamic keys that no industry declared explicitly.

        :param declared_keys: Keys that already have a stored field definition.
        :param scope: Whether the inspected documents are events or entities.
        :param industry: Industry the inferred definitions are attributed to.
        :param scope_filter: Restriction limiting the sample, for example to a single industry.
        :return: The inferred field definitions, ordered behind every declared field.
        """
        discovered = await self.discover_dynamic_keys(scope_filter=scope_filter)
        inferred: list[FieldResponse] = []
        for index, (key, field_type) in enumerate(sorted(discovered.items())):
            if key in declared_keys:
                continue
            inferred.append(
                FieldResponse(
                    id=f"discovered:{key}",
                    name=key.replace("_", " ").title(),
                    key=key,
                    type=field_type,
                    array=False,
                    default=None,
                    required=False,
                    scope=scope,
                    industry=industry,
                    entity_type=None,
                    metadata=FieldMetadata(description="Discovered from the stored documents"),
                    constraints=[],
                    filterable=True,
                    sortable=True,
                    editable=False,
                    visible=False,
                    order=DISCOVERED_ORDER + index,
                    created_at=datetime.now(tz=timezone.utc),
                    updated_at=None,
                    created_by=None,
                ),
            )

        return inferred

    async def distinct_values(self, path: str, limit: int = DEFAULT_DISTINCT_LIMIT) -> list[str]:
        """
        Collect the values a single path currently holds, used to offer ready made filter options.

        Grouping over the whole collection would read every document for every dropdown the user opens, which
        is work that grows with the inventory rather than with the amount of options shown. The values are
        therefore counted over a bounded window of the matching documents: a value that is common enough to be
        worth offering as a ready made option appears inside it, and a value that appears nowhere in twenty
        thousand documents is one the user types by hand anyway.

        :param path: Document path the values are read from.
        :param limit: Largest amount of values that is returned.
        :return: The distinct values of the path as text, ordered by how often they appear in the window.
        """
        pipeline: list[dict[str, Any]] = [
            {"$match": {path: {"$nin": [None, ""]}}},
            {"$limit": self._distinct_scan_limit},
            {"$group": {"_id": f"${path}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
            {"$limit": limit},
        ]

        values: list[str] = []
        async for document in self._collection.aggregate(pipeline):
            values.append(str(document["_id"]))

        return values


# ----- FUNCTIONS ----- #


def _sampling_stages(
    scope_filter: dict[str, Any] | None,
    sample_size: int,
    scan_limit: int,
) -> list[dict[str, Any]]:
    """
    Build the leading stages that pick the documents one introspection run is allowed to look at.

    :param scope_filter: Restriction limiting the inspected documents, for example to a single industry.
    :param sample_size: Amount of documents an unrestricted run samples out of the whole collection.
    :param scan_limit: Amount of documents a restricted run reads out of the matching ones.
    :return: The stages the rest of the pipeline is appended to.
    """
    if not scope_filter:
        return [{"$sample": {"size": sample_size}}]

    return [{"$match": scope_filter}, {"$limit": scan_limit}]


def _pick_field_type(bson_types: list[str]) -> FieldType:
    """
    Pick the primitive type that describes a set of observed document types best.

    :param bson_types: Type names the document store reported for one key.
    :return: The primitive type the generated column is built with.
    """
    mapped = {BSON_TYPE_MAPPING[name] for name in bson_types if name in BSON_TYPE_MAPPING}
    if not mapped:
        return FieldType.STRING

    if len(mapped) == 1:
        return mapped.pop()

    if mapped <= {FieldType.INTEGER, FieldType.NUMBER}:
        return FieldType.NUMBER

    return FieldType.STRING
