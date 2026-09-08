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
  UploadPart,
  UploadSession,
  UploadStatus,
} from '@/models/storage'
import { API_BASE_URL, UPLOAD_TIMEOUT_MS, client } from '@/requests/client'
import { downloadBlob, openLink } from '@truth-platform/core-ui'

const STORAGE_PATH = '/storage/artifacts'

/** What the service answers a window of a file with, as opposed to the whole of it. */
const PARTIAL_CONTENT = 206

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

/*
 * Past this a file is written by the browser itself rather than handed over in one request.
 *
 * The request per file shape is the right one almost always: one round trip, one answer, nothing to keep
 * track of. It is only wrong when the file is large enough that finishing the request stops being likely -
 * a connection that drops thirty gigabytes into a forty gigabyte upload costs all thirty, and there is
 * nothing in the shape of that request that could ever have made it cost less. Past this size the browser
 * opens an upload, writes it part by part, retries the parts that fail one at a time, and picks a wait that
 * was interrupted back up from whatever landed.
 */
const DRIVEN_UPLOAD_BYTES = 64 * 1024 * 1024

/** How many parts of one driven upload travel at the same time. */
const PART_CONCURRENCY = 4

/** How many times one part is tried again before the whole upload is given up on. */
const PART_ATTEMPTS = 4

/** How long the wait before retrying a part is, doubling each time so a struggling link is not hammered. */
const RETRY_BACKOFF_MS = 500

/** Where the open uploads of this browser are remembered, so a wait survives the page being reloaded. */
const SESSION_STORE_KEY = 'skyscanner.uploads.open'

/** How long an interrupted upload is worth coming back to, after which the bucket has likely swept it. */
const SESSION_LIFETIME_MS = 24 * 60 * 60 * 1000

/**
 * An upload that was opened and not finished, kept so that picking the same file again resumes it.
 *
 * The parts themselves are not remembered here. The bucket is the only account of what actually landed, so
 * resuming asks it rather than trusting a note this side of the wire that a failed request may have been
 * written after.
 */
interface OpenUpload {
  uploadId: string
  path: string
  partSize: number
  /** What the file has to look like for this to be the same file: its name, its size and when it changed. */
  fingerprint: string
  openedAt: number
}

/** What a file is recognised by across a reload, which is as much as a browser will say about one. */
const fingerprintOf = (file: File, options: UploadOptions): string =>
  [file.name, file.size, file.lastModified, options.ownerKind, options.ownerId ?? '', options.folder ?? ''].join('|')

/**
 * Read the uploads this browser left open, dropping the ones too old to still be there.
 */
const readOpenUploads = (): OpenUpload[] => {
  try {
    const stored: unknown = JSON.parse(window.localStorage.getItem(SESSION_STORE_KEY) ?? '[]')
    if (!Array.isArray(stored)) {
      return []
    }
    const fresh = Date.now() - SESSION_LIFETIME_MS

    return (stored as OpenUpload[]).filter((entry) => entry.openedAt > fresh)
  } catch {
    /* A store that cannot be read is a store with nothing worth resuming in it. */
    return []
  }
}

/**
 * Write the uploads this browser is holding open back, which is what a reload reads on the way back in.
 */
const writeOpenUploads = (uploads: OpenUpload[]): void => {
  try {
    window.localStorage.setItem(SESSION_STORE_KEY, JSON.stringify(uploads))
  } catch {
    /* A browser that refuses the store still uploads; it just cannot resume across a reload. */
  }
}

/** Remember an upload as open, replacing whatever was remembered for the same file. */
const rememberUpload = (upload: OpenUpload): void => {
  writeOpenUploads([...readOpenUploads().filter((entry) => entry.fingerprint !== upload.fingerprint), upload])
}

/** Forget an upload, which is what finishing one or giving it up amounts to. */
const forgetUpload = (fingerprint: string): void => {
  writeOpenUploads(readOpenUploads().filter((entry) => entry.fingerprint !== fingerprint))
}

/** The descriptor both ends of a driven upload carry, which is everything about a file that is not its bytes. */
const descriptorOf = (file: File, options: UploadOptions) => ({
  file_name: file.name,
  content_type: file.type.length > 0 ? file.type : 'application/octet-stream',
  owner_kind: options.ownerKind,
  owner_id: options.ownerId,
  kind: options.kind,
  folder: options.folder,
  descriptor: options.descriptor,
})

/** Wait a moment before trying a part again, so a link that is struggling is given room to recover. */
const pause = (milliseconds: number): Promise<void> =>
  new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds)
  })

/**
 * Open an upload for one file, resuming the one this browser left open for it when there is one.
 *
 * Resuming is confirmed against the bucket rather than assumed: an upload the bucket has swept, finished or
 * never heard of answers the status read with a failure, and a fresh upload is opened instead. That check is
 * what stops a stale note in this browser from turning into a file that can never be uploaded again.
 */
const openUpload = async (file: File, options: UploadOptions): Promise<{
  session: UploadSession
  landed: Map<number, UploadPart>
  fingerprint: string
}> => {
  const fingerprint = fingerprintOf(file, options)
  const remembered = readOpenUploads().find((entry) => entry.fingerprint === fingerprint)

  if (remembered !== undefined) {
    try {
      const status = await client.get<UploadStatus>(`${STORAGE_PATH}/uploads/${remembered.uploadId}`, {
        params: { path: remembered.path },
      })

      return {
        session: {
          upload_id: remembered.uploadId,
          path: remembered.path,
          part_size: remembered.partSize,
          max_parts: MOST_PARTS,
        },
        landed: new Map(status.data.parts.map((part) => [part.number, part])),
        fingerprint,
      }
    } catch {
      forgetUpload(fingerprint)
    }
  }

  const opened = await client.post<UploadSession>(`${STORAGE_PATH}/uploads`, {
    ...descriptorOf(file, options),
    size_bytes: file.size,
  })
  rememberUpload({
    uploadId: opened.data.upload_id,
    path: opened.data.path,
    partSize: opened.data.part_size,
    fingerprint,
    openedAt: Date.now(),
  })

  return { session: opened.data, landed: new Map(), fingerprint }
}

/**
 * Work out how large one part has to be for the file to fit inside the amount of parts allowed.
 *
 * The service names a part size that suits the bucket, and the protocol caps how many parts one upload may
 * be split into. A file large enough to need more parts than that is given larger ones instead of being
 * refused, which is the difference between a ceiling on the size of a file and no ceiling at all.
 */
const partSizeFor = (size: number, session: UploadSession): number => {
  const allowed = Math.ceil(size / Math.max(session.max_parts, 1))

  return Math.max(session.part_size, allowed)
}

/**
 * Write one part, trying again when the wire rather than the bucket is what refused it.
 */
const writePart = async (
  session: UploadSession,
  number: number,
  chunk: Blob,
): Promise<UploadPart> => {
  let failure: unknown = null

  for (let attempt = 0; attempt < PART_ATTEMPTS; attempt += 1) {
    try {
      const written = await client.put<UploadPart>(
        `${STORAGE_PATH}/uploads/${session.upload_id}/parts/${number}`,
        chunk,
        {
          params: { path: session.path },
          headers: { 'Content-Type': 'application/octet-stream' },
          timeout: UPLOAD_TIMEOUT_MS,
        },
      )

      return written.data
    } catch (error) {
      failure = error
      if (attempt < PART_ATTEMPTS - 1) {
        await pause(RETRY_BACKOFF_MS * 2 ** attempt)
      }
    }
  }

  throw failure instanceof Error ? failure : new Error(`Part ${number} of the upload could not be written`)
}

/**
 * Write one large file by driving the upload from here, part by part.
 *
 * What makes this survivable is that no single request carries very much of the file: a part that fails is
 * a part that is written again, and an upload that is interrupted altogether is picked back up from what the
 * bucket already holds rather than from the beginning.
 */
const uploadDriven = async (
  file: File,
  options: UploadOptions,
  report: (bytes: number) => void,
): Promise<Artifact> => {
  const { session, landed, fingerprint } = await openUpload(file, options)
  const partSize = partSizeFor(file.size, session)
  const count = Math.max(Math.ceil(file.size / partSize), 1)

  const parts: UploadPart[] = []
  landed.forEach((part) => {
    parts.push(part)
    report(part.size_bytes)
  })

  let next = 1

  /**
   * Take the next part nobody has started yet, skipping the ones a previous attempt already landed.
   */
  const worker = async (): Promise<void> => {
    for (;;) {
      const number = next
      next += 1
      if (number > count) {
        return
      }
      if (landed.has(number)) {
        continue
      }

      const from = (number - 1) * partSize
      const chunk = file.slice(from, Math.min(from + partSize, file.size))
      const written = await writePart(session, number, chunk)
      parts.push(written)
      report(chunk.size)
    }
  }

  try {
    await Promise.all(Array.from({ length: Math.min(PART_CONCURRENCY, count) }, () => worker()))

    const finished = await client.post<Artifact>(
      `${STORAGE_PATH}/uploads/${session.upload_id}/complete`,
      { ...descriptorOf(file, options), path: session.path, parts },
      { timeout: UPLOAD_TIMEOUT_MS },
    )
    forgetUpload(fingerprint)

    return finished.data
  } catch (error) {
    /*
     * The upload is left open rather than given up on, because the whole point of writing it this way is
     * that the next attempt continues it. It is swept from this browser once it is too old to still be there.
     */
    throw error instanceof Error ? error : new Error('The upload could not be completed')
  }
}

/** How many very large files are written at once. Each of them already has several parts in the air. */
const DRIVEN_CONCURRENCY = 2

/** The ceiling the protocol puts on how many parts one upload may be split into. */
const MOST_PARTS = 10000

/** One picked file together with where it sat in the pick, so the records come home in that order. */
interface PickedFile {
  file: File
  index: number
}

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
 * Split the ordinary files of a pick into the requests they travel in.
 *
 * A file past the batching size is given a request of its own, because a batch takes as long as the largest
 * file in it, and everything else is grouped so that a pick of two hundred small files does not become two
 * hundred round trips. Where each file sat in the pick travels with it, which is what lets the answers of
 * requests that landed in any order be put back into the order the files were picked in.
 */
const toUploadBatches = (picked: PickedFile[]): PickedFile[][] => {
  const batches: PickedFile[][] = []
  let current: PickedFile[] = []

  picked.forEach((entry) => {
    if (entry.file.size >= LARGE_FILE_BYTES) {
      if (current.length > 0) {
        batches.push(current)
        current = []
      }
      batches.push([entry])

      return
    }

    current.push(entry)
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
const uploadBatch = async (
  batch: PickedFile[],
  options: UploadOptions,
  report: (bytes: number) => void,
): Promise<Artifact[]> => {
  const payload = new FormData()
  batch.forEach((entry) => payload.append('files', entry.file))
  payload.append('owner_kind', options.ownerKind)
  payload.append('kind', options.kind)
  payload.append('descriptor', options.descriptor)
  if (options.ownerId !== null) {
    payload.append('owner_id', options.ownerId)
  }
  if (options.folder !== null) {
    payload.append('folder', options.folder)
  }

  /* The bar follows the bytes that actually left, and each report is the movement since the last one. */
  let announced = 0

  const response = await client.post<ArtifactUploadResponse>(STORAGE_PATH, payload, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: UPLOAD_TIMEOUT_MS,
    onUploadProgress: (event) => {
      report(event.loaded - announced)
      announced = event.loaded
    },
  })

  return response.data.artifacts
}

/**
 * Run a set of tasks with only so many of them in the air at once.
 */
const withConcurrency = async (tasks: (() => Promise<void>)[], limit: number): Promise<void> => {
  let next = 0

  const worker = async (): Promise<void> => {
    for (;;) {
      const index = next
      next += 1
      if (index >= tasks.length) {
        return
      }
      await tasks[index]()
    }
  }

  await Promise.all(Array.from({ length: Math.min(limit, tasks.length) }, () => worker()))
}

/**
 * Write every picked file into the bucket and hand back the artifact records the inventory stores.
 *
 * A pick is written along two roads at once. The ordinary files travel as several requests running side by
 * side, so a hundred of them take about as long as the slowest few rather than as long as all hundred added
 * together. A file large enough that finishing a single request stops being likely is written by the browser
 * itself instead, part by part, and a wait that is interrupted is picked back up rather than started again.
 *
 * A file that fails takes the whole pick down with it, exactly as the single request did: the caller is left
 * to pick again rather than with half its files attached and no way of telling which half.
 */
const uploadArtifacts = async (files: File[], options: UploadOptions): Promise<Artifact[]> => {
  if (files.length === 0) {
    return []
  }

  const picked: PickedFile[] = files.map((file, index) => ({ file, index }))
  const total = picked.reduce((sum, entry) => sum + entry.file.size, 0)
  const answers = new Array<Artifact | null>(files.length).fill(null)
  let written = 0

  /** Announce how far along the whole pick is, whatever road the bytes that just landed travelled. */
  const reporter = (name: string) => (bytes: number) => {
    written += bytes
    options.onProgress?.({ written: Math.min(written, total), total, name })
  }

  const driven = picked.filter((entry) => entry.file.size >= DRIVEN_UPLOAD_BYTES)
  const batches = toUploadBatches(picked.filter((entry) => entry.file.size < DRIVEN_UPLOAD_BYTES))

  await Promise.all([
    withConcurrency(
      driven.map((entry) => async () => {
        answers[entry.index] = await uploadDriven(entry.file, options, reporter(entry.file.name))
      }),
      DRIVEN_CONCURRENCY,
    ),
    withConcurrency(
      batches.map((batch) => async () => {
        const stored = await uploadBatch(batch, options, reporter(batch[0].file.name))
        batch.forEach((entry, at) => {
          answers[entry.index] = stored[at] ?? null
        })
      }),
      UPLOAD_CONCURRENCY,
    ),
  ])

  /* The records come home in the order the files were picked in, whatever order the requests landed in. */
  return answers.filter((artifact): artifact is Artifact => artifact !== null)
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
 * Read one window of a stored file, so that a very large one can be looked at without being pulled over.
 *
 * The service answers a window with the partial content the protocol asks for; a service or a proxy that
 * ignores the ask answers the whole file instead, which for the files this exists for is exactly what must
 * not happen. The answer is therefore checked rather than assumed, and a window that came back as the whole
 * file is reported as one the viewer cannot honour.
 *
 * :param path: Key the file is stored under.
 * :param start: First byte that is wanted, counted from zero.
 * :param end: Last byte that is wanted, included.
 * :return: The bytes of the window, decoded as text.
 */
const readArtifactWindow = async (path: string, start: number, end: number): Promise<string> => {
  const response = await fetch(buildContentUrl(path, true), {
    headers: { Range: `bytes=${start}-${end}` },
  })
  if (!response.ok) {
    throw new Error('The file could not be read')
  }
  if (response.status !== PARTIAL_CONTENT) {
    throw new Error('The service answered with the whole file rather than the part that was asked for')
  }

  return response.text()
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
  readArtifactWindow,
  deleteArtifact,
  downloadArtifact,
  downloadEntityArchive,
  readDownloadLink,
  toArchiveSources,
  uploadArtifacts,
}
