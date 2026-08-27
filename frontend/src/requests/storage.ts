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

/*
 * What a single entry of an archive may never carry, whatever alphabet the rest of it is written in. A
 * separator would silently move the file into a folder of its own and a control character is refused outright
 * by the unpacking tools; everything else is kept, because the format has carried UTF-8 entry names for two
 * decades and an entity called in Hebrew reaches the reader called in Hebrew.
 */
/* eslint-disable-next-line no-control-regex -- a control character in a file name is exactly what is caught. */
const UNSAFE_PATH_CHARACTERS = /[\\/\u0000-\u001f\u007f]+/g

/** Runs of spaces are collapsed rather than kept, so that a name does not carry a gap of its own making. */
const REPEATED_WHITESPACE = /\s+/g

/** A dot or a space at either edge of a segment is dropped by some file systems, so neither is left there. */
const TRIMMED_EDGES = /^[.\s]+|[.\s]+$/g

/** The name a segment falls back to once nothing usable is left of it. */
const FALLBACK_SEGMENT = 'unnamed'

/*
 * How many files travel in one request, and how many of those requests are in the air at once.
 *
 * Every picked file used to go into a single request, so dropping four hundred files meant one upload that
 * had to survive from the first byte to the last - and a connection that dropped at the end of it lost all
 * four hundred. The pick is split into batches instead: each of them is its own request, several of them
 * travel at the same time, and the storage service writes the files inside each one concurrently as well.
 */
const UPLOAD_BATCH_SIZE = 8
const UPLOAD_CONCURRENCY = 3

/*
 * Past this a file travels on its own rather than sharing a request.
 *
 * A batch is only ever as quick as the largest file in it, so putting a two gigabyte recording in with seven
 * small ones holds all eight of them up. The storage service writes anything this size as a multipart upload,
 * which is exactly the file that deserves a request to itself.
 */
const LARGE_FILE_BYTES = 16 * 1024 * 1024

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
 * Split a pick into the requests it travels in.
 *
 * A large file is given a request of its own, because a batch takes as long as the largest file in it, and
 * everything else is grouped so that a pick of two hundred small files does not become two hundred round
 * trips. The order the files were picked in is kept, which is what lets the answers be joined back up.
 */
const toUploadBatches = (files: File[]): File[][] => {
  const batches: File[][] = []
  let current: File[] = []

  files.forEach((file) => {
    if (file.size >= LARGE_FILE_BYTES) {
      if (current.length > 0) {
        batches.push(current)
        current = []
      }
      batches.push([file])

      return
    }

    current.push(file)
    if (current.length >= UPLOAD_BATCH_SIZE) {
      batches.push(current)
      current = []
    }
  })

  if (current.length > 0) {
    batches.push(current)
  }

  return batches
}

/**
 * Write one batch of files into the bucket and hand back the artifact records of exactly those files.
 */
const uploadBatch = async (files: File[], options: UploadOptions): Promise<Artifact[]> => {
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
 * Write every picked file into the bucket and hand back the artifact records the inventory stores.
 *
 * The pick travels as several requests running side by side rather than as one long one, so a hundred files
 * take about as long as the slowest few of them rather than as long as all hundred added together, and a
 * large file gets a request of its own instead of holding a batch of small ones up behind it. A batch that
 * fails takes the whole upload down with it, exactly as the single request did: the caller is left to pick
 * again rather than with half its files attached and no way of telling which half.
 */
const uploadArtifacts = async (files: File[], options: UploadOptions): Promise<Artifact[]> => {
  if (files.length === 0) {
    return []
  }

  const batches = toUploadBatches(files)
  const answers: Artifact[][] = new Array<Artifact[]>(batches.length).fill([])
  let next = 0

  /**
   * Take the next batch that nobody has started yet, until there are none left.
   */
  const worker = async (): Promise<void> => {
    while (next < batches.length) {
      const index = next
      next += 1
      answers[index] = await uploadBatch(batches[index], options)
    }
  }

  const workers = Array.from({ length: Math.min(UPLOAD_CONCURRENCY, batches.length) }, () => worker())
  await Promise.all(workers)

  /* The records come home in the order the files were picked in, whatever order the batches landed in. */
  return answers.flat()
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
const buildContentUrl = (path: string, inline: boolean, name?: string): string => {
  const parameters = new URLSearchParams({ path, inline: String(inline) })
  if (name !== undefined && name.length > 0) {
    parameters.set('name', name)
  }

  return `${API_BASE_URL}${STORAGE_PATH}/content?${parameters.toString()}`
}

/**
 * Hand one stored file to the browser as a download, streamed through the service so that the bucket stays private.
 *
 * Every upload is written under a fresh identifier so that two of them can never overwrite one another, which
 * makes the key of a file a poor name to save it under. The name the file was picked with travels with the
 * request instead, so a download lands on the disk called what the user called it - in any alphabet.
 */
const downloadArtifact = (artifact: Artifact) => {
  openLink(buildContentUrl(artifact.path, false, artifact.name))
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
  const cleaned = value
    .normalize('NFC')
    .replace(UNSAFE_PATH_CHARACTERS, '_')
    .replace(REPEATED_WHITESPACE, ' ')
    .replace(TRIMMED_EDGES, '')

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
