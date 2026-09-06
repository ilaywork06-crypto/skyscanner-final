/**
 * The registries that map the names a generated column carries onto the components the client renders with.
 *
 * A generated column names a renderer for its body and a filter for its header, and neither of those names
 * means anything until it is resolved here - which is what keeps every column definition in the schema and
 * every pixel of it in the client.
 *
 * The renderers below are the ones any table needs. A product that draws something of its own - a link into
 * one of its own pages, a list of files it knows how to fetch - registers that by name on top of these.
 */

import type { CellRendererRegistry, FilterComponentRegistry } from '@truth-platform/ag-grid-ts'

import BooleanCellRenderer from '../components/cells/BooleanCellRenderer.vue'
import ChipCellRenderer from '../components/cells/ChipCellRenderer.vue'
import ChipListCellRenderer from '../components/cells/ChipListCellRenderer.vue'
import CoordinateCellRenderer from '../components/cells/CoordinateCellRenderer.vue'
import DateCellRenderer from '../components/cells/DateCellRenderer.vue'
import ExpandCellRenderer from '../components/cells/ExpandCellRenderer.vue'
import JsonCellRenderer from '../components/cells/JsonCellRenderer.vue'
import StatusCellRenderer from '../components/cells/StatusCellRenderer.vue'
import TextCellRenderer from '../components/cells/TextCellRenderer.vue'
import SetColumnFilter from '../components/filters/SetColumnFilter.vue'

const baseRenderers: CellRendererRegistry = {
  BooleanCellRenderer,
  ChipCellRenderer,
  ChipListCellRenderer,
  CoordinateCellRenderer,
  DateCellRenderer,
  ExpandCellRenderer,
  JsonCellRenderer,
  StatusCellRenderer,
  TextCellRenderer,
}

/*
 * The community build of the grid carries a filter for text, for numbers and for dates and nothing else, so
 * the one that picks from a declared vocabulary is registered here under the name the columns generate.
 */
const baseFilters: FilterComponentRegistry = {
  SetColumnFilter,
}

/**
 * Expose the renderer registry the generated columns are resolved against, plus whatever this product adds.
 */
const useCellRenderers = (extra: CellRendererRegistry = {}): CellRendererRegistry => ({
  ...baseRenderers,
  ...extra,
})

/**
 * Expose the filter registry the generated columns resolve their filter names against.
 */
const useColumnFilters = (extra: FilterComponentRegistry = {}): FilterComponentRegistry => ({
  ...baseFilters,
  ...extra,
})

export { useCellRenderers, useColumnFilters }
