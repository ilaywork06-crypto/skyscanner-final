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

import type { CellRendererRegistry } from './parse'
import { parseColumnDefinitions } from './parse'
import type { GeneratedGridConfiguration, GridRow } from './types'

interface GridOptionsInput {
  configuration: GeneratedGridConfiguration
  registry: CellRendererRegistry
  visibleColumns?: string[]
  detailRowHeight?: number
  onRowClicked?: (row: GridRow) => void
}

const DETAIL_ROW_KEY = '__detail'
const DEFAULT_DETAIL_HEIGHT = 320
const TOOLTIP_SHOW_DELAY_MS = 200
const TOOLTIP_HIDE_DELAY_MS = 60000

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

  const columnDefs: ColDef<GridRow>[] = parseColumnDefinitions(input.configuration, {
    registry: input.registry,
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
    /*
     * The tooltip stays on screen once it is open and accepts the pointer, so that a value which is too
     * wide for its cell can be read in full and selected out of the tooltip.
     */
    tooltipInteraction: true,
    tooltipShowDelay: TOOLTIP_SHOW_DELAY_MS,
    tooltipHideDelay: TOOLTIP_HIDE_DELAY_MS,
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
