"""
The collection of the assumptions, which is the one collection of this register expected to grow without end.

Every index declared here exists to answer one shape of question the table actually asks, and the two unusual
ones are the whole reason a register of a hundred thousand assumptions reads as quickly as a register of
thirty:

The text index over the folded blob answers a free text search as a lookup. Without it a search is a pass
over every assumption, and the pass gets longer every day the register is used.

The wildcard index over the values answers a restriction on an attribute no index could have been declared
for, because the attributes come from the schemas and the schemas are written by the people using the
register. It is the one index that does not have to be revised when a declaration is.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from typing import Any

from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel

from skyscanner_common.mongo import MongoProvider

from truth_service.constants import ASSUMPTIONS_COLLECTION, LATEST_FIELD, LINEAGE_FIELD, SEARCH_FIELD
from truth_service.documents import AssumptionDocument
from truth_service.repositories.base_repository import BaseRepository, alive

# ----- CONSTS ----- #

# How many documents a vocabulary is gathered out of before the answer says it was cut short.
FACET_SCAN_LIMIT: int = 100_000

# ----- CLASSES ----- #


class AssumptionRepository(BaseRepository[AssumptionDocument]):
    """
    Reads and writes of the assumptions, revision by revision.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the assumptions collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(
            provider=provider,
            collection_name=ASSUMPTIONS_COLLECTION,
            document_type=AssumptionDocument,
        )

    def indexes(self) -> list[IndexModel]:
        """
        Declare every index the register is read through.

        Every one of these is written to answer a restriction and an ordering at once, and each ends with
        the identifier. The table always asks for a window of an ordering rather than for a set, and an
        index that answers the restriction but stops short of the ordering leaves the whole match to be
        sorted in memory - which for this register meant reading a hundred thousand documents to draw
        twenty five rows. The identifier is on the end because the ordering carries it as a tiebreaker, and
        an index missing the last field of a sort serves none of it.

        :return: The index definitions of the collection.
        """
        return [
            IndexModel(
                [("deleted", ASCENDING), (LATEST_FIELD, ASCENDING), ("created_at", DESCENDING), ("_id", ASCENDING)],
                name="latest_created",
            ),
            IndexModel(
                [("deleted", ASCENDING), (LATEST_FIELD, ASCENDING), ("name", ASCENDING), ("_id", ASCENDING)],
                name="latest_name",
            ),
            IndexModel(
                [("deleted", ASCENDING), (LATEST_FIELD, ASCENDING), ("creator", ASCENDING), ("_id", ASCENDING)],
                name="latest_creator",
            ),
            IndexModel(
                [
                    ("deleted", ASCENDING),
                    (LATEST_FIELD, ASCENDING),
                    ("proposing_party", ASCENDING),
                    ("_id", ASCENDING),
                ],
                name="latest_party",
            ),
            IndexModel(
                [("deleted", ASCENDING), (LATEST_FIELD, ASCENDING), ("tags", ASCENDING), ("_id", ASCENDING)],
                name="latest_tags",
            ),
            IndexModel(
                [
                    ("deleted", ASCENDING),
                    (LATEST_FIELD, ASCENDING),
                    ("industries.id", ASCENDING),
                    ("created_at", DESCENDING),
                    ("_id", ASCENDING),
                ],
                name="latest_industry_created",
            ),
            IndexModel(
                [
                    ("deleted", ASCENDING),
                    (LATEST_FIELD, ASCENDING),
                    ("industries.name", ASCENDING),
                    ("created_at", DESCENDING),
                    ("_id", ASCENDING),
                ],
                name="latest_industry_name_created",
            ),
            IndexModel(
                [
                    ("deleted", ASCENDING),
                    (LATEST_FIELD, ASCENDING),
                    ("schemas.id", ASCENDING),
                    ("created_at", DESCENDING),
                    ("_id", ASCENDING),
                ],
                name="latest_schema_created",
            ),
            IndexModel([(LINEAGE_FIELD, ASCENDING), ("revision", DESCENDING)], name="lineage_revision"),
            IndexModel([(SEARCH_FIELD, TEXT)], name="search_text"),
            # One declaration of this covers every attribute any schema will ever declare, including the ones
            # declared after it was created. A named index per attribute could not, because nothing knows the
            # names until somebody writes a schema.
            IndexModel([("values.$**", ASCENDING)], name="values_wildcard"),
            IndexModel([("deleted", ASCENDING)], name="deleted"),
        ]

    async def query_page(
        self,
        query: dict[str, Any],
        sort: list[tuple[str, int]],
        offset: int,
        limit: int,
    ) -> list[AssumptionDocument]:
        """
        Read one window of the assumptions matching a restriction.

        :param query: Restriction the assumptions have to satisfy.
        :param sort: Ordering applied before the window is taken.
        :param offset: Amount of assumptions skipped before collecting.
        :param limit: Largest amount of assumptions that is returned.
        :return: The assumptions of the window.
        """
        return await self.find_many(query=query, sort=sort, skip=offset, limit=limit)

    async def find_latest_of_lineage(self, lineage: str) -> AssumptionDocument | None:
        """
        Read the current revision of one assumption.

        :param lineage: Identifier grouping every revision of the assumption.
        :return: The current revision, or nothing when the lineage is unknown.
        """
        return await self.find_one(query={LINEAGE_FIELD: lineage, LATEST_FIELD: True})

    async def find_latest_by_key(self, key: str) -> AssumptionDocument | None:
        """
        Read the current revision of the assumption addressed by whichever key the caller had.

        :param key: Identifier of a revision or identifier of the lineage.
        :return: The current revision, or nothing when neither addresses one.
        """
        latest = await self.find_latest_of_lineage(key)
        if latest is not None:
            return latest

        revision = await self.find_by_id(key)
        if revision is None:
            return None

        return await self.find_latest_of_lineage(revision.lineage)

    async def facet(self, field: str, query: dict[str, Any], limit: int) -> tuple[list[str], bool]:
        """
        Gather every value one attribute is known to hold among the assumptions matching a restriction.

        An attribute holding a list is gathered one entry at a time rather than as the list it is, so that a
        filter over the industries of an assumption offers each industry rather than each combination of
        them. The gathering is bounded twice over - by how many assumptions it reads and by how many values
        it keeps - because a filter offering a hundred thousand choices helps nobody and costs everybody.

        :param field: Path of the attribute the vocabulary is gathered for.
        :param query: Restriction the assumptions have to satisfy.
        :param limit: Largest amount of values that is returned.
        :return: The values the attribute holds, and whether more were left ungathered.
        """
        pipeline: list[dict[str, Any]] = [
            {"$match": alive(query)},
            {"$limit": FACET_SCAN_LIMIT},
            {"$project": {"value": f"${field}"}},
            {"$unwind": {"path": "$value", "preserveNullAndEmptyArrays": False}},
            {"$group": {"_id": "$value"}},
            {"$limit": limit + 1},
        ]

        gathered: list[str] = []
        async for entry in self.collection.aggregate(pipeline):
            value = entry.get("_id")
            if value is None or value == "":
                continue
            gathered.append(str(value))

        truncated = len(gathered) > limit

        return sorted(gathered[:limit], key=str.casefold), truncated

    async def unmark_latest(self, lineage: str) -> int:
        """
        Take the current marker off every revision of one assumption, before a new one is written.

        :param lineage: Identifier grouping every revision of the assumption.
        :return: How many revisions stopped being the current one.
        """
        return await self.update_many_fields(query={LINEAGE_FIELD: lineage}, updates={LATEST_FIELD: False})
