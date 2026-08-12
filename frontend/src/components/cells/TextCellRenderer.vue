<template>
  <span
    class="text-cell"
    :class="{ 'text-cell--expandable': isExpandable }"
  >
    <span
      class="text-cell__preview"
      @click="openViewer"
    >
      <HighlightedText
        v-if="isMatch"
        :text="display"
        :term="search"
      />
      <template v-else>{{ display }}</template>
    </span>

    <!--
      A value that only fits the cell in fragments used to announce itself by nothing but the text happening
      to be clickable, which nobody discovers. The affordance says out loud that there is more to read, and
      because a keyboard never hovers it is a real button rather than something the pointer alone can reach.
      On a value the search matched it stops waiting to be hovered at all, because the fragment on screen is
      the one place a reader cannot tell whether the rest of the value holds more of what they searched for.
    -->
    <button
      v-if="isExpandable"
      type="button"
      class="text-cell__expand"
      :class="{ 'text-cell__expand--matched': mayHideMatch }"
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
      :value="full"
      :title="headerName"
    />
  </span>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import { EMPTY_PLACEHOLDER, SkyValueViewer as ValueViewerDialog } from '@skyscanner/sky-ui'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow>
}

/** Beyond this many characters the cell can only ever show a fragment, so it offers the full value instead. */
const TEXT_LIMIT = 64

/**
 * What the column definition of a value that was typed item by item asks for.
 *
 * The notes of an entity are a list - they are written one item at a time and read back as bullets - while
 * the information field of an event is free text that happens to run over several lines. Both arrive here as
 * one string with newlines in it, so nothing about the value itself tells the two apart and the column has
 * to say which of them it is showing.
 */
const LIST_DISPLAY = 'list'
</script>

<script setup lang="ts">
import { computed, ref } from 'vue'

import HighlightedText from '@/components/HighlightedText.vue'
import { readContext } from '@/utils/grid-context'
import { matchesTerm, previewAround } from '@/utils/highlight'
import { splitNotes, toBulletedText, toNotePreview } from '@/utils/notes'

const props = defineProps<Props>()

const dialog = ref<boolean>(false)

const text = computed<string>(() => {
  const value = props.params.value
  if (value === null || value === undefined || value === '') {
    return ''
  }

  return Array.isArray(value) ? value.join(', ') : String(value)
})

/* Which of the two shapes a value carries is a property of the column rather than of the value. */
const isList = computed<boolean>(() => props.params.colDef?.cellRendererParams?.display === LIST_DISPLAY)

const items = computed<string[]>(() => splitNotes(text.value))

/*
 * A value written over several lines is only ever readable in one piece, whether those lines are the items of
 * a list or the paragraphs of free text: one row of a table has a single line to show all of them on.
 */
const hasSeveralLines = computed<boolean>(() => items.value.length > 1)

const isExpandable = computed<boolean>(() => text.value.length > TEXT_LIMIT || hasSeveralLines.value)

/* The one line a cell has room for: the items of a list strung along it, and free text with its breaks flattened. */
const oneLine = computed<string>(() =>
  isList.value ? toNotePreview(items.value) : text.value.replace(/\s+/g, ' '),
)

const search = computed<string>(() => readContext(props.params).search)

const preview = computed<string>(() => previewAround(oneLine.value, search.value, TEXT_LIMIT))

const display = computed<string>(() => (text.value.length === 0 ? EMPTY_PLACEHOLDER : preview.value))

/** What the viewer reads out: the items of a list as bullets, and free text exactly as it was written. */
const full = computed<string>(() => (isList.value ? toBulletedText(items.value) : text.value))

const isMatch = computed<boolean>(() => matchesTerm(display.value, search.value))

/*
 * Whether the whole of the value may hold more of the term than the fragment on screen does. The fragment is
 * windowed onto the first match, so a second one, or anything the window left behind, is out of sight - and a
 * cell cannot tell that it is without measuring what fits, which is why a match anywhere counts.
 */
const mayHideMatch = computed<boolean>(() => isExpandable.value && matchesTerm(text.value, search.value))

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
.text-cell {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  min-inline-size: 0;
}

.text-cell__preview {
  flex: 1 1 auto;
  min-inline-size: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-cell--expandable .text-cell__preview {
  cursor: pointer;
}

.text-cell--expandable:hover .text-cell__preview {
  text-decoration: underline;
}

.text-cell__expand {
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
 * The affordance stays out of the way until the cell is under the pointer, so that a table of long values is
 * not a wall of icons. A keyboard never hovers, which is why focus reveals it just as hovering does.
 */
.text-cell:hover .text-cell__expand,
.text-cell__expand:focus-visible {
  opacity: 0.75;
}

.text-cell__expand:hover {
  opacity: 1;
}

/* A value the search reached into is worth opening, so its way in is on screen rather than under the pointer. */
.text-cell__expand--matched {
  opacity: 1;
  color: rgb(var(--v-theme-warning));
}
</style>
