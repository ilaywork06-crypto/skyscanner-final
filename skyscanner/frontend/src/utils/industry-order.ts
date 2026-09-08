/**
 * The browser side store of the order the industry tabs stand in.
 *
 * Which industry a person works in every day is theirs alone, and the service has no per user identity yet -
 * every caller reaches it as the same anonymous account - so an order written to the document store would be
 * handed straight back to everyone. Until identities exist, the order therefore stays in the browser it was
 * arranged in, exactly as the private table templates do.
 */

import type { Industry } from '@/models/industry'

const STORAGE_KEY = 'skyscanner.industry-tabs.order'

/**
 * Read the arranged order of this browser, tolerating a storage that was cleared or corrupted.
 */
const readOrder = (): string[] => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const parsed: unknown = raw === null ? [] : JSON.parse(raw)

    return Array.isArray(parsed) ? parsed.filter((key): key is string => typeof key === 'string') : []
  } catch {
    return []
  }
}

/**
 * Keep the arranged order in this browser, ignoring a storage that refuses to be written to.
 */
const writeOrder = (keys: string[]): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(keys))
  } catch {
    /* A full or disabled storage costs the user the arrangement, never the tab they were pressing. */
  }
}

/**
 * Put the industries in the order this browser arranged them in.
 *
 * The stored order is a preference rather than a record: an industry that was declared after the arrangement
 * was made is not in it, and one that was removed since still is. Anything the order does not name therefore
 * follows behind in the order the service handed it over, and anything it names that no longer exists is
 * simply passed over, so the tabs never lose an industry to a stale preference.
 *
 * The All tab is not part of this at all. It is not an industry, it is the absence of a choice of one, and
 * the place a reader looks first, so it is rendered ahead of the arrangement rather than inside it.
 */
const orderIndustries = (industries: Industry[], order: string[]): Industry[] => {
  const byKey = new Map(industries.map((industry) => [industry.key, industry]))
  const arranged = order
    .map((key) => byKey.get(key))
    .filter((industry): industry is Industry => industry !== undefined)
  const placed = new Set(arranged.map((industry) => industry.key))

  return [...arranged, ...industries.filter((industry) => !placed.has(industry.key))]
}

/**
 * Move one industry to where it was dropped, and answer with the order that follows from it.
 */
const moveIndustry = (keys: string[], from: number, to: number): string[] => {
  if (from === to || from < 0 || to < 0 || from >= keys.length || to >= keys.length) {
    return keys
  }

  const moved = [...keys]
  const [carried] = moved.splice(from, 1)
  moved.splice(to, 0, carried)

  return moved
}

export { STORAGE_KEY, moveIndustry, orderIndustries, readOrder, writeOrder }
