/**
 * Initialisation of AG Grid - the module registration and the grid options built from a generated configuration.
 */

import {
  AllCommunityModule,
  ModuleRegistry,
  type GridOptions,
  type IRowNode,
  type PostSortRowsParams,
  type RowClassParams,
  type ColDef,
} from 'ag-grid-community'

import { applyThemeCompatibility } from './compatibility'
import type { CellRendererRegistry, FilterComponentRegistry } from './parse'
import { parseColumnDefinitions } from './parse'
import type { GeneratedGridConfiguration, GridRow } from './types'

interface GridOptionsInput {
  configuration: GeneratedGridConfiguration
  registry: CellRendererRegistry
  filters?: FilterComponentRegistry
  visibleColumns?: string[]
  detailRowHeight?: number
  onRowClicked?: (row: GridRow) => void
}

const DETAIL_ROW_KEY = '__detail'
const DEFAULT_DETAIL_HEIGHT = 320

let modulesRegistered = false

/**
 * Register the AG Grid community modules exactly once per browser session.
 */
const registerGridModules = () => {
  if (modulesRegistered) {
    return
  }

  ModuleRegistry.registerModules([AllCommunityModule])
  modulesRegistered = true
}

/**
 * Give a browser without the colour function the palette the theme derived, once the theme has been written.
 *
 * The grid injects its generated stylesheet while it builds itself, so the rewrite is queued behind that
 * rather than run before it. On a browser that understands the function this does nothing at all.
 */
const repairInjectedTheme = () => {
  if (typeof window === 'undefined') {
    return
  }

  window.setTimeout(() => applyThemeCompatibility(), 0)
}

/**
 * Decide whether one row of the table is a detail row rendered across the full width.
 */
const isDetailRow = (row: GridRow | undefined): boolean =>
  row !== undefined && row[DETAIL_ROW_KEY] === true

/**
 * Reattach every detail row directly underneath the row it belongs to.
 *
 * The ordering of the table is decided by the backend, but AG Grid still sorts the rows it was handed. A detail
 * row carries none of the sorted values, so it drifts away from its parent - to the top of the block for a
 * descending sort. Running after the sort, this puts each detail row back below its own row.
 */
const attachDetailRows = (params: PostSortRowsParams<GridRow>) => {
  const nodes = params.nodes
  const details = new Map<string, IRowNode<GridRow>>()
  const parents: IRowNode<GridRow>[] = []

  nodes.forEach((node) => {
    if (isDetailRow(node.data)) {
      details.set(String(node.data?.parentId ?? ''), node)

      return
    }
    parents.push(node)
  })

  const ordered: IRowNode<GridRow>[] = []
  parents.forEach((node) => {
    ordered.push(node)
    const detail = details.get(String(node.data?.id ?? ''))
    if (detail !== undefined) {
      ordered.push(detail)
    }
  })

  nodes.length = 0
  nodes.push(...ordered)
}

/**
 * Build the grid options of a table out of the configuration the backend generated.
 */
const buildGridOptions = (input: GridOptionsInput): GridOptions<GridRow> => {
  registerGridModules()
  repairInjectedTheme()

  const columnDefs: ColDef<GridRow>[] = parseColumnDefinitions(input.configuration, {
    registry: input.registry,
    filters: input.filters,
    visibleColumns: input.visibleColumns,
  })

  return {
    columnDefs,
    defaultColDef: {
      sortable: false,
      resizable: true,
      suppressHeaderMenuButton: true,
      suppressMovable: false,
      cellClass: 'sky-cell',
      headerClass: 'sky-header',
    },
    rowHeight: input.configuration.rowHeight,
    headerHeight: input.configuration.headerHeight,
    animateRows: true,
    suppressCellFocus: true,
    suppressDragLeaveHidesColumns: true,
    rowSelection: {
      mode: 'multiRow',
      checkboxes: true,
      headerCheckbox: true,
      enableClickSelection: false,
      selectAll: 'filtered',
    },
    selectionColumnDef: {
      pinned: 'left',
      lockPosition: 'left',
      suppressMovable: true,
      width: 50
    },
    isRowSelectable: (node) => !isDetailRow(node.data),
    postSortRows: attachDetailRows,
    getRowId: (params) => String(params.data.id),
    isFullWidthRow: (params) => isDetailRow(params.rowNode.data),
    getRowHeight: (params) =>
      isDetailRow(params.data) ? (input.detailRowHeight ?? DEFAULT_DETAIL_HEIGHT) : input.configuration.rowHeight,
    getRowClass: (params: RowClassParams<GridRow>) =>
      isDetailRow(params.data) ? 'sky-row sky-row--detail' : 'sky-row',
    onRowClicked: (event) => {
      if (input.onRowClicked !== undefined && event.data !== undefined && !isDetailRow(event.data)) {
        input.onRowClicked(event.data)
      }
    },
  }
}

export type { GridOptionsInput }
export { DETAIL_ROW_KEY, buildGridOptions, isDetailRow, registerGridModules }
