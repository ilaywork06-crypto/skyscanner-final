/**
 * The search, filter and sort payloads the toolbar and the grid send to the backend.
 */

import type { JsonValue, ParseState } from './common'

export type { FilterCondition, FilterOperator, SortDirection, SortSpecification } from '@truth-platform/core-ui'

import type { FilterCondition, SortSpecification } from '@truth-platform/core-ui'

interface SearchQuery {
  search: string | null
  industry: string | null
  parse_state: ParseState
  filters: FilterCondition[]
  sort: SortSpecification[]
  page: number
  page_size: number
}

interface GridRowsRequest extends SearchQuery {
  columns: string[]
}

interface EventExportRequest extends GridRowsRequest {
  event_ids: string[]
}

/** Kept so that a caller which only needs the JSON vocabulary does not reach past this module for it. */
type QueryValue = JsonValue

export type { EventExportRequest, GridRowsRequest, QueryValue, SearchQuery }
