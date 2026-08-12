<template>
  <span
    class="json-cell"
    :class="{ 'json-cell--expandable': isExpandable }"
  >
    <span
      class="json-cell__preview"
      @click="openViewer"
    >{{ preview }}</span>

    <!--
      A document flattened onto one line is unreadable by construction, so the cell says out loud that the
      whole of it can be opened rather than leaving that to whoever thinks of clicking the text.
    -->
    <button
      v-if="isExpandable"
      type="button"
      class="json-cell__expand"
      :aria-label="`Read the full value of ${headerName}`"
      @click.stop="dialog = true"
    >
      <v-icon
        icon="mdi-arrow-expand"
        size="x-small"
      />
    </button>

    <ValueViewerDialog
      v-if="isExpandable"
      v-model="dialog"
      :value="pretty"
      :title="headerName"
      monospace
    />
  </span>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import { EMPTY_PLACEHOLDER, SkyValueViewer as ValueViewerDialog, truncate } from '@skyscanner/sky-ui'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow>
}

const PREVIEW_LIMIT = 48

/** Indenting a document puts a line break into everything but a bare scalar, which is what a cell can show. */
const INDENT = 2
</script>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<Props>()

const dialog = ref<boolean>(false)

const pretty = computed<string>(() => {
  const value = props.params.value
  if (value === null || value === undefined) {
    return ''
  }

  return JSON.stringify(value, null, INDENT)
})

const isExpandable = computed<boolean>(() => pretty.value.length > PREVIEW_LIMIT || pretty.value.includes('\n'))

const preview = computed<string>(() =>
  pretty.value.length === 0 ? EMPTY_PLACEHOLDER : truncate(pretty.value.replace(/\s+/g, ' '), PREVIEW_LIMIT),
)

const headerName = computed<string>(() => props.params.colDef?.headerName ?? 'Value')

/**
 * Open the viewer from the text itself, which is where a reader who already knows the value is cut off
 * reaches first. The row underneath must not act on that click, or reading a value would expand the event.
 */
const openViewer = (event: MouseEvent) => {
  if (!isExpandable.value) {
    return
  }

  event.stopPropagation()
  dialog.value = true
}
</script>

<style>
.json-cell {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  min-inline-size: 0;
  font-family: ui-monospace, 'SFMono-Regular', 'Consolas', monospace;
  font-size: 0.75rem;
}

.json-cell__preview {
  flex: 1 1 auto;
  min-inline-size: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.json-cell--expandable .json-cell__preview {
  cursor: pointer;
}

.json-cell--expandable:hover .json-cell__preview {
  text-decoration: underline;
}

.json-cell__expand {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  border: none;
  background: none;
  padding: 0;
  color: inherit;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease-in-out;
}

/*
 * The affordance stays out of the way until the cell is under the pointer, so that a table of documents is
 * not a wall of icons. A keyboard never hovers, which is why focus reveals it just as hovering does.
 */
.json-cell:hover .json-cell__expand,
.json-cell__expand:focus-visible {
  opacity: 0.75;
}

.json-cell__expand:hover {
  opacity: 1;
}
</style>
