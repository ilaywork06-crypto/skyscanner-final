<template>
  <div class="detail-row">
    <!--
      The panel reads against two different industries: the one the event belongs to, which decides the fields
      it shows, and the one the inventory is currently narrowed to, which the panel gets from the table because
      an expanded row is the only place that knows it.
    -->
    <EventDetailPanel
      v-if="parentRow !== undefined"
      :event-id="parentId"
      :event-row="parentRow"
      :industry="industry"
      :industry-filter="readContext(props.params).industryFilter"
      @open="onOpen"
      @download="onDownload"
    />
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
import { computed } from 'vue'

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
</script>

<style>
.detail-row {
  inline-size: 100%;
  block-size: 100%;
  overflow: auto;
}
</style>
