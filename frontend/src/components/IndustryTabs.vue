<template>
  <nav
    class="industry-tabs"
    aria-label="Industries"
  >
    <!--
      All is not an industry, it is the absence of a choice of one, so it leads the row and never takes part
      in the arrangement: it cannot be dragged and nothing can be dropped in front of it.
    -->
    <v-btn
      class="industry-tabs__tab"
      :class="{ 'industry-tabs__tab--active': modelValue === null }"
      variant="text"
      @click="emit('update:modelValue', null)"
    >
      All
    </v-btn>
    <v-btn
      v-for="(industry, index) in orderedIndustries"
      :key="industry.key"
      class="industry-tabs__tab"
      :class="{
        'industry-tabs__tab--active': modelValue === industry.key,
        'industry-tabs__tab--dragged': draggedKey === industry.key,
        'industry-tabs__tab--target': dropIndex === index && draggedKey !== industry.key,
      }"
      variant="text"
      draggable="true"
      :title="`${industry.name} — drag to move this tab`"
      @click="emit('update:modelValue', industry.key)"
      @dragstart="onDragStart(industry.key, $event)"
      @dragover.prevent="dropIndex = index"
      @dragleave="onDragLeave(index)"
      @drop.prevent="onDrop(index)"
      @dragend="onDragEnd"
    >
      {{ industry.name }}
    </v-btn>
  </nav>
</template>

<script lang="ts">
import type { Industry } from '@/models/industry'

interface Props {
  industries: Industry[]
  modelValue: string | null
}

interface Emits {
  (event: 'update:modelValue', industry: string | null): void
}

/** What a drag carries, which a browser insists on being handed something for. */
const DRAG_MEDIA_TYPE = 'text/plain'
</script>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { moveIndustry, orderIndustries, readOrder, writeOrder } from '@/utils/industry-order'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

/* The arrangement this browser was left in, which the tabs are rendered in until it is changed again. */
const order = ref<string[]>(readOrder())

const draggedKey = ref<string | null>(null)
const dropIndex = ref<number | null>(null)

const orderedIndustries = computed<Industry[]>(() => orderIndustries(props.industries, order.value))

const orderedKeys = computed<string[]>(() => orderedIndustries.value.map((industry) => industry.key))

const onDragStart = (key: string, event: DragEvent) => {
  draggedKey.value = key
  event.dataTransfer?.setData(DRAG_MEDIA_TYPE, key)
  if (event.dataTransfer !== null) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

/*
 * Leaving one tab is only worth forgetting the marker for when the pointer has really left it, rather than
 * when it has crossed onto the next one - which fires the leave of the old tab after the over of the new.
 */
const onDragLeave = (index: number) => {
  if (dropIndex.value === index) {
    dropIndex.value = null
  }
}

const onDrop = (index: number) => {
  const key = draggedKey.value
  const from = key === null ? -1 : orderedKeys.value.indexOf(key)
  if (from >= 0) {
    /* The whole arrangement is written, not only the tab that moved, so that an industry the stored order
       never named takes its place in it rather than falling back behind every reload. */
    order.value = moveIndustry(orderedKeys.value, from, index)
    writeOrder(order.value)
  }

  onDragEnd()
}

const onDragEnd = () => {
  draggedKey.value = null
  dropIndex.value = null
}
</script>

<style scoped>
.industry-tabs {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 0.375rem;
  padding-inline: 2rem;
  overflow-x: auto;
}

.industry-tabs__tab.v-btn {
  border: 0.0625rem solid rgba(var(--v-theme-on-surface), 0.35);
  border-block-end: none;
  border-start-start-radius: 0.5rem;
  border-start-end-radius: 0.5rem;
  border-end-start-radius: 0;
  border-end-end-radius: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  padding-inline: 1.75rem;
  padding-block: 0.625rem;
  font-size: 0.9375rem;
  font-weight: 400;
  letter-spacing: normal;
  text-transform: none;
  block-size: auto;
  min-inline-size: 0;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s ease-in-out;
}

.industry-tabs__tab.v-btn:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.1);
}

/*
 * The industry currently on screen has to be readable at a glance, so the selected tab drops out of the
 * header gradient entirely instead of shifting one shade inside it.
 */
.industry-tabs__tab--active.v-btn {
  background-color: rgb(var(--v-theme-tab-active));
  color: rgb(var(--v-theme-on-tab-active));
  border-color: transparent;
  font-weight: 600;
}

.industry-tabs__tab--active.v-btn:hover {
  background-color: rgb(var(--v-theme-tab-active));
}

/* The tab being carried fades, and the one it would land on shows the edge it would land against. */
.industry-tabs__tab--dragged.v-btn {
  opacity: 0.4;
}

.industry-tabs__tab--target.v-btn {
  border-inline-start: 0.1875rem solid rgb(var(--v-theme-primary));
}

@media (max-width: 48rem) {
  .industry-tabs {
    padding-inline: 1rem;
  }

  .industry-tabs__tab {
    padding-inline: 1rem;
  }
}
</style>
