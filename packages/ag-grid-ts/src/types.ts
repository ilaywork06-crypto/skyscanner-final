/**
 * The wire shape of the table configuration the backend generates, mirrored one to one on the client side.
 */

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }

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

interface SortSpecification {
  key: string
  direction: SortDirection
}

interface FilterCondition {
  key: string
  operator: FilterOperator
  value: JsonValue
  values: JsonValue[]
}

/** One value a column is known to be able to hold, offered by its filter instead of being typed by hand. */
interface FilterOption {
  value: string
  label: string
}

interface GeneratedColumn {
  colId: string
  field: string
  headerName: string
  sortable: boolean
  filter: string | boolean
  floatingFilter: boolean
  resizable: boolean
  hide: boolean
  editable: boolean
  flex: number | null
  minWidth: number | null
  maxWidth: number | null
  width: number | null
  pinned: string | null
  cellRenderer: string | null
  cellRendererParams: Record<string, JsonValue>
  cellDataType: string | boolean
  headerClass: string | null
  cellClass: string | null
  autoHeight: boolean
  fieldType: string
  dynamic: boolean
  /** Whether nobody declared this column and it was read off the stored documents instead. */
  discovered: boolean
  industry: string | null
  /** The vocabulary the values of this column are drawn from, empty when they are not a vocabulary at all. */
  filterOptions: FilterOption[]
  /** Whether the column is worth offering as one of the quick filters above the table. */
  quickFilter: boolean
}

interface GeneratedGridConfiguration {
  scope: string
  industry: string | null
  columns: GeneratedColumn[]
  defaultSort: SortSpecification[]
  quickFilterKeys: string[]
  rowHeight: number
  headerHeight: number
  version: string
}

interface GridRow {
  id: string
  [key: string]: JsonValue
}

interface GridRowsPage {
  rows: GridRow[]
  total: number
  page: number
  pageSize: number
  pages: number
}

export type {
  FilterCondition,
  FilterOperator,
  FilterOption,
  GeneratedColumn,
  GeneratedGridConfiguration,
  GridRow,
  GridRowsPage,
  JsonValue,
  SortDirection,
  SortSpecification,
}
