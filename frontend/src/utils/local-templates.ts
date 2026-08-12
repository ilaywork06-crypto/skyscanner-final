/**
 * The browser side store of the private table templates.
 *
 * A template that is not shared belongs to one person and to nobody else. The service has no per user
 * identity yet - every caller reaches it as the same anonymous account - so a private template written to
 * the document store would be handed straight back to everyone. Until identities exist, a private template
 * therefore never leaves the browser it was saved in, and only a shared one is sent to the service.
 */

import type { FieldScope } from '@/models/common'
import type { TableTemplate, TemplateCreateRequest } from '@/models/template'

const STORAGE_KEY = 'skyscanner.templates.private'
const LOCAL_ID_PREFIX = 'local:'
const LOCAL_OWNER = 'me'

/**
 * Decide whether an identifier belongs to a template kept in this browser rather than in the service.
 */
const isLocalTemplate = (templateId: string): boolean => templateId.startsWith(LOCAL_ID_PREFIX)

/**
 * Read every private template of this browser, tolerating a storage that was cleared or corrupted.
 */
const readAll = (): TableTemplate[] => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const parsed: unknown = raw === null ? [] : JSON.parse(raw)

    return Array.isArray(parsed) ? (parsed as TableTemplate[]) : []
  } catch {
    return []
  }
}

/**
 * Replace the stored private templates, ignoring a storage that refuses to be written to.
 */
const writeAll = (templates: TableTemplate[]): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(templates))
  } catch {
    /* A full or disabled storage costs the user the template, never the action they were performing. */
  }
}

/**
 * Read the private templates that belong to one table, which is one scope and one industry.
 */
const listLocalTemplates = (scope: FieldScope, industry: string | null): TableTemplate[] =>
  readAll()
    .filter((template) => template.scope === scope)
    .filter((template) => template.industry === null || template.industry === industry)
    .sort((left, right) => left.name.localeCompare(right.name))

/**
 * Save one private template in this browser, replacing an earlier template of the same name.
 */
const createLocalTemplate = (request: TemplateCreateRequest): TableTemplate => {
  const stored: TableTemplate = {
    ...request,
    id: `${LOCAL_ID_PREFIX}${crypto.randomUUID()}`,
    owner: LOCAL_OWNER,
    created_at: new Date().toISOString(),
    updated_at: null,
  }
  const others = readAll().filter(
    (template) => template.scope !== request.scope || template.name !== request.name,
  )
  writeAll([...others, stored])

  return stored
}

/**
 * Forget one private template of this browser.
 */
const deleteLocalTemplate = (templateId: string): void => {
  writeAll(readAll().filter((template) => template.id !== templateId))
}

export { createLocalTemplate, deleteLocalTemplate, isLocalTemplate, listLocalTemplates }
