<template>
  <v-dialog
    :model-value="modelValue"
    max-width="64rem"
    scrollable
    @update:model-value="close"
  >
    <v-card
      v-if="artifact !== null"
      class="viewer"
    >
      <v-card-title class="viewer__title">
        <v-icon
          class="viewer__icon"
          size="small"
          icon="mdi-file-outline"
        />
        <span class="viewer__name">{{ artifact.name }}</span>
        <span class="viewer__size">{{ formatBytes(artifact.size_bytes) }}</span>
        <v-spacer />
        <v-btn
          icon="mdi-download"
          variant="text"
          density="comfortable"
          :aria-label="`Download ${artifact.name}`"
          @click="emit('download', artifact)"
        />
        <v-btn
          icon="mdi-close"
          variant="text"
          density="comfortable"
          aria-label="Close the viewer"
          @click="close"
        />
      </v-card-title>

      <v-card-text class="viewer__body">
        <FilePreview
          :artifact="artifact"
          @download="emit('download', $event)"
        />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import type { Artifact } from '@/models/common'
import { formatBytes } from '@skyscanner/sky-ui'

interface Props {
  modelValue: boolean
  artifact?: Artifact | null
}

interface Emits {
  (event: 'update:modelValue', value: boolean): void
  (event: 'download', artifact: Artifact): void
}
</script>

<script setup lang="ts">
import FilePreview from '@/components/FilePreview.vue'

withDefaults(defineProps<Props>(), { artifact: null })
const emit = defineEmits<Emits>()

const close = () => {
  emit('update:modelValue', false)
}
</script>

<style scoped>
.viewer {
  background-color: rgb(var(--v-theme-surface));
}

.viewer__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}

.viewer__icon {
  flex: 0 0 auto;
}

.viewer__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-inline-size: 0;
}

.viewer__size {
  font-size: 0.8125rem;
  font-weight: 400;
  opacity: 0.6;
  flex: 0 0 auto;
}

.viewer__body {
  display: flex;
  flex-direction: column;
  block-size: 70vh;
  padding: 1rem;
}
</style>
