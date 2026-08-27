/**
 * The reactive controller that keeps a generated table, its rows and its query in sync with the backend.
 */

import { computed, ref, shallowRef, type ComputedRef, type Ref, type ShallowRef } from 'vue'
import type { FilterModel, GridApi, SortModelItem } from 'ag-grid-community'

import { buildFilterConditions, buildSortSpecifications } from './datasource'
import { DETAIL_ROW_KEY } from './grid'
import type {
  FilterCondition,
  GeneratedGridConfiguration,
  GridRow,
  GridRowsPage,
  SortSpecification,
} from './types'

interface RowsQuery {
  search: string | null
  industry: string | null
  parseState: string
  filters: FilterCondition[]
  sort: SortSpecification[]
  page: number
  pageSize: number
}

interface GridControllerInput {
  loadConfiguration: (industry: string | null) => Promise<GeneratedGridConfiguration>
  loadRows: (query: RowsQuery) => Promise<GridRowsPage>
  pageSize?: number
}

interface GridController {
  configuration: ShallowRef<GeneratedGridConfiguration | null>
  rows: Ref<GridRow[]>
  displayedRows: ComputedRef<GridRow[]>
  total: Ref<number>
  page: Ref<number>
  pageSize: Ref<number>
  pageCount: ComputedRef<number>
  loading: Ref<boolean>
  errorMessage: Ref<string>
  search: Ref<string>
  industry: Ref<string | null>
  parseState: Ref<string>
  expandedIds: Ref<string[]>
  sortSpecifications: Ref<SortSpecification[]>
  filterConditions: Ref<FilterCondition[]>
  setGridApi: (api: GridApi<GridRow> | null) => void
  refreshConfiguration: () => Promise<void>
  refreshRows: () => Promise<void>
  applyGridModels: (sortModel: SortModelItem[], filterModel: FilterModel) => Promise<void>
  toggleExpanded: (rowId: string) => void
  collapseAll: () => void
  goToPage: (page: number) => Promise<void>
  setPageSize: (size: number) => Promise<void>
}

const DEFAULT_PAGE_SIZE = 25

/**
 * Build the reactive controller of one generated table.
 */
const createGridController = (input: GridControllerInput): GridController => {
  const configuration = shallowRef<GeneratedGridConfiguration | null>(null)
  const rows = shallowRef<GridRow[]>([])
  const total = ref<number>(0)
  const page = ref<number>(1)
  const pageSize = ref<number>(input.pageSize ?? DEFAULT_PAGE_SIZE)
  const loading = ref<boolean>(false)
  const errorMessage = ref<string>('')
  const search = ref<string>('')
  const industry = ref<string | null>(null)
  const parseState = ref<string>('all')
  const expandedIds = ref<string[]>([])
  const filters = shallowRef<FilterCondition[]>([])
  const sort = ref<SortSpecification[]>([])
  const gridApi = shallowRef<GridApi<GridRow> | null>(null)

  const pageCount = computed<number>(() =>
    pageSize.value > 0 ? Math.max(1, Math.ceil(total.value / pageSize.value)) : 1,
  )

  const displayedRows = computed<GridRow[]>(() => {
    const materialised: GridRow[] = []
    rows.value.forEach((row) => {
      materialised.push(row)
      if (expandedIds.value.includes(String(row.id))) {
        materialised.push({ id: `${String(row.id)}::detail`, [DETAIL_ROW_KEY]: true, parentId: String(row.id) })
      }
    })

    return materialised
  })

  const buildQuery = (): RowsQuery => ({
    search: search.value.length > 0 ? search.value : null,
    industry: industry.value,
    parseState: parseState.value,
    filters: filters.value,
    sort: sort.value,
    page: page.value,
    pageSize: pageSize.value,
  })

  const refreshRows = async (): Promise<void> => {
    loading.value = true
    errorMessage.value = ''
    try {
      const answer = await input.loadRows(buildQuery())
      rows.value = answer.rows
      total.value = answer.total
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : 'The rows could not be loaded'
      rows.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  const refreshConfiguration = async (): Promise<void> => {
    errorMessage.value = ''
    try {
      configuration.value = await input.loadConfiguration(industry.value)
      sort.value = configuration.value.defaultSort
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : 'The table could not be built'
    }
  }

  /**
   * Take the ordering and the restrictions the table is currently running, and reload the rows against them.
   *
   * A table raises these while it is being arranged as much as while it is being used - restoring a saved
   * view, showing a column, rebuilding a header - and several of those raise it without anything having
   * actually changed. Such a round is dropped: it would otherwise cost a full query for the answer the table
   * is already showing, and it would throw a reader who was on page three back to page one for nothing.
   */
  const applyGridModels = async (sortModel: SortModelItem[], filterModel: FilterModel): Promise<void> => {
    const requestedSort = buildSortSpecifications(sortModel)
    const requestedFilters = buildFilterConditions(filterModel)
    const unchanged =
      JSON.stringify(requestedSort) === JSON.stringify(sort.value) &&
      JSON.stringify(requestedFilters) === JSON.stringify(filters.value)

    if (unchanged) {
      return
    }

    sort.value = requestedSort
    filters.value = requestedFilters
    page.value = 1
    await refreshRows()
  }

  const toggleExpanded = (rowId: string) => {
    expandedIds.value = expandedIds.value.includes(rowId)
      ? expandedIds.value.filter((candidate) => candidate !== rowId)
      : [...expandedIds.value, rowId]
  }

  /**
   * Close every open panel at once, which is what a table full of expanded rows needs to become readable again.
   */
  const collapseAll = () => {
    expandedIds.value = []
  }

  const goToPage = async (target: number): Promise<void> => {
    page.value = Math.min(Math.max(1, target), pageCount.value)
    await refreshRows()
  }

  const setPageSize = async (size: number): Promise<void> => {
    pageSize.value = size
    page.value = 1
    await refreshRows()
  }

  const setGridApi = (api: GridApi<GridRow> | null) => {
    gridApi.value = api
  }

  return {
    configuration,
    rows,
    displayedRows,
    total,
    page,
    pageSize,
    pageCount,
    loading,
    errorMessage,
    search,
    industry,
    parseState,
    expandedIds,
    sortSpecifications: sort,
    filterConditions: filters,
    setGridApi,
    refreshConfiguration,
    refreshRows,
    applyGridModels,
    toggleExpanded,
    collapseAll,
    goToPage,
    setPageSize,
  }
}

export type { GridController, GridControllerInput, RowsQuery }
export { createGridController }
