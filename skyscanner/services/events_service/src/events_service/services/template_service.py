"""
The rules around the saved table templates, so that a user can restore the view they built for themselves.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Any

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.errors import ConflictError, NotFoundError, PermissionDeniedError
from skyscanner_models.common import UserContext
from skyscanner_models.enums import FieldScope
from skyscanner_models.template import TemplateCreateRequest, TemplateResponse, TemplateUpdateRequest

from events_service.documents import TemplateDocument
from events_service.repositories.template_repository import TemplateRepository

# ----- CLASSES ----- #


class TemplateService:
    """
    Owner of the saved table layouts, guarding that only the owner of a template may change it.
    """

    def __init__(self, repository: TemplateRepository) -> None:
        """
        Bind the service to the repository of the templates.

        :param repository: Persistence of the templates.
        """
        self._repository = repository

    async def list_templates(
        self,
        user: UserContext,
        scope: FieldScope = FieldScope.EVENT,
        industry: str | None = None,
        offset: int = 0,
        limit: int = 0,
    ) -> list[TemplateResponse]:
        """
        Read the templates the caller may load, which are their own ones and the shared ones.

        :param user: Identity the templates are read for.
        :param scope: Whether the templates target events or entities.
        :param industry: Industry the templates are narrowed to, empty for the global view.
        :param offset: Amount of templates skipped before collecting.
        :param limit: Largest amount of templates that is returned, zero for all of them.
        :return: The matching templates.
        """
        documents = await self._repository.list_visible(
            owner=user.username,
            scope=scope,
            industry=industry,
            offset=offset,
            limit=limit,
        )

        return [document.to_response() for document in documents]

    async def create_template(self, request: TemplateCreateRequest, user: UserContext) -> TemplateResponse:
        """
        Save the current table layout under a name the caller chose.

        :param request: Template supplied by the user.
        :param user: Identity the template belongs to.
        :return: The stored template.
        :raises ConflictError: When the caller already saved a template with the same name.
        """
        existing = await self._repository.find_one(
            query={"owner": user.username, "scope": request.scope.value, "name": request.name},
        )
        if existing is not None:
            raise ConflictError(message="A template with this name already exists", details={"name": request.name})

        document = TemplateDocument(**request.model_dump(), owner=user.username)
        await self._repository.insert(document=document)

        return document.to_response()

    async def update_template(
        self,
        template_id: str,
        request: TemplateUpdateRequest,
        user: UserContext,
    ) -> TemplateResponse:
        """
        Change a stored template the caller owns.

        :param template_id: Identifier of the template that is changed.
        :param request: Attributes the caller wants to change.
        :param user: Identity that asks for the change.
        :return: The changed template.
        :raises NotFoundError: When the identifier is unknown.
        :raises PermissionDeniedError: When the caller does not own the template.
        """
        document = await self._require_template(template_id=template_id, user=user)
        updates: dict[str, Any] = request.model_dump(exclude_unset=True, exclude_none=True)
        if request.columns is not None:
            updates["columns"] = [column.model_dump() for column in request.columns]
        if request.filters is not None:
            updates["filters"] = [condition.model_dump() for condition in request.filters]
        if request.sort is not None:
            updates["sort"] = [specification.model_dump() for specification in request.sort]

        updates["updated_at"] = utc_now()
        await self._repository.update_fields(identifier=document.id, updates=updates)

        refreshed = await self._repository.find_by_id(identifier=template_id)
        if refreshed is None:
            raise NotFoundError(message="The template does not exist", details={"id": template_id})

        return refreshed.to_response()

    async def delete_template(self, template_id: str, user: UserContext) -> None:
        """
        Remove a stored template the caller owns.

        :param template_id: Identifier of the template that is removed.
        :param user: Identity that asks for the removal.
        :raises NotFoundError: When the identifier is unknown.
        :raises PermissionDeniedError: When the caller does not own the template.
        """
        document = await self._require_template(template_id=template_id, user=user)
        await self._repository.delete(identifier=document.id, user=user.username)

    async def _require_template(self, template_id: str, user: UserContext) -> TemplateDocument:
        """
        Read a template and refuse to continue when it is missing or belongs to somebody else.

        :param template_id: Identifier of the template.
        :param user: Identity that asks for the template.
        :return: The stored template.
        :raises NotFoundError: When the identifier is unknown.
        :raises PermissionDeniedError: When the caller does not own the template.
        """
        document = await self._repository.find_by_id(identifier=template_id)
        if document is None:
            raise NotFoundError(message="The template does not exist", details={"id": template_id})

        if document.owner != user.username:
            raise PermissionDeniedError(message="Only the owner of a template may change it")

        return document
