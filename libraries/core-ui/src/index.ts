/**
 * The public surface of the shared UI library.
 *
 * What belongs in here is what any product built on this platform could render: presentation primitives that
 * are driven entirely by their props, the generated table's renderers and filters, the formatting rules that
 * decide how a value reads, and the vocabulary all of that is typed in. Anything that reaches for a
 * particular API, router or application state stays in the product that owns it, because a component which
 * knows about those is a piece of that product rather than a reusable part.
 */

import ActiveFilters from './components/ActiveFilters.vue'
import AppSnackbar from './components/AppSnackbar.vue'
import AttributesTable from './components/AttributesTable.vue'
import CoordinateField from './components/CoordinateField.vue'
import DynamicCell from './components/DynamicCell.vue'
import DynamicFieldInput from './components/DynamicFieldInput.vue'
import FileList from './components/FileList.vue'
import HighlightedText from './components/HighlightedText.vue'
import UiLinkedText from './components/UiLinkedText.vue'
import PaginationBar from './components/PaginationBar.vue'
import QuickFilters from './components/QuickFilters.vue'
import UiChip from './components/UiChip.vue'
import UiDropzone from './components/UiDropzone.vue'
import UiInfoIcon from './components/UiInfoIcon.vue'
import UiNotesInput from './components/UiNotesInput.vue'
import UiTooltip from './components/UiTooltip.vue'
import UiValueViewer from './components/UiValueViewer.vue'
import UnsavedChangesDialog from './components/UnsavedChangesDialog.vue'
import BooleanCellRenderer from './components/cells/BooleanCellRenderer.vue'
import ChipCellRenderer from './components/cells/ChipCellRenderer.vue'
import ChipListCellRenderer from './components/cells/ChipListCellRenderer.vue'
import CoordinateCellRenderer from './components/cells/CoordinateCellRenderer.vue'
import DateCellRenderer from './components/cells/DateCellRenderer.vue'
import ExpandCellRenderer from './components/cells/ExpandCellRenderer.vue'
import JsonCellRenderer from './components/cells/JsonCellRenderer.vue'
import StatusCellRenderer from './components/cells/StatusCellRenderer.vue'
import TextCellRenderer from './components/cells/TextCellRenderer.vue'
import SetColumnFilter from './components/filters/SetColumnFilter.vue'

export type { FilterChip, ScopeFilter } from './components/ActiveFilters.vue'
export type { QuickFilterChoice } from './components/QuickFilters.vue'
export type { AppTheme, ThemeNames } from './composables/useAppTheme'
export type { Dictionary, Language, LanguageState, Translations } from './composables/useLanguage'
export type { SnackbarTone } from './composables/useSnackbar'
export type {
  Artifact,
  ArtifactKind,
  Coordinate,
  FieldScope,
  FieldType,
  JsonValue,
  MetadataAttribute,
  ObjectTypeReference,
  OperationResult,
  PageResponse,
  TaxonomyItem,
} from './models/common'
export type {
  DependencyOperator,
  FieldConstraint,
  FieldDefinition,
  FieldDependency,
  FieldMetadata,
  FieldValue,
} from './models/field'
export type {
  DetailGridRow,
  FilesCellValue,
  FilterOption,
  GeneratedColumn,
  GeneratedGridConfiguration,
  GridRow,
  GridRowsPage,
} from './models/grid'
export type { FilterCondition, FilterOperator, SortDirection, SortSpecification } from './models/query'
export type { FieldChange, Revision, RevisionTarget } from './models/revision'
export type { TableTemplate, TemplateColumn, TemplateCreateRequest } from './models/template'
export type { GridContext } from './utils/grid-context'
export type { HighlightSegment } from './utils/highlight'
export type { LinkSegment } from './utils/links'
export type { ThemeColors } from './utils/grid-theme'

export { configureThemes, useAppTheme } from './composables/useAppTheme'
export {
  LANGUAGES,
  LANGUAGE_NAMES,
  language,
  registerTranslations,
  translate,
  useLanguage,
} from './composables/useLanguage'
export { useCellRenderers, useColumnFilters } from './composables/useCellRenderers'
export { useDirtyGuard } from './composables/useDirtyGuard'
export { useSnackbar } from './composables/useSnackbar'

export type { SheetContent } from './utils/sheets'
export { delimiterOf, parseDelimited, readWorkbook, wholeLines } from './utils/sheets'
export { readActiveTemplate, writeActiveTemplate } from './utils/active-template'
export { applicableFields, dependenciesHold, dependencyHolds, isFilled } from './utils/dependencies'
export { downloadBlob, openLink } from './utils/download'
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
export {
  DYNAMIC_FIELD_PREFIX,
  TYPE_RENDERERS,
  attributeColumns,
  undeclaredAttributes,
  undeclaredColumn,
} from './utils/grid-columns'
export {
  EMPTY_CONTEXT,
  provideSearchTerm,
  readContext,
  readRowId,
  useSearchTerm,
} from './utils/grid-context'
export { buildGridTheme } from './utils/grid-theme'
export { gridIsRtl, gridLanguageKey, gridLocaleText, localiseColumns } from './utils/grid-locale'
/*
 * Imported for what loading it does rather than for what it exports: it puts the words of the table into
 * the dictionary, and it has to have done so before the first component of this library renders.
 */
export { SHARED_TRANSLATIONS } from './utils/translations'
export { matchesTerm, previewAround, splitHighlights } from './utils/highlight'
export { installRuntimeShims } from './utils/runtime'
export { holdsLink, splitLinks } from './utils/links'
export {
  CHIP_COLOUR_NAMES,
  CHIP_PALETTE,
  DEFAULT_TOKEN,
  hashText,
  hashedToken,
  taxonomyToken,
} from './utils/palette'
export {
  createLocalTemplate,
  deleteLocalTemplate,
  isLocalTemplate,
  listLocalTemplates,
} from './utils/local-templates'
export { readArtifacts, readPath, readText, toMetadataAttributes, toValueMap, toValueTypeMap } from './utils/rows'
export type { MapTiles } from './utils/coordinates'
export { configureMapTiles, formatCoordinate, mapTiles, toCoordinate } from './utils/coordinates'
export { splitNotes, toBulletedText, toNotePreview } from './utils/notes'

export {
  ActiveFilters,
  AppSnackbar,
  AttributesTable,
  BooleanCellRenderer,
  ChipCellRenderer,
  ChipListCellRenderer,
  CoordinateCellRenderer,
  CoordinateField,
  DateCellRenderer,
  DynamicCell,
  DynamicFieldInput,
  ExpandCellRenderer,
  FileList,
  HighlightedText,
  UiLinkedText,
  JsonCellRenderer,
  PaginationBar,
  QuickFilters,
  SetColumnFilter,
  StatusCellRenderer,
  TextCellRenderer,
  UiChip,
  UiDropzone,
  UiInfoIcon,
  UiNotesInput,
  UiTooltip,
  UiValueViewer,
  UnsavedChangesDialog,
}
