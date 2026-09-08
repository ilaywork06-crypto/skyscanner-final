"""
The collection of the schema revisions, which is where a declaration and its whole history are kept.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from pymongo import ASCENDING, DESCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider

from truth_service.constants import LATEST_FIELD, LINEAGE_FIELD, SCHEMAS_COLLECTION
from truth_service.documents import SchemaDocument
from truth_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class SchemaRepository(BaseRepository[SchemaDocument]):
    """
    Reads and writes of the declarations, revision by revision.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the schemas collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=SCHEMAS_COLLECTION, document_type=SchemaDocument)

    def indexes(self) -> list[IndexModel]:
        """
        Declare the indexes the declarations are read through.

        :return: The index definitions of the collection.
        """
        return [
            IndexModel([(LINEAGE_FIELD, ASCENDING), ("revision", DESCENDING)], name="lineage_revision"),
            IndexModel([(LATEST_FIELD, ASCENDING), ("name", ASCENDING)], name="latest_name"),
            IndexModel([(LATEST_FIELD, ASCENDING), ("created_at", DESCENDING)], name="latest_created"),
            IndexModel([("industries.id", ASCENDING)], name="industry_ids"),
            IndexModel([("deleted", ASCENDING)], name="deleted"),
        ]

    async def list_latest(self, offset: int, limit: int) -> list[SchemaDocument]:
        """
        Read one window of the declarations, each at the revision it currently stands at.

        :param offset: Amount of declarations skipped before collecting.
        :param limit: Largest amount of declarations that is returned, zero for all of them.
        :return: The current revision of each declaration in the window.
        """
        return await self.find_many(
            query={LATEST_FIELD: True},
            sort=[("created_at", ASCENDING), ("_id", ASCENDING)],
            skip=offset,
            limit=limit,
        )

    async def find_latest_of_lineage(self, lineage: str) -> SchemaDocument | None:
        """
        Read the current revision of one declaration.

        :param lineage: Identifier grouping every revision of the declaration.
        :return: The current revision, or nothing when the lineage is unknown.
        """
        return await self.find_one(query={LINEAGE_FIELD: lineage, LATEST_FIELD: True})

    async def find_latest_by_name(self, name: str) -> SchemaDocument | None:
        """
        Read the current revision of the declaration answering to one name.

        :param name: Name of the declaration.
        :return: The current revision, or nothing when no declaration answers to that name.
        """
        return await self.find_one(query={"name": name, LATEST_FIELD: True})

    async def find_latest_by_key(self, key: str) -> SchemaDocument | None:
        """
        Read the current revision of the declaration addressed by whichever key the caller had.

        A declaration is addressed three ways: by the identifier of one of its revisions, by the identifier
        of the lineage, and by its name. All three land on the revision it currently stands at.

        :param key: Identifier of a revision, identifier of the lineage, or name of the declaration.
        :return: The current revision, or nothing when none of the three addresses one.
        """
        latest = await self.find_one(query={"$or": [{LINEAGE_FIELD: key}, {"name": key}], LATEST_FIELD: True})
        if latest is not None:
            return latest

        revision = await self.find_by_id(key)
        if revision is None:
            return None

        return await self.find_latest_of_lineage(revision.lineage)

    async def find_revisions(self, lineage: str) -> list[SchemaDocument]:
        """
        Read every revision of one declaration, newest first.

        :param lineage: Identifier grouping every revision of the declaration.
        :return: The revisions of that declaration.
        """
        return await self.find_many(query={LINEAGE_FIELD: lineage}, sort=[("revision", DESCENDING)])

    async def unmark_latest(self, lineage: str) -> int:
        """
        Take the current marker off every revision of one declaration, before a new one is written.

        :param lineage: Identifier grouping every revision of the declaration.
        :return: How many revisions stopped being the current one.
        """
        return await self.update_many_fields(query={LINEAGE_FIELD: lineage}, updates={LATEST_FIELD: False})
