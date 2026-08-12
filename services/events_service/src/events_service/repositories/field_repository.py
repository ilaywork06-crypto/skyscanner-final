"""
Persistence of the dynamic field declarations that give every industry its own schema for events and entities.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from pymongo import ASCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider
from skyscanner_models.enums import FieldScope

from events_service.constants import FIELDS_COLLECTION
from events_service.documents import FieldDocument
from events_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class FieldRepository(BaseRepository[FieldDocument]):
    """
    The single door to the field declarations, offering the lookups the schema and the grid generation need.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the fields collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=FIELDS_COLLECTION, document_type=FieldDocument)

    async def ensure_indexes(self) -> None:
        """
        Create the indexes that keep a field key unique inside the scope and the industry that declared it.
        """
        await self.create_indexes(
            [
                IndexModel(
                    [("scope", ASCENDING), ("industry", ASCENDING), ("entity_type", ASCENDING), ("key", ASCENDING)],
                    unique=True,
                    name="field_key_unique",
                ),
                IndexModel([("industry", ASCENDING)], name="industry"),
            ],
        )

    async def list_for_scope(
        self,
        scope: FieldScope,
        industry: str | None = None,
        entity_type: str | None = None,
        include_shared: bool = True,
        offset: int = 0,
        limit: int = 0,
    ) -> list[FieldDocument]:
        """
        Read the declarations that apply to a scope, optionally narrowed to one industry and one entity type.

        :param scope: Whether the declarations target events or entities.
        :param industry: Industry whose own declarations are added to the shared ones.
        :param entity_type: Entity type the declarations are limited to.
        :param include_shared: Whether the declarations that belong to no industry are included.
        :param offset: Amount of declarations skipped before collecting.
        :param limit: Largest amount of declarations that is returned, zero for all of them.
        :return: The matching declarations ordered by their relative position.
        """
        industry_clauses: list[dict[str, Any]] = []
        if include_shared:
            industry_clauses.append({"industry": None})
        if industry:
            industry_clauses.append({"industry": industry})

        query: dict[str, Any] = {"scope": scope.value}
        if industry_clauses:
            query["$or"] = industry_clauses
        if entity_type:
            query["$and"] = [{"$or": [{"entity_type": None}, {"entity_type": entity_type}]}]

        return await self.find_many(
            query=query,
            sort=[("order", ASCENDING), ("name", ASCENDING)],
            skip=offset,
            limit=limit,
        )

    async def find_by_key(
        self,
        scope: FieldScope,
        key: str,
        industry: str | None = None,
        entity_type: str | None = None,
    ) -> FieldDocument | None:
        """
        Read a single declaration addressed by the scope, the industry, the entity type and the key.

        :param scope: Whether the declaration targets events or entities.
        :param key: Machine key of the declaration.
        :param industry: Industry that owns the declaration.
        :param entity_type: Entity type the declaration is limited to.
        :return: The declaration, or nothing when the combination is unknown.
        """
        return await self.find_one(
            query={"scope": scope.value, "key": key, "industry": industry, "entity_type": entity_type},
        )

    async def list_industries_with_fields(self) -> list[str]:
        """
        Read the industries that declared at least one field of their own.

        :return: The industry keys that own a declaration.
        """
        values = await self.collection.distinct("industry", {"industry": {"$ne": None}})

        return [str(value) for value in values]
