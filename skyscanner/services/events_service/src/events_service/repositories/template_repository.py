"""
Persistence of the saved table templates, which every user keeps for themselves or shares with the whole industry.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from pymongo import ASCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider
from skyscanner_models.enums import FieldScope

from events_service.constants import TEMPLATES_COLLECTION
from events_service.documents import TemplateDocument
from events_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class TemplateRepository(BaseRepository[TemplateDocument]):
    """
    The single door to the templates collection.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the templates collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=TEMPLATES_COLLECTION, document_type=TemplateDocument)

    async def ensure_indexes(self) -> None:
        """
        Create the index that keeps a template name unique per owner and scope.
        """
        await super().ensure_indexes()
        await self.create_indexes(
            [
                IndexModel(
                    [("owner", ASCENDING), ("scope", ASCENDING), ("name", ASCENDING)],
                    unique=True,
                    name="template_name_unique",
                ),
            ],
        )

    async def list_visible(
        self,
        owner: str,
        scope: FieldScope,
        industry: str | None = None,
        offset: int = 0,
        limit: int = 0,
    ) -> list[TemplateDocument]:
        """
        Read the templates a user may load, which are their own ones and the shared ones of the scope.

        :param owner: User the templates are read for.
        :param scope: Whether the templates target events or entities.
        :param industry: Industry the templates are narrowed to, empty for the global view.
        :param offset: Amount of templates skipped before collecting.
        :param limit: Largest amount of templates that is returned, zero for all of them.
        :return: The matching templates ordered by their name.
        """
        query: dict[str, Any] = {
            "scope": scope.value,
            "$or": [{"owner": owner}, {"shared": True}],
        }
        if industry:
            query["$and"] = [{"$or": [{"industry": None}, {"industry": industry}]}]

        return await self.find_many(query=query, sort=[("name", ASCENDING)], skip=offset, limit=limit)
