"""
The import endpoint, reading a bundle back into the inventory it was exported out of - or into another one.

:date: 2026-09-09
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile, status

from skyscanner_common.errors import ValidationError
from skyscanner_models.common import UserContext
from skyscanner_models.enums import Permission

from events_service.dependencies import BundleServiceDependency, require_permission
from events_service.services.bundle_service import MAX_BUNDLE_BYTES

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/imports", tags=["imports"])

# ----- FUNCTIONS ----- #


@ROUTER.post("/events", status_code=status.HTTP_201_CREATED)
async def import_events(
    service: BundleServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.EVENT_CREATE))],
    file: Annotated[UploadFile, File(description="The bundle written by the bundle export")],
) -> dict[str, Any]:
    """
    Read a bundle back in, writing everything in it that this inventory does not already hold.

    The declarations go first and the events afterwards, because an event names its industry, its types, its
    platforms and its fields by key and a key that has not been declared yet is a column no form offers and
    a chip no page can colour. The files go in between: every one of them is written into this system's
    bucket and every record that pointed at it is repointed at where it actually landed, because a bucket
    key from the system the bundle came from names nothing here.

    An event whose identifier is already in this inventory is left exactly as it is. That is what makes a
    restore that was interrupted safe to run again, and it is also why this is not a way to overwrite
    anything: an import adds what is missing and never rewrites what is there.

    Two capabilities are involved and only one is asked for here. Creating events is what this endpoint
    does, so that is its guard; writing the files is done by the storage service, which asks the caller for
    the upload capability itself when the identity is forwarded to it. A caller who may create events but
    may not upload files therefore restores the events and is told, file by file, which bytes did not
    follow - rather than being refused at the door for a permission half the bundle never needed.

    :param service: Owner of the bundle.
    :param user: Identity the restore is performed on behalf of and its files attributed to.
    :param file: The bundle, as the archive the export wrote.
    :return: What was written, what was left alone and what could not be written.
    :raises ValidationError: When the upload is larger than one import may carry, or is not a bundle at all.
    """
    payload = await file.read()
    if len(payload) > MAX_BUNDLE_BYTES:
        raise ValidationError(
            message="The bundle is larger than one import may carry",
            details={"size_bytes": str(len(payload)), "limit_bytes": str(MAX_BUNDLE_BYTES)},
        )

    try:
        return await service.restore_bundle(payload=payload, user=user)
    except ValueError as error:
        raise ValidationError(message=str(error)) from error
