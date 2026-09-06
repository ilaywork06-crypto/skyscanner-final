/**
 * Writing the rows on screen out as a spreadsheet.
 *
 * The API has no export endpoint, so the file is built in the browser out of the very rows the table is
 * showing - which means an export carries the search, the filters and the ordering the reader was looking at,
 * and carries exactly the columns they had on screen.
 */

import type { GeneratedColumn, GridRow, JsonValue } from '@truth-platform/core-ui'
import { downloadBlob } from '@truth-platform/core-ui'
import { utils, write } from 'xlsx'

/** What the sheet inside the workbook is called. */
const SHEET_NAME = 'Assumptions'

/** The stem every export is named after, before the moment it was taken. */
const FILE_PREFIX = 'truth-assumptions'

/** The column that holds the chevron carries nothing worth exporting. */
const SKIPPED_COLUMNS: string[] = ['expand']

/**
 * Render one value as the single cell a spreadsheet holds it in.
 */
const toCell = (value: JsonValue): string | number | boolean => {
  if (value === null) {
    return ''
  }

  if (Array.isArray(value)) {
    return value.map((item) => String(toCell(item))).join(', ')
  }

  if (typeof value === 'object') {
    return JSON.stringify(value)
  }

  return value
}

/**
 * Read the value one column addresses out of one row, following the path the column was generated with.
 */
const readColumn = (row: GridRow, column: GeneratedColumn): JsonValue => {
  const parts = column.field.split('.')
  let current: JsonValue = row as JsonValue

  for (const part of parts) {
    if (current === null || typeof current !== 'object' || Array.isArray(current)) {
      return null
    }
    current = current[part] ?? null
  }

  return current
}

/**
 * Build the name an export is saved under, stamped so that two of them never overwrite one another.
 */
const buildFileName = (): string => {
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z')

  return `${FILE_PREFIX}-${stamp}.xlsx`
}

/**
 * Write the given rows out as a spreadsheet and hand it to the browser as a download.
 */
const exportRows = (rows: GridRow[], columns: GeneratedColumn[]): void => {
  const exported = columns.filter((column) => !SKIPPED_COLUMNS.includes(column.colId))
  const table = rows.map((row) => {
    const line: Record<string, string | number | boolean> = {}
    exported.forEach((column) => {
      line[column.headerName.length > 0 ? column.headerName : column.colId] = toCell(readColumn(row, column))
    })

    return line
  })

  const sheet = utils.json_to_sheet(table)
  const book = utils.book_new()
  utils.book_append_sheet(book, sheet, SHEET_NAME)

  const buffer: ArrayBuffer = write(book, { bookType: 'xlsx', type: 'array' })
  downloadBlob(
    new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }),
    buildFileName(),
  )
}

export { buildFileName, exportRows, readColumn, toCell }
