/**
 * The browser side store of the private table templates.
 *
 * A template that is not shared belongs to one person and to nobody else. The service has no per user
 * identity yet - every caller reaches it as the same anonymous account - so a private template written to
 * the document store would be handed straight back to everyone. Until identities exist, a private template
 * therefore never leaves the browser it was saved in, and only a shared one is sent to the service.
 */

import type { FieldScope } from '../models/common'
import type { TableTemplate, TemplateCreateRequest } from '../models/template'

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
 * Mint an identifier for a template that never leaves this browser.
 *
 * The obvious way to do this is `crypto.randomUUID`, and it is the wrong one twice over. It arrived in
 * Chrome 92, which is newer than the floor this client is built for; and it is offered only in a secure
 * context, so on a deployment reached as `http://<machine>:8080` from another desk - which is how this
 * system is actually opened - it is missing from the newest browser there is. Saving a private view threw
 * in both cases. It is used where it exists and worked out by hand where it does not, because the only thing
 * asked of this value is that two templates in one browser never collide.
 */
const newLocalId = (): string => {
  const source = globalThis.crypto
  if (source !== undefined && typeof source.randomUUID === 'function') {
    return source.randomUUID()
  }

  const random = Math.random().toString(36).slice(2, 10)

  return `${Date.now().toString(36)}-${random}`
}

/**
 * Save one private template in this browser, replacing an earlier template of the same name.
 */
const createLocalTemplate = (request: TemplateCreateRequest): TableTemplate => {
  const stored: TableTemplate = {
    ...request,
    id: `${LOCAL_ID_PREFIX}${newLocalId()}`,
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
