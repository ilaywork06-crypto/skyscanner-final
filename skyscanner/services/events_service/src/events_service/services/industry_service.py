"""
The rules around the industries, which drive the tabs above the table and decide which part of the schema is shown.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from skyscanner_common.errors import ConflictError, NotFoundError
from skyscanner_models.industry import IndustryCreateRequest, IndustryResponse, IndustryUpdateRequest

from events_service.documents import IndustryDocument
from events_service.repositories.event_repository import EventRepository
from events_service.repositories.industry_repository import IndustryRepository

# ----- CLASSES ----- #


class IndustryService:
    """
    Owner of the industries, pairing every industry with the amount of events currently linked to it.
    """

    def __init__(self, repository: IndustryRepository, event_repository: EventRepository) -> None:
        """
        Bind the service to the repositories it reads the industries and their event counts from.

        :param repository: Persistence of the industries.
        :param event_repository: Persistence of the events, used for the counters of the tabs.
        """
        self._repository = repository
        self._event_repository = event_repository

    async def list_industries(self, offset: int = 0, limit: int = 0) -> list[IndustryResponse]:
        """
        Read every registered industry together with the amount of events it holds.

        :param offset: Amount of industries skipped before collecting.
        :param limit: Largest amount of industries that is returned, zero for all of them.
        :return: Every registered industry inside the requested window.
        """
        documents = await self._repository.list_all(offset=offset, limit=limit)
        counts = await self._event_repository.counts_by_industry()

        return [document.to_response(event_count=counts.get(document.key, 0)) for document in documents]

    async def get_industry(self, key: str) -> IndustryResponse:
        """
        Read a single industry addressed by its machine key.

        :param key: Machine key of the industry.
        :return: The industry together with the amount of events it holds.
        :raises NotFoundError: When the key is unknown.
        """
        document = await self._repository.find_by_key(key=key)
        if document is None:
            raise NotFoundError(message="The industry does not exist", details={"key": key})

        counts = await self._event_repository.counts_by_industry()

        return document.to_response(event_count=counts.get(key, 0))

    async def create_industry(self, request: IndustryCreateRequest) -> IndustryResponse:
        """
        Register a new industry, refusing a key that is already taken.

        :param request: Industry supplied by the user.
        :return: The stored industry.
        :raises ConflictError: When the key is already registered.
        """
        existing = await self._repository.find_by_key(key=request.key)
        if existing is not None:
            raise ConflictError(message="An industry with this key already exists", details={"key": request.key})

        document = IndustryDocument(**request.model_dump())
        await self._repository.insert(document=document)

        return document.to_response(event_count=0)

    async def update_industry(self, key: str, request: IndustryUpdateRequest) -> IndustryResponse:
        """
        Change a registered industry, which is how the vocabulary of the entity modules is maintained.

        :param key: Machine key of the industry that is changed.
        :param request: Attributes the caller wants to change.
        :return: The changed industry.
        :raises NotFoundError: When the key is unknown.
        """
        document = await self._repository.find_by_key(key=key)
        if document is None:
            raise NotFoundError(message="The industry does not exist", details={"key": key})

        updates = request.model_dump(exclude_unset=True, exclude_none=True)
        if updates:
            await self._repository.update_fields(identifier=document.id, updates=updates)

        return await self.get_industry(key=key)

    async def allowed_modules(self, key: str) -> list[str]:
        """
        Read the vocabulary an entity of one industry may name as its module.

        :param key: Machine key of the industry.
        :return: The declared modules, empty when the industry accepts any text.
        """
        document = await self._repository.find_by_key(key=key)

        return [] if document is None else list(document.modules)
