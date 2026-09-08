"""
The industries, which are the vocabulary the register is filed under and the top of its navigation.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from skyscanner_common.errors import ConflictError, NotFoundError

from truth_service.constants import ASSUMPTIONS_COLLECTION
from truth_service.documents import IndustryDocument
from truth_service.models.industry import IndustryCreateRequest, IndustryResponse
from truth_service.repositories.industry_repository import IndustryRepository

# ----- CLASSES ----- #


class IndustryService:
    """
    Everything the register does with its industries.
    """

    def __init__(self, industries: IndustryRepository) -> None:
        """
        Bind the service to the collection of the industries.

        :param industries: Reads and writes of the industries.
        """
        self._industries = industries

    async def list_industries(self, offset: int, limit: int, with_counts: bool = False) -> list[IndustryResponse]:
        """
        Read one window of the industries.

        The counts are gathered in one pass over the register rather than one count per industry, and only
        when they were asked for - most readers of this listing want a name to put on a chip.

        :param offset: Amount of industries skipped before collecting.
        :param limit: Largest amount of industries that is returned, zero for all of them.
        :param with_counts: Whether each industry is answered with how many assumptions name it.
        :return: The industries of the window.
        """
        documents = await self._industries.list_window(offset=offset, limit=limit)
        counts = (
            await self._industries.counts_by_industry(collection_name=ASSUMPTIONS_COLLECTION) if with_counts else {}
        )

        return [
            to_response(document=document, count=counts.get(document.id, 0) if with_counts else None)
            for document in documents
        ]

    async def get_industry(self, key: str) -> IndustryResponse:
        """
        Read one industry addressed by its identifier or by its name.

        :param key: Identifier or name of the industry.
        :return: The industry.
        :raises NotFoundError: When neither addresses an industry.
        """
        document = await self._industries.find_by_key(key)
        if document is None:
            raise NotFoundError(message="No industry answers to that name or identifier", details={"key": key})

        return to_response(document=document, count=None)

    async def get_industry_by_name(self, name: str) -> IndustryResponse:
        """
        Read one industry addressed by its name alone.

        :param name: Name of the industry.
        :return: The industry.
        :raises NotFoundError: When no industry answers to that name.
        """
        document = await self._industries.find_by_name(name)
        if document is None:
            raise NotFoundError(message="No industry answers to that name", details={"name": name})

        return to_response(document=document, count=None)

    async def create_industry(self, request: IndustryCreateRequest) -> IndustryResponse:
        """
        Register a new industry.

        :param request: Industry as the caller described it.
        :return: The industry as it was stored.
        :raises ConflictError: When an industry of that name is already registered.
        """
        name = request.name.strip()
        if await self._industries.find_by_name(name) is not None:
            raise ConflictError(message="An industry of that name is already registered", details={"name": name})

        document = IndustryDocument(name=name, description=request.description, creator=request.creator)

        return to_response(document=await self._industries.insert(document), count=None)


# ----- FUNCTIONS ----- #


def to_response(document: IndustryDocument, count: int | None) -> IndustryResponse:
    """
    Shape one stored industry into the payload every endpoint answers with.

    :param document: Industry as it is stored.
    :param count: How many assumptions name it, or nothing when that was not asked for.
    :return: The industry as the API hands it over.
    """
    return IndustryResponse(
        id=document.id,
        name=document.name,
        description=document.description,
        creator=document.creator,
        created_at=document.created_at,
        assumption_count=count,
    )
