<template>
  <div class="register">
    <RegisterToolbar
      :search="controller.search.value"
      :columns="columns"
      :hidden-columns="hiddenColumns"
      :total="controller.total.value"
      @update:search="onSearch"
      @toggle-column="onToggleColumn"
      @create="createOpen = true"
      @export="onExport"
    >
      <template #actions>
        <slot name="actions" />
      </template>
    </RegisterToolbar>


    <QuickFilters
      v-if="quickFilterColumns.length > 0"
      :columns="quickFilterColumns"
      :filters="controller.filterConditions.value"
      @update="onQuickFilter"
    />

    <ActiveFilters
      :search="controller.search.value"
      :scope="scope"
      :filters="controller.filterConditions.value"
      :columns="columns"
      @remove="onRemoveFilter"
      @clear="onClearFilters"
    />

    <AssumptionsGrid
      ref="grid"
      :configuration="controller.configuration.value"
      :rows="controller.displayedRows.value"
      :source-rows="controller.rows.value"
      :loading="controller.loading.value"
      :expanded-ids="controller.expandedIds.value"
      :search="controller.search.value"
      :taxonomy="taxonomy"
      :visible-columns="visibleColumns"
      @toggle-expanded="controller.toggleExpanded"
      @open-row="onOpenRow"
      @models-changed="onModelsChanged"
    />

    <p
      v-if="!controller.loading.value && controller.total.value === 0"
      class="register__empty"
    >
      {{ emptyMessage }}
    </p>

    <PaginationBar
      v-if="controller.total.value > 0"
      :page="controller.page.value"
      :page-count="controller.pageCount.value"
      :page-size="controller.pageSize.value"
      :total="controller.total.value"
      @update:page="controller.goToPage"
      @update:page-size="controller.setPageSize"
    />

    <CreateAssumptionDialog
      v-model="createOpen"
      @created="onCreated"
    />
  </div>
</template>

<script lang="ts">
import type { GeneratedColumn, ScopeFilter, TaxonomyItem } from '@truth-platform/core-ui'

interface Props {
  /** The industry the register is being read under, named by its identifier, or nothing for all of it. */
  industry?: string | null
}
</script>

<script setup lang="ts">
import {
  ActiveFilters,
  PaginationBar,
  QuickFilters,
  hashedToken,
  useSnackbar,
  type FilterChip,
  type QuickFilterChoice,
} from '@truth-platform/core-ui'
import type { FilterModel, SortModelItem } from 'ag-grid-community'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AssumptionsGrid from '@/components/AssumptionsGrid.vue'
import CreateAssumptionDialog from '@/components/CreateAssumptionDialog.vue'
import RegisterToolbar from '@/components/RegisterToolbar.vue'
import { useAssumptionsGrid } from '@/composables/useAssumptionsGrid'
import { useRegister } from '@/composables/useRegister'
import { exportRows } from '@/utils/export'

const props = withDefaults(defineProps<Props>(), { industry: null })

const router = useRouter()
const { industries, fields, findIndustry } = useRegister()
const { notify, reportError } = useSnackbar()

const industry = computed<string | null>(() => props.industry)
const { controller } = useAssumptionsGrid({ fields, industry })

const grid = ref<InstanceType<typeof AssumptionsGrid> | null>(null)
const createOpen = ref<boolean>(false)
const hiddenColumns = ref<string[]>([])

const columns = computed<GeneratedColumn[]>(() => controller.configuration.value?.columns ?? [])

const visibleColumns = computed<string[]>(() =>
  columns.value.filter((column) => !hiddenColumns.value.includes(column.colId)).map((column) => column.colId),
)

const quickFilterColumns = computed<GeneratedColumn[]>(() =>
  columns.value.filter((column) => column.quickFilter && column.filterOptions.length > 0),
)

/* The industries are the vocabulary the chips of the table are coloured from. */
const taxonomy = computed<TaxonomyItem[]>(() =>
  industries.value.map((item) => ({ key: item.name, name: item.name, color: hashedToken(item.name) })),
)

/** The industry the register is narrowed to, shown as a chip so that it can be seen and left. */
const scope = computed<ScopeFilter | null>(() => {
  if (props.industry === null) {
    return null
  }

  return { field: 'Industry', value: findIndustry(props.industry)?.name ?? props.industry }
})

/*
 * The table is never handed the register, so it cannot tell an empty register from an empty answer by
 * looking at what it holds. It asks instead: a narrowed table showing nothing is a search that found
 * nothing, and only a table narrowed by nothing is looking at a register with nothing in it.
 */
const narrowed = computed<boolean>(
  () => controller.search.value.length > 0 || controller.filterConditions.value.length > 0,
)

const emptyMessage = computed<string>(() =>
  narrowed.value ? 'No assumptions match what you are looking for.' : 'No assumptions have been created yet.',
)

const onSearch = async (term: string) => {
  controller.search.value = term
  await controller.goToPage(1)
}

const onToggleColumn = (colId: string, visible: boolean) => {
  hiddenColumns.value = visible
    ? hiddenColumns.value.filter((candidate) => candidate !== colId)
    : [...hiddenColumns.value, colId]
  grid.value?.setColumnVisible(colId, visible)
}

const onModelsChanged = (sort: SortModelItem[], filters: FilterModel) => {
  void controller.applyGridModels(sort, filters)
}

/* A quick filter is the column's own filter set from outside it, so the table stays its single owner. */
const onQuickFilter = (choice: QuickFilterChoice) => {
  grid.value?.setColumnFilterValues(choice.colId, choice.values)
}

const onRemoveFilter = (chip: FilterChip) => {
  if (chip.kind === 'column') {
    grid.value?.clearColumnFilter(chip.colId)

    return
  }

  if (chip.kind === 'search') {
    void onSearch('')

    return
  }

  /* Leaving the industry means leaving its page, because that is what the narrowing came from. */
  void router.push('/assumptions')
}

const onClearFilters = () => {
  controller.search.value = ''
  grid.value?.clearFilters()
  void controller.refreshRows()
}

const onOpenRow = (rowId: string) => {
  void router.push(`/assumptions/${rowId}`)
}

/**
 * Show the assumption that was just created, by asking the register again rather than by splicing it in.
 *
 * The table shows one window of an answer it did not compute, so where a new assumption belongs in that
 * answer - or whether it belongs in the window at all - is the register's to say and not this page's.
 */
const onCreated = async () => {
  try {
    await controller.refreshRows()
  } catch (error) {
    reportError(error)
  }
}

/**
 * Write the rows the table is currently showing out as a spreadsheet.
 */
const onExport = () => {
  try {
    exportRows(controller.rows.value, columns.value.filter((column) => visibleColumns.value.includes(column.colId)))
    notify('The current view was exported', 'success')
  } catch (error) {
    reportError(error)
  }
}

onMounted(async () => {
  await controller.refreshConfiguration()
  await controller.refreshRows()
})

/* Leaving one industry for another narrows the very same table rather than building a second one. */
watch(industry, async () => {
  await controller.refreshConfiguration()
  await controller.goToPage(1)
})
</script>

<style scoped>
.register {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-inline-size: 0;
}

.register__empty {
  padding-block: 2rem;
  text-align: center;
  color: rgb(var(--v-theme-app-muted));
}
</style>
