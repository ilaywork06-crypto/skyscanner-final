<template>
  <!--
    An event is a page of its own, so the identifier that leads to it is a real link: it can be opened in a
    new tab, copied, and read by anything that understands a document, which a clickable span cannot offer.
    The same renderer serves the number the system minted and the name a reader recognises, because both of
    them lead to the same page and only the column definition knows which of the two it is showing.
  -->
  <a
    v-if="isName && text.length > 0"
    class="event-link event-link--name"
    :href="href"
    :title="text"
    @click="open"
  >
    <HighlightedText
      v-if="isMatch"
      :text="text"
      :term="search"
    />
    <template v-else>{{ text }}</template>
  </a>
  <!-- An event that was never named has nothing to click, so its cell says so instead of offering an empty link. -->
  <span
    v-else-if="isName"
    class="event-link__empty"
  >{{ EMPTY_PLACEHOLDER }}</span>
  <a
    v-else
    class="event-link event-link--number"
    :href="href"
    @click="open"
  >#{{ text }}</a>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import { EMPTY_PLACEHOLDER } from '@skyscanner/sky-ui'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow>
}

/** What the column definition of the name column asks for, where every other column asks for nothing. */
const NAME_DISPLAY = 'name'
</script>

<script setup lang="ts">
import { computed } from 'vue'

import HighlightedText from '@/components/HighlightedText.vue'
import { readContext, readRowId } from '@/utils/grid-context'
import { matchesTerm } from '@/utils/highlight'

const props = defineProps<Props>()

/*
 * Which of the two shapes to render is a property of the column rather than of the row, so it is read off the
 * column definition the backend generated rather than off the value.
 */
const isName = computed<boolean>(() => {
  const display: unknown = props.params.colDef?.cellRendererParams?.display

  return display === NAME_DISPLAY
})

const text = computed<string>(() => {
  const value = props.params.value

  return value === null || value === undefined ? '' : String(value)
})

const search = computed<string>(() => readContext(props.params).search)

/* Only the name of an event is searched for; the number beside it is minted rather than typed. */
const isMatch = computed<boolean>(() => isName.value && matchesTerm(text.value, search.value))

const href = computed<string>(() => `/events/${readRowId(props.params)}`)

/**
 * Route to the event inside the application, while leaving the browser its own handling of a modified
 * click so that opening the event in a new tab keeps working.
 */
const open = (event: MouseEvent) => {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) {
    return
  }

  event.preventDefault()
  event.stopPropagation()
  readContext(props.params).openEvent(readRowId(props.params))
}
</script>

<style>
.event-link {
  display: inline-block;
  color: inherit;
  font-weight: 500;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-inline-size: 100%;
}

/* A minted number reads as a column of digits, which only lines up while every digit is the same width. */
.event-link--number {
  font-variant-numeric: tabular-nums;
}

.event-link:hover,
.event-link:focus-visible {
  text-decoration: underline;
}

.event-link__empty {
  opacity: 0.6;
}
</style>
