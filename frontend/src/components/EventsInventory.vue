<template>
  <div
    class="inventory"
    :class="{ 'inventory--zoomed': fullscreen }"
  >
    <EventsToolbar
      :search="controller.search.value"
      :parse-state="parseState"
      :sort-key="sortKey"
      :sort-direction="sortDirection"
      :columns="columns"
      :visible-columns="visibleColumns"
      :templates="templates"
      :selected-count="selectedIds.length"
      :archiving="archiving"
      :fullscreen="fullscreen"
      @update:search="onSearch"
      @update:parse-state="onParseState"
      @update:sort="onSort"
      @toggle-column="onToggleColumn"
      @apply-template="onApplyTemplate"
      @save-template="onOpenSaveTemplate"
      @export="onExport"
      @download-files="onDownloadFiles"
      @select-all="onSelectAll"
      @create="createDialog = true"
      @toggle-fullscreen="fullscreen = !fullscreen"
    />

    <ActiveFilters
      :search="controller.search.value"
      :parse-state="parseState"
      :filters="controller.filterConditions.value"
      :columns="columns"
      @remove="onRemoveFilter"
      @clear="onClearFilters"
    />

    <ExpandedRows
      :expanded-ids="controller.expandedIds.value"
      :rows="controller.rows.value"
      @collapse="controller.toggleExpanded"
      @collapse-all="controller.collapseAll"
    />

    <EventsGrid
      ref="grid"
      :configuration="controller.configuration.value"
      :rows="controller.displayedRows.value"
      :source-rows="controller.rows.value"
      :loading="controller.loading.value"
      :expanded-ids="controller.expandedIds.value"
      :selected-ids="selectedIds"
      :industries="industries"
      :visible-columns="visibleColumns"
      :search="controller.search.value"
      :industry="industry"
      :pinned="fullscreen"
      @toggle-expanded="controller.toggleExpanded"
      @update:selected="onSelectionChanged"
      @open-event="onOpenEvent"
      @open-artifact="onOpenArtifact"
      @download="onDownload"
      @models-changed="onModelsChanged"
    />

    <FileViewerDialog
      v-model="viewerDialog"
      :artifact="viewedArtifact"
      @download="onDownload"
    />

    <PaginationBar
      :page="controller.page.value"
      :page-size="controller.pageSize.value"
      :page-count="controller.pageCount.value"
      :total="controller.total.value"
      @update:page="controller.goToPage"
      @update:page-size="controller.setPageSize"
    />

    <CreateEventDialog
      v-model="createDialog"
      :default-industry="industry"
      @created="onCreated"
    />

    <v-dialog
      v-model="templateDialog"
      max-width="28rem"
      @update:model-value="onTemplateDialogToggle"
    >
      <v-card>
        <v-card-title>Save the current view</v-card-title>
        <v-card-text class="inventory__dialog">
          <v-text-field
            v-model="templateName"
            label="Name"
          />
          <v-text-field
            v-model="templateDescription"
            label="Description"
          />
          <v-checkbox
            v-model="templateShared"
            label="Share with other users"
            hide-details
          />
          <p class="inventory__dialog-hint">
            {{
              templateShared
                ? 'Every user of the system will see this view.'
                : 'This view stays private and is kept in this browser only.'
            }}
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="onCancelSaveTemplate"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            @click="onSaveTemplate"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!--
      Loading a template replaces the whole view, and the columns, ordering and filters the user arranged by
      hand are nowhere else. Rather than dropping them without a word, the switch is named first and the view
      that is about to be lost can be kept as a template of its own.
    -->
    <v-dialog
      v-model="switchDialog"
      max-width="32rem"
    >
      <v-card>
        <v-card-title>Switch to another view?</v-card-title>
        <v-card-text>
          <p>
            The columns, ordering and filters of the current view were changed and are not saved anywhere.
            Loading <strong>{{ pendingTemplateName }}</strong> replaces them.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-btn
            variant="text"
            @click="onCancelSwitch"
          >
            Cancel
          </v-btn>
          <v-spacer />
          <v-btn
            variant="text"
            @click="onSaveBeforeSwitch"
          >
            SAVE CURRENT VIEW FIRST
          </v-btn>
          <v-btn
            color="primary"
            @click="onConfirmSwitch"
          >
            SWITCH ANYWAY
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import type { FilterModel, SortModelItem } from 'ag-grid-community'
import type { FilterChip } from '@/components/ActiveFilters.vue'
import type { GridColumnLayout } from '@/components/EventsGrid.vue'
import type { ExportChoice } from '@/components/EventsToolbar.vue'
import type { Artifact, ParseState } from '@/models/common'
import type { GeneratedColumn } from '@/models/grid'
import type { SortDirection, SortSpecification } from '@/models/query'
import type { TableTemplate, TemplateColumn } from '@/models/template'

interface Props {
  industry: string | null
}

const SEARCH_DEBOUNCE_MS = 350

/** The key that leaves the zoomed table, which is the way out every full screen view of a browser offers. */
const ESCAPE_KEY = 'Escape'
</script>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import ActiveFilters from '@/components/ActiveFilters.vue'
import CreateEventDialog from '@/components/CreateEventDialog.vue'
import EventsGrid from '@/components/EventsGrid.vue'
import EventsToolbar from '@/components/EventsToolbar.vue'
import FileViewerDialog from '@/components/FileViewerDialog.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import ExpandedRows from '@/components/inventory/ExpandedRows.vue'
import { buildExportRequest, useEventsGrid } from '@/composables/useEventsGrid'
import { useSnackbar } from '@/composables/useSnackbar'
import { useIndustries } from '@/composables/useIndustries'
import { downloadArtifact } from '@/requests/storage'
import { createTemplate, downloadEventFiles, exportEvents, listTemplates } from '@/requests/templates'
import { downloadBlob } from '@/utils/download'

const props = defineProps<Props>()

const router = useRouter()
const { industries } = useIndustries()
const { notify, reportError } = useSnackbar()

const controller = useEventsGrid(props.industry)

const grid = ref<InstanceType<typeof EventsGrid> | null>(null)
const templates = ref<TableTemplate[]>([])
const visibleColumns = ref<string[]>([])
const selectedIds = ref<string[]>([])
const createDialog = ref<boolean>(false)
const templateDialog = ref<boolean>(false)
const switchDialog = ref<boolean>(false)
const viewerDialog = ref<boolean>(false)
const viewedArtifact = ref<Artifact | null>(null)
const archiving = ref<boolean>(false)
const fullscreen = ref<boolean>(false)
const templateName = ref<string>('')
const templateDescription = ref<string>('')
const templateShared = ref<boolean>(false)

/*
 * The template that is waiting for an answer about the unsaved view, and the fingerprint of the view as it was
 * last saved or loaded. A view that has no fingerprint yet - the table has not finished building itself - is
 * treated as saved, because there is nothing the user arranged that could be lost.
 */
const pendingTemplate = ref<TableTemplate | null>(null)
const savedFingerprint = ref<string | null>(null)

let searchTimer: ReturnType<typeof setTimeout> | null = null

const columns = computed<GeneratedColumn[]>(() => controller.configuration.value?.columns ?? [])
const parseState = computed<ParseState>(() => controller.parseState.value as ParseState)
const sortKey = computed<string>(() => controller.sortSpecifications.value[0]?.key ?? 'created_at')
const sortDirection = computed<SortDirection>(() => controller.sortSpecifications.value[0]?.direction ?? 'desc')
const pendingTemplateName = computed<string>(() => pendingTemplate.value?.name ?? '')

/**
 * Read the presentation of the columns the way a template stores it, taken from the running table so that a
 * column that was dragged, resized or pinned by hand is saved as it looks.
 *
 * A table that has not built itself yet has no state to read, and the generated configuration stands in for it.
 */
const readTemplateColumns = (): TemplateColumn[] => {
  const declared = new Set(columns.value.map((column) => column.colId))
  const layout = (grid.value?.readColumnLayout() ?? []).filter((column) => declared.has(column.colId))
  const generated: GridColumnLayout[] = columns.value.map((column) => ({
    colId: column.colId,
    visible: visibleColumns.value.includes(column.colId),
    width: column.width,
    pinned: column.pinned,
  }))
  const source: GridColumnLayout[] = layout.length > 0 ? layout : generated

  return source.map((column, index) => ({
    key: column.colId,
    visible: column.visible,
    order: index,
    width: column.width,
    pinned: column.pinned,
  }))
}

/**
 * Take a fingerprint of the view as it stands, so switching template can tell whether anything would be lost.
 *
 * The widths are left out of it on purpose: a flexible column measures differently after the window is resized,
 * and a resized window is not a change the user made to the view.
 */
const readViewFingerprint = (): string =>
  JSON.stringify({
    columns: readTemplateColumns().map((column) => ({
      key: column.key,
      visible: column.visible,
      order: column.order,
      pinned: column.pinned,
    })),
    sort: controller.sortSpecifications.value,
    filters: controller.filterConditions.value,
    search: controller.search.value,
    parseState: controller.parseState.value,
  })

/**
 * Record the view as saved, which is what every later comparison is made against.
 */
const rememberView = () => {
  savedFingerprint.value = readViewFingerprint()
}

const load = async (): Promise<void> => {
  controller.industry.value = props.industry
  await controller.refreshConfiguration()
  visibleColumns.value = columns.value.filter((column) => !column.hide).map((column) => column.colId)
  await controller.refreshRows()
  await nextTick()
  /* The generated ordering is told to the table as well, so the first filter that is typed does not lose it. */
  grid.value?.applySort(controller.sortSpecifications.value)
  rememberView()
  try {
    templates.value = await listTemplates('event', props.industry)
  } catch (error) {
    reportError(error)
  }
}

const onSearch = (value: string) => {
  controller.search.value = value
  if (searchTimer !== null) {
    clearTimeout(searchTimer)
  }
  searchTimer = setTimeout(() => {
    void controller.goToPage(1)
  }, SEARCH_DEBOUNCE_MS)
}

const onParseState = (value: ParseState) => {
  controller.parseState.value = value
  void controller.goToPage(1)
}

const onSort = (specification: SortSpecification) => {
  controller.sortSpecifications.value = [specification]
  grid.value?.applySort([specification])
  void controller.goToPage(1)
}

const onToggleColumn = (colId: string) => {
  visibleColumns.value = visibleColumns.value.includes(colId)
    ? visibleColumns.value.filter((candidate) => candidate !== colId)
    : [...visibleColumns.value, colId]
}

const onModelsChanged = (sortModel: SortModelItem[], filterModel: FilterModel) => {
  void controller.applyGridModels(sortModel, filterModel)
}

/**
 * Lift a single restriction. A column filter is dropped inside the grid so that its own header input
 * empties too and the reload follows from the grid, while the toolbar restrictions are reset here.
 */
const onRemoveFilter = (chip: FilterChip) => {
  if (chip.kind === 'column') {
    grid.value?.clearColumnFilter(chip.colId)

    return
  }

  if (chip.kind === 'search') {
    onSearch('')

    return
  }

  onParseState('all')
}

const onClearFilters = () => {
  const hadColumnFilters = controller.filterConditions.value.length > 0
  controller.search.value = ''
  controller.parseState.value = 'all'

  /*
   * Emptying the grid filters raises a filter change, which reloads the rows against the freshly cleared
   * toolbar state on its own. Only a view without column filters has to ask for the reload itself.
   */
  if (hadColumnFilters) {
    grid.value?.clearFilters()

    return
  }

  void controller.goToPage(1)
}

const onSelectionChanged = (rowIds: string[]) => {
  selectedIds.value = rowIds
}

const onSelectAll = () => {
  grid.value?.setAllSelected(selectedIds.value.length !== controller.rows.value.length)
}

const onOpenEvent = (rowId: string) => {
  void router.push(`/events/${rowId}`)
}

const onOpenArtifact = (artifact: Artifact) => {
  viewedArtifact.value = artifact
  viewerDialog.value = true
}

const onDownload = (artifact: Artifact) => {
  downloadArtifact(artifact)
}

const onExport = async (choice: ExportChoice): Promise<void> => {
  const picked = choice.selectionOnly ? selectedIds.value : []
  try {
    /*
     * The name is the one the events service stamped the export with, so two exports of the same view never
     * land in the download folder as one file quietly overwriting the other.
     */
    const exported = await exportEvents(
      buildExportRequest(controller, visibleColumns.value, picked),
      choice.format,
    )
    downloadBlob(exported.blob, exported.name)
    notify(
      choice.selectionOnly
        ? `${picked.length} selected event(s) were exported`
        : 'The current view was exported',
      'success',
    )
  } catch (error) {
    reportError(error)
  }
}

/**
 * Download every file of the current view, or of the ticked rows, as one archive.
 */
const onDownloadFiles = async (selectionOnly: boolean): Promise<void> => {
  const picked = selectionOnly ? selectedIds.value : []
  archiving.value = true
  notify('The archive is being packed, this can take a while', 'info')
  try {
    const archive = await downloadEventFiles(buildExportRequest(controller, visibleColumns.value, picked))
    downloadBlob(archive.blob, archive.name)
    notify('The archive was downloaded', 'success')
  } catch (error) {
    reportError(error)
  } finally {
    archiving.value = false
  }
}

const onOpenSaveTemplate = () => {
  templateDialog.value = true
}

/**
 * Giving up on the save gives up on the switch that was waiting for it too, so a template picked earlier is
 * never loaded later on by a save that had nothing to do with it.
 */
const onTemplateDialogToggle = (open: boolean) => {
  if (!open) {
    pendingTemplate.value = null
  }
}

const onCancelSaveTemplate = () => {
  templateDialog.value = false
  pendingTemplate.value = null
}

const onSaveTemplate = async (): Promise<void> => {
  try {
    const saved = await createTemplate({
      name: templateName.value,
      description: templateDescription.value,
      scope: 'event',
      industry: props.industry,
      shared: templateShared.value,
      columns: readTemplateColumns(),
      filters: controller.filterConditions.value,
      sort: controller.sortSpecifications.value,
    })
    templates.value = [...templates.value, saved]
    templateDialog.value = false
    templateName.value = ''
    templateDescription.value = ''
    rememberView()
    notify('The view was saved as a template', 'success')
    await applyPendingTemplate()
  } catch (error) {
    reportError(error)
  }
}

/**
 * Load a saved view into the running table - its columns, its ordering and its filters together.
 *
 * The visibility is handed to the table as a prop, and the order, the widths, the pinning and the filters are
 * written into the grid itself, so that the header inputs, the chips of the active filters and the rows that
 * come back all describe the same view. The rows are reloaded once, at the end, against the whole of it.
 */
const applyTemplate = async (template: TableTemplate): Promise<void> => {
  const ordered = [...template.columns].sort((left, right) => left.order - right.order)
  visibleColumns.value = ordered.filter((column) => column.visible).map((column) => column.key)

  await grid.value?.applyViewState({
    columns: ordered.map((column) => ({
      colId: column.key,
      visible: column.visible,
      width: column.width,
      pinned: column.pinned,
    })),
    sort: template.sort,
    filters: template.filters,
  })

  controller.filterConditions.value = template.filters
  if (template.sort.length > 0) {
    controller.sortSpecifications.value = template.sort
  }
  await controller.goToPage(1)
  rememberView()
}

/**
 * Load the template that was waiting for the unsaved view to be dealt with, if there is one.
 */
const applyPendingTemplate = async (): Promise<void> => {
  const waiting = pendingTemplate.value
  pendingTemplate.value = null
  if (waiting !== null) {
    await applyTemplate(waiting)
  }
}

const onApplyTemplate = (template: TableTemplate) => {
  if (savedFingerprint.value === null || savedFingerprint.value === readViewFingerprint()) {
    void applyTemplate(template)

    return
  }

  pendingTemplate.value = template
  switchDialog.value = true
}

const onCancelSwitch = () => {
  pendingTemplate.value = null
  switchDialog.value = false
}

const onConfirmSwitch = () => {
  switchDialog.value = false
  void applyPendingTemplate()
}

/**
 * Keep the current view under a name of its own before the picked template replaces it.
 */
const onSaveBeforeSwitch = () => {
  switchDialog.value = false
  templateDialog.value = true
}

const onCreated = () => {
  void controller.refreshRows()
}

/**
 * Leave the zoomed table on the key every full screen view is left with.
 */
const onKeyDown = (event: KeyboardEvent) => {
  if (event.key === ESCAPE_KEY && fullscreen.value) {
    fullscreen.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  void load()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
})

watch(() => props.industry, load)
</script>

<style scoped>
/*
 * The inventory grows with the table it holds and lets the browser scroll the page, so a block of rows is
 * shown in full instead of being squeezed into a letterbox between the toolbar and the pager.
 */
.inventory {
  /* The zoomed table covers the page but stays under the dialogs and menus Vuetify teleports above it. */
  --inventory-zoom-layer: 100;

  display: flex;
  flex-direction: column;
  inline-size: 100%;
  min-inline-size: 0;
}

/*
 * Zoomed, the inventory is lifted out of the page and over the surrounding chrome, and pinned to the viewport,
 * so that the toolbar and the pager frame a table that scrolls inside its own body with its header in place.
 */
.inventory--zoomed {
  position: fixed;
  inset: 0;
  z-index: var(--inventory-zoom-layer);
  background-color: rgb(var(--v-theme-background));
  padding-inline: 2rem;
  padding-block-end: 0.5rem;
  min-block-size: 0;
  overflow: hidden;
  /* Reaching the end of the rows must not carry on into the page that is still there behind the overlay. */
  overscroll-behavior: contain;
}

.inventory__dialog {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.inventory__dialog-hint {
  font-size: 0.8125rem;
  opacity: 0.7;
}

@media (max-width: 48rem) {
  .inventory--zoomed {
    padding-inline: 1rem;
  }
}
</style>
