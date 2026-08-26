<template>
  <div class="detail-row">
    <!--
      The panel is measured through a wrapper of its own rather than through the row it sits in: the row is
      given a height, so measuring it would only report back the height it was already given. This grows with
      what is inside it and nothing else, which is what makes it worth measuring.
    -->
    <div
      ref="content"
      class="detail-row__content"
    >
      <!-- The industry of the event is what decides the schema every entity table below is rendered with. -->
      <EventDetailPanel
        v-if="parentRow !== undefined"
        :event-id="parentId"
        :event-row="parentRow"
        :industry="industry"
        @open="onOpen"
        @download="onDownload"
      />
    </div>
  </div>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import type { Artifact } from '@/models/common'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow>
}
</script>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import EventDetailPanel from '@/components/EventDetailPanel.vue'
import { provideSearchTerm, readContext } from '@/utils/grid-context'
import { readText } from '@/utils/rows'

const props = defineProps<Props>()

/*
 * The panel below is a page of tables of its own, and the values at the bottom of it - the name, the origin
 * and the notes of every entity - are searched by the very same box the rows above were found with. The row
 * offers the term to whatever ends up painting one of those values, so that neither the panel nor the tables
 * in between have to carry a search term they have nothing to do with.
 */
provideSearchTerm(computed<string>(() => readContext(props.params).search))

const parentId = computed<string>(() => {
  const row = props.params.data

  return row === undefined ? '' : String(row.parentId ?? '')
})

const parentRow = computed<GridRow | undefined>(() => readContext(props.params).findRow(parentId.value))

const industry = computed<string>(() => (parentRow.value === undefined ? '' : readText(parentRow.value, 'industry')))

const onOpen = (artifact: Artifact) => {
  readContext(props.params).openArtifact(artifact)
}

const onDownload = (artifact: Artifact) => {
  readContext(props.params).downloadArtifact(artifact)
}

/*
 * The panel says how tall it turned out to be, and keeps saying so: it loads its entities after it is first
 * drawn, a group grows when an entity is added to it, and a row of it grows when its attributes are opened.
 * Every one of those changes the height the row underneath ought to have.
 */
const content = ref<HTMLElement | null>(null)
let observer: ResizeObserver | null = null

const report = () => {
  const element = content.value
  if (element === null || parentId.value.length === 0) {
    return
  }

  readContext(props.params).reportDetailHeight(parentId.value, element.getBoundingClientRect().height)
}

onMounted(() => {
  const element = content.value
  if (element === null) {
    return
  }

  observer = new ResizeObserver(report)
  observer.observe(element)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})
</script>

<style>
.detail-row {
  inline-size: 100%;
  block-size: 100%;
  /* A panel taller than the ceiling a single row may take scrolls inside itself rather than being cut off. */
  overflow: auto;
}

.detail-row__content {
  inline-size: 100%;
}
</style>
