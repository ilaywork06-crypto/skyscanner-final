"""
The endpoints of the stored files - uploading new ones, linking to them, streaming them and removing them.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from skyscanner_common.object_storage import content_disposition
from skyscanner_common.text import file_suffix, safe_path_segment
from skyscanner_models.common import Artifact, OperationResult, UserContext
from skyscanner_models.enums import ArtifactKind, Permission
from skyscanner_models.storage import (
    ArchiveRequest,
    ArtifactUploadResponse,
    DownloadLinkResponse,
    StorageObjectResponse,
    UploadBeginRequest,
    UploadBeginResponse,
    UploadCompleteRequest,
    UploadPart,
    UploadStatusResponse,
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

UNNAMED_FILE: str = "unnamed"

CONTENT_RANGE: str = "Content-Range"
ACCEPT_RANGES: str = "Accept-Ranges"
CONTENT_LENGTH: str = "Content-Length"
BYTE_UNIT: str = "bytes"

# How much of a part is read off the wire at a time. The part itself is held in memory before it is handed to
# the bucket, because the protocol wants its length up front, and a part is a few megabytes by construction.
PART_READ_CHUNK: int = 1024 * 1024

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
    # The upload is handed over as the way to read it rather than as its bytes: the service feeds the bucket
    # from it piece by piece, so a file larger than the memory of the process is an ordinary upload.
    payloads = [
        UploadPayload(
            file_name=safe_path_segment(upload.filename or UNNAMED_FILE, fallback=UNNAMED_FILE),
            read=upload.read,
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


@ROUTER.post("/uploads", response_model=UploadBeginResponse, status_code=status.HTTP_201_CREATED)
async def begin_upload(
    request: UploadBeginRequest,
    service: ArtifactServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_UPLOAD))],
) -> UploadBeginResponse:
    """
    Open an upload the browser drives itself, writing the file one part per request.

    This is the road a very large file takes. The endpoint above puts a whole pick into one request, which
    is right for the ordinary case and hopeless past a few gigabytes: the request has to survive from the
    first byte to the last, and a connection that drops near the end costs every byte that got there. Here
    the browser opens the upload once, writes the parts as separate requests it can retry one at a time, and
    asks what landed before sending the rest of a wait that was interrupted.

    :param request: What the file is called and who it will belong to.
    :param service: Owner of the stored files.
    :return: The identifier of the opened upload, the key it lands under and the size of one part.
    """
    return await service.begin_upload(request=request)


@ROUTER.put("/uploads/{upload_id}/parts/{number}", response_model=UploadPart)
async def write_upload_part(
    upload_id: str,
    number: int,
    request: Request,
    service: ArtifactServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_UPLOAD))],
    path: str,
) -> UploadPart:
    """
    Write one part of an opened upload, taking the bytes as the body of the request.

    The part arrives as the raw body rather than as a form, because it is bytes and nothing else: wrapping a
    few megabytes of a file in a multipart envelope only to unwrap it again costs a copy of the part on both
    sides of the wire for no information whatsoever.

    :param upload_id: Identifier of the opened upload.
    :param number: One based position of the part inside the file.
    :param request: Incoming request whose body is the bytes of the part.
    :param service: Owner of the stored files.
    :param path: Key the file is being stored under, as the opening answer named it.
    :return: The part as the bucket recorded it.
    """
    chunk = bytearray()
    async for piece in request.stream():
        chunk.extend(piece)

    return await service.write_upload_part(path=path, upload_id=upload_id, number=number, chunk=bytes(chunk))


@ROUTER.get("/uploads/{upload_id}", response_model=UploadStatusResponse)
async def read_upload_status(
    upload_id: str,
    service: ArtifactServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_UPLOAD))],
    path: str,
) -> UploadStatusResponse:
    """
    Read which parts of an opened upload already landed, which is what an interrupted one resumes from.

    :param upload_id: Identifier of the opened upload.
    :param service: Owner of the stored files.
    :param path: Key the file is being stored under.
    :return: Every part the bucket is already holding.
    """
    return await service.upload_status(path=path, upload_id=upload_id)


@ROUTER.post("/uploads/{upload_id}/complete", response_model=Artifact)
async def complete_upload(
    upload_id: str,
    request: UploadCompleteRequest,
    service: ArtifactServiceDependency,
    user: Annotated[UserContext, Depends(require_permission(Permission.FILE_UPLOAD))],
) -> Artifact:
    """
    Join the parts of an opened upload into the one stored file they describe.

    :param upload_id: Identifier of the opened upload.
    :param request: The parts of the file together with everything describing it.
    :param service: Owner of the stored files.
    :param user: Identity the upload is recorded against.
    :return: The artifact record of the finished file.
    """
    return await service.complete_upload(upload_id=upload_id, request=request, uploaded_by=user.username)


@ROUTER.delete("/uploads/{upload_id}", response_model=OperationResult)
async def abort_upload(
    upload_id: str,
    service: ArtifactServiceDependency,
    _: Annotated[UserContext, Depends(require_permission(Permission.FILE_UPLOAD))],
    path: str,
) -> OperationResult:
    """
    Give up an opened upload, so that the parts already written leave the bucket rather than lingering.

    :param upload_id: Identifier of the opened upload.
    :param service: Owner of the stored files.
    :param path: Key the file was being stored under.
    :return: The acknowledgement that the upload was given up.
    """
    await service.abort_upload(path=path, upload_id=upload_id)

    return OperationResult(success=True, message="The upload was given up", affected=1)


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
    name: str | None = None,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
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
    :param name: Name the file is offered under, defaulting to the last segment of its key.
    :param range_header: Window of the file the caller asked for, when it asked for one rather than all of it.
    :return: The answer streaming the stored file, or the window of it that was asked for.
    """
    metadata = await service.describe(path=path)
    # Every upload is written under a fresh identifier so that two of them can never overwrite one another,
    # which makes the key a poor name to hand a user. The caller says what the file is called instead.
    file_name = safe_path_segment(name, fallback=UNNAMED_FILE) if name else path.rsplit("/", maxsplit=1)[-1]
    media_type = metadata.content_type
    if inline:
        media_type = _preview_media_type(content_type=metadata.content_type, file_name=file_name)

    headers = {
        CONTENT_DISPOSITION: content_disposition(
            disposition=INLINE_DISPOSITION if inline else ATTACHMENT_DISPOSITION,
            file_name=file_name,
        ),
        # Saying so is what lets a reader of a very large file ask for a window of it rather than all of it,
        # and what lets a browser seek inside an audio or a video file instead of waiting for the whole one.
        ACCEPT_RANGES: BYTE_UNIT,
    }

    window = _read_range(header=range_header, size=metadata.size_bytes)
    if window is None:
        return StreamingResponse(content=service.stream(path=path), media_type=media_type, headers=headers)

    start, end = window
    headers[CONTENT_RANGE] = f"{BYTE_UNIT} {start}-{end}/{metadata.size_bytes}"
    headers[CONTENT_LENGTH] = str(end - start + 1)

    return StreamingResponse(
        content=service.stream(path=path, start=start, end=end),
        media_type=media_type,
        headers=headers,
        status_code=status.HTTP_206_PARTIAL_CONTENT,
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
            CONTENT_DISPOSITION: content_disposition(
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


def _read_range(header: str | None, size: int) -> tuple[int, int] | None:
    """
    Read the window a caller asked for, or nothing when it asked for the whole file.

    Only a single window is honoured. The protocol allows several to be asked for at once and answered as a
    multipart body, and nothing that reads this service wants that: a viewer paging through a sheet asks for
    one stretch at a time, and a browser seeking in a video does the same. Anything that cannot be read as
    one window is answered with the whole file, which is what the protocol asks for when a range is ignored.

    :param header: The window as the caller wrote it, or nothing when it asked for none.
    :param size: How large the stored file is, which is what an open ended window is measured against.
    :return: The first and the last byte that are wanted, both included, or nothing for the whole file.
    """
    if header is None or size <= 0:
        return None

    unit, _, spans = header.partition("=")
    if unit.strip().lower() != BYTE_UNIT or "," in spans:
        return None

    first, separator, last = spans.strip().partition("-")
    if not separator:
        return None

    try:
        # `-500` asks for the last five hundred bytes rather than for everything up to byte five hundred.
        if not first:
            length = int(last)
            start = max(size - length, 0) if length > 0 else 0
            end = size - 1
        else:
            start = int(first)
            end = int(last) if last else size - 1
    except ValueError:
        return None

    end = min(end, size - 1)
    if start < 0 or start > end:
        return None

    return start, end


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
