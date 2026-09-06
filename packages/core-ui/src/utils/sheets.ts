/**
 * The readers that turn a sheet shaped file - a delimited text or a workbook - into the rows a table renders.
 *
 * A sheet is not a text split on commas: a quoted field may hold the delimiter itself, a line break or a
 * doubled quote, and a reader that ignores that shifts every column that follows it. The rules below are the
 * ones of RFC 4180, which is what every tool that writes a csv follows.
 */

/** The rows of a sheet, together with whether the file carried more of them than were read. */
interface SheetContent {
  rows: string[][]
  truncated: boolean
}

const COMMA = ','
const TAB = '\t'
const SEMICOLON = ';'
const QUOTE = '"'
const CARRIAGE_RETURN = '\r'
const LINE_FEED = '\n'

/** The suffixes written with a tab rather than with a comma. */
const TAB_SUFFIXES: string[] = ['tsv', 'tab']

/** How far into the text the delimiter is looked for, so that a huge single line is not scanned twice. */
const DELIMITER_SAMPLE_LENGTH = 4096

/**
 * Work out which character separates the fields of a delimited file.
 *
 * The suffix decides it when it says so, and otherwise the first line does: a sheet exported by a machine
 * that writes decimal commas is separated by semicolons, and reading it with a comma yields one column.
 */
const delimiterOf = (suffix: string, text: string): string => {
  if (TAB_SUFFIXES.includes(suffix)) {
    return TAB
  }

  const sample = text.slice(0, DELIMITER_SAMPLE_LENGTH).split(LINE_FEED)[0] ?? ''
  const counts = [COMMA, SEMICOLON, TAB].map((candidate) => ({
    candidate,
    count: sample.split(candidate).length - 1,
  }))
  const best = counts.reduce((chosen, current) => (current.count > chosen.count ? current : chosen))

  return best.count > 0 ? best.candidate : COMMA
}

/**
 * Read a delimited text into its rows, stopping once enough of them are in hand.
 *
 * The reader stops at the limit rather than reading everything and slicing afterwards, because a telemetry
 * sheet can hold millions of lines and none of them past the limit is ever rendered.
 */
const parseDelimited = (text: string, delimiter: string, rowLimit: number): SheetContent => {
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let quoted = false

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index]

    if (quoted) {
      if (character !== QUOTE) {
        field += character
      } else if (text[index + 1] === QUOTE) {
        field += QUOTE
        index += 1
      } else {
        quoted = false
      }
      continue
    }

    if (character === QUOTE) {
      quoted = true
      continue
    }

    if (character === delimiter) {
      row.push(field)
      field = ''
      continue
    }

    if (character === LINE_FEED || character === CARRIAGE_RETURN) {
      if (character === CARRIAGE_RETURN && text[index + 1] === LINE_FEED) {
        index += 1
      }
      row.push(field)
      rows.push(row)
      field = ''
      row = []
      if (rows.length >= rowLimit) {
        return { rows, truncated: index + 1 < text.length }
      }
      continue
    }

    field += character
  }

  /* A file that does not end in a line break still ends in a row, while one that does must not gain an empty one. */
  if (field.length > 0 || row.length > 0) {
    row.push(field)
    rows.push(row)
  }

  return { rows, truncated: false }
}

/**
 * Read the first sheet of a workbook into its rows.
 *
 * The library that understands the workbook formats is several hundred kilobytes, and most files opened in
 * the viewer are not workbooks, so it is pulled in only once one is actually opened.
 */
const readWorkbook = async (buffer: ArrayBuffer, rowLimit: number): Promise<SheetContent> => {
  const xlsx = await import('xlsx')
  const workbook = xlsx.read(new Uint8Array(buffer), { type: 'array' })
  const sheetName = workbook.SheetNames[0]
  const sheet = sheetName === undefined ? undefined : workbook.Sheets[sheetName]
  const reference = sheet?.['!ref']
  if (sheet === undefined || reference === undefined) {
    return { rows: [], truncated: false }
  }

  /* Only the rows that are rendered are converted, so a sheet of a million rows costs the handful that show. */
  const range = xlsx.utils.decode_range(reference)
  const lastRow = Math.min(range.e.r, range.s.r + rowLimit - 1)
  const cells = xlsx.utils.sheet_to_json<unknown[]>(sheet, {
    header: 1,
    raw: false,
    defval: '',
    blankrows: false,
    range: { s: range.s, e: { r: lastRow, c: range.e.c } },
  })

  return {
    rows: cells.map((row) => row.map((cell) => (cell === null || cell === undefined ? '' : String(cell)))),
    truncated: range.e.r > lastRow,
  }
}

export type { SheetContent }
export { delimiterOf, parseDelimited, readWorkbook }
