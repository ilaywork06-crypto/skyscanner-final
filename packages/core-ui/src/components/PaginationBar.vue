<template>
  <div class="pagination">
    <span class="pagination__summary">
      {{ rangeLabel }}
    </span>

    <div class="pagination__controls">
      <v-select
        :model-value="pageSize"
        :items="PAGE_SIZES"
        class="pagination__size"
        density="compact"
        hide-details
        @update:model-value="emit('update:pageSize', $event)"
      />
      <v-pagination
        :model-value="page"
        :length="pageCount"
        :total-visible="5"
        density="comfortable"
        rounded="circle"
        @update:model-value="emit('update:page', $event)"
      />
    </div>
  </div>
</template>

<script lang="ts">
interface Props {
  page: number
  pageSize: number
  pageCount: number
  total: number
}

interface Emits {
  (event: 'update:page', page: number): void
  (event: 'update:pageSize', size: number): void
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

const PAGE_SIZES: number[] = [10, 25, 50, 100]

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const rangeLabel = computed<string>(() => {
  if (props.total === 0) {
    return 'No events'
  }

  const first = (props.page - 1) * props.pageSize + 1
  const last = Math.min(props.page * props.pageSize, props.total)

  return `${first} – ${last} of ${props.total} events`
})
</script>

<style scoped>
.pagination {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding-block: 0.75rem;
}

.pagination__summary {
  font-size: 0.875rem;
  opacity: 0.75;
}

.pagination__controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.pagination__size {
  inline-size: 6rem;
}
</style>
