<template>
  <v-tooltip
    :activator="activator"
    :location="location"
    :open-delay="OPEN_DELAY_MS"
    :close-delay="CLOSE_DELAY_MS"
    :close-on-content-click="false"
    content-class="sky-tooltip"
  >
    <slot />
  </v-tooltip>
</template>

<script lang="ts">
interface Props {
  activator?: string
  location?: 'top' | 'bottom' | 'start' | 'end'
}

const OPEN_DELAY_MS = 200
const CLOSE_DELAY_MS = 250
</script>

<script setup lang="ts">
withDefaults(defineProps<Props>(), { activator: 'parent', location: 'top' })
</script>

<style>
/*
 * The tooltip stays reachable with the pointer and keeps its text selectable, so that a value
 * that is too long for its cell can still be read in full and copied out of the tooltip.
 */
.sky-tooltip {
  pointer-events: auto;
  user-select: text;
  max-inline-size: 32rem;
  overflow-wrap: anywhere;
  opacity: 1 !important;
}
</style>
