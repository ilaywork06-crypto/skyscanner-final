"""
The endpoints of the dynamic schema, where an industry declares the fields its events and entities carry.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends, status

from skyscanner_models.common import OperationResult, UserContext
from skyscanner_models.enums import FieldScope, Permission
from skyscanner_models.field import FieldCreateRequest, FieldResponse, FieldUpdateRequest

from events_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from events_service.dependencies import FieldServiceDependency, require_permission

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/fields", tags=["fields"])

# ----- FUNCTIONS ----- #


@ROUTER.get("", response_model=list[FieldResponse])
async def list_fields(
    service: FieldServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    scope: FieldScope = FieldScope.EVENT,
    industry: str | None = None,
    entity_type: str | None = None,
    include_shared: bool = True,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[FieldResponse]:
    """
    Read the declarations that apply to a scope, so that the client can render the matching schema.

    :param service: Owner of the dynamic schema.
    :param scope: Whether the declarations target events or entities.
    :param industry: Industry whose own declarations are added to the shared ones.
    :param entity_type: Entity type the declarations are limited to.
    :param include_shared: Whether the declarations that belong to no industry are included.
    :param offset: Amount of declarations skipped before collecting.
    :param limit: Largest amount of declarations that is returned, zero for all of them.
    :return: The matching declarations.
    """
    return await service.list_fields(
        scope=scope,
        industry=industry,
        entity_type=entity_type,
        include_shared=include_shared,
        offset=offset,
        limit=limit,
    )


@ROUTER.post("", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def create_field(
    request: FieldCreateRequest,
    service: FieldServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> FieldResponse:
    """
    Declare a new dynamic field for an industry.

    :param request: Declaration supplied by the user.
    :param service: Owner of the dynamic schema.
    :param user: Identity the declaration is attributed to.
    :return: The stored declaration.
    """
    return await service.create_field(request=request, user=user)


@ROUTER.patch("/{field_id}", response_model=FieldResponse)
async def update_field(
    field_id: str,
    request: FieldUpdateRequest,
    service: FieldServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> FieldResponse:
    """
    Change a stored declaration, leaving every attribute the caller omitted untouched.

    :param field_id: Identifier of the declaration that is changed.
    :param request: Attributes the caller wants to change.
    :param service: Owner of the dynamic schema.
    :return: The changed declaration.
    """
    return await service.update_field(field_id=field_id, request=request)


@ROUTER.delete("/{field_id}", response_model=OperationResult)
async def delete_field(
    field_id: str,
    service: FieldServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FIELD_MANAGE))],
) -> OperationResult:
    """
    Remove a stored declaration, which hides the generated column without touching the stored values.

    :param field_id: Identifier of the declaration that is removed.
    :param service: Owner of the dynamic schema.
    :return: The acknowledgement of the removal.
    """
    await service.delete_field(field_id=field_id)

    return OperationResult(success=True, message="The field declaration was removed", affected=1)
