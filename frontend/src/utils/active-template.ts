/**
 * The browser side memory of which saved view a user last had open.
 *
 * Loading a template was a decision that lasted until the page was reloaded, and a user who works out of one
 * view every day had to pick it again every morning. The choice is therefore remembered, and it is remembered
 * per table rather than once: the columns of one industry mean nothing to the next, so the view of each is
 * kept apart. It lives in the browser for the same reason the private templates do - the services have no per
 * user identity yet, so a choice written to the document store would be handed straight back to everybody.
 */

const STORAGE_KEY = 'skyscanner.templates.active'

/** Which table a remembered choice belongs to: one scope and one industry, or the view of all of them. */
const tableKey = (scope: string, industry: string | null): string => `${scope}:${industry ?? ''}`

/**
 * Read every remembered choice, tolerating a storage that was cleared or corrupted.
 */
const readAll = (): Record<string, string> => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const parsed: unknown = raw === null ? {} : JSON.parse(raw)

    return parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, string>)
      : {}
  } catch {
    return {}
  }
}

/**
 * Replace the remembered choices, ignoring a storage that refuses to be written to.
 */
const writeAll = (choices: Record<string, string>): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(choices))
  } catch {
    /* A full or disabled storage costs the user the memory of a choice, never the choice itself. */
  }
}

/**
 * Read which template one table was last left showing, or nothing when it was left on the default view.
 */
const readActiveTemplate = (scope: string, industry: string | null): string | null =>
  readAll()[tableKey(scope, industry)] ?? null

/**
 * Remember which template a table is showing, or forget the choice when it is back on the default view.
 */
const writeActiveTemplate = (scope: string, industry: string | null, templateId: string | null): void => {
  const choices = readAll()
  const key = tableKey(scope, industry)
  if (templateId === null) {
    delete choices[key]
  } else {
    choices[key] = templateId
  }

  writeAll(choices)
}

export { STORAGE_KEY, readActiveTemplate, writeActiveTemplate }
