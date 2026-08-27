/**
 * The public surface of the Skyscanner UI library.
 *
 * What belongs in here is what any surface of the system could render: presentation primitives that are
 * driven entirely by their props, and the formatting rules that decide how a value reads. Anything that
 * reaches for the API, the router or the application state stays in the web client, because a component
 * that knows about those is a piece of that client rather than a reusable part.
 */

import SkyChip from './components/SkyChip.vue'
import SkyInfoIcon from './components/SkyInfoIcon.vue'
import SkyNotesInput from './components/SkyNotesInput.vue'
import SkyTooltip from './components/SkyTooltip.vue'
import SkyDropzone from './components/SkyDropzone.vue'
import SkyValueViewer from './components/SkyValueViewer.vue'

export { DEFAULT_FILE_ICON, fileIcon } from './utils/file-icons'
export {
  EMPTY_PLACEHOLDER,
  formatBytes,
  formatCompactDateTime,
  formatDate,
  formatDateTime,
  humanizeKey,
  slugify,
  toDateInput,
  toIsoDate,
  truncate,
} from './utils/format'

export { SkyChip, SkyDropzone, SkyInfoIcon, SkyNotesInput, SkyTooltip, SkyValueViewer }
