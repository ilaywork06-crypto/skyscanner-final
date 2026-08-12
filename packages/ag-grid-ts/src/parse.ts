/**
 * Parsing of the generated configuration into the column definitions AG Grid understands.
 */

import type { ColDef } from 'ag-grid-community'
import type { Component } from 'vue'

import type { GeneratedColumn, GeneratedGridConfiguration, GridRow } from './types'

type CellRendererRegistry = Record<string, Component>

interface ParseOptions {
  registry: CellRendererRegistry
  hiddenColumns?: string[]
  visibleColumns?: string[]
}

const EMPTY_RENDERER_PARAMS: Record<string, never> = {}

/**
 * Decide whether a generated column has to start hidden for the current template.
 */
const isHidden = (column: GeneratedColumn, options: ParseOptions): boolean => {
  if (options.visibleColumns !== undefined && options.visibleColumns.length > 0) {
    return !options.visibleColumns.includes(column.colId)
  }

  if (options.hiddenColumns !== undefined && options.hiddenColumns.includes(column.colId)) {
    return true
  }

  return column.hide
}

/**
 * Turn one generated column into an AG Grid column definition, resolving its renderer from the registry.
 */
const parseColumn = (column: GeneratedColumn, options: ParseOptions): ColDef<GridRow> => {
  const definition: ColDef<GridRow> = {
    colId: column.colId,
    field: column.field,
    headerName: column.headerName,
    sortable: column.sortable,
    resizable: column.resizable,
    editable: column.editable,
    hide: isHidden(column, options),
    filter: column.filter,
    floatingFilter: column.floatingFilter,
    autoHeight: column.autoHeight,
    cellRendererParams: { ...EMPTY_RENDERER_PARAMS, ...column.cellRendererParams },
    headerTooltip: column.headerName,
  }

  if (column.flex !== null) {
    definition.flex = column.flex
  }
  if (column.minWidth !== null) {
    definition.minWidth = column.minWidth
  }
  if (column.maxWidth !== null) {
    definition.maxWidth = column.maxWidth
  }
  if (column.width !== null) {
    definition.width = column.width
  }
  if (column.pinned === 'left' || column.pinned === 'right') {
    console.log(column)
    definition.pinned = column.pinned
    definition.lockPinned = true
    definition.lockPosition = column.pinned
    definition.suppressMovable = true
  }
  if (column.tooltipField !== null) {
    definition.tooltipField = column.tooltipField
  }
  if (column.headerClass !== null) {
    definition.headerClass = column.headerClass
  }
  if (column.cellClass !== null) {
    definition.cellClass = column.cellClass
  }
  if (column.cellRenderer !== null && options.registry[column.cellRenderer] !== undefined) {
    definition.cellRenderer = options.registry[column.cellRenderer]
  }

  return definition
}

/**
 * Turn the whole generated configuration into the ordered column definitions of the table.
 */
const parseColumnDefinitions = (
  configuration: GeneratedGridConfiguration,
  options: ParseOptions,
): ColDef<GridRow>[] => configuration.columns.map((column) => parseColumn(column, options))

export type { CellRendererRegistry, ParseOptions }
export { parseColumnDefinitions }
