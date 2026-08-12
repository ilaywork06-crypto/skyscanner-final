<template>
  <!--
    A panel pushes the rows below it far down the page, so a table with several of them open no longer shows
    which rows opened them. Every open one is therefore named here, and closing one, or all of them, is done
    from this strip without hunting for the row it belongs to.
  -->
  <div
    v-if="chips.length > 0"
    class="expanded-rows"
  >
    <span class="expanded-rows__label">Expanded</span>

    <button
      v-for="chip in chips"
      :key="chip.rowId"
      type="button"
      class="expanded-rows__chip"
      :aria-label="`Collapse the event ${chip.label}`"
      @click="emit('collapse', chip.rowId)"
    >
      <span class="expanded-rows__chip-label">{{ chip.label }}</span>
      <v-icon
        size="x-small"
        icon="mdi-close"
      />
    </button>

    <v-btn
      class="expanded-rows__collapse"
      variant="text"
      size="small"
      prepend-icon="mdi-unfold-less-horizontal"
      @click="emit('collapse-all')"
    >
      COLLAPSE ALL
    </v-btn>
  </div>
</template>

<script lang="ts">
import type { GridRow } from '@/models/grid'

/** One open panel, named the way the table names its event. */
interface ExpandedChip {
  rowId: string
  label: string
}

interface Props {
  expandedIds: string[]
  rows: GridRow[]
}

interface Emits {
  (event: 'collapse', rowId: string): void
  (event: 'collapse-all'): void
}

/** The column the inventory shows an event under, which is what a chip has to name it by. */
const EVENT_ID_KEY = 'event_id'

export type { ExpandedChip }
</script>

<script setup lang="ts">
import { computed } from 'vue'

import { findRowById } from '@/composables/useEventsGrid'
import { readText } from '@/utils/rows'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const chips = computed<ExpandedChip[]>(() =>
  props.expandedIds.map((rowId) => {
    /*
     * A panel can outlive the block of rows that opened it - the page moved on, or the filters narrowed past
     * it - so a chip whose row is no longer loaded falls back to the identifier it was opened under.
     */
    const row = findRowById(props.rows, rowId)
    const eventId = row === undefined ? '' : readText(row, EVENT_ID_KEY)

    return { rowId, label: `#${eventId.length > 0 ? eventId : rowId}` }
  }),
)
</script>

<style scoped>
.expanded-rows {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding-block-end: 0.75rem;
}

.expanded-rows__label {
  font-size: 0.8125rem;
  opacity: 0.7;
}

.expanded-rows__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  border: 0.0625rem solid rgb(var(--v-theme-control-border));
  border-radius: 999rem;
  background-color: rgb(var(--v-theme-control-surface));
  color: rgb(var(--v-theme-on-surface));
  padding-inline: 0.75rem;
  padding-block: 0.25rem;
  font-size: 0.8125rem;
  cursor: pointer;
}

.expanded-rows__chip:hover {
  background-color: rgb(var(--v-theme-control-surface-hover));
}

.expanded-rows__chip-label {
  font-weight: 600;
  white-space: nowrap;
}

.expanded-rows__collapse.v-btn {
  letter-spacing: normal;
}
</style>
