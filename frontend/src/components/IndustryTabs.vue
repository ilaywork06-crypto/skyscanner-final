<template>
  <nav
    class="industry-tabs"
    aria-label="Industries"
  >
    <v-btn
      class="industry-tabs__tab"
      :class="{ 'industry-tabs__tab--active': modelValue === null }"
      variant="text"
      @click="emit('update:modelValue', null)"
    >
      All
    </v-btn>
    <v-btn
      v-for="industry in industries"
      :key="industry.key"
      class="industry-tabs__tab"
      :class="{ 'industry-tabs__tab--active': modelValue === industry.key }"
      variant="text"
      @click="emit('update:modelValue', industry.key)"
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
</script>

<script setup lang="ts">
defineProps<Props>()
const emit = defineEmits<Emits>()
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

@media (max-width: 48rem) {
  .industry-tabs {
    padding-inline: 1rem;
  }

  .industry-tabs__tab {
    padding-inline: 1rem;
  }
}
</style>
