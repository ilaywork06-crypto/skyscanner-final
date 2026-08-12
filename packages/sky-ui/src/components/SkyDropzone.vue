<template>
  <div class="dropzone">
    <p
      v-if="label.length > 0"
      class="dropzone__label"
    >
      {{ label }}
    </p>
    <p class="dropzone__hint">
      Multiple files are allowed
    </p>

    <div
      class="dropzone__area"
      :class="{ 'dropzone__area--active': dragging }"
      role="button"
      tabindex="0"
      @click="picker?.click()"
      @keydown.enter.prevent="picker?.click()"
      @keydown.space.prevent="picker?.click()"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <span
        v-if="files.length === 0"
        class="dropzone__placeholder"
      >Drag &amp; Drop Or Click</span>

      <div
        v-else
        class="dropzone__files"
      >
        <span
          v-for="(file, index) in files"
          :key="`${file.name}-${index}`"
          class="dropzone__file"
        >
          <v-icon
            size="x-small"
            icon="mdi-file-outline"
          />
          {{ file.name }}
          <span class="dropzone__size">{{ formatBytes(file.size) }}</span>
          <v-btn
            icon="mdi-close"
            size="x-small"
            variant="text"
            :aria-label="`Remove ${file.name}`"
            @click.stop="remove(index)"
          />
        </span>
      </div>
    </div>

    <input
      ref="picker"
      type="file"
      multiple
      class="dropzone__input"
      @change="onPick"
    >
  </div>
</template>

<script lang="ts">
interface Props {
  files: File[]
  label?: string
}

interface Emits {
  (event: 'update:files', files: File[]): void
}
</script>

<script setup lang="ts">
import { ref } from 'vue'

import { formatBytes } from '../utils/format'

const props = withDefaults(defineProps<Props>(), { label: 'Files' })
const emit = defineEmits<Emits>()

const picker = ref<HTMLInputElement | null>(null)
const dragging = ref<boolean>(false)

const append = (incoming: FileList | null) => {
  if (incoming === null) {
    return
  }

  emit('update:files', [...props.files, ...Array.from(incoming)])
}

const onPick = (event: Event) => {
  const target = event.target as HTMLInputElement
  append(target.files)
  target.value = ''
}

const onDrop = (event: DragEvent) => {
  dragging.value = false
  append(event.dataTransfer?.files ?? null)
}

const remove = (index: number) => {
  emit(
    'update:files',
    props.files.filter((_, candidate) => candidate !== index),
  )
}
</script>

<style scoped>
.dropzone {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  inline-size: 100%;
}

.dropzone__label {
  font-size: 0.9375rem;
  font-weight: 500;
}

.dropzone__hint {
  font-size: 0.75rem;
  opacity: 0.7;
}

.dropzone__area {
  display: flex;
  align-items: center;
  justify-content: center;
  min-block-size: 9rem;
  border: 0.09375rem dashed rgba(var(--v-theme-on-surface), 0.45);
  border-radius: 0.75rem;
  padding: 1rem;
  cursor: pointer;
  transition: border-color 0.15s ease-in-out, background-color 0.15s ease-in-out;
}

.dropzone__area--active {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.08);
}

.dropzone__placeholder {
  opacity: 0.8;
}

.dropzone__files {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  inline-size: 100%;
}

.dropzone__file {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  border-radius: 0.5rem;
  background-color: rgba(var(--v-theme-on-surface), 0.08);
  padding-inline: 0.625rem;
  padding-block: 0.25rem;
  font-size: 0.8125rem;
}

.dropzone__size {
  opacity: 0.6;
  font-size: 0.75rem;
}

.dropzone__input {
  display: none;
}
</style>
