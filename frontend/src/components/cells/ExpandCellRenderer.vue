<template>
  <div class="expand-cell">
    <!--
      The arrow points the way the panel is about to move: down while the row is shut, because pressing it
      opens the panel underneath, and up once it is open, because pressing it folds the panel away again.
    -->
    <v-btn
      :icon="expanded ? 'mdi-chevron-up' : 'mdi-chevron-down'"
      size="small"
      variant="text"
      :aria-label="expanded ? 'Hide the details of the event' : 'Show the details of the event'"
      :aria-expanded="expanded"
      @click.stop="toggleDetails"
    />
  </div>
</template>

<script lang="ts">
import type { ICellRendererParams } from 'ag-grid-community'
import type { GridRow } from '@/models/grid'

interface Props {
  params: ICellRendererParams<GridRow>
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

import { readContext, readRowId } from '@/utils/grid-context'

const props = defineProps<Props>()

const rowId = computed<string>(() => readRowId(props.params))
const expanded = computed<boolean>(() => readContext(props.params).expandedIds.includes(rowId.value))

const toggleDetails = () => {
  readContext(props.params).toggleExpanded(rowId.value)
}
</script>

<style>
.expand-cell {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: flex-start;
  block-size: 100%;
  inline-size: 100%;
}
</style>
