/**
 * The filter and sort vocabulary shared by the toolbar, the column filters and the generated tables.
 */

import type { JsonValue } from './common'

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

export type { FilterCondition, FilterOperator, SortDirection, SortSpecification }
