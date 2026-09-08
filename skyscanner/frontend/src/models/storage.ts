/**
 * The payloads of the storage service - the result of an upload and the temporary links used to read files back.
 */

import type { Artifact, ArtifactKind } from './common'

interface ArtifactUploadResponse {
  artifacts: Artifact[]
}

interface DownloadLink {
  url: string
  name: string
  content_type: string
  expires_at: string
}

interface UploadOptions {
  ownerKind: string
  ownerId: string | null
  kind: ArtifactKind
  folder: string | null
  descriptor: string
  /** Told how far along the whole pick is, whenever a file or a part of one lands. */
  onProgress?: (progress: UploadProgress) => void
}

/** How much of a pick has been written, which is what a progress bar over a long upload reads. */
interface UploadProgress {
  /** Bytes of the pick the bucket has taken so far. */
  written: number
  /** Bytes the pick holds altogether. */
  total: number
  /** The file currently being written, for a pick that is more than one. */
  name: string
}

/** What the service answers when an upload the browser drives itself is opened. */
interface UploadSession {
  upload_id: string
  path: string
  part_size: number
  max_parts: number
}

/** One part of a driven upload as the bucket recorded it. */
interface UploadPart {
  number: number
  etag: string
  size_bytes: number
}

/** Which parts of an interrupted upload the bucket is already holding. */
interface UploadStatus {
  upload_id: string
  path: string
  parts: UploadPart[]
}

/** One stored file together with the path it takes inside a downloaded archive. */
interface ArchiveEntry {
  path: string
  entry: string
}

/** The manifest of an archive: which stored files it holds and how they are laid out inside it. */
interface ArchiveManifest {
  entries: ArchiveEntry[]
  archive_name: string
}

/**
 * One entity whose stored files are packed into an archive.
 *
 * The caller of an entity download already holds the flattened row of the entity, so the manifest is built
 * from these four values rather than from a second read of the entity.
 */
interface EntityArchiveSource {
  name: string
  typeName: string
  rawFiles: Artifact[]
  parsedFiles: Artifact[]
  parsedAdditionalFiles: Artifact[]
}

export type {
  ArchiveEntry,
  ArchiveManifest,
  ArtifactUploadResponse,
  DownloadLink,
  EntityArchiveSource,
  UploadOptions,
  UploadPart,
  UploadProgress,
  UploadSession,
  UploadStatus,
}
