"""
The rules around the declared platforms an event may name, which are their own thing rather than a kind of type.

:date: 2026-09-08
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from skyscanner_common.errors import ConflictError, NotFoundError, ValidationError
from skyscanner_models.common import RenameResult, UserContext
from skyscanner_models.platform import PlatformCreateRequest, PlatformResponse, PlatformUpdateRequest

from events_service.documents import PlatformDocument
from events_service.repositories.platform_repository import PlatformRepository
from events_service.services.rename_service import RenameService

# ----- CLASSES ----- #


class PlatformService:
    """
    Owner of the declared platforms - the rigs, the aircraft and the benches the events of the system ran on.
    """

    def __init__(self, repository: PlatformRepository, renames: RenameService) -> None:
        """
        Bind the service to the platforms and to the rewriter that carries a renamed key through the store.

        :param repository: Persistence of the platforms.
        :param renames: Owner of the rewrites a changed key costs elsewhere.
        """
        self._repository = repository
        self._renames = renames

    async def list_platforms(
        self,
        industry: str | None = None,
        offset: int = 0,
        limit: int = 0,
    ) -> list[PlatformResponse]:
        """
        Read the platforms an industry may name on its events.

        :param industry: Industry whose own platforms are added to the shared ones.
        :param offset: Amount of platforms skipped before collecting.
        :param limit: Largest amount of platforms that is returned, zero for all of them.
        :return: The matching platforms.
        """
        documents = await self._repository.list_all(industry=industry, offset=offset, limit=limit)

        return [document.to_response() for document in documents]

    async def get_platform(self, key: str) -> PlatformResponse:
        """
        Read a single platform addressed by its machine key.

        :param key: Machine key of the platform.
        :return: The platform.
        :raises NotFoundError: When the key is unknown.
        """
        document = await self._require_key(key=key)

        return document.to_response()

    async def create_platform(self, request: PlatformCreateRequest) -> PlatformResponse:
        """
        Declare a new platform, refusing a key that is already taken.

        :param request: Platform supplied by the user.
        :return: The stored platform.
        :raises ConflictError: When a platform with the same key is already declared.
        """
        existing = await self._repository.find_by_key(key=request.key)
        if existing is not None:
            raise ConflictError(message="A platform with this key is already declared", details={"key": request.key})

        document = PlatformDocument(**request.model_dump())
        await self._repository.insert(document=document)

        return document.to_response()

    async def update_platform(self, platform_id: str, request: PlatformUpdateRequest) -> PlatformResponse:
        """
        Change a stored platform, carrying a changed key through every event that named it.

        :param platform_id: Identifier of the platform that is changed.
        :param request: Attributes the caller wants to change.
        :return: The changed platform.
        :raises NotFoundError: When the identifier is unknown.
        :raises ConflictError: When the new key is already taken by another platform.
        """
        document = await self._require_id(platform_id=platform_id)
        updates = request.model_dump(exclude_unset=True)
        moved = await self._move_key(document=document, updates=updates)

        await self._repository.update_fields(identifier=platform_id, updates=updates)
        refreshed = await self._require_id(platform_id=platform_id)
        _ = moved

        return refreshed.to_response()

    async def preview_rename(self, platform_id: str, key: str) -> RenameResult:
        """
        Say what renaming a platform would touch, without touching any of it.

        A key is stored by value on every event that ran on the platform, so changing one is a write across
        the store rather than an edit to a single document. Whoever is about to do that is shown the size of
        it first, which is the difference between an informed change and a surprise.

        :param platform_id: Identifier of the platform that would be renamed.
        :param key: Key it would be renamed to.
        :return: How many documents of each collection carry the current key.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._require_id(platform_id=platform_id)
        affected = await self._renames.rename_platform(old=document.key, new=key, apply=False)

        return RenameResult(key=key, previous_key=document.key, affected=affected)

    async def delete_platform(self, platform_id: str, user: UserContext) -> None:
        """
        Remove a declared platform, which hides it from the selectors without touching the events naming it.

        :param platform_id: Identifier of the platform that is removed.
        :param user: Identity the removal is attributed to.
        :raises NotFoundError: When the identifier is unknown.
        """
        removed = await self._repository.delete(identifier=platform_id, user=user.username)
        if not removed:
            raise NotFoundError(message="The platform does not exist", details={"id": platform_id})

    async def _move_key(self, document: PlatformDocument, updates: dict[str, object]) -> dict[str, int]:
        """
        Carry a changed key through the store, or do nothing when the key is not what changed.

        :param document: The platform as it stands before the change.
        :param updates: Attributes the caller wants to change, from which a key of no change is dropped.
        :return: How many documents of each collection were rewritten.
        :raises ConflictError: When the new key is already taken.
        :raises ValidationError: When the new key is empty.
        """
        key = updates.get("key")
        if key is None or key == document.key:
            updates.pop("key", None)

            return {}

        if not isinstance(key, str) or not key.strip():
            raise ValidationError(message="A platform needs a key", details={"id": document.id})

        taken = await self._repository.find_by_key(key=key)
        if taken is not None and taken.id != document.id:
            raise ConflictError(message="A platform with this key is already declared", details={"key": key})

        return await self._renames.rename_platform(old=document.key, new=key)

    async def _require_id(self, platform_id: str) -> PlatformDocument:
        """
        Read a platform by its identifier, refusing one that is not declared.

        :param platform_id: Identifier of the platform.
        :return: The stored platform.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._repository.find_by_id(identifier=platform_id)
        if document is None:
            raise NotFoundError(message="The platform does not exist", details={"id": platform_id})

        return document

    async def _require_key(self, key: str) -> PlatformDocument:
        """
        Read a platform by its machine key, refusing one that is not declared.

        :param key: Machine key of the platform.
        :return: The stored platform.
        :raises NotFoundError: When the key is unknown.
        """
        document = await self._repository.find_by_key(key=key)
        if document is None:
            raise NotFoundError(message="The platform is not declared", details={"key": key})

        return document

    async def resolve_platforms(self, keys: list[str], industry: str) -> list[PlatformDocument]:
        """
        Resolve the platform keys chosen in the wizard, refusing one the industry may not name.

        The platforms are a declared vocabulary rather than free text, and each of them says which industries
        it belongs to, so an event can only ever name the ones its own industry was offered.

        :param keys: Machine keys the client sent.
        :param industry: Industry of the event the platforms are named on.
        :return: The stored declarations behind the keys.
        :raises NotFoundError: When one of the keys is not declared.
        :raises ValidationError: When a declared platform does not belong to the industry of the event.
        """
        resolved: list[PlatformDocument] = []
        for key in keys:
            document = await self._require_key(key=key)
            if document.industries and industry not in document.industries:
                raise ValidationError(
                    message="The platform is not declared for the industry of this event",
                    details={"platform": document.key, "industry": industry},
                )
            resolved.append(document)

        return resolved
