/**
 * The payloads of the generated tables, together with the row shape the inventory flattens its events into.
 */

export type {
  DetailGridRow,
  FilesCellValue,
  FilterOption,
  GeneratedColumn,
  GeneratedGridConfiguration,
  GridRow,
  GridRowsPage,
} from '@truth-platform/core-ui'

import type { GridRow } from '@truth-platform/core-ui'

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

export type { EventGridRow }
