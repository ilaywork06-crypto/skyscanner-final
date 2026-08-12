/**
 * The search, filter and sort payloads the toolbar and the grid send to the backend.
 */

import type { JsonValue, ParseState } from './common'

type SortDirection = 'asc' | 'desc'

type FilterOperator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'starts_with'
  | 'ends_with'
  | 'greater_than'
  | 'greater_or_equal'
  | 'less_than'
  | 'less_or_equal'
  | 'in'
  | 'not_in'
  | 'between'
  | 'is_empty'
  | 'is_not_empty'

interface FilterCondition {
  key: string
  operator: FilterOperator
  value: JsonValue
  values: JsonValue[]
}

interface SortSpecification {
  key: string
  direction: SortDirection
}

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

export type {
  EventExportRequest,
  FilterCondition,
  FilterOperator,
  GridRowsRequest,
  SearchQuery,
  SortDirection,
  SortSpecification,
}
