<template>
  <div class="toolbar">
    <div class="toolbar__filters">
      <!--
        Nothing is ever written under this field - it validates nothing and reports nothing - so the room a
        field keeps for its messages is given back to the table instead of padding the toolbar with it.
      -->
      <v-text-field
        :model-value="search"
        class="toolbar__search"
        placeholder="Search"
        prepend-inner-icon="mdi-magnify"
        rounded="pill"
        density="compact"
        clearable
        hide-details
        @update:model-value="onSearch"
      />

      <v-menu
        :close-on-content-click="false"
        location="bottom start"
      >
        <template #activator="{ props: activator }">
          <v-btn
            v-bind="activator"
            class="toolbar__pill"
            variant="text"
          >
            <span class="toolbar__pill-label">Show:</span>
            <!--
              Held at the width of the longest of the three states, so that switching between them changes the
              word inside the pill and never the place of the controls beside it.
            -->
            <span class="toolbar__pill-value toolbar__pill-value--parse">{{ parseStateLabel }}</span>
            <v-icon
              size="small"
              icon="mdi-menu-down"
            />
          </v-btn>
        </template>
        <!--
          Both boxes ticked means everything is shown. Clearing the last remaining one would leave a table
          that shows nothing, so that box refuses to be cleared and stays ticked instead.
        -->
        <v-list
          density="compact"
          class="toolbar__menu"
        >
          <v-list-item>
            <v-checkbox-btn
              :model-value="showParsed"
              label="PARSED"
              density="compact"
              @update:model-value="onToggleParsed"
            />
          </v-list-item>
          <v-list-item>
            <v-checkbox-btn
              :model-value="showNotParsed"
              label="NOT PARSED"
              density="compact"
              @update:model-value="onToggleNotParsed"
            />
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu
        :close-on-content-click="false"
        location="bottom start"
      >
        <template #activator="{ props: activator }">
          <v-btn
            v-bind="activator"
            class="toolbar__pill"
            variant="text"
            :title="`Sorted by ${sortLabel}`"
          >
            <v-icon
              size="small"
              icon="mdi-sort"
            />
            <span class="toolbar__pill-label">Sort by:</span>
            <!--
              Held at the width of the longest header the menu below can put here, so that picking another
              column changes the word inside the pill and never the place of the controls beside it. A header
              longer than the pill is meant to grow to is cut short here and read in full from the tooltip.
            -->
            <span
              class="toolbar__pill-value toolbar__pill-value--sort"
              :style="{ inlineSize: sortValueWidth }"
            >{{ sortLabel }}</span>
            <v-icon
              size="small"
              icon="mdi-menu-down"
            />
          </v-btn>
        </template>
        <v-list
          density="compact"
          class="toolbar__menu"
        >
          <v-list-item
            v-for="column in sortableColumns"
            :key="column.colId"
            :title="column.headerName"
            :active="sortKey === column.colId"
            @click="emit('update:sort', { key: column.colId, direction: sortDirection })"
          />
          <v-divider />
          <v-list-item
            :title="sortDirection === 'asc' ? 'Ascending' : 'Descending'"
            prepend-icon="mdi-swap-vertical"
            @click="toggleDirection"
          />
        </v-list>
      </v-menu>

      <!--
        The menu of the columns stays open while it is used: closing after every tick would make showing three
        columns three trips through the toolbar.
      -->
      <v-menu
        :close-on-content-click="false"
        location="bottom start"
      >
        <template #activator="{ props: activator }">
          <v-btn
            v-bind="activator"
            class="toolbar__pill"
            variant="text"
          >
            <v-icon
              size="small"
              icon="mdi-view-column-outline"
            />
            <span class="toolbar__pill-label">Columns</span>
          </v-btn>
        </template>
        <v-list
          density="compact"
          class="toolbar__menu toolbar__menu--tall"
        >
          <v-list-item
            v-for="column in toggleableColumns"
            :key="column.colId"
          >
            <v-checkbox-btn
              :model-value="visibleColumns.includes(column.colId)"
              :label="column.headerName"
              density="compact"
              @update:model-value="emit('toggle-column', column.colId)"
            />
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu location="bottom start">
        <template #activator="{ props: activator }">
          <v-btn
            v-bind="activator"
            class="toolbar__pill"
            variant="text"
          >
            <v-icon
              size="small"
              icon="mdi-bookmark-outline"
            />
            <span class="toolbar__pill-label">Templates</span>
          </v-btn>
        </template>
        <v-list
          density="compact"
          class="toolbar__menu"
        >
          <v-list-item
            v-for="template in templates"
            :key="template.id"
            :title="template.name"
            :subtitle="template.shared ? 'Shared' : 'Private'"
            @click="emit('apply-template', template)"
          />
          <v-divider v-if="templates.length > 0" />
          <v-list-item
            title="Save current view"
            prepend-icon="mdi-content-save-outline"
            @click="emit('save-template')"
          />
        </v-list>
      </v-menu>
    </div>

    <div class="toolbar__actions">
      <!--
        The zoom lifts the table over the rest of the page, which is what reading a wide table on a large
        screen needs. It is an icon rather than a labelled button so that the row of actions stays readable.
      -->
      <v-btn
        class="toolbar__zoom"
        variant="text"
        :icon="fullscreen ? 'mdi-fullscreen-exit' : 'mdi-fullscreen'"
        :aria-label="fullscreen ? 'Leave the full screen table' : 'Show the table full screen'"
        :title="fullscreen ? 'Leave the full screen table (Esc)' : 'Show the table full screen'"
        @click="emit('toggle-fullscreen')"
      />

      <v-menu location="bottom end">
        <template #activator="{ props: activator }">
          <v-btn
            v-bind="activator"
            class="toolbar__action"
            variant="text"
            prepend-icon="mdi-download-outline"
            :loading="archiving"
          >
            Export
          </v-btn>
        </template>
        <!--
          The export always covers the table as it is currently filtered. Once rows are ticked the menu
          also offers the narrower export, so that a selection is never mistaken for the whole view.
        -->
        <v-list density="compact">
          <v-list-subheader>Whole current view</v-list-subheader>
          <v-list-item
            title="Export as CSV"
            @click="emit('export', { format: 'csv', selectionOnly: false })"
          />
          <v-list-item
            title="Export as JSON"
            @click="emit('export', { format: 'json', selectionOnly: false })"
          />
          <v-list-item
            title="Download all files as ZIP"
            prepend-icon="mdi-folder-zip-outline"
            @click="emit('download-files', false)"
          />
          <template v-if="selectedCount > 0">
            <v-divider />
            <v-list-subheader>Selected only - {{ selectedCount }}</v-list-subheader>
            <v-list-item
              title="Export as CSV"
              @click="emit('export', { format: 'csv', selectionOnly: true })"
            />
            <v-list-item
              title="Export as JSON"
              @click="emit('export', { format: 'json', selectionOnly: true })"
            />
            <v-list-item
              title="Download their files as ZIP"
              prepend-icon="mdi-folder-zip-outline"
              @click="emit('download-files', true)"
            />
          </template>
        </v-list>
      </v-menu>

      <v-btn
        class="toolbar__action"
        color="primary"
        variant="tonal"
        @click="emit('select-all')"
      >
        {{ selectedCount > 0 ? `SELECTED ${selectedCount}` : 'SELECT ALL' }}
      </v-btn>

      <v-btn
        class="toolbar__action"
        color="primary"
        prepend-icon="mdi-plus"
        @click="emit('create')"
      >
        EVENT
      </v-btn>
    </div>
  </div>
</template>

<script lang="ts">
import type { ParseState } from '@/models/common'
import type { GeneratedColumn } from '@/models/grid'
import type { SortDirection, SortSpecification } from '@/models/query'
import type { TableTemplate } from '@/models/template'

interface Props {
  search: string
  parseState: ParseState
  sortKey: string
  sortDirection: SortDirection
  columns: GeneratedColumn[]
  visibleColumns: string[]
  templates: TableTemplate[]
  selectedCount: number
  fullscreen: boolean
  archiving?: boolean
}

interface ExportChoice {
  format: string
  selectionOnly: boolean
}

interface Emits {
  (event: 'update:search', value: string): void
  (event: 'update:parseState', value: ParseState): void
  (event: 'update:sort', value: SortSpecification): void
  (event: 'toggle-column', colId: string): void
  (event: 'apply-template', template: TableTemplate): void
  (event: 'save-template'): void
  (event: 'export', choice: ExportChoice): void
  (event: 'download-files', selectionOnly: boolean): void
  (event: 'select-all'): void
  (event: 'create'): void
  (event: 'toggle-fullscreen'): void
}

export type { ExportChoice }
</script>

<script setup lang="ts">
import { computed } from 'vue'

const PARSE_LABELS: Record<ParseState, string> = {
  all: 'ALL',
  parsed: 'PARSED',
  not_parsed: 'NOT PARSED',
}

const NON_TOGGLEABLE: string[] = ['expander', 'actions']

/** The column the inventory falls back to when the ordering names one the current table does not carry. */
const DEFAULT_SORT_LABEL = 'Created at'

/*
 * The `ch` unit measures a digit, and a header is written in proportional letters that are narrower than one,
 * so the count of its characters is scaled by this before it becomes a width.
 */
const SORT_LABEL_WIDTH_FACTOR = 0.95

/** Even a table of very short headers keeps a pill wide enough to read the word inside it. */
const SORT_LABEL_MIN_CHARACTERS = 8

/*
 * A dynamic field can be declared under a name of any length, and one long header would otherwise widen the
 * pill until the row of controls no longer fits on one line. Past this the name is cut short inside the pill
 * and stays readable in full from the tooltip the pill carries.
 */
const SORT_LABEL_MAX_CHARACTERS = 14

const props = withDefaults(defineProps<Props>(), { archiving: false })
const emit = defineEmits<Emits>()

/*
 * The two boxes are a view of the single parse state rather than state of their own, so they can never drift
 * away from the table they describe.
 */
const showParsed = computed<boolean>(() => props.parseState !== 'not_parsed')
const showNotParsed = computed<boolean>(() => props.parseState !== 'parsed')

const parseStateLabel = computed<string>(() => PARSE_LABELS[props.parseState])

const sortableColumns = computed<GeneratedColumn[]>(() => props.columns.filter((column) => column.sortable))

const toggleableColumns = computed<GeneratedColumn[]>(() =>
  props.columns.filter((column) => !NON_TOGGLEABLE.includes(column.colId)),
)

const sortLabel = computed<string>(() => {
  const column = props.columns.find((candidate) => candidate.colId === props.sortKey)

  return column === undefined ? DEFAULT_SORT_LABEL : column.headerName
})

/**
 * Work out how wide the name of the ordering has to be held.
 *
 * A pill that shrinks and grows around the column it names drags every control to its right along with it, so
 * the width is taken from the longest name the menu is able to put there rather than from the current one, and
 * capped so that a single long header cannot push the rest of the toolbar onto a second line.
 */
const sortValueWidth = computed<string>(() => {
  const longest = sortableColumns.value.reduce(
    (widest, column) => Math.max(widest, column.headerName.length),
    Math.max(SORT_LABEL_MIN_CHARACTERS, DEFAULT_SORT_LABEL.length),
  )
  const held = Math.min(longest, SORT_LABEL_MAX_CHARACTERS)

  return `${(held * SORT_LABEL_WIDTH_FACTOR).toFixed(2)}ch`
})

const onSearch = (value: string | null) => {
  emit('update:search', value ?? '')
}

/**
 * Turn the two boxes into the single state the table runs on, keeping at least one of them ticked.
 */
const applyParse = (parsed: boolean, notParsed: boolean) => {
  if (!parsed && !notParsed) {
    return
  }

  if (parsed && notParsed) {
    emit('update:parseState', 'all')

    return
  }

  emit('update:parseState', parsed ? 'parsed' : 'not_parsed')
}

const onToggleParsed = (value: boolean | null) => {
  applyParse(value === true, showNotParsed.value)
}

const onToggleNotParsed = (value: boolean | null) => {
  applyParse(showParsed.value, value === true)
}

const toggleDirection = () => {
  emit('update:sort', {
    key: props.sortKey,
    direction: props.sortDirection === 'asc' ? 'desc' : 'asc',
  })
}
</script>

<style scoped>
.toolbar {
  /*
   * The whole row - the search, the four filter pills and the four actions - is meant to stand on one line at
   * an ordinary desktop width, so every control of it is measured against the same few metrics rather than
   * being spaced by whatever its component defaults to.
   */
  --toolbar-gap: 0.5rem;

  /*
   * The height every control of the row shares. It is the height Vuetify gives a compact field, so that the
   * search, the pills and the buttons stand as one row of controls rather than three sizes of them.
   */
  --toolbar-control-height: 2.5rem;

  /* Wide enough for NOT PARSED, the longest of the three states the Show pill can name. */
  --toolbar-parse-width: 5.75rem;

  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--toolbar-gap);
  /* Every row of padding above the toolbar is a row of the table the user does not get to see. */
  padding-block: 0.5rem 0.75rem;
}

.toolbar__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--toolbar-gap);
  flex: 1 1 auto;
  min-inline-size: 0;
}

/*
 * The search is the one control of the row that has no natural width, so it is the one that gives way: it is
 * laid out narrow enough for the whole row to fit and spends whatever the row has left over, up to a width
 * past which a search term is not any easier to read.
 */
.toolbar__search {
  flex: 1 1 10rem;
  max-inline-size: 20rem;
  min-inline-size: 8rem;
}

/* The search box is a control like the pills next to it, so it carries the same fill and outline. */
.toolbar__search :deep(.v-field) {
  background-color: rgb(var(--v-theme-control-surface));
  border: 0.0625rem solid rgb(var(--v-theme-control-border));
}

/* A term is read here as a value of the table, at the size the pills next to it name their values in. */
.toolbar__search :deep(.v-field__input) {
  font-size: 0.875rem;
}

.toolbar__search :deep(.v-field:hover) {
  background-color: rgb(var(--v-theme-control-surface-hover));
}

.toolbar__search :deep(.v-field--focused) {
  border-color: rgb(var(--v-theme-primary));
}

/*
 * The filter controls sit straight on the page background. In the dark palette the fill alone separates them,
 * but in the light one the fill is only a shade away from the page, so they also carry a border to stay
 * readable as controls rather than melting into the background.
 */
.toolbar__pill.v-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  border: 0.0625rem solid rgb(var(--v-theme-control-border));
  border-radius: 999rem;
  background-color: rgb(var(--v-theme-control-surface));
  color: rgb(var(--v-theme-on-surface));
  padding-inline: 0.625rem;
  padding-block: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 400;
  letter-spacing: normal;
  text-transform: none;
  block-size: auto;
  min-block-size: var(--toolbar-control-height);
  min-inline-size: 0;
  cursor: pointer;
  white-space: nowrap;
}

.toolbar__pill.v-btn:hover {
  background-color: rgb(var(--v-theme-control-surface-hover));
}

.toolbar__pill.v-btn :deep(.v-btn__content) {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.toolbar__pill-label {
  opacity: 0.75;
}

.toolbar__pill-value {
  font-weight: 600;
  text-align: start;
}

.toolbar__pill-value--parse {
  min-inline-size: var(--toolbar-parse-width);
}

/* The width of this one is held from the script, and a header too long for it ends in an ellipsis. */
.toolbar__pill-value--sort {
  overflow: hidden;
  text-overflow: ellipsis;
}

/*
 * The actions hold the end of the row. Once the window is too narrow to keep them on the same line as the
 * filters they drop onto a line of their own, and the margin keeps them at the end of that line as well.
 */
.toolbar__actions {
  display: flex;
  align-items: center;
  gap: var(--toolbar-gap);
  flex: 0 0 auto;
  margin-inline-start: auto;
}

/*
 * The buttons are written in capitals, which are wide, and the row has no width to spare. Dropping the extra
 * spacing Vuetify sets between their letters is what keeps them on the line with the filters beside them.
 */
.toolbar__action.v-btn {
  --v-btn-height: var(--toolbar-control-height);

  padding-inline: 0.75rem;
  font-size: 0.8125rem;
  letter-spacing: normal;
}

/* An icon button is laid out wider than the buttons beside it, and here it stands in the row with them. */
.toolbar__zoom.v-btn {
  inline-size: var(--toolbar-control-height);
  block-size: var(--toolbar-control-height);
}

.toolbar__menu {
  min-inline-size: 12rem;
}

.toolbar__menu--tall {
  max-block-size: 24rem;
  overflow-y: auto;
}

/*
 * A window this narrow cannot hold the row on one line whatever the controls are shrunk to, so the search is
 * given a line of its own instead of being squeezed to a box a term no longer fits in.
 */
@media (max-width: 48rem) {
  .toolbar__search {
    flex: 1 1 100%;
    max-inline-size: none;
  }
}
</style>
