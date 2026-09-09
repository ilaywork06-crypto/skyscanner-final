<template>
  <div class="register">
    <RegisterToolbar
      :search="controller.search.value"
      :columns="columns"
      :hidden-columns="hiddenColumns"
      :total="controller.total.value"
      :exporting="exporting"
      @update:search="onSearch"
      @toggle-column="onToggleColumn"
      @create="createOpen = true"
      @export="onExportSheet"
      @export-bundle="onExportBundle"
      @import="importOpen = true"
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
        {{ t('register.reading', { done: progress.completed, total: progress.total }) }}
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

    <ImportBundleDialog
      v-model="importOpen"
      @restored="onRestored"
    />
  </div>
</template>

<script lang="ts">
import type { GeneratedColumn, ScopeFilter, TaxonomyItem } from '@truth-platform/core-ui'

interface Props {
  /**
   * The industry whose register this is, named by its identifier.
   *
   * Required, because there is no longer a table of every industry at once. An assumption is always read
   * under the industry it was filed under, and a page that showed all of them together answered a question
   * nobody was asking - so the narrowing is what the table is rather than something applied to it.
   */
  industry: string
}
</script>

<script setup lang="ts">
import {
  ActiveFilters,
  PaginationBar,
  QuickFilters,
  downloadBlob,
  hashedToken,
  useLanguage,
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
import ImportBundleDialog from '@/components/ImportBundleDialog.vue'
import { useAssumptionsGrid } from '@/composables/useAssumptionsGrid'
import { useRegister } from '@/composables/useRegister'
import { readLatestAssumption } from '@/requests/assumptions'
import { buildBundle, bundleFileName, writeBundle } from '@/utils/bundle'
import { exportRows } from '@/utils/export'
import { readCreator } from '@/utils/identity'

const props = defineProps<Props>()

const router = useRouter()
const {
  assumptions,
  industries,
  schemaDetails,
  fields,
  completing,
  progress,
  findIndustry,
  refreshAssumption,
} = useRegister()
const { notify, reportError } = useSnackbar()
const { t } = useLanguage()

const industry = computed<string | null>(() => props.industry)
const { controller } = useAssumptionsGrid({ assumptions, fields, industry })

const grid = ref<InstanceType<typeof AssumptionsGrid> | null>(null)
const createOpen = ref<boolean>(false)
const importOpen = ref<boolean>(false)
const hiddenColumns = ref<string[]>([])
const exporting = ref<boolean>(false)

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

/*
 * The industry the register is narrowed to, shown as a chip so that it can be seen. It cannot be lifted -
 * lifting it would land on a register of every industry, which is the page that no longer exists - so the
 * chip names what is being read rather than offering a way out of it.
 */
const scope = computed<ScopeFilter | null>(() => ({
  field: t('column.industry'),
  value: findIndustry(props.industry)?.name ?? props.industry,
}))

const progressPercent = computed<number>(() =>
  progress.value.total === 0 ? 0 : (progress.value.completed / progress.value.total) * 100,
)

const emptyMessage = computed<string>(() =>
  assumptions.value.length === 0 ? t('register.empty') : t('register.emptyNarrowed'),
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
  }

  /*
   * The industry chip is the one chip that cannot be lifted. It is not a filter somebody applied to this
   * table - it is which table this is - so pressing it does nothing rather than landing the reader on a
   * register of everything, which is not a page this client has.
   */
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
 * Take up the register a restore has just rewritten.
 *
 * A restore creates rows, industries and declarations at once, and the dialog has already read the whole
 * register again by the time this runs - so there is nothing to splice in here, only a table to redraw
 * against what is now held.
 */
const onRestored = async () => {
  try {
    await controller.refreshConfiguration()
    await controller.refreshRows()
  } catch (error) {
    reportError(error)
  }
}

/**
 * Write the rows the table is currently showing out as a spreadsheet.
 *
 * This is the export for a person: it carries the columns that were on screen, in the order they were on
 * screen, with every value flattened into the one cell a sheet holds it in. That flattening is exactly what
 * makes it something to read rather than something to restore, which is what the bundle below is for.
 */
const onExportSheet = () => {
  try {
    exportRows(controller.rows.value, columns.value.filter((column) => visibleColumns.value.includes(column.colId)))
    notify(t('register.exported'), 'success')
  } catch (error) {
    reportError(error)
  }
}

/**
 * Write this industry's register out whole, in the shapes the API creates things in.
 *
 * Every assumption of the industry is carried, not the page on screen and not the columns on screen: a
 * bundle is what puts the register back, and half of one puts half a register back. The rows the register
 * has not finished reading are read here, one at a time up to a few at once, because their values and their
 * industries arrive with nothing else.
 */
const onExportBundle = async () => {
  exporting.value = true
  try {
    const rows = assumptions.value.filter((row) =>
      row.detail === null
        ? true
        : row.detail.industries.some(
            (item) => item.id === props.industry || item.name === props.industry,
          ),
    )

    const details = await Promise.all(
      rows.map(async (row) => row.detail ?? (await readLatestAssumption(row.id))),
    )
    /*
     * A row whose reading had not landed could not be narrowed to the industry before it was read, so the
     * narrowing is applied again now that every one of them has been.
     */
    const scoped = details.filter((detail) =>
      detail.industries.some((item) => item.id === props.industry || item.name === props.industry),
    )

    const named = new Set(scoped.flatMap((detail) => detail.schemas.map((schema) => schema.name)))
    const bundle = buildBundle({
      industry: findIndustry(props.industry)?.name ?? props.industry,
      industries: industries.value,
      schemas: [...schemaDetails.value.values()].filter((schema) => named.has(schema.name)),
      assumptions: scoped,
      creator: readCreator(),
    })

    downloadBlob(
      new Blob([writeBundle(bundle)], { type: 'application/json' }),
      bundleFileName(findIndustry(props.industry)?.name ?? null),
    )
    notify(t('register.exported'), 'success')
  } catch (error) {
    reportError(error)
  } finally {
    exporting.value = false
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
