"""
Persistence of the edit history, which is written once per change and never updated afterwards.

:date: 2026-08-12
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel

from skyscanner_common.mongo import MongoProvider

from events_service.constants import REVISIONS_COLLECTION
from events_service.documents import RevisionDocument
from events_service.repositories.base_repository import BaseRepository

# ----- CLASSES ----- #


class RevisionRepository(BaseRepository[RevisionDocument]):
    """
    The single door to the revisions collection, which is an append only log of every recorded edit.
    """

    def __init__(self, provider: MongoProvider) -> None:
        """
        Bind the repository to the revisions collection.

        :param provider: Owner of the shared motor client.
        """
        super().__init__(provider=provider, collection_name=REVISIONS_COLLECTION, document_type=RevisionDocument)

    async def ensure_indexes(self) -> None:
        """
        Create the index the history of one event is read through.
        """
        await self.create_indexes(
            [
                IndexModel(
                    [("event_id", ASCENDING), ("entity_id", ASCENDING), ("version", DESCENDING)],
                    name="revision_history",
                ),
            ],
        )

    async def next_version(self, event_id: str, entity_id: str | None) -> int:
        """
        Work out the running number the next edit of one target takes.

        :param event_id: Identifier of the event the edit belongs to.
        :param entity_id: Identifier of the entity, empty when the event itself is edited.
        :return: The version the next recorded edit carries.
        """
        latest = await self.find_many(
            query={"event_id": event_id, "entity_id": entity_id},
            sort=[("version", DESCENDING)],
            limit=1,
        )

        return latest[0].version + 1 if latest else 1

    async def list_history(
        self,
        event_id: str,
        entity_id: str | None = None,
        include_entities: bool = False,
    ) -> list[RevisionDocument]:
        """
        Read the recorded edits of one event, of one of its entities, or of the event and everything in it.

        :param event_id: Identifier of the event the history is read for.
        :param entity_id: Identifier of one entity, empty for the event itself.
        :param include_entities: Whether the edits of the nested entities are read as well.
        :return: The matching edits, newest first.
        """
        query: dict[str, Any] = {"event_id": event_id}
        if entity_id is not None:
            query["entity_id"] = entity_id
        elif not include_entities:
            query["entity_id"] = None

        return await self.find_many(query=query, sort=[("changed_at", DESCENDING)])
