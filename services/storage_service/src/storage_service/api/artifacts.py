"""
The endpoints of the stored files - uploading new ones, linking to them, streaming them and removing them.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import re
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import StreamingResponse

from skyscanner_common.text import file_suffix
from skyscanner_models.common import OperationResult, UserContext
from skyscanner_models.enums import ArtifactKind, Permission
from skyscanner_models.storage import (
    ArchiveRequest,
    ArtifactUploadResponse,
    DownloadLinkResponse,
    StorageObjectResponse,
)

from storage_service.constants import (
    DEFAULT_CONTENT_TYPE,
    DEFAULT_OWNER_KIND,
    IMAGE_CONTENT_TYPE_PREFIX,
    INLINE_TEXT_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    TEXT_CONTENT_TYPE_PREFIX,
    TEXT_CONTENT_TYPE_SUFFIXES,
    TEXT_CONTENT_TYPES,
    TEXT_FILE_SUFFIXES,
)
from storage_service.dependencies import ArtifactServiceDependency, require_permission
from storage_service.services.artifact_service import UploadPayload

# ----- CONSTS ----- #

ROUTER: APIRouter = APIRouter(prefix="/artifacts", tags=["artifacts"])
CONTENT_DISPOSITION: str = "Content-Disposition"
ARCHIVE_MEDIA_TYPE: str = "application/zip"
INLINE_DISPOSITION: str = "inline"
ATTACHMENT_DISPOSITION: str = "attachment"

# A header carries plain ASCII and cannot carry a quote or a backslash unescaped, while a stored file is named
# in whatever alphabet its owner works in. Everything outside the printable ASCII range is therefore replaced
# in the plain file name, and the real name travels next to it in the encoded form of RFC 5987.
UNSAFE_HEADER_CHARACTERS: re.Pattern[str] = re.compile(r'[^\x20-\x7e]|["\\]')
FALLBACK_HEADER_CHARACTER: str = "_"
FALLBACK_FILE_NAME: str = "download"

# ----- FUNCTIONS ----- #


@ROUTER.post("", response_model=ArtifactUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_artifacts(
    service: ArtifactServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.FILE_UPLOAD))],
    files: Annotated[list[UploadFile], File(description="Files the user picked in the browser")],
    owner_kind: Annotated[str, Form()] = DEFAULT_OWNER_KIND,
    owner_id: Annotated[str | None, Form()] = None,
    kind: Annotated[ArtifactKind, Form()] = ArtifactKind.ADDITIONAL,
    folder: Annotated[str | None, Form()] = None,
    descriptor: Annotated[str, Form()] = "",
) -> ArtifactUploadResponse:
    """
    Write every picked file into the bucket and hand back the artifact records the inventory stores.

    :param service: Owner of the stored files.
    :param user: Identity the upload is performed on behalf of, recorded on every written artifact.
    :param files: Files the user picked in the browser.
    :param owner_kind: Top level folder of the key, telling events and entities apart.
    :param owner_id: Identifier of the owner the files belong to, if it is known already.
    :param kind: Role the files play for their owner.
    :param folder: Virtual folder used to group the files in the table.
    :param descriptor: Free text describing what the files hold.
    :return: The artifact records of the written files.
    """
    payloads = [
        UploadPayload(
            file_name=upload.filename or "unnamed",
            content=await upload.read(),
            content_type=upload.content_type or DEFAULT_CONTENT_TYPE,
        )
        for upload in files
    ]
    artifacts = await service.upload(
        payloads=payloads,
        owner_kind=owner_kind,
        owner_id=owner_id,
        kind=kind,
        folder=folder,
        descriptor=descriptor,
        uploaded_by=user.username,
    )

    return ArtifactUploadResponse(artifacts=artifacts)


@ROUTER.get("/link", response_model=DownloadLinkResponse)
async def read_download_link(
    service: ArtifactServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_DOWNLOAD))],
    path: str,
    name: str | None = None,
) -> DownloadLinkResponse:
    """
    Mint a temporary link that lets the browser read one stored file straight from the bucket.

    :param service: Owner of the stored files.
    :param path: Key the file is stored under.
    :param name: Name the browser should save the download as.
    :return: The link together with the moment it stops working.
    """
    return await service.download_link(path=path, name=name)


@ROUTER.get("/metadata", response_model=StorageObjectResponse)
async def read_metadata(
    service: ArtifactServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_DOWNLOAD))],
    path: str,
) -> StorageObjectResponse:
    """
    Read the metadata the bucket keeps for one stored file.

    :param service: Owner of the stored files.
    :param path: Key the file is stored under.
    :return: The metadata of the stored file.
    """
    return await service.describe(path=path)


@ROUTER.get("/content")
async def read_content(
    service: ArtifactServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_DOWNLOAD))],
    path: str,
    inline: bool = False,
) -> StreamingResponse:
    """
    Stream one stored file through the service, which is what the preview pane of the event page reads.

    A preview and a download are the same bytes under two different promises. The download hands the file
    over exactly as it was stored, because that is the file the user asked to keep. The preview instead
    serves anything text shaped as plain text, because a browser handed a csv or an unrecognised type saves
    it to disk rather than showing it, and the user who clicked a file in the viewer ends up with a download
    they never asked for. Pictures and documents keep their own type, since a browser renders those already.

    :param service: Owner of the stored files.
    :param path: Key the file is stored under.
    :param inline: Whether the browser should render the file instead of saving it.
    :return: The answer streaming the stored file.
    """
    metadata = await service.describe(path=path)
    file_name = path.rsplit("/", maxsplit=1)[-1]
    media_type = metadata.content_type
    if inline:
        media_type = _preview_media_type(content_type=metadata.content_type, file_name=file_name)

    return StreamingResponse(
        content=service.stream(path=path),
        media_type=media_type,
        headers={
            CONTENT_DISPOSITION: _content_disposition(
                disposition=INLINE_DISPOSITION if inline else ATTACHMENT_DISPOSITION,
                file_name=file_name,
            ),
        },
    )


@ROUTER.post("/archive")
async def download_archive(
    request: ArchiveRequest,
    service: ArtifactServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_DOWNLOAD))],
) -> StreamingResponse:
    """
    Pack a set of stored files into one archive and hand it to the browser as a single download.

    The manifest says which files to take and where each of them sits inside the archive, so the caller
    decides the folder structure and this endpoint only reads the bucket and zips.

    :param request: Files the archive holds and the path each of them takes inside it.
    :param service: Owner of the stored files.
    :return: The answer streaming the archive as an attachment.
    """
    return StreamingResponse(
        content=service.build_archive(request=request),
        media_type=ARCHIVE_MEDIA_TYPE,
        headers={
            CONTENT_DISPOSITION: _content_disposition(
                disposition=ATTACHMENT_DISPOSITION,
                file_name=request.archive_name,
            ),
        },
    )


@ROUTER.delete("", response_model=OperationResult)
async def delete_artifact(
    service: ArtifactServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_UPLOAD))],
    path: str,
) -> OperationResult:
    """
    Remove one stored file from the bucket.

    :param service: Owner of the stored files.
    :param path: Key the file is stored under.
    :return: The acknowledgement of the removal.
    """
    await service.delete(path=path)

    return OperationResult(success=True, message="The file was removed", affected=1)


def _preview_media_type(content_type: str, file_name: str) -> str:
    """
    Pick the type a file is previewed under, which is its own only when a browser renders that type.

    :param content_type: Type the file was stored under.
    :param file_name: Name the file is stored as, read when the stored type says nothing useful.
    :return: The type the preview is served under.
    """
    stored = content_type.split(";", maxsplit=1)[0].strip().lower()
    if stored.startswith(IMAGE_CONTENT_TYPE_PREFIX) or stored == PDF_CONTENT_TYPE:
        return content_type

    if _is_text_shaped(content_type=stored, file_name=file_name):
        return INLINE_TEXT_CONTENT_TYPE

    return content_type


def _is_text_shaped(content_type: str, file_name: str) -> bool:
    """
    Decide whether a stored file is one a reader would expect to see as text.

    :param content_type: Type the file was stored under, already reduced to its bare form.
    :param file_name: Name the file is stored as.
    :return: Whether the file holds text.
    """
    if content_type.startswith(TEXT_CONTENT_TYPE_PREFIX) or content_type in TEXT_CONTENT_TYPES:
        return True

    if content_type.endswith(TEXT_CONTENT_TYPE_SUFFIXES):
        return True

    return file_suffix(file_name=file_name) in TEXT_FILE_SUFFIXES


def _content_disposition(disposition: str, file_name: str) -> str:
    """
    Build the disposition header of an answer so that any file name survives it, quoted or not ASCII.

    :param disposition: Whether the browser renders the file or saves it.
    :param file_name: Name the file is offered under.
    :return: The value of the disposition header.
    """
    fallback = UNSAFE_HEADER_CHARACTERS.sub(FALLBACK_HEADER_CHARACTER, file_name).strip() or FALLBACK_FILE_NAME
    encoded = quote(file_name, safe="")

    return f"{disposition}; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"
