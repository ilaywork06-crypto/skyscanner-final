/**
 * Every call around the saved table templates and the export of the current view.
 */

import type { FieldScope } from '@/models/common'
import type { EventExportRequest } from '@/models/query'
import type { TableTemplate, TemplateCreateRequest } from '@/models/template'
import { client } from '@/requests/client'
import {
  createLocalTemplate,
  deleteLocalTemplate,
  isLocalTemplate,
  listLocalTemplates,
} from '@/utils/local-templates'

const TEMPLATES_PATH = '/templates'

/** Packing a hundred events worth of telemetry takes far longer than an ordinary request. */
const ARCHIVE_TIMEOUT_MS = 600000

/** The header a service offers a generated file under, exposed to the browser by the gateway. */
const CONTENT_DISPOSITION = 'content-disposition'

/** The file name inside that header, quoted or bare. */
const FILE_NAME_PATTERN = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i

/** The stem the events service names an export after, repeated here only for the answer that carries no name. */
const EXPORT_NAME_PREFIX = 'skyscanner-events'

/** A file a download already holds, together with the name it is offered to the browser under. */
interface DownloadedFile {
  blob: Blob
  name: string
}

/** The manifest the events service builds and the storage service turns into an archive. */
interface ArchiveManifest {
  entries: { path: string; entry: string }[]
  archive_name: string
}

/**
 * Read the templates the caller may load: the shared ones of the service and their own private ones.
 */
const listTemplates = async (scope: FieldScope, industry: string | null): Promise<TableTemplate[]> => {
  const response = await client.get<TableTemplate[]>(TEMPLATES_PATH, {
    params: { scope, industry: industry ?? undefined },
  })

  return [...response.data.filter((template) => template.shared), ...listLocalTemplates(scope, industry)]
}

/**
 * Save the current table layout under a name the caller chose.
 *
 * A shared template is sent to the service so that every user of the system sees it, while a private one
 * stays in the browser of the person who saved it.
 */
const createTemplate = async (request: TemplateCreateRequest): Promise<TableTemplate> => {
  if (!request.shared) {
    return createLocalTemplate(request)
  }

  const response = await client.post<TableTemplate>(TEMPLATES_PATH, request)

  return response.data
}

/**
 * Remove a template, from the browser or from the service depending on where it was saved.
 */
const deleteTemplate = async (templateId: string): Promise<void> => {
  if (isLocalTemplate(templateId)) {
    deleteLocalTemplate(templateId)

    return
  }

  await client.delete(`${TEMPLATES_PATH}/${templateId}`)
}

/**
 * Build the name an export is offered under when the answer carried no name of its own.
 *
 * It repeats the stamp the events service writes - the moment of the export in UTC, down to its seconds - so
 * that a browser which was not handed the header still saves the file under the name every other export uses.
 */
const buildFallbackName = (extension: string): string => {
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z')

  return `${EXPORT_NAME_PREFIX}-${stamp}.${extension}`
}

/**
 * Read the name a service offered its answer under, so a download keeps the stamp the backend put on it.
 */
const readOfferedName = (disposition: unknown, fallback: string): string => {
  if (typeof disposition !== 'string') {
    return fallback
  }

  const matched = FILE_NAME_PATTERN.exec(disposition)

  return matched === null ? fallback : decodeURIComponent(matched[1])
}

/**
 * Materialise the events of the current view, or the picked subset of it, in the format the user asked for.
 *
 * The name travels with the file: every export of the same view would otherwise arrive as the same file name
 * and quietly overwrite the one downloaded a minute earlier.
 */
const exportEvents = async (request: EventExportRequest, exportFormat: string): Promise<DownloadedFile> => {
  const response = await client.post<Blob>('/exports/events', request, {
    params: { export_format: exportFormat },
    responseType: 'blob',
  })

  return {
    blob: response.data,
    name: readOfferedName(response.headers[CONTENT_DISPOSITION], buildFallbackName(exportFormat)),
  }
}

/**
 * Download every file of the picked events as one archive, laid out in a folder per event.
 *
 * The events service works out the layout, because only it knows which event and which entity a file
 * belongs to, and the storage service builds the archive, because only it may read the bucket.
 */
const downloadEventFiles = async (request: EventExportRequest): Promise<DownloadedFile> => {
  const manifest = await client.post<ArchiveManifest>('/exports/events/files', request)
  if (manifest.data.entries.length === 0) {
    throw new Error('The picked events carry no files to download')
  }

  const archive = await client.post<Blob>('/storage/artifacts/archive', manifest.data, {
    responseType: 'blob',
    timeout: ARCHIVE_TIMEOUT_MS,
  })

  return { blob: archive.data, name: manifest.data.archive_name }
}

export type { DownloadedFile }
export { createTemplate, deleteTemplate, downloadEventFiles, exportEvents, listTemplates }
