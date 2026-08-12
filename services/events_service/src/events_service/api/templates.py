"""
The endpoints of the saved table templates, letting a user keep the view they built and load it again later.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends, status

from skyscanner_models.common import OperationResult, UserContext
from skyscanner_models.enums import FieldScope, Permission
from skyscanner_models.template import TemplateCreateRequest, TemplateResponse, TemplateUpdateRequest

from events_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from events_service.dependencies import CurrentUser, TemplateServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/templates", tags=["templates"])

# ----- FUNCTIONS ----- #


@ROUTER.get("", response_model=list[TemplateResponse])
async def list_templates(
    service: TemplateServiceDependency,
    user: CurrentUser,
    scope: FieldScope = FieldScope.EVENT,
    industry: str | None = None,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[TemplateResponse]:
    """
    Read the templates the caller may load, which are their own ones and the shared ones.

    :param service: Owner of the templates.
    :param user: Identity the templates are read for.
    :param scope: Whether the templates target events or entities.
    :param industry: Industry the templates are narrowed to, empty for the global view.
    :param offset: Amount of templates skipped before collecting.
    :param limit: Largest amount of templates that is returned, zero for all of them.
    :return: The matching templates.
    """
    return await service.list_templates(user=user, scope=scope, industry=industry, offset=offset, limit=limit)


@ROUTER.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: TemplateCreateRequest,
    service: TemplateServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.TEMPLATE_MANAGE))],
) -> TemplateResponse:
    """
    Save the current table layout under a name the caller chose.

    :param request: Template supplied by the user.
    :param service: Owner of the templates.
    :param user: Identity the template belongs to.
    :return: The stored template.
    """
    return await service.create_template(request=request, user=user)


@ROUTER.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: TemplateUpdateRequest,
    service: TemplateServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.TEMPLATE_MANAGE))],
) -> TemplateResponse:
    """
    Change a stored template the caller owns.

    :param template_id: Identifier of the template that is changed.
    :param request: Attributes the caller wants to change.
    :param service: Owner of the templates.
    :param user: Identity that asks for the change.
    :return: The changed template.
    """
    return await service.update_template(template_id=template_id, request=request, user=user)


@ROUTER.delete("/{template_id}", response_model=OperationResult)
async def delete_template(
    template_id: str,
    service: TemplateServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.TEMPLATE_MANAGE))],
) -> OperationResult:
    """
    Remove a stored template the caller owns.

    :param template_id: Identifier of the template that is removed.
    :param service: Owner of the templates.
    :param user: Identity that asks for the removal.
    :return: The acknowledgement of the removal.
    """
    await service.delete_template(template_id=template_id, user=user)

    return OperationResult(success=True, message="The template was removed", affected=1)
