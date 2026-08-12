<template>
  <div
    ref="root"
    class="events-grid"
    :class="{ 'events-grid--pinned': pinned }"
    @wheel="onWheel"
  >
    <AgGridVue
      v-if="gridOptions !== null"
      class="events-grid__table"
      :grid-options="gridOptions"
      :column-defs="columnDefs"
      :row-data="rows"
      :context="context"
      @grid-ready="onGridReady"
      @sort-changed="onModelChanged"
      @filter-changed="onModelChanged"
      @selection-changed="onSelectionChanged"
    />

    <div
      v-if="loading"
      class="events-grid__overlay"
    >
      <div class="events-grid__spinner">
        <v-progress-circular
          indeterminate
          color="primary"
          size="36"
        />
      </div>
    </div>

    <!--
      The grid carries an overlay of its own for an empty table, which said the same thing a second time
      right underneath this one. It is suppressed in the grid options, so this is the only message left.
    -->
    <div
      v-if="!loading && rows.length === 0"
      class="events-grid__empty"
    >
      No events match the current filters.
    </div>

    <!--
      Zoomed, the table scrolls inside its own body and the scrollbar of the columns is already on screen, so
      the sticky one stands down rather than being a second bar over the first.
    -->
    <StickyScrollBar
      v-if="!pinned"
      :viewport="scrollViewport"
    />
  </div>
</template>

<script lang="ts">
import type {
  ColDef,
  ColumnState,
  DomLayoutType,
  FilterModel,
  GridApi,
  GridOptions,
  GridReadyEvent,
  SortModelItem,
} from 'ag-grid-community'
import type { Artifact } from '@/models/common'
import type { GeneratedGridConfiguration, GridRow } from '@/models/grid'
import type { Industry } from '@/models/industry'
import type { FilterCondition, SortDirection, SortSpecification } from '@/models/query'
import type { GridContext } from '@/utils/grid-context'

interface Props {
  configuration: GeneratedGridConfiguration | null
  rows: GridRow[]
  loading: boolean
  expandedIds: string[]
  selectedIds: string[]
  industries: Industry[]
  visibleColumns: string[]
  sourceRows: GridRow[]
  search: string
  industry: string | null
  pinned: boolean
}

interface Emits {
  (event: 'toggle-expanded', rowId: string): void
  (event: 'update:selected', rowIds: string[]): void
  (event: 'open-event', rowId: string): void
  (event: 'open-artifact', artifact: Artifact): void
  (event: 'download', artifact: Artifact): void
  (event: 'models-changed', sortModel: SortModelItem[], filterModel: FilterModel): void
}

/** One column the way the running table presents it, which is what a saved view has to be able to restore. */
interface GridColumnLayout {
  colId: string
  visible: boolean
  width: number | null
  pinned: string | null
}

/** Everything a saved view pushes back into the running table in one go. */
interface GridViewState {
  columns: GridColumnLayout[]
  sort: SortSpecification[]
  filters: FilterCondition[]
}

/*
 * The context of the table is the shared contract every cell renderer reads, widened by the two values this
 * particular table is the only one that knows: the term the rows were searched for and the industry the
 * inventory is narrowed to.
 */
type InventoryGridContext = GridContext & {
  search: string
  industryFilter: string | null
}

/** The chrome of an expanded panel: its own padding, the industry values above the entities and the gaps. */
const DETAIL_ROW_PADDING = 120

/**
 * An event without a single entity still shows its industry values and the invitation to add an entity, and
 * a panel shorter than this cuts into both of them.
 */
const DETAIL_ROW_MIN_HEIGHT = 288

/** The least room one entity section takes, however few entities it holds. */
const DETAIL_ENTITY_SECTION_HEIGHT = 240

/** What a section spends before its first entity: its heading and the header row of its table. */
const DETAIL_ENTITY_SECTION_CHROME = 96

/** One entity of a section, matching the padding the entity table renders its cells with. */
const DETAIL_ENTITY_ROW_HEIGHT = 52

/**
 * An event with hundreds of entities would otherwise reserve a row taller than any screen and leave the table
 * unusable, so past this the panel does scroll inside itself after all.
 */
const DETAIL_ROW_MAX_HEIGHT = 1400

/**
 * The element AG Grid scrolls the columns with.
 *
 * It is the viewport of the scrollbar the grid draws underneath itself, and both the sticky bar and the wheel
 * move the table by moving it, so that every way of scrolling sideways speaks to the grid as one and the same.
 */
const SCROLL_VIEWPORT_SELECTOR = '.ag-body-horizontal-scroll-viewport'

/** A wheel that reports its movement in lines or pages rather than pixels, read as this many pixels a step. */
const WHEEL_LINE_PIXELS = 16

export type { GridColumnLayout, GridViewState }
</script>

<script setup lang="ts">
import { buildFilterModel, buildGridOptions, isDetailRow, parseColumnDefinitions } from '@skyscanner/ag-grid-ts'
import { AgGridVue } from 'ag-grid-vue3'
import { computed, nextTick, ref, shallowRef, watch } from 'vue'

import DetailRowRenderer from '@/components/cells/DetailRowRenderer.vue'
import StickyScrollBar from '@/components/inventory/StickyScrollBar.vue'
import { useAppTheme } from '@/composables/useAppTheme'
import { useCellRenderers } from '@/composables/useCellRenderers'
import { buildGridTheme } from '@/utils/grid-theme'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const registry = useCellRenderers()
const { colors, isDark } = useAppTheme()
const gridApi = shallowRef<GridApi<GridRow> | null>(null)
const root = ref<HTMLElement | null>(null)
const scrollViewport = shallowRef<HTMLElement | null>(null)

/*
 * Restoring a saved view writes the ordering and the filters of the table itself, and every one of those writes
 * raises the very event that reloads the rows. While a view is being restored the events are therefore held
 * back, so that the page reloads once, against the whole restored view rather than against half of it.
 */
let restoringView = false

const context = computed<InventoryGridContext>(() => ({
  industries: props.industries,
  expandedIds: props.expandedIds,
  toggleExpanded: (rowId: string) => emit('toggle-expanded', rowId),
  openEvent: (rowId: string) => emit('open-event', rowId),
  openArtifact: (artifact: Artifact) => emit('open-artifact', artifact),
  downloadArtifact: (artifact: Artifact) => emit('download', artifact),
  findRow: (rowId: string) => props.sourceRows.find((row) => String(row.id) === rowId),
  search: props.search,
  industryFilter: props.industry,
}))

/**
 * Count the entities of one event group by group, which is how its panel is laid out.
 */
const readEntitySections = (row: GridRow): number[] => {
  const counts = row.entity_counts
  if (counts === null || typeof counts !== 'object' || Array.isArray(counts)) {
    return []
  }

  return Object.values(counts)
    .map((amount) => Number(amount))
    .filter((amount) => amount > 0)
}

/**
 * Measure how tall the panel of one expanded event has to be.
 *
 * The panel is given the room its own content needs rather than a fixed allowance, so that it grows with the
 * entities of the event instead of scrolling them out of sight inside a row the size of every other row. An
 * event without a single entity is measured just as honestly and does not reserve the room of tables it has not
 * got, and a hopelessly crowded one is capped so that one row can never swallow the whole table.
 */
const detailHeight = (parentId: string): number => {
  const parent = props.sourceRows.find((row) => String(row.id) === parentId)
  const sections = parent === undefined ? [] : readEntitySections(parent)
  const measured = sections.reduce(
    (total, entities) =>
      total +
      Math.max(DETAIL_ENTITY_SECTION_HEIGHT, DETAIL_ENTITY_SECTION_CHROME + entities * DETAIL_ENTITY_ROW_HEIGHT),
    DETAIL_ROW_PADDING,
  )

  return Math.min(DETAIL_ROW_MAX_HEIGHT, Math.max(DETAIL_ROW_MIN_HEIGHT, measured))
}

/**
 * Decide how the table fills its page.
 *
 * On the page the table renders the whole block of rows at its natural height and the browser scrolls the page,
 * which is what gives the rows the room of the whole window. Zoomed, the table is pinned to the viewport
 * instead and scrolls inside its own body, so that its header stays on screen above the rows.
 */
const layoutOf = (pinned: boolean): DomLayoutType => (pinned ? 'normal' : 'autoHeight')

/*
 * AG Grid reads the grid options object exactly once, when the grid is created, so the columns cannot ride
 * along with it: toggling one in the toolbar or loading a template would rebuild the object and change
 * nothing on screen. The column definitions therefore travel as their own prop, which the Vue wrapper does
 * watch and does push into the running grid.
 */
const columnDefs = computed<ColDef<GridRow>[]>(() =>
  props.configuration === null
    ? []
    : parseColumnDefinitions(props.configuration, { registry, visibleColumns: props.visibleColumns }),
)

/*
 * A stored condition says nothing about the input the header of its column renders, so the filter component of
 * every column of the current table is handed to the rebuilder along with the conditions of the saved view.
 */
const filterComponents = computed<Record<string, string>>(() => {
  const components: Record<string, string> = {}
  const declared = props.configuration === null ? [] : props.configuration.columns
  declared.forEach((column) => {
    if (typeof column.filter === 'string') {
      components[column.colId] = column.filter
    }
  })

  return components
})

const gridOptions = computed<GridOptions<GridRow> | null>(() => {
  if (props.configuration === null) {
    return null
  }

  const rowHeight = props.configuration.rowHeight
  const options = buildGridOptions({
    configuration: props.configuration,
    registry,
    visibleColumns: props.visibleColumns,
  })

  return {
    ...options,
    theme: buildGridTheme(colors.value, isDark.value),
    domLayout: layoutOf(props.pinned),
    suppressNoRowsOverlay: true,
    fullWidthCellRenderer: DetailRowRenderer,
    getRowHeight: (params) =>
      isDetailRow(params.data) ? detailHeight(String(params.data?.parentId ?? '')) : rowHeight,
  }
})

/**
 * Take hold of the element the grid scrolls its columns with, once the grid has built itself.
 */
const locateScrollViewport = async (): Promise<void> => {
  await nextTick()
  scrollViewport.value = root.value?.querySelector<HTMLElement>(SCROLL_VIEWPORT_SELECTOR) ?? null
}

const onGridReady = (event: GridReadyEvent<GridRow>) => {
  gridApi.value = event.api
  void locateScrollViewport()
}

/**
 * Read how far sideways a wheel gesture means to move the table, in pixels.
 *
 * Holding shift is how a mouse asks for sideways movement, and browsers disagree about whether they then
 * report it as horizontal or still as vertical, so both are accepted. Without shift only a gesture that is
 * mostly sideways - the swipe of a trackpad - is taken, and an ordinary one is left to scroll the page.
 */
const readWheelDelta = (event: WheelEvent): number => {
  const sideways = event.shiftKey
    ? (event.deltaX === 0 ? event.deltaY : event.deltaX)
    : (Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : 0)

  return event.deltaMode === WheelEvent.DOM_DELTA_PIXEL ? sideways : sideways * WHEEL_LINE_PIXELS
}

/**
 * Move the table sideways under the pointer, so that the columns further right can be reached from anywhere
 * over the table rather than only from the scrollbar underneath it.
 */
const onWheel = (event: WheelEvent) => {
  const viewport = scrollViewport.value
  const delta = readWheelDelta(event)
  if (viewport === null || delta === 0) {
    return
  }

  const travel = viewport.scrollWidth - viewport.clientWidth
  const position = Math.min(Math.max(viewport.scrollLeft + delta, 0), travel)

  /* At either end of the columns the gesture is handed back to the page, which is what a trackpad expects. */
  if (position === viewport.scrollLeft) {
    return
  }

  event.preventDefault()
  viewport.scrollLeft = position
}

const onModelChanged = () => {
  const api = gridApi.value
  if (api === null || restoringView) {
    return
  }

  const sortModel: SortModelItem[] = api
    .getColumnState()
    .filter((state) => state.sort !== null && state.sort !== undefined)
    .sort((left, right) => (left.sortIndex ?? 0) - (right.sortIndex ?? 0))
    .map((state) => ({ colId: state.colId, sort: state.sort === 'asc' ? 'asc' : 'desc' }))

  emit('models-changed', sortModel, api.getFilterModel())
}

const onSelectionChanged = () => {
  const api = gridApi.value
  if (api === null) {
    return
  }

  emit(
    'update:selected',
    api.getSelectedNodes().map((node) => String(node.data?.id ?? '')),
  )
}

/**
 * Select or clear every row of the current block, which is what the button of the toolbar asks for.
 */
const setAllSelected = (selected: boolean) => {
  gridApi.value?.selectAll(selected ? 'filtered' : undefined)
  if (!selected) {
    gridApi.value?.deselectAll()
  }
}

/**
 * Drop every column filter the grid holds, so that lifting the filters outside the table also empties the
 * filter inputs inside its headers instead of leaving them showing a restriction that no longer applies.
 */
const clearFilters = () => {
  gridApi.value?.setFilterModel(null)
}

/**
 * Drop the filter of a single column, leaving the rest of them in place.
 */
const clearColumnFilter = (colId: string) => {
  const api = gridApi.value
  if (api === null) {
    return
  }

  const model = { ...api.getFilterModel() }
  delete model[colId]
  api.setFilterModel(model)
}

/**
 * Keep only a side the grid recognises, so a stored value that means nothing to it is simply not pinned.
 */
const readPinnedSide = (pinned: string | boolean | null): 'left' | 'right' | null =>
  pinned === 'left' || pinned === 'right' ? pinned : null

/**
 * Read the presentation of every column the table currently shows, which is what saving a view has to record.
 *
 * The order is the order the columns stand in, drag included, so a view that was rearranged by hand is saved
 * the way it looks rather than the way the backend generated it.
 */
const readColumnLayout = (): GridColumnLayout[] => {
  const api = gridApi.value
  if (api === null) {
    return []
  }

  return api.getColumnState().map((state) => ({
    colId: state.colId,
    visible: state.hide !== true,
    width: state.width ?? null,
    pinned: readPinnedSide(state.pinned ?? null),
  }))
}

/**
 * Read the direction a saved view sorts one column by, if it sorts by it at all.
 */
const readSortOf = (sort: SortSpecification[], colId: string): SortDirection | null =>
  sort.find((specification) => specification.key === colId)?.direction ?? null

/**
 * Read where one column stands in the ordering of a saved view, which is what a multi column sort needs.
 */
const readSortIndexOf = (sort: SortSpecification[], colId: string): number | null => {
  const index = sort.findIndex((specification) => specification.key === colId)

  return index < 0 ? null : index
}

/**
 * Turn the columns of a saved view into the column state the grid applies.
 */
const toColumnState = (state: GridViewState): ColumnState[] =>
  state.columns.map((column) => ({
    colId: column.colId,
    hide: !column.visible,
    width: column.width ?? undefined,
    pinned: readPinnedSide(column.pinned),
    sort: readSortOf(state.sort, column.colId),
    sortIndex: readSortIndexOf(state.sort, column.colId),
  }))

/**
 * Write an ordering into the table itself, so that the toolbar and the headers of the table agree on it.
 *
 * The rows are ordered by the backend and the toolbar is where the inventory is ordered from, but a change of
 * any column filter reads the ordering back out of the table. Without this the table would answer that it is
 * not ordered at all, and picking a column in the toolbar would be undone by the next filter that is typed.
 */
const applySort = (sort: SortSpecification[]) => {
  const api = gridApi.value
  if (api === null) {
    return
  }

  restoringView = true
  try {
    api.applyColumnState({
      state: sort.map((specification, index) => ({
        colId: specification.key,
        sort: specification.direction,
        sortIndex: index,
      })),
      defaultState: { sort: null, sortIndex: null },
    })
  } finally {
    restoringView = false
  }
}

/**
 * Push a whole saved view into the running table - its columns, its ordering and its filters.
 *
 * The filters have to reach the inputs in the headers and not only the query, otherwise the table shows rows
 * that its own headers claim are not filtered. The visibility of the columns travels as a prop and rebuilds
 * the column definitions, which resets the state of every column, so the saved order, width and pinning are
 * only written once that rebuild has landed.
 */
const applyViewState = async (state: GridViewState): Promise<void> => {
  const api = gridApi.value
  if (api === null) {
    return
  }

  restoringView = true
  try {
    await nextTick()
    api.applyColumnState({ state: toColumnState(state), applyOrder: true })
    api.setFilterModel(buildFilterModel(state.filters, filterComponents.value))
    await nextTick()
  } finally {
    restoringView = false
  }
}

defineExpose({ setAllSelected, clearFilters, clearColumnFilter, readColumnLayout, applySort, applyViewState })

/*
 * The theme object is read once when the grid is created, so switching between the dark and the light
 * palette has to be pushed into the running grid instead of waiting for the next mount.
 */
watch([colors, isDark], () => {
  gridApi.value?.setGridOption('theme', buildGridTheme(colors.value, isDark.value))
})

/*
 * The layout is read once as well, so entering and leaving the zoom mode has to be pushed into the running
 * grid rather than waiting for a mount that never comes.
 */
watch(
  () => props.pinned,
  (pinned) => {
    gridApi.value?.setGridOption('domLayout', layoutOf(pinned))
  },
)

watch(
  () => props.expandedIds,
  () => {
    gridApi.value?.refreshCells({ force: true })
    gridApi.value?.resetRowHeights()
  },
  { deep: true },
)
</script>

<style scoped>
/*
 * On the page the table is as tall as the rows it holds and the browser scrolls the whole page, so the rows
 * get the room of the window instead of a letterbox between the toolbar and the pager.
 */
.events-grid {
  position: relative;
  display: flex;
  flex-direction: column;
  inline-size: 100%;
  min-inline-size: 0;
}

.events-grid__table {
  inline-size: 100%;
}

/*
 * On the page the columns are moved with the sticky bar underneath the table, and the bar the grid draws for
 * itself is the one that sits at the foot of a table taller than the window and cannot be reached. Its thumb
 * is hidden so that the end of the table does not show two bars under one another. The strip itself stays, and
 * so does everything it scrolls: the sticky bar is a copy of exactly that movement and writes it back here.
 */
.events-grid:not(.events-grid--pinned) :deep(.ag-body-horizontal-scroll-viewport) {
  scrollbar-width: none;
}

.events-grid:not(.events-grid--pinned) :deep(.ag-body-horizontal-scroll-viewport)::-webkit-scrollbar {
  display: none;
}

/*
 * Zoomed, the table is pinned to the height it was given and scrolls inside its own body, which is what keeps
 * its header on screen while the rows move underneath it.
 */
.events-grid--pinned {
  flex: 1 1 auto;
  min-block-size: 0;
}

.events-grid--pinned .events-grid__table {
  block-size: 100%;
}

.events-grid__overlay {
  /* Far enough down that the spinner clears the header of the table rather than covering it. */
  --events-grid-spinner-clearance: 4rem;

  /* Where the spinner comes to rest against the top of the window once the page is scrolled. */
  --events-grid-spinner-inset: 1rem;

  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background-color: rgba(var(--v-theme-surface), 0.55);
  border-radius: 0.75rem;
}

/*
 * A page of rows is taller than the window, so a spinner centred over the whole table would be reloading it
 * somewhere off screen. Sticking to the top of whatever part of the table is on screen keeps it in sight.
 */
.events-grid__spinner {
  position: sticky;
  inset-block-start: var(--events-grid-spinner-inset);
  padding-block-start: var(--events-grid-spinner-clearance);
}

.events-grid__empty {
  padding-block: 3rem;
  text-align: center;
  opacity: 0.7;
}

/* Pinned there is no room underneath the table for the message, so it is centred over the empty body instead. */
.events-grid--pinned .events-grid__empty {
  position: absolute;
  inset-block-start: 50%;
  inset-inline: 0;
  padding-block: 0;
}

/* Use for hidding scrollbar */
/* :deep(.ag-body-horizontal-scroll) {
  visibility: hidden;
} */
</style>
