<template>
  <span
    class="text-cell"
    :class="{ 'text-cell--expandable': isExpandable, 'text-cell--wrapped': wraps }"
  >
    <!--
      A value short enough to be shown whole has its addresses read out of it, so a link stored in a field is
      a link in the table. A value the cell had to window is left as characters: what is on screen is a
      fragment, and half of an address is not one - the viewer behind the affordance shows the whole value
      and reads the addresses out of that instead.
    -->
    <!--
      `dir="auto"` rather than a direction of its own: the value decides which way it runs, from the first
      letter in it that has a direction at all. A Hebrew note inside an English table reads right to left and
      an English identifier inside a Hebrew one reads left to right, and a value that mixes the two keeps
      each run the way it was written instead of the whole line being turned around.
    -->
    <span
      class="text-cell__preview"
      dir="auto"
      @click="openViewer"
    >
      <UiLinkedText
        v-if="!isExpandable"
        :text="display"
        :term="isMatch ? search : ''"
      />
      <HighlightedText
        v-else-if="isMatch"
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
import { EMPTY_PLACEHOLDER, UiValueViewer as ValueViewerDialog } from '../../index'
import type { GridRow } from '../../models/grid'

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
import { useLanguage } from '../../composables/useLanguage'

import { computed, ref } from 'vue'

import HighlightedText from '../../components/HighlightedText.vue'
import UiLinkedText from '../../components/UiLinkedText.vue'
import { readContext } from '../../utils/grid-context'
import { matchesTerm, previewAround } from '../../utils/highlight'
import { splitNotes, toBulletedText, toNotePreview } from '../../utils/notes'

const { t } = useLanguage()

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

/*
 * Whether this column shows a value whole, across as many lines as it takes, rather than on the one line a
 * table row usually gives it. It is a property of the column rather than of the value: a table is either
 * one a reader scans or one they read, and that is decided where the columns are, not per cell.
 */
const wraps = computed<boolean>(() => props.params.colDef?.wrapText === true)

/*
 * A wrapped cell hides nothing, so it offers no way of opening what it is hiding. The affordance is for the
 * cells that had to window their value, and on a cell showing all of it, it would open a viewer holding
 * exactly what is already on screen.
 */
const isExpandable = computed<boolean>(
  () => !wraps.value && (text.value.length > TEXT_LIMIT || hasSeveralLines.value),
)

/* The one line a cell has room for: the items of a list strung along it, and free text with its breaks flattened. */
const oneLine = computed<string>(() =>
  isList.value ? toNotePreview(items.value) : text.value.replace(/\s+/g, ' '),
)

const search = computed<string>(() => readContext(props.params).search)

const preview = computed<string>(() => previewAround(oneLine.value, search.value, TEXT_LIMIT))

/** The whole value: the items of a list as bullets, and free text exactly as it was written. */
const full = computed<string>(() => (isList.value ? toBulletedText(items.value) : text.value))

const display = computed<string>(() => {
  if (text.value.length === 0) {
    return EMPTY_PLACEHOLDER
  }

  /* Wrapped, the value is shown as it was written - the items of a list as lines, free text with its breaks. */
  return wraps.value ? full.value : preview.value
})

const isMatch = computed<boolean>(() => matchesTerm(display.value, search.value))

/*
 * Whether the whole of the value may hold more of the term than the fragment on screen does. The fragment is
 * windowed onto the first match, so a second one, or anything the window left behind, is out of sight - and a
 * cell cannot tell that it is without measuring what fits, which is why a match anywhere counts.
 */
const mayHideMatch = computed<boolean>(() => isExpandable.value && matchesTerm(text.value, search.value))

const headerName = computed<string>(() => props.params.colDef?.headerName ?? t('value.title'))

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

/*
 * A wrapped cell reads as a paragraph rather than as a line: it keeps the breaks the value was written with,
 * breaks the long words that would otherwise push the column open, and sits at the top of its row so that
 * the first line of a tall cell is level with the short cells beside it.
 */
.text-cell--wrapped {
  align-items: flex-start;
  inline-size: 100%;
}

.text-cell--wrapped .text-cell__preview {
  overflow: visible;
  text-overflow: clip;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
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
