<template>
  <span
    class="date-cell"
    :title="fullMoment"
  >{{ display }}</span>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import { formatDate, formatDateTime } from '@skyscanner/sky-ui'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow> & { withTime?: boolean }
}
</script>

<script setup lang="ts">
import { computed } from 'vue'


const props = defineProps<Props>()

const raw = computed<string | null>(() => {
  const value = props.params.value

  return typeof value === 'string' ? value : null
})

/*
 * A date the user chose is a day, but a moment the system recorded is a point in time - knowing that two
 * events were uploaded on the same day is rarely enough, so those columns ask for the clock as well.
 */
const display = computed<string>(() =>
  props.params.withTime === true ? formatDateTime(raw.value) : formatDate(raw.value),
)
const fullMoment = computed<string>(() => formatDateTime(raw.value))
</script>

<style>
.date-cell {
  display: block;
  white-space: nowrap;
}
</style>
