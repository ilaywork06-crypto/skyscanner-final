/**
 * The payloads of the generated tables, re-exported from the grid library so that pages import them from one place.
 */

import type { GeneratedColumn, GeneratedGridConfiguration, GridRow, GridRowsPage } from '@skyscanner/ag-grid-ts'

import type { Artifact } from './common'

interface EventGridRow extends GridRow {
  event_id: number
  name: string
  industry: string
  platform: string
  status: string
  notes: string
  event_date: string | null
  created_at: string
}

interface DetailGridRow extends GridRow {
  parentId: string
}

interface FilesCellValue {
  files: Artifact[]
}

export type {
  DetailGridRow,
  EventGridRow,
  FilesCellValue,
  GeneratedColumn,
  GeneratedGridConfiguration,
  GridRow,
  GridRowsPage,
}
