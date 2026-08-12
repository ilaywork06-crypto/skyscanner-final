"""
The export endpoint, handing the user the very rows they filtered as a sheet or as raw data.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from skyscanner_models.common import UserContext
from skyscanner_models.enums import Permission
from skyscanner_models.grid import EventExportRequest
from skyscanner_models.storage import ArchiveRequest

from events_service.dependencies import ExportServiceDependency, require_permission
from events_service.services.export_service import ENTITY_MODE_SUMMARY

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/exports", tags=["exports"])
CONTENT_DISPOSITION: str = "Content-Disposition"

# ----- FUNCTIONS ----- #


@ROUTER.post("/events")
async def export_events(
    request: EventExportRequest,
    service: ExportServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.EVENT_READ))],
    export_format: str = "csv",
    entity_mode: str = ENTITY_MODE_SUMMARY,
) -> Response:
    """
    Materialise the events of the current view, or the hand picked subset of it, in the requested format.

    The entities of every exported event travel with it: nested under the event in the JSON, folded into
    summary columns in the sheet, or written as one row each when the caller asks for the row mode.

    :param request: Query the exported rows are read with, the columns to keep and the optional selection.
    :param service: Owner of the export.
    :param export_format: Either csv or json.
    :param entity_mode: Either summary for one row per event, or rows for one row per entity of an event.
    :return: The answer carrying the export as an attachment.
    """
    body, media_type, file_name = await service.export_events(
        query=request,
        columns=request.columns,
        export_format=export_format,
        event_ids=request.event_ids,
        entity_mode=entity_mode,
    )

    return Response(
        content=body,
        media_type=media_type,
        headers={CONTENT_DISPOSITION: f'attachment; filename="{file_name}"'},
    )


@ROUTER.post("/events/files", response_model=ArchiveRequest)
async def build_file_archive_manifest(
    request: EventExportRequest,
    service: ExportServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_DOWNLOAD))],
) -> ArchiveRequest:
    """
    Work out which stored files belong to a set of events and how they are laid out inside an archive.

    The manifest is handed to the archive endpoint of the storage service, which is the only service that
    may read the bucket. Splitting it this way keeps the knowledge of the events here and the bucket there.

    :param request: Query the events are read with, together with the optional selection.
    :param service: Owner of the export.
    :return: The manifest of the archive.
    """
    return await service.build_archive_manifest(query=request, event_ids=request.event_ids)
