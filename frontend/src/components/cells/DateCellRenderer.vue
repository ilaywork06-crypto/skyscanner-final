<template>
  <!--
    A moment the system recorded rather than one anybody chose - created at, updated at - stands at the end of
    its column behind the mark of a date, quieter and shorter than the values beside it. It is worth having
    and rarely what a reader opened the table for, and it used to take the two widest columns in the row.
  -->
  <span
    v-if="isStamp"
    class="date-cell date-cell--stamp"
  >
    <v-icon
      v-if="raw !== null"
      class="date-cell__icon"
      size="x-small"
      icon="mdi-calendar-blank-outline"
    />
    {{ display }}
  </span>
  <span
    v-else
    class="date-cell"
  >{{ display }}</span>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import { formatCompactDateTime, formatDate, formatDateTime } from '@skyscanner/sky-ui'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow> & { withTime?: boolean, stamp?: boolean }
}
</script>

<script setup lang="ts">
import { computed } from 'vue'


const props = defineProps<Props>()

const raw = computed<string | null>(() => {
  const value = props.params.value

  return typeof value === 'string' ? value : null
})

/* Whether this column carries a moment the system recorded rather than one the user picked. */
const isStamp = computed<boolean>(() => props.params.stamp === true)

/*
 * A date the user chose is a day, but a moment the system recorded is a point in time - knowing that two
 * events were uploaded on the same day is rarely enough, so those columns ask for the clock as well. A stamp
 * asks for it in the shortest form that still reads, because taking as little of the row as possible is the
 * whole point of it.
 */
const display = computed<string>(() => {
  if (props.params.withTime !== true) {
    return formatDate(raw.value)
  }

  return isStamp.value ? formatCompactDateTime(raw.value) : formatDateTime(raw.value)
})
</script>

<style>
.date-cell {
  display: block;
  white-space: nowrap;
}

/*
 * The stamp sits at the end of its column in digits of one width, so that a column of them lines up and can
 * be compared down the page rather than read one row at a time.
 */
.date-cell--stamp {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
  font-variant-numeric: tabular-nums;
  opacity: 0.65;
}

.date-cell__icon {
  flex: 0 0 auto;
  opacity: 0.8;
}
</style>
