/**
 * The display rules of a note, which is a list of items travelling the wire as one string.
 *
 * A note is typed item by item and serialised by joining the items with newline characters. The API model
 * stays a plain string, so that newline convention - and not a type - is the whole contract between the
 * editors that write a note and every surface that reads one back.
 */

const NOTE_SEPARATOR = '\n'

/** A cell has one line to spend, so the items are strung along it instead of being stacked. */
const PREVIEW_SEPARATOR = ' · '

const BULLET = '• '

/**
 * Split a stored note into its items, dropping the blank lines an editor leaves behind so that they never
 * read as empty bullets.
 */
const splitNotes = (value: string): string[] =>
  value
    .split(NOTE_SEPARATOR)
    .map((item) => item.trim())
    .filter((item) => item.length > 0)

/**
 * String the items of a note along the single line a cell has room for.
 */
const toNotePreview = (items: string[]): string => items.join(PREVIEW_SEPARATOR)

/**
 * Lay a list of items out as a bulleted list.
 *
 * The viewer renders the string it is handed with its line breaks preserved, so the bullets belong to the
 * text itself: that is what turns a note read out of one string back into the list it was typed as.
 */
const toBulletedText = (items: string[]): string => items.map((item) => `${BULLET}${item}`).join(NOTE_SEPARATOR)

export { splitNotes, toBulletedText, toNotePreview }
