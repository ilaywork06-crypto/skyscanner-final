<template>
  <div class="dropzone">
    <p
      v-if="label.length > 0"
      class="dropzone__label"
    >
      {{ label }}
    </p>
    <p class="dropzone__hint">
      Multiple files are allowed, but the same file name only once
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

    <!--
      A name that is already on the list is refused rather than added beside it: two files under one name
      leave the owner with two records nobody can tell apart, and only the person picking knows which one
      they meant. Saying which names were turned away is what tells that apart from a picker that did nothing.
    -->
    <p
      v-if="rejected.length > 0"
      class="dropzone__rejected"
    >
      Already picked, so not added again: {{ rejected.join(', ') }}
    </p>

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

/** The names of the last pick that were turned away, so that a refusal is never silent. */
const rejected = ref<string[]>([])

/**
 * Take the picked files the list does not hold already, and remember the names of the ones it does.
 */
const append = (incoming: FileList | null) => {
  if (incoming === null) {
    return
  }

  const taken = new Set(props.files.map((file) => file.name))
  const accepted: File[] = []
  const refused: string[] = []

  Array.from(incoming).forEach((file) => {
    if (taken.has(file.name)) {
      refused.push(file.name)

      return
    }

    taken.add(file.name)
    accepted.push(file)
  })

  rejected.value = [...new Set(refused)]
  if (accepted.length > 0) {
    emit('update:files', [...props.files, ...accepted])
  }
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
  /* Taking a file off makes room for its name again, so the refusal it caused is no longer worth showing. */
  rejected.value = []
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

.dropzone__rejected {
  font-size: 0.75rem;
  color: rgb(var(--v-theme-error));
}

.dropzone__input {
  display: none;
}
</style>
