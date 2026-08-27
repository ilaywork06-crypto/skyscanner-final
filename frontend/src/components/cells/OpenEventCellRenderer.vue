<template>
  <!--
    The way into the event page, at the end of every row.

    The number and the brief have always led there, but nothing on a row said so, and a reader who never
    happened to click one of those two cells never found the page at all. This is the same link written as
    the arrow every list uses to mean "there is more of this behind here" - a real link, so it can be opened
    in a new tab and read by anything that understands a document.
  -->
  <a
    class="open-event"
    :href="href"
    aria-label="Open the page of this event"
    @click="open"
  >
    <v-icon
      class="open-event__icon"
      size="small"
      icon="mdi-chevron-right"
    />
    <SkyTooltip>Open the event page</SkyTooltip>
  </a>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import { SkyTooltip } from '@skyscanner/sky-ui'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow>
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

import { readContext, readRowId } from '@/utils/grid-context'

const props = defineProps<Props>()

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

<!-- Unscoped for the same reason every renderer of this table is: the grid mounts it outside the tree. -->
<style>
.open-event {
  display: flex;
  align-items: center;
  justify-content: center;
  block-size: 100%;
  inline-size: 100%;
  border-radius: 999rem;
  color: inherit;
  text-decoration: none;
}

/*
 * The arrow is quiet until the row is pointed at: a column of bright chevrons down the side of the table
 * would shout louder than anything the rows actually say.
 */
.open-event__icon {
  opacity: 0.4;
  transition: opacity 0.12s ease-in-out, transform 0.12s ease-in-out;
}

.sky-row:hover .open-event__icon {
  opacity: 0.85;
}

.open-event:hover .open-event__icon,
.open-event:focus-visible .open-event__icon {
  opacity: 1;
  color: rgb(var(--v-theme-primary));
  transform: translateX(0.125rem);
}
</style>
