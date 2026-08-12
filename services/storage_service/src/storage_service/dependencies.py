"""
The dependency wiring of the storage service, handing every request the client of the bucket and the caller.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated, Callable, cast

from fastapi import Depends, Request

from skyscanner_common.errors import PermissionDeniedError
from skyscanner_common.identity import build_user_context
from skyscanner_common.object_storage import ObjectStorageClient
from skyscanner_common.settings import get_auth_settings
from skyscanner_models.common import UserContext
from skyscanner_models.enums import Permission

from storage_service.services.artifact_service import ArtifactService

# ----- FUNCTIONS ----- #


def get_storage_client(request: Request) -> ObjectStorageClient:
    """
    Fetch the shared client of the bucket that was opened when the service started.

    :param request: Incoming request carrying the application state.
    :return: The shared client of the bucket.
    """
    return cast(ObjectStorageClient, request.app.state.storage)


def get_user_context(request: Request) -> UserContext:
    """
    Build the caller identity out of the headers the authenticating reverse proxy injected.

    :param request: Incoming request carrying the identity headers.
    :return: The identity the request is handled on behalf of.
    """
    return build_user_context(headers=request.headers, settings=get_auth_settings())


def require_permission(permission: Permission) -> Callable[[UserContext], UserContext]:
    """
    Build a dependency that lets a request through only when the caller holds one capability.

    :param permission: Capability the endpoint asks for.
    :return: The dependency guarding the endpoint.
    """

    def guard(user: Annotated[UserContext, Depends(get_user_context)]) -> UserContext:
        """
        Verify that the caller holds the capability the endpoint asks for.

        :param user: Identity the request is handled on behalf of.
        :return: The very same identity, so that endpoints can read the caller from the guard.
        :raises PermissionDeniedError: When the caller does not hold the capability.
        """
        if permission not in user.permissions:
            raise PermissionDeniedError(
                message="The identity is not allowed to perform this action",
                details={"permission": permission.value},
            )

        return user

    return guard


StorageDependency = Annotated[ObjectStorageClient, Depends(get_storage_client)]


def get_artifact_service(storage: StorageDependency) -> ArtifactService:
    """
    Build the owner of the stored files for one request.

    :param storage: Client of the object storage.
    :return: The service that owns the stored files.
    """
    return ArtifactService(storage=storage)


ArtifactServiceDependency = Annotated[ArtifactService, Depends(get_artifact_service)]
