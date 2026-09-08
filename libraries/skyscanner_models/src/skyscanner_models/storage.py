"""
Payloads of the storage service, covering uploads into the bucket and the temporary links used to read files back.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from skyscanner_models.common import Artifact

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
