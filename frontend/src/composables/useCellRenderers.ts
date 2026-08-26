/**
 * The registry that maps the renderer names the backend generates onto the components the client renders.
 */

import type { CellRendererRegistry } from '@skyscanner/ag-grid-ts'

import BooleanCellRenderer from '@/components/cells/BooleanCellRenderer.vue'
import ChipCellRenderer from '@/components/cells/ChipCellRenderer.vue'
import ChipListCellRenderer from '@/components/cells/ChipListCellRenderer.vue'
import CoordinateCellRenderer from '@/components/cells/CoordinateCellRenderer.vue'
import DateCellRenderer from '@/components/cells/DateCellRenderer.vue'
import EventLinkCellRenderer from '@/components/cells/EventLinkCellRenderer.vue'
import ExpandCellRenderer from '@/components/cells/ExpandCellRenderer.vue'
import FilesCellRenderer from '@/components/cells/FilesCellRenderer.vue'
import JsonCellRenderer from '@/components/cells/JsonCellRenderer.vue'
import StatusCellRenderer from '@/components/cells/StatusCellRenderer.vue'
import TextCellRenderer from '@/components/cells/TextCellRenderer.vue'

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
  StatusCellRenderer,
  TextCellRenderer,
}

/**
 * Expose the renderer registry the generated columns are resolved against.
 */
const useCellRenderers = (): CellRendererRegistry => registry

export { useCellRenderers }
