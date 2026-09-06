<template>
  <div
    ref="root"
    class="assumptions-grid"
  >
    <AgGridVue
      v-if="gridOptions !== null"
      class="assumptions-grid__table"
      :grid-options="gridOptions"
      :column-defs="columnDefs"
      :row-data="rows"
      :context="context"
      :theme="gridTheme"
      @grid-ready="onGridReady"
      @sort-changed="onModelChanged"
      @filter-changed="onModelChanged"
    />

    <div
      v-if="loading"
      class="assumptions-grid__overlay"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>
  </div>
</template>

<script lang="ts">
import type {
  GeneratedColumn,
  GeneratedGridConfiguration,
  GridContext,
  GridRow,
  TaxonomyItem,
} from '@truth-platform/core-ui'
import type { FilterModel, SortModelItem } from 'ag-grid-community'

/**
 * What the panel under a row needs on top of what every table's cells need.
 *
 * The panel renders the schema declared attributes of its row, and only the table knows which columns those
 * currently are, so they travel with the rest of the context.
 */
interface AssumptionGridContext extends GridContext {
  columns: GeneratedColumn[]
}

interface Props {
  configuration: GeneratedGridConfiguration | null
  rows: GridRow[]
  sourceRows: GridRow[]
  loading: boolean
  expandedIds: string[]
  search: string
  taxonomy: TaxonomyItem[]
  visibleColumns: string[]
}

interface Emits {
  (event: 'toggle-expanded', rowId: string): void
  (event: 'open-row', rowId: string): void
  (event: 'models-changed', sort: SortModelItem[], filters: FilterModel): void
}

export type { AssumptionGridContext }

/** What an open panel is given before it has rendered and can be measured. */
const DEFAULT_DETAIL_HEIGHT = 260

/** How far a measurement has to move before the table is worth resetting its row heights for. */
const HEIGHT_TOLERANCE = 2
</script>

<script setup lang="ts">
import {
  SET_FILTER_TYPE,
  buildGridOptions,
  isDetailRow,
  parseColumnDefinitions,
  registerGridModules,
} from '@truth-platform/ag-grid-ts'
import { buildGridTheme, hashedToken, useAppTheme, useCellRenderers, useColumnFilters } from '@truth-platform/core-ui'
import type { ColDef, GridApi, GridOptions, GridReadyEvent } from 'ag-grid-community'
import { AgGridVue } from 'ag-grid-vue3'
import { computed, ref, shallowRef } from 'vue'

import AssumptionDetailRow from '@/components/AssumptionDetailRow.vue'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

registerGridModules()

/*
 * The panel opened under a row is the one renderer only this product can draw, so it is registered on top of
 * the ones every table shares.
 */
const registry = useCellRenderers()
const filterRegistry = useColumnFilters()
const { colors, isDark } = useAppTheme()

const root = ref<HTMLElement | null>(null)
const gridApi = shallowRef<GridApi<GridRow> | null>(null)

/*
 * What each open panel measured. The heights are kept here rather than left to the row itself because the
 * table resets every row height whenever a panel is opened or closed.
 */
const detailHeights = ref<Record<string, number>>({})

const context = computed<AssumptionGridContext>(() => ({
  taxonomy: props.taxonomy,
  columns: props.configuration?.columns ?? [],
  expandedIds: props.expandedIds,
  toggleExpanded: (rowId: string) => emit('toggle-expanded', rowId),
  openRow: (rowId: string) => emit('open-row', rowId),
  /* Nothing in this API stores a file, so the two artifact actions are here only to satisfy the contract. */
  openArtifact: () => undefined,
  downloadArtifact: () => undefined,
  findRow: (rowId: string) => props.sourceRows.find((row) => String(row.id) === rowId),
  /*
   * An assumption carries no status of its own in this API, so a coloured value is coloured by its own name.
   * That is stable, so the same word is always painted the same way wherever it appears.
   */
  tokenFor: (value: string) => hashedToken(value),
  reportDetailHeight: (parentId: string, height: number) => rememberDetailHeight(parentId, height),
  search: props.search,
}))

/**
 * How tall one open panel is drawn, which is what it measured or the estimate it has not replaced yet.
 */
const detailHeight = (parentId: string): number => detailHeights.value[parentId] ?? DEFAULT_DETAIL_HEIGHT

/*
 * The visibility of a column belongs in the definition only at the moment the grid is built; afterwards the
 * table owns it, which is why the definitions are recomputed while the options are not.
 */
const columnDefs = computed<ColDef<GridRow>[]>(() =>
  props.configuration === null
    ? []
    : parseColumnDefinitions(props.configuration, {
        registry,
        filters: filterRegistry,
        visibleColumns: props.visibleColumns,
      }),
)

/*
 * The palette of the table is bound as a prop of its own rather than folded into the grid options.
 *
 * The options are read once, when the grid builds itself, so a theme that lived in them stayed on whichever
 * one was active at that moment - switching to the light theme repainted the page around a table still
 * lettered for the dark one. As a prop it is watched, and the table follows the switch.
 */
const gridTheme = computed(() => buildGridTheme(colors.value, isDark.value))

const gridOptions = computed<GridOptions<GridRow> | null>(() => {
  if (props.configuration === null) {
    return null
  }

  const rowHeight = props.configuration.rowHeight
  const options = buildGridOptions({
    configuration: props.configuration,
    registry,
    filters: filterRegistry,
    visibleColumns: props.visibleColumns,
  })

  return {
    ...options,
    domLayout: 'autoHeight',
    suppressNoRowsOverlay: true,
    fullWidthCellRenderer: AssumptionDetailRow,
    getRowHeight: (params) =>
      isDetailRow(params.data) ? detailHeight(String(params.data?.parentId ?? '')) : rowHeight,
  }
})

/**
 * Remember what one open panel measured, and give its row exactly that.
 *
 * A row of the table is given its height before anything is drawn inside it, so the table can only estimate
 * the panel; the panel measures itself instead and says so, and the row is then given what it actually needs.
 *
 * The height is written onto the row itself rather than left to be recalculated. Asking the table to reset
 * its heights does not send it back to `getRowHeight` for a row it has already measured, so the panel would
 * report the height it needs and keep the estimate it was given - which is what cuts a tall panel off.
 */
const rememberDetailHeight = (parentId: string, height: number) => {
  const rounded = Math.ceil(height)
  if (Math.abs(detailHeight(parentId) - rounded) < HEIGHT_TOLERANCE) {
    return
  }

  detailHeights.value = { ...detailHeights.value, [parentId]: rounded }

  const api = gridApi.value
  if (api === null) {
    return
  }

  /* The panel's own row is the one carrying this parent, whatever identifier the page gave it. */
  api.forEachNode((node) => {
    if (isDetailRow(node.data) && String(node.data?.parentId ?? '') === parentId) {
      node.setRowHeight(rounded)
    }
  })
  api.onRowHeightChanged()
}

const onGridReady = (event: GridReadyEvent<GridRow>) => {
  gridApi.value = event.api
}

/**
 * Hand the ordering and the narrowing the table is running back to whoever owns the query.
 */
const onModelChanged = () => {
  const api = gridApi.value
  if (api === null) {
    return
  }

  const sortModel: SortModelItem[] = api
    .getColumnState()
    .filter((state) => state.sort === 'asc' || state.sort === 'desc')
    .map((state) => ({ colId: state.colId, sort: state.sort === 'desc' ? 'desc' : 'asc' }))

  emit('models-changed', sortModel, api.getFilterModel())
}

defineExpose({
  /** Lift the narrowing one column is under, which is what a chip of the active filters undoes. */
  clearColumnFilter: (colId: string) => {
    void gridApi.value?.setColumnFilterModel(colId, null).then(() => gridApi.value?.onFilterChanged())
  },
  /** Lift every narrowing at once. */
  clearFilters: () => {
    void gridApi.value?.setFilterModel(null)
  },
  /** Show or hide one column, which is what the column picker of the toolbar does. */
  setColumnVisible: (colId: string, visible: boolean) => {
    gridApi.value?.setColumnsVisible([colId], visible)
  },
  /**
   * Narrow one column to a set of values, which is what a quick filter above the table does.
   *
   * It is written into the table's own filter model rather than alongside it, so that the pill above the
   * table and the filter in its header can never disagree about what is being shown.
   */
  setColumnFilterValues: (colId: string, values: string[]) => {
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
    void api.setFilterModel(model)
  },
})
</script>

<style scoped>
.assumptions-grid {
  position: relative;
  display: flex;
  flex-direction: column;
  min-inline-size: 0;
}

.assumptions-grid__table {
  inline-size: 100%;
}

/*
 * The spinner is laid over the table rather than replacing it, so that a reload does not empty the screen and
 * throw the reader's place away with it.
 */
.assumptions-grid__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(var(--v-theme-background), 0.55);
  pointer-events: none;
}
</style>
