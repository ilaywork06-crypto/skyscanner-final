<template>
  <div class="attributes-table">
    <p
      v-if="title.length > 0"
      class="attributes-table__title"
    >
      {{ title }}
    </p>

    <!--
      The header row and the value row are one grid rather than two flex rows of their own, so a value always
      stands under the name of the column it belongs to. They used to be two independent rows that each sized
      their cells from their own content, which is why a long value pushed itself out from under its heading.
    -->
    <div
      v-if="columns.length > 0"
      class="attributes-table__frame"
    >
      <div
        class="attributes-table__grid"
        :style="gridStyle"
      >
        <!--
          A column nobody declared is one read straight off the value the row was written with, so it says so
          under its own name rather than leaving a reader to wonder who invented it.
        -->
        <div
          v-for="column in columns"
          :key="`head-${column.colId}`"
          class="attributes-table__cell attributes-table__cell--head"
        >
          {{ column.headerName }}
          <span
            v-if="column.discovered"
            class="attributes-table__origin"
          >not declared</span>
        </div>
        <div
          v-for="column in columns"
          :key="`value-${column.colId}`"
          class="attributes-table__cell"
        >
          <DynamicCell
            :column="column"
            :row="row"
            :industries="industries"
            @open="emit('open', $event)"
            @download="emit('download', $event)"
          />
        </div>
      </div>
    </div>

    <p
      v-else
      class="attributes-table__empty"
    >
      {{ emptyText }}
    </p>
  </div>
</template>

<script lang="ts">
import type { Artifact } from '@/models/common'
import type { GeneratedColumn, GridRow } from '@/models/grid'
import type { Industry } from '@/models/industry'

interface Props {
  /** The columns the table is laid out with, one heading and one value apiece. */
  columns: GeneratedColumn[]
  /** The row the values are read out of, addressed by the paths of the columns. */
  row: GridRow
  industries?: Industry[]
  title?: string
  emptyText?: string
}

interface Emits {
  (event: 'open', artifact: Artifact): void
  (event: 'download', artifact: Artifact): void
}

/** How narrow one column may become before the table scrolls sideways instead of squeezing further. */
const MIN_COLUMN_WIDTH = '11rem'
</script>

<script setup lang="ts">
import { computed } from 'vue'

import DynamicCell from '@/components/DynamicCell.vue'

const props = withDefaults(defineProps<Props>(), {
  industries: () => [],
  title: '',
  emptyText: 'Nothing was recorded here yet.',
})
const emit = defineEmits<Emits>()

/*
 * Every column is given the same share of the room and the same floor, so the two rows of the grid cannot
 * disagree about where a column starts. Past that floor the frame around the grid scrolls sideways rather
 * than the cells being crushed into unreadable slivers.
 */
const gridStyle = computed<Record<string, string>>(() => ({
  gridTemplateColumns: `repeat(${props.columns.length}, minmax(${MIN_COLUMN_WIDTH}, 1fr))`,
}))
</script>

<style scoped>
.attributes-table {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  min-inline-size: 0;
}

.attributes-table__title {
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  opacity: 0.8;
}

.attributes-table__frame {
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
  overflow-x: auto;
  max-inline-size: 100%;
}

.attributes-table__grid {
  display: grid;
  min-inline-size: fit-content;
}

.attributes-table__cell {
  padding-inline: 1rem;
  padding-block: 0.75rem;
  min-inline-size: 0;
  overflow: hidden;
  background-color: rgb(var(--v-theme-table-row));
  border-block-start: 0.0625rem solid rgb(var(--v-theme-app-border));
}

/*
 * The headings are the first row of the grid, so they carry the header colour themselves rather than sitting
 * in a container of their own, and the separator above them is dropped because nothing stands above them.
 */
.attributes-table__cell--head {
  background-color: rgb(var(--v-theme-table-header));
  border-block-start: none;
  padding-block: 0.625rem;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}

/* The origin of an undeclared column is read second, so it is set smaller and quieter than its name. */
.attributes-table__origin {
  display: block;
  font-size: 0.625rem;
  font-weight: 400;
  letter-spacing: normal;
  text-transform: none;
  opacity: 0.65;
}

.attributes-table__empty {
  font-size: 0.8125rem;
  opacity: 0.7;
}
</style>
