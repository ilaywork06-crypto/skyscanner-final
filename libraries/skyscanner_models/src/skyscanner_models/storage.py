"""
Payloads of the storage service, covering uploads into the bucket and the temporary links used to read files back.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from skyscanner_models.common import Artifact
from skyscanner_models.enums import ArtifactKind

# ----- CLASSES ----- #


class ArtifactUploadResponse(BaseModel):
    """
    The stored artifacts produced by a single multipart upload request.
    """

    model_config = ConfigDict(populate_by_name=True)

    artifacts: list[Artifact] = Field(default_factory=list, description="Artifacts that were written to the bucket")


class DownloadLinkResponse(BaseModel):
    """
    A temporary link that lets the browser read one stored file directly from the bucket.
    """

    model_config = ConfigDict(populate_by_name=True)

    url: str = Field(description="Presigned link the browser may follow")
    name: str = Field(description="Original file name of the artifact")
    content_type: str = Field(default="application/octet-stream", description="MIME type of the stored file")
    expires_at: datetime = Field(description="UTC moment the link stops working")


class ArchiveEntry(BaseModel):
    """
    One stored file together with the path it takes inside a downloaded archive.
    """

    model_config = ConfigDict(populate_by_name=True)

    path: str = Field(description="Key the file is stored under in the bucket")
    entry: str = Field(description="Path the file takes inside the archive, folders included")


class ArchiveRequest(BaseModel):
    """
    The manifest of an archive: which stored files it holds and how they are laid out inside it.

    The events service works out the layout, because only it knows which event and which entity a file
    belongs to, and the storage service builds the archive, because only it may read the bucket.
    """

    model_config = ConfigDict(populate_by_name=True)

    entries: list[ArchiveEntry] = Field(default_factory=list, description="Files the archive is built from")
    archive_name: str = Field(default="skyscanner-files.zip", description="Name the archive is offered under")


class StorageObjectResponse(BaseModel):
    """
    The metadata of one object as reported by the bucket.
    """

    model_config = ConfigDict(populate_by_name=True)

    path: str = Field(description="Key the object is stored under")
    size_bytes: int = Field(default=0, ge=0, description="Size of the object in bytes")
    content_type: str = Field(default="application/octet-stream", description="MIME type of the object")
    checksum: str | None = Field(default=None, description="Checksum reported by the bucket")
    last_modified: datetime | None = Field(default=None, description="UTC moment the object last changed")


class UploadDescriptor(BaseModel):
    """
    Everything about a file that is not its bytes, which a resumable upload carries at both of its ends.

    A file written across many requests cannot be described once at the start and remembered: remembering it
    would mean a second store of half finished uploads, kept in step with the bucket, cleaned up when the
    browser that started one never comes back. The bucket already remembers the parts, so the description
    travels with the requests instead and is checked when the upload is finished.
    """

    model_config = ConfigDict(populate_by_name=True)

    file_name: str = Field(description="Name the file was picked under, which it is stored and offered as")
    content_type: str = Field(default="application/octet-stream", description="MIME type the browser claimed")
    owner_kind: str = Field(default="events", description="Top level folder of the key, telling owners apart")
    owner_id: str | None = Field(default=None, description="Identifier of the owner, when it is known already")
    kind: ArtifactKind = Field(default=ArtifactKind.ADDITIONAL, description="Role the file plays for its owner")
    folder: str | None = Field(default=None, description="Virtual folder the file is grouped under")
    descriptor: str = Field(default="", description="Free text describing what the file holds")


class UploadBeginRequest(UploadDescriptor):
    """
    The payload that opens an upload the browser drives itself, one part per request.
    """

    size_bytes: int = Field(default=0, ge=0, description="How large the file is, as the browser measured it")


class UploadBeginResponse(BaseModel):
    """
    What a browser needs to start sending the parts of a file it has just opened an upload for.
    """

    model_config = ConfigDict(populate_by_name=True)

    upload_id: str = Field(description="Identifier of the opened upload, quoted on every further request")
    path: str = Field(description="Key the finished file will be stored under")
    part_size: int = Field(gt=0, description="How many bytes of the file one part carries")
    max_parts: int = Field(gt=0, description="Most parts one upload may be split into")


class UploadPart(BaseModel):
    """
    One part of an upload as the bucket recorded it, which finishing the upload is verified against.
    """

    model_config = ConfigDict(populate_by_name=True)

    number: int = Field(ge=1, description="One based position of the part inside the file")
    etag: str = Field(description="Checksum the bucket recorded for the part")
    size_bytes: int = Field(default=0, ge=0, description="How many bytes the part carries")


class UploadStatusResponse(BaseModel):
    """
    Which parts of an interrupted upload the bucket is already holding, so a browser sends only the rest.
    """

    model_config = ConfigDict(populate_by_name=True)

    upload_id: str = Field(description="Identifier of the opened upload")
    path: str = Field(description="Key the finished file will be stored under")
    parts: list[UploadPart] = Field(default_factory=list, description="Every part the bucket already holds")


class UploadCompleteRequest(UploadDescriptor):
    """
    The payload that joins the parts of a driven upload into the one stored file they describe.
    """

    path: str = Field(description="Key the file is being stored under, as the opening answer named it")
    parts: list[UploadPart] = Field(description="Every part of the file, which the bucket checks against its own")
