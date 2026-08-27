/**
 * The registries that map the names the backend generates onto the components the client renders with.
 *
 * A generated column names a renderer for its body and a filter for its header, and neither of those names
 * means anything until it is resolved here - which is what keeps every column definition in the backend and
 * every pixel of it in the client.
 */

import type { CellRendererRegistry, FilterComponentRegistry } from '@skyscanner/ag-grid-ts'

import BooleanCellRenderer from '@/components/cells/BooleanCellRenderer.vue'
import ChipCellRenderer from '@/components/cells/ChipCellRenderer.vue'
import ChipListCellRenderer from '@/components/cells/ChipListCellRenderer.vue'
import CoordinateCellRenderer from '@/components/cells/CoordinateCellRenderer.vue'
import DateCellRenderer from '@/components/cells/DateCellRenderer.vue'
import EventLinkCellRenderer from '@/components/cells/EventLinkCellRenderer.vue'
import ExpandCellRenderer from '@/components/cells/ExpandCellRenderer.vue'
import FilesCellRenderer from '@/components/cells/FilesCellRenderer.vue'
import JsonCellRenderer from '@/components/cells/JsonCellRenderer.vue'
import OpenEventCellRenderer from '@/components/cells/OpenEventCellRenderer.vue'
import StatusCellRenderer from '@/components/cells/StatusCellRenderer.vue'
import TextCellRenderer from '@/components/cells/TextCellRenderer.vue'
import SetColumnFilter from '@/components/filters/SetColumnFilter.vue'

const registry: CellRendererRegistry = {
  BooleanCellRenderer,
  ChipCellRenderer,
  ChipListCellRenderer,
  CoordinateCellRenderer,
  DateCellRenderer,
  EventLinkCellRenderer,
  ExpandCellRenderer,
  FilesCellRenderer,
  JsonCellRenderer,
  OpenEventCellRenderer,
  StatusCellRenderer,
  TextCellRenderer,
}

/*
 * The community build of the grid carries a filter for text, for numbers and for dates and nothing else, so
 * the one that picks from a declared vocabulary is registered here under the name the backend generates.
 */
const filters: FilterComponentRegistry = {
  SetColumnFilter,
}

/**
 * Expose the renderer registry the generated columns are resolved against.
 */
const useCellRenderers = (): CellRendererRegistry => registry

/**
 * Expose the filter registry the generated columns resolve their filter names against.
 */
const useColumnFilters = (): FilterComponentRegistry => filters

export { useCellRenderers, useColumnFilters }
