"""
The endpoints of the schemas, which declare what attributes an assumption carries.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from fastapi import APIRouter, status

from truth_service.api.pagination import LIMIT_QUERY, OFFSET_QUERY
from truth_service.dependencies import SchemaServiceDependency
from truth_service.models.schema import (
    SchemaCreateRequest,
    SchemaDetailResponse,
    SchemaRevisionRequest,
    SchemaSummaryResponse,
)

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/schema", tags=["schemas"])

# ----- FUNCTIONS ----- #


@ROUTER.get("", response_model=list[SchemaSummaryResponse])
async def list_schemas(
    service: SchemaServiceDependency,
    offset: int = OFFSET_QUERY,
    limit: int = LIMIT_QUERY,
) -> list[SchemaSummaryResponse]:
    """
    Read one window of the declarations, each at the revision it currently stands at.

    :param service: Owner of the declarations.
    :param offset: Amount of declarations skipped before collecting.
    :param limit: Largest amount of declarations that is returned.
    :return: The declarations of the window.
    """
    return await service.list_schemas(offset=offset, limit=limit)


@ROUTER.post("", response_model=SchemaDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_schema(request: SchemaCreateRequest, service: SchemaServiceDependency) -> SchemaDetailResponse:
    """
    Declare a new schema, which is the first revision of a new lineage.

    :param request: Declaration supplied by the caller.
    :param service: Owner of the declarations.
    :return: The declaration as it was stored, carrying the identifier it was given.
    """
    return await service.create_schema(request=request)


@ROUTER.get("/name/{name}", response_model=SchemaDetailResponse)
async def read_schema_by_name(name: str, service: SchemaServiceDependency) -> SchemaDetailResponse:
    """
    Read the current revision of the declaration answering to one name.

    :param name: Name of the declaration.
    :param service: Owner of the declarations.
    :return: The current revision, whole.
    """
    return await service.get_by_name(name=name)


@ROUTER.post("/name/{name}/revisions", response_model=SchemaDetailResponse, status_code=status.HTTP_201_CREATED)
async def revise_schema_by_name(
    name: str,
    request: SchemaRevisionRequest,
    service: SchemaServiceDependency,
) -> SchemaDetailResponse:
    """
    Write a new revision of the declaration answering to one name.

    :param name: Name of the declaration.
    :param request: The declaration as it now stands, and why it was changed.
    :param service: Owner of the declarations.
    :return: The revision that was written.
    """
    return await service.revise_schema(key=name, request=request)


@ROUTER.get("/{schema_id}/latest", response_model=SchemaDetailResponse)
async def read_latest_schema(schema_id: str, service: SchemaServiceDependency) -> SchemaDetailResponse:
    """
    Read the current revision of a declaration addressed by any of its identifiers.

    :param schema_id: Identifier of a revision or of the lineage.
    :param service: Owner of the declarations.
    :return: The current revision, whole.
    """
    return await service.get_latest(key=schema_id)


@ROUTER.post("/{schema_id}/revisions", response_model=SchemaDetailResponse, status_code=status.HTTP_201_CREATED)
async def revise_schema(
    schema_id: str,
    request: SchemaRevisionRequest,
    service: SchemaServiceDependency,
) -> SchemaDetailResponse:
    """
    Write a new revision of a declaration, which is the only way a declaration is ever changed.

    :param schema_id: Identifier of a revision or of the lineage.
    :param request: The declaration as it now stands, and why it was changed.
    :param service: Owner of the declarations.
    :return: The revision that was written.
    """
    return await service.revise_schema(key=schema_id, request=request)


@ROUTER.get("/{schema_id}", response_model=SchemaDetailResponse)
async def read_schema(schema_id: str, service: SchemaServiceDependency) -> SchemaDetailResponse:
    """
    Read exactly the revision that was addressed, falling back to the current one of its lineage.

    :param schema_id: Identifier of a revision, of the lineage, or the name of the declaration.
    :param service: Owner of the declarations.
    :return: That revision, whole.
    """
    return await service.get_revision(identifier=schema_id)
