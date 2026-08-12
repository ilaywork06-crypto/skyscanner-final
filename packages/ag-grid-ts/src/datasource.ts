/**
 * Translation between the AG Grid sort and filter models and the query payload the backend expects.
 */

import type { FilterModel, SortModelItem } from 'ag-grid-community'

import type { FilterCondition, FilterOperator, JsonValue, SortSpecification } from './types'

interface AgFilterLeaf {
  filterType?: string
  type?: string
  filter?: JsonValue
  filterTo?: JsonValue
  dateFrom?: string | null
  dateTo?: string | null
  values?: JsonValue[]
}

interface AgFilterGroup extends AgFilterLeaf {
  operator?: string
  conditions?: AgFilterLeaf[]
}

/** The kind of filter a rebuilt leaf declares, which has to match the filter component of its column. */
type AgFilterType = 'text' | 'number' | 'date'

const OPERATOR_BY_AG_TYPE: Record<string, FilterOperator> = {
  contains: 'contains',
  notContains: 'not_contains',
  equals: 'equals',
  notEqual: 'not_equals',
  startsWith: 'starts_with',
  endsWith: 'ends_with',
  blank: 'is_empty',
  notBlank: 'is_not_empty',
  empty: 'is_empty',
  greaterThan: 'greater_than',
  greaterThanOrEqual: 'greater_or_equal',
  lessThan: 'less_than',
  lessThanOrEqual: 'less_or_equal',
  inRange: 'between',
}

/*
 * The way back out of a stored condition. The list operators are missing on purpose: they are written by a set
 * filter, which the community build of the grid does not carry, so nothing can render them back.
 */
const AG_TYPE_BY_OPERATOR: Partial<Record<FilterOperator, string>> = {
  contains: 'contains',
  not_contains: 'notContains',
  equals: 'equals',
  not_equals: 'notEqual',
  starts_with: 'startsWith',
  ends_with: 'endsWith',
  is_empty: 'blank',
  is_not_empty: 'notBlank',
  greater_than: 'greaterThan',
  greater_or_equal: 'greaterThanOrEqual',
  less_than: 'lessThan',
  less_or_equal: 'lessThanOrEqual',
  between: 'inRange',
}

const AG_TYPE_BY_FILTER_COMPONENT: Record<string, AgFilterType> = {
  agTextColumnFilter: 'text',
  agNumberColumnFilter: 'number',
  agDateColumnFilter: 'date',
}

/** Every leaf of one column narrows the rows further, which is what joining them again has to preserve. */
const JOIN_OPERATOR = 'AND'

/** A date filter of the grid reads a timestamp down to its seconds and nothing beyond them. */
const DATE_TEXT_LENGTH = 19

/**
 * Read the value a filter leaf carries, preferring the date fields of a date filter.
 */
const readValue = (leaf: AgFilterLeaf): JsonValue => {
  if (leaf.dateFrom !== undefined && leaf.dateFrom !== null) {
    return leaf.dateFrom
  }

  return leaf.filter ?? null
}

/**
 * Read the second value of a range filter, preferring the date fields of a date filter.
 */
const readSecondValue = (leaf: AgFilterLeaf): JsonValue => {
  if (leaf.dateTo !== undefined && leaf.dateTo !== null) {
    return leaf.dateTo
  }

  return leaf.filterTo ?? null
}

/**
 * Turn one filter leaf of the grid into the condition the backend understands.
 */
const parseLeaf = (key: string, leaf: AgFilterLeaf): FilterCondition | null => {
  if (leaf.values !== undefined) {
    return { key, operator: 'in', value: null, values: leaf.values }
  }

  const operator = OPERATOR_BY_AG_TYPE[leaf.type ?? 'contains']
  if (operator === undefined) {
    return null
  }

  if (operator === 'between') {
    return { key, operator, value: null, values: [readValue(leaf), readSecondValue(leaf)] }
  }

  return { key, operator, value: readValue(leaf), values: [] }
}

/**
 * Turn the whole filter model of the grid into the list of conditions the backend understands.
 */
const buildFilterConditions = (model: FilterModel): FilterCondition[] => {
  const conditions: FilterCondition[] = []

  Object.entries(model).forEach(([key, rawEntry]) => {
    const entry = rawEntry as AgFilterGroup
    const leaves = entry.conditions !== undefined && entry.conditions.length > 0 ? entry.conditions : [entry]
    leaves.forEach((leaf) => {
      const condition = parseLeaf(key, leaf)
      if (condition !== null) {
        conditions.push(condition)
      }
    })
  })

  return conditions
}

/**
 * Read the filter component one column renders with, falling back to the shape of the stored value.
 *
 * A stored condition says nothing about the filter its column carries, so the caller hands over the filters
 * of the current table and the value decides for a column that is no longer part of it.
 */
const readFilterType = (condition: FilterCondition, component: string | undefined): AgFilterType => {
  const declared = component === undefined ? undefined : AG_TYPE_BY_FILTER_COMPONENT[component]
  if (declared !== undefined) {
    return declared
  }

  return typeof condition.value === 'number' ? 'number' : 'text'
}

/**
 * Render one stored value as the text an AG Grid date filter reads, which is a space separated timestamp.
 */
const toDateText = (value: JsonValue): string | null => {
  if (value === null || typeof value === 'object') {
    return null
  }

  return String(value).replace('T', ' ').slice(0, DATE_TEXT_LENGTH)
}

/**
 * Rebuild the leaf of one stored condition in the shape the filter component of its column reads.
 */
const buildLeaf = (condition: FilterCondition, filterType: AgFilterType): AgFilterLeaf | null => {
  const type = AG_TYPE_BY_OPERATOR[condition.operator]
  if (type === undefined) {
    return null
  }

  const leaf: AgFilterLeaf = { filterType, type }
  if (condition.operator === 'is_empty' || condition.operator === 'is_not_empty') {
    return leaf
  }

  const ranged = condition.operator === 'between'
  const first = ranged ? (condition.values[0] ?? null) : condition.value
  const second = ranged ? (condition.values[1] ?? null) : null

  if (filterType === 'date') {
    leaf.dateFrom = toDateText(first)
    leaf.dateTo = toDateText(second)

    return leaf
  }

  leaf.filter = first
  if (ranged) {
    leaf.filterTo = second
  }

  return leaf
}

/**
 * Turn a stored list of conditions back into the filter model of the grid, the inverse of the reading above.
 *
 * Restoring a saved view has to reach the filter inputs in the headers and not only the query, otherwise the
 * table shows rows that its own headers claim are not filtered. Several conditions on one column were
 * flattened into their own entries on the way out and all of them narrow the rows, so they are joined again
 * under the operator that keeps that meaning.
 *
 * @param conditions - The conditions a saved view carries.
 * @param filterComponents - The filter component of each column of the current table, keyed by its identifier.
 */
const buildFilterModel = (
  conditions: FilterCondition[],
  filterComponents: Record<string, string> = {},
): FilterModel => {
  const leavesByKey = new Map<string, AgFilterLeaf[]>()

  conditions.forEach((condition) => {
    const leaf = buildLeaf(condition, readFilterType(condition, filterComponents[condition.key]))
    if (leaf === null) {
      return
    }

    leavesByKey.set(condition.key, [...(leavesByKey.get(condition.key) ?? []), leaf])
  })

  const model: FilterModel = {}
  leavesByKey.forEach((leaves, key) => {
    const first = leaves[0]
    if (first === undefined) {
      return
    }

    const group: AgFilterGroup = { filterType: first.filterType, operator: JOIN_OPERATOR, conditions: leaves }
    model[key] = leaves.length === 1 ? first : group
  })

  return model
}

/**
 * Turn the sort model of the grid into the ordering the backend understands.
 */
const buildSortSpecifications = (model: SortModelItem[]): SortSpecification[] =>
  model.map((item) => ({ key: item.colId, direction: item.sort === 'asc' ? 'asc' : 'desc' }))

export type { AgFilterGroup, AgFilterLeaf, AgFilterType }
export { buildFilterConditions, buildFilterModel, buildSortSpecifications }
