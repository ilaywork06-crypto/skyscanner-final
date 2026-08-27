/**
 * Parsing of the generated configuration into the column definitions AG Grid understands.
 */

import type { ColDef } from 'ag-grid-community'
import type { Component } from 'vue'

import type { GeneratedColumn, GeneratedGridConfiguration, GridRow } from './types'

type CellRendererRegistry = Record<string, Component>

/**
 * The filter components the client registers itself, keyed by the name the backend generates them under.
 *
 * The community build of the grid carries a filter for text, for numbers and for dates and nothing else, so
 * a column whose values are a declared vocabulary - a platform, a status, an industry - is given a filter
 * from here instead of a box to type a key into.
 */
type FilterComponentRegistry = Record<string, Component>

interface ParseOptions {
  registry: CellRendererRegistry
  filters?: FilterComponentRegistry
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
    /* The vocabulary of the column travels to whatever filter it carries, which is what fills its list. */
    filterParams: { options: column.filterOptions, headerName: column.headerName },
    /*
     * A header carries no tooltip of its own: it said the header again, which is the one thing already on
     * screen. A header too long for its column wraps instead, which is what the grid options ask for.
     */
    wrapHeaderText: true,
    autoHeaderHeight: true,
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
    definition.pinned = column.pinned
    definition.lockPinned = true
    definition.lockPosition = column.pinned
    definition.suppressMovable = true
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

  /*
   * A filter the backend named and the client registered is handed over as the component itself; the built
   * in names of the grid stay the strings they already are and resolve inside the grid.
   */
  const registered = typeof column.filter === 'string' ? options.filters?.[column.filter] : undefined
  if (registered !== undefined) {
    definition.filter = registered
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

export type { CellRendererRegistry, FilterComponentRegistry, ParseOptions }
export { parseColumnDefinitions }
