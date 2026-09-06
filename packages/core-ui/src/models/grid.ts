/**
 * The payloads of the generated tables, re-exported from the grid library so that pages import them from one place.
 */

import type {
  FilterOption,
  GeneratedColumn,
  GeneratedGridConfiguration,
  GridRow,
  GridRowsPage,
} from '@truth-platform/ag-grid-ts'

import type { Artifact } from './common'

/** A row of a panel opened underneath the row it belongs to. */
interface DetailGridRow extends GridRow {
  parentId: string
}

/** What a file shaped cell is handed, which is the list of files rather than one of them. */
interface FilesCellValue {
  files: Artifact[]
}

export type {
  DetailGridRow,
  FilesCellValue,
  FilterOption,
  GeneratedColumn,
  GeneratedGridConfiguration,
  GridRow,
  GridRowsPage,
}
