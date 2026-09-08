<template>
  <div
    v-if="visible"
    class="upload-progress"
  >
    <v-progress-linear
      :model-value="percent"
      color="primary"
      height="6"
      rounded
    />
    <span class="upload-progress__label">{{ label }}</span>
  </div>
</template>

<script lang="ts">
interface Props {
  /** Whether the pick is large enough to be worth watching at all. */
  visible: boolean
  /** How much of it has landed, out of a hundred. */
  percent: number
  /** What has been written so far, and which file is being written. */
  label: string
}
</script>

<script setup lang="ts">
defineProps<Props>()
</script>

<style scoped>
.upload-progress {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.25rem;
  min-inline-size: 12rem;
}

.upload-progress__label {
  font-size: 0.75rem;
  opacity: 0.7;
}
</style>
