/**
 * Every call to the storage service - uploading files, linking to them and streaming them back.
 */

import type { Artifact } from '@/models/common'
import type { EntityResponse } from '@/models/entity'
import type {
  ArchiveEntry,
  ArchiveManifest,
  ArtifactUploadResponse,
  DownloadLink,
  EntityArchiveSource,
  UploadOptions,
} from '@/models/storage'
import { API_BASE_URL, UPLOAD_TIMEOUT_MS, client } from '@/requests/client'
import { downloadBlob, openLink } from '@/utils/download'

const STORAGE_PATH = '/storage/artifacts'

/** Packing the telemetry of a whole event takes far longer than an ordinary request. */
const ARCHIVE_TIMEOUT_MS = 600000

/** Anything an unpacking tool would read as a separator or refuse outright inside an entry. */
const UNSAFE_PATH_CHARACTERS = /[^A-Za-z0-9._-]+/g

/** The name a segment falls back to once nothing usable is left of it. */
const FALLBACK_SEGMENT = 'unnamed'

/** The stamp every archive carries, which is what tells two downloads of the same entity apart. */
const STAMP_PATTERN = /[-:]|\.\d+(?=Z$)/g

/** The folders one entity is laid out in, named the way the events service names them in its own archives. */
const ROLE_FOLDERS: { role: 'rawFiles' | 'parsedFiles' | 'parsedAdditionalFiles'; folder: string }[] = [
  { role: 'rawFiles', folder: 'raw_files' },
  { role: 'parsedFiles', folder: 'parsed_files' },
  { role: 'parsedAdditionalFiles', folder: 'parsed_additional_files' },
]

/** What an archive of several entities is named after, since it cannot be named after one of them. */
const MANY_ENTITIES_NAME = 'entities'

/**
 * Write every picked file into the bucket and hand back the artifact records the inventory stores.
 */
const uploadArtifacts = async (files: File[], options: UploadOptions): Promise<Artifact[]> => {
  if (files.length === 0) {
    return []
  }

  const payload = new FormData()
  files.forEach((file) => payload.append('files', file))
  payload.append('owner_kind', options.ownerKind)
  payload.append('kind', options.kind)
  payload.append('descriptor', options.descriptor)
  if (options.ownerId !== null) {
    payload.append('owner_id', options.ownerId)
  }
  if (options.folder !== null) {
    payload.append('folder', options.folder)
  }

  const response = await client.post<ArtifactUploadResponse>(STORAGE_PATH, payload, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: UPLOAD_TIMEOUT_MS,
  })

  return response.data.artifacts
}

/**
 * Mint a temporary link that lets a caller read one stored file straight from the bucket.
 *
 * The link carries the address the services reach the bucket under, which is not necessarily the address a
 * browser can reach. Use it for server side consumers and use downloadArtifact for the web client.
 */
const readDownloadLink = async (path: string, name: string): Promise<DownloadLink> => {
  const response = await client.get<DownloadLink>(`${STORAGE_PATH}/link`, { params: { path, name } })

  return response.data
}

/**
 * Build the address that streams one stored file through the service, used by the preview pane.
 */
const buildContentUrl = (path: string, inline: boolean): string => {
  const parameters = new URLSearchParams({ path, inline: String(inline) })

  return `${API_BASE_URL}${STORAGE_PATH}/content?${parameters.toString()}`
}

/**
 * Hand one stored file to the browser as a download, streamed through the service so that the bucket stays private.
 */
const downloadArtifact = (artifact: Artifact) => {
  openLink(buildContentUrl(artifact.path, false))
}

/**
 * Remove one stored file from the bucket.
 */
const deleteArtifact = async (path: string): Promise<void> => {
  await client.delete(STORAGE_PATH, { params: { path } })
}

/**
 * Turn a name into one that every unpacking tool accepts as a single path segment.
 *
 * An entity is named by whoever uploaded it, which means it may carry a slash, a colon or an alphabet the
 * archive format never promised to keep - and any of those either breaks the entry or silently moves it.
 */
const safeSegment = (value: string): string => {
  const cleaned = value.replace(UNSAFE_PATH_CHARACTERS, '_').replace(/^[._]+|[._]+$/g, '')

  return cleaned.length > 0 ? cleaned : FALLBACK_SEGMENT
}

/**
 * Place one set of files inside a folder of the archive, keeping their names apart when they collide.
 *
 * Two files of the same entity may well be called the same thing, and an archive that holds the same entry
 * twice loses one of them, so every repeat is numbered the way the events service numbers its own.
 */
const entriesFor = (files: Artifact[], folder: string): ArchiveEntry[] => {
  const seen = new Map<string, number>()

  return files.map((artifact) => {
    const name = safeSegment(artifact.name)
    const taken = seen.get(name) ?? 0
    seen.set(name, taken + 1)

    return { path: artifact.path, entry: `${folder}/${taken === 0 ? name : `${taken}-${name}`}` }
  })
}

/**
 * Work out where the files of the picked entities sit inside an archive and what that archive is called.
 *
 * The layout is the one the events service builds for a whole event, minus the event folder: a folder per
 * entity type, a folder per entity inside it and one folder per role its files play. A reader who unpacks a
 * download of two entities therefore finds the same structure as one who unpacked the whole event.
 */
const buildEntityManifest = (
  eventNumber: string,
  eventName: string,
  sources: EntityArchiveSource[],
): ArchiveManifest => {
  const entries: ArchiveEntry[] = []
  const seen = new Map<string, number>()

  sources.forEach((source) => {
    const base = `${safeSegment(source.typeName)}/${safeSegment(source.name)}`
    const taken = seen.get(base) ?? 0
    seen.set(base, taken + 1)
    const folder = taken === 0 ? base : `${base}-${taken}`
    ROLE_FOLDERS.forEach((role) => {
      entries.push(...entriesFor(source[role.role], `${folder}/${role.folder}`))
    })
  })

  const stem = sources.length === 1 ? sources[0].name : MANY_ENTITIES_NAME
  const stamp = new Date().toISOString().replace(STAMP_PATTERN, '')

  return {
    entries,
    archive_name: `${safeSegment(`event-${eventNumber}-${eventName}-${stem}`)}-${stamp}.zip`,
  }
}

/**
 * Describe the entities an archive is built from, which is the four values the manifest is laid out by.
 */
const toArchiveSources = (entities: EntityResponse[]): EntityArchiveSource[] =>
  entities.map((entity) => ({
    name: entity.name,
    typeName: entity.object_type.name,
    rawFiles: entity.raw_files,
    parsedFiles: entity.parsed_files,
    parsedAdditionalFiles: entity.parsed_additional_files,
  }))

/**
 * Download the stored files of one or more entities as a single archive.
 *
 * The caller already holds the entities it is downloading, so the manifest is built here rather than asked
 * for: the storage service only reads the bucket and zips what the manifest names.
 */
const downloadEntityArchive = async (
  eventNumber: string,
  eventName: string,
  sources: EntityArchiveSource[],
): Promise<void> => {
  const manifest = buildEntityManifest(eventNumber, eventName, sources)
  if (manifest.entries.length === 0) {
    throw new Error('The picked entities carry no files to download')
  }

  const archive = await client.post<Blob>(`${STORAGE_PATH}/archive`, manifest, {
    responseType: 'blob',
    timeout: ARCHIVE_TIMEOUT_MS,
  })
  downloadBlob(archive.data, manifest.archive_name)
}

export {
  buildContentUrl,
  deleteArtifact,
  downloadArtifact,
  downloadEntityArchive,
  readDownloadLink,
  toArchiveSources,
  uploadArtifacts,
}
