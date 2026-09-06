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

    <!--
      The listing of an assumption carries neither its values nor its industries, so every row has to be read
      on its own before the table can filter or colour by either. That takes one request per assumption and
      there is no endpoint that would make it fewer, so the table is usable while it happens and says so.
    -->
    <div
      v-if="completing"
      class="register__progress"
    >
      <v-progress-linear
        :model-value="progressPercent"
        color="primary"
        height="4"
        rounded
      />
      <span class="register__progress-label">
        Reading assumption details — {{ progress.completed }} of {{ progress.total }}. Values and industries
        appear as they arrive.
      </span>
    </div>

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
const { assumptions, industries, fields, completing, progress, findIndustry, refreshAssumption } = useRegister()
const { notify, reportError } = useSnackbar()

const industry = computed<string | null>(() => props.industry)
const { controller } = useAssumptionsGrid({ assumptions, fields, industry })

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

const progressPercent = computed<number>(() =>
  progress.value.total === 0 ? 0 : (progress.value.completed / progress.value.total) * 100,
)

const emptyMessage = computed<string>(() =>
  assumptions.value.length === 0
    ? 'No assumptions have been created yet.'
    : 'No assumptions match what you are looking for.',
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
 * Read the assumption that was just created, so that it appears in the table without the page being reloaded.
 */
const onCreated = async (assumptionId: string) => {
  try {
    const detail = await refreshAssumption(assumptionId)
    assumptions.value = [{ ...detail, detail }, ...assumptions.value.filter((row) => row.id !== assumptionId)]
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

.register__progress {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.register__progress-label {
  font-size: 0.8125rem;
  color: rgb(var(--v-theme-app-muted));
}

.register__empty {
  padding-block: 2rem;
  text-align: center;
  color: rgb(var(--v-theme-app-muted));
}
</style>
