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

/* The context of the table is the shared contract every cell renderer reads, exactly as it is declared. */
type InventoryGridContext = GridContext

/*
 * What a panel is expected to measure, used for the one frame between the row being given a height and the
 * panel inside it reporting the height it actually turned out to be. Everything after that frame is the
 * measurement rather than the guess, so these only have to be close enough not to jump.
 */

/** The chrome of an expanded panel: its own padding and the gaps between the tables inside it. */
const DETAIL_ROW_PADDING = 56

/**
 * The table of the attributes of the event itself, which every panel opens with.
 *
 * It is one heading, one header row and one row of values whatever the event holds, so it costs the same
 * whether the event carries two declared fields or twenty - those widen the table rather than lengthen it.
 */
const DETAIL_ATTRIBUTES_HEIGHT = 96

/**
 * An event without a single entity still shows the invitation to add one, and a panel shorter than this
 * cuts into it.
 */
const DETAIL_ROW_MIN_HEIGHT = 264

/** What a section spends before its first entity: its heading and the header row of its table. */
const DETAIL_ENTITY_SECTION_CHROME = 72

/** One entity of a section, matching the padding the entity table renders its cells with. */
const DETAIL_ENTITY_ROW_HEIGHT = 52

/**
 * An event with hundreds of entities would otherwise reserve a row taller than any screen and leave the table
 * unusable, so past this the panel does scroll inside itself after all.
 */
const DETAIL_ROW_MAX_HEIGHT = 1400

/** A measurement less than this away from the height the row already has is not worth a relayout. */
const DETAIL_HEIGHT_EPSILON = 1

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
import {
  SET_FILTER_TYPE,
  buildFilterModel,
  buildGridOptions,
  isDetailRow,
  parseColumnDefinitions,
} from '@skyscanner/ag-grid-ts'
import { AgGridVue } from 'ag-grid-vue3'
import { computed, nextTick, ref, shallowRef, watch } from 'vue'

import DetailRowRenderer from '@/components/cells/DetailRowRenderer.vue'
import StickyScrollBar from '@/components/inventory/StickyScrollBar.vue'
import { useAppTheme } from '@/composables/useAppTheme'
import { useCellRenderers, useColumnFilters } from '@/composables/useCellRenderers'
import { buildGridTheme } from '@/utils/grid-theme'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const registry = useCellRenderers()
const filterRegistry = useColumnFilters()
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
  reportDetailHeight: (parentId: string, height: number) => rememberDetailHeight(parentId, height),
  search: props.search,
}))

/*
 * What each open panel measured. The heights are kept here rather than left to the row itself because the
 * table resets every row height whenever a panel is opened or closed, and a measurement that did not survive
 * that reset would be taken, thrown away and taken again on every toggle.
 */
const measuredDetailHeights = new Map<string, number>()

/**
 * Take the height a panel reported and give its row exactly that, unless it already has it.
 */
const rememberDetailHeight = (parentId: string, height: number) => {
  const rounded = Math.ceil(height)
  if (Math.abs((measuredDetailHeights.get(parentId) ?? 0) - rounded) < DETAIL_HEIGHT_EPSILON) {
    return
  }

  measuredDetailHeights.set(parentId, rounded)
  gridApi.value?.resetRowHeights()
}

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
 * Say how tall the row of one expanded event has to be.
 *
 * The panel that has already drawn itself answers this itself, and what it reports is what its row gets, so
 * there is never a band of empty table underneath it nor a panel cut off inside it. Only the frame before
 * that first measurement is estimated, out of the entity counts the row carries, and a hopelessly crowded
 * panel is capped so that one row can never swallow the whole table.
 */
const detailHeight = (parentId: string): number => {
  const measured = measuredDetailHeights.get(parentId)
  if (measured !== undefined) {
    return Math.min(DETAIL_ROW_MAX_HEIGHT, measured)
  }

  const parent = props.sourceRows.find((row) => String(row.id) === parentId)
  const sections = parent === undefined ? [] : readEntitySections(parent)
  const expected = sections.reduce(
    (total, entities) => total + DETAIL_ENTITY_SECTION_CHROME + entities * DETAIL_ENTITY_ROW_HEIGHT,
    DETAIL_ROW_PADDING + DETAIL_ATTRIBUTES_HEIGHT,
  )

  return Math.min(DETAIL_ROW_MAX_HEIGHT, Math.max(DETAIL_ROW_MIN_HEIGHT, expected))
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
 * along with it: a changed schema would rebuild the object and change nothing on screen. The column
 * definitions therefore travel as their own prop, which the Vue wrapper does watch and does push into the
 * running grid.
 *
 * Which columns are *shown* is deliberately not part of this. Handing the grid a new set of definitions makes
 * it build its columns again from scratch, and a column built again is a column whose filter was thrown away
 * - so ticking a box in the Columns menu, or loading a saved view, used to silently drop every filter the
 * table was running. Visibility is state rather than declaration, and it is written as state below.
 */
const columnDefs = computed<ColDef<GridRow>[]>(() =>
  props.configuration === null ? [] : parseColumnDefinitions(props.configuration, { registry, filters: filterRegistry }),
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
  /* Read once, when the grid is built, which is the one moment the visibility belongs in a definition. */
  const options = buildGridOptions({
    configuration: props.configuration,
    registry,
    filters: filterRegistry,
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
 * Narrow one column to a set of values, which is what the quick filters above the table ask for.
 *
 * The pick is written into the filter of the column rather than kept beside the table, so it reaches the
 * header of that column, the chips that name every active restriction, and the view that gets saved - one
 * pick, one place it lives, and one way it is lifted again.
 */
const setColumnFilterValues = (colId: string, values: string[]) => {
  const api = gridApi.value
  if (api === null) {
    return
  }

  const model = { ...api.getFilterModel() }
  if (values.length === 0) {
    delete model[colId]
  } else {
    model[colId] = { filterType: SET_FILTER_TYPE, values: [...values] }
  }
  api.setFilterModel(model)
}

/**
 * Show exactly the columns that were asked for, without rebuilding a single column definition.
 *
 * Only the columns the configuration declares are written: the tick box column is the grid's own and appears
 * in its state without ever appearing in the configuration, so a blanket write would hide it.
 */
const applyVisibility = (visible: string[]) => {
  const api = gridApi.value
  const declared = props.configuration?.columns ?? []
  if (api === null || declared.length === 0) {
    return
  }

  const shown = new Set(visible)
  api.applyColumnState({
    state: declared.map((column) => ({ colId: column.colId, hide: !shown.has(column.colId) })),
  })
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

/**
 * Put the running table back the way the backend generated it - every column at its declared place and width,
 * no filter in any header, and the ordering the configuration asked for.
 *
 * The visibility travels as a prop and rebuilds the column definitions, which is what resets the state of
 * every column, so the reset is written only once that rebuild has landed - the same reason a saved view is
 * restored the way it is.
 */
const resetView = async (sort: SortSpecification[]): Promise<void> => {
  const api = gridApi.value
  if (api === null) {
    return
  }

  restoringView = true
  try {
    await nextTick()
    api.resetColumnState()
    api.setFilterModel(null)
    api.applyColumnState({
      state: sort.map((specification, index) => ({
        colId: specification.key,
        sort: specification.direction,
        sortIndex: index,
      })),
      defaultState: { sort: null, sortIndex: null },
    })
    await nextTick()
  } finally {
    restoringView = false
  }
}

defineExpose({
  setAllSelected,
  clearFilters,
  clearColumnFilter,
  setColumnFilterValues,
  readColumnLayout,
  applySort,
  applyViewState,
  resetView,
})

/*
 * Showing and hiding a column is written straight into the running grid rather than through a rebuild of the
 * column definitions, which is what lets a table keep the filters it is running while its columns change.
 * A view being restored writes its own visibility along with the rest of itself, so this stands down for it.
 */
watch(
  () => props.visibleColumns,
  (visible) => {
    if (!restoringView) {
      applyVisibility(visible)
    }
  },
  { deep: true },
)

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

/*
 * Which rows are open travels to the cells inside the context of the table, and the wrapper pushes a changed
 * context into the running grid with a watcher of its own. That watcher is created when the grid mounts,
 * which is after this one, so redrawing the cells here used to redraw them against the context of the
 * previous state: the arrow of the row that was just opened kept pointing the way it did before, and every
 * toggle after it was one behind. The context is therefore written into the grid first and the cells are
 * redrawn against it, so the arrow and the panel underneath it always tell the same story.
 */
watch(
  () => props.expandedIds,
  () => {
    const api = gridApi.value
    if (api === null) {
      return
    }

    api.setGridOption('context', context.value)
    api.refreshCells({ force: true })
    api.resetRowHeights()
  },
  { deep: true },
)

/*
 * A block of rows that was replaced - another page, another filter - carries panels that were never opened,
 * and the heights measured for the rows that went with it are no longer about anything. The rows that stayed
 * keep theirs: their panels are still mounted and still that tall, and nothing would measure them again.
 */
watch(
  () => props.sourceRows,
  (rows) => {
    const present = new Set(rows.map((row) => String(row.id)))
    measuredDetailHeights.forEach((_, parentId) => {
      if (!present.has(parentId)) {
        measuredDetailHeights.delete(parentId)
      }
    })
  },
)
</script>

<style scoped>
/*
 * On the page the table is as tall as the rows it holds and the browser scrolls the whole page, so the rows
 * get the room of the window instead of a letterbox between the toolbar and the pager.
 */
.events-grid {
  /* The bars of the table are as thin as the sticky one underneath it, whichever of the two is on screen. */
  --events-grid-scrollbar-thickness: 0.875rem;

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
 *
 * The grid draws that strip in three pieces - one under the columns pinned to either side and one under the
 * columns that move - and only the middle one was ever quietened. The two beside it scroll nothing at all, so
 * a browser bar drawn on them is noise wherever it appears, and they are quietened with it.
 */
.events-grid:not(.events-grid--pinned) :deep(.ag-body-horizontal-scroll-viewport),
.events-grid :deep(.ag-horizontal-left-spacer),
.events-grid :deep(.ag-horizontal-right-spacer) {
  scrollbar-width: none;
}

.events-grid:not(.events-grid--pinned) :deep(.ag-body-horizontal-scroll-viewport)::-webkit-scrollbar,
.events-grid :deep(.ag-horizontal-left-spacer)::-webkit-scrollbar,
.events-grid :deep(.ag-horizontal-right-spacer)::-webkit-scrollbar {
  display: none;
}

/*
 * Zoomed there is no sticky bar - the table scrolls inside its own body and its own bars are the ones on
 * screen - so those take the look the sticky one has on the page rather than whatever the browser draws by
 * default, and the two ways of reading the same table look like the same table.
 */
.events-grid--pinned :deep(.ag-body-horizontal-scroll-viewport),
.events-grid--pinned :deep(.ag-body-viewport) {
  scrollbar-width: thin;
  scrollbar-color: rgb(var(--v-theme-control-border)) transparent;
}

.events-grid--pinned :deep(.ag-body-horizontal-scroll-viewport)::-webkit-scrollbar,
.events-grid--pinned :deep(.ag-body-viewport)::-webkit-scrollbar {
  inline-size: var(--events-grid-scrollbar-thickness);
  block-size: var(--events-grid-scrollbar-thickness);
}

.events-grid--pinned :deep(.ag-body-horizontal-scroll-viewport)::-webkit-scrollbar-track,
.events-grid--pinned :deep(.ag-body-viewport)::-webkit-scrollbar-track {
  background: transparent;
}

.events-grid--pinned :deep(.ag-body-horizontal-scroll-viewport)::-webkit-scrollbar-thumb,
.events-grid--pinned :deep(.ag-body-viewport)::-webkit-scrollbar-thumb {
  background-color: rgb(var(--v-theme-control-border));
  border-radius: 999rem;
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
</style>
