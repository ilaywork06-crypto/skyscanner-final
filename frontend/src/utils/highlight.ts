/**
 * Splitting a cell value into the runs a free text search matched, so that the table can paint them.
 *
 * The answer is plain data rather than markup because every value that reaches here was typed by a user: the
 * renderers bind the segments with `v-for` and wrap the matched ones in `<mark>`, so a value that happens to
 * read like HTML stays text.
 *
 * What counts as a match is decided the same way the API decides it: the term is trimmed, matched without
 * regard to case, and matched as a substring anywhere in the value rather than as a word. A term the rows
 * were found by is therefore a term the cells of those rows can paint.
 */

import { truncate } from '@skyscanner/sky-ui'

interface HighlightSegment {
  text: string
  matched: boolean
}

/** A lowercased value alongside the run of the original that every position of it came from. */
interface LoweredValue {
  text: string
  starts: number[]
  ends: number[]
}

/** What a search over a string answers when the term does not occur again. */
const NOT_FOUND = -1

/** How much of the text before a match a windowed preview keeps, so that the match is read in its context. */
const PREVIEW_LEAD = 12

/** What a preview says on a side it was cut on. */
const ELLIPSIS = '…'

/** The shape a term is compared in, which is the shape the API compares it in as well. */
const normalise = (term: string): string => term.trim().toLowerCase()

/**
 * Answer whether a term occurs in a value at all, which is all a cell needs to know before it paints: a value
 * the term never occurs in is rendered exactly as it is rendered when nothing was searched for.
 */
const matchesTerm = (value: string, term: string): boolean => {
  const needle = normalise(term)

  return needle.length > 0 && value.toLowerCase().includes(needle)
}

/**
 * Lowercase a value while recording, for every position of the result, the run of the original it came from.
 *
 * Lowercasing is not always one character for one - a Turkish dotted capital becomes two - and past such a
 * character an offset into the lowercased form addresses a different place than it does in the original.
 * Cutting the original at the bounds of the characters a match covered is exact whatever the lengths did,
 * which is what lets a value like that be painted at all rather than left alone.
 */
const lowerWithBounds = (value: string): LoweredValue => {
  const starts: number[] = []
  const ends: number[] = []
  let text = ''
  let offset = 0

  for (const character of value) {
    const lowered = character.toLowerCase()
    for (let index = 0; index < lowered.length; index += 1) {
      starts.push(offset)
      ends.push(offset + character.length)
    }

    text += lowered
    offset += character.length
  }

  return { text, starts, ends }
}

/**
 * Split a value into its matched and unmatched runs of a term, case insensitively and at every occurrence.
 *
 * Nothing to paint answers with no segments at all - an empty term, an empty value, or a value the term never
 * occurs in - so that a table rendered without a search spends one scan per cell and every renderer keeps its
 * plain, unwrapped text. The scan walks each value once, so the cost stays proportional to what is on screen.
 */
const splitHighlights = (value: string, term: string): HighlightSegment[] => {
  const needle = normalise(term)
  if (needle.length === 0 || value.length === 0) {
    return []
  }

  /*
   * A value that lowercases to the same length - which is every value an inventory is made of - is cut at the
   * offsets of the match itself, and only the rare value that grows under lowercasing pays for the map.
   */
  const direct = value.toLowerCase()
  const lowered: LoweredValue | null = direct.length === value.length ? null : lowerWithBounds(value)
  const haystack = lowered === null ? direct : lowered.text

  const segments: HighlightSegment[] = []
  let cursor = 0
  let match = haystack.indexOf(needle)

  while (match !== NOT_FOUND) {
    const start = lowered === null ? match : lowered.starts[match]
    const end = lowered === null ? match + needle.length : lowered.ends[match + needle.length - 1]

    /* Once one character stands for several, two matches can land inside the one run the first already painted. */
    if (start >= cursor && end > start) {
      if (start > cursor) {
        segments.push({ text: value.slice(cursor, start), matched: false })
      }

      segments.push({ text: value.slice(start, end), matched: true })
      cursor = end
    }

    match = haystack.indexOf(needle, match + needle.length)
  }

  if (segments.length > 0 && cursor < value.length) {
    segments.push({ text: value.slice(cursor), matched: false })
  }

  return segments
}

/**
 * Choose the fragment of a long value a cell shows, so that what the search matched is inside it.
 *
 * A cell has room for a fixed number of characters, and cutting a value at that number hides everything past
 * it - including, on a value the search matched deep inside, the very run that put the row on screen. That is
 * a row which looks as if it matched nothing at all. The window therefore opens a few characters before the
 * first match rather than at the beginning of the value, and says on either side that it was cut.
 */
const previewAround = (value: string, term: string, limit: number): string => {
  const needle = normalise(term)
  if (needle.length === 0 || value.length <= limit) {
    return truncate(value, limit)
  }

  const match = value.toLowerCase().indexOf(needle)
  if (match === NOT_FOUND || match + needle.length <= limit - ELLIPSIS.length) {
    return truncate(value, limit)
  }

  const from = Math.max(0, match - PREVIEW_LEAD)
  const lead = from === 0 ? '' : ELLIPSIS

  return `${lead}${truncate(value.slice(from), limit - lead.length)}`
}

export type { HighlightSegment }
export { matchesTerm, previewAround, splitHighlights }
