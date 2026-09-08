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
}
