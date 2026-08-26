<template>
  <div class="stored-files">
    <div class="stored-files__head">
      <span class="stored-files__title">{{ label }}</span>
      <span class="stored-files__count">{{ modelValue.length }} of {{ stored.length }} kept</span>
    </div>

    <p
      v-if="stored.length === 0"
      class="stored-files__empty"
    >
      No file is attached yet.
    </p>

    <!--
      A file is taken off by marking it and saving, never by a button that reaches into the bucket on its own:
      the removal belongs to the same edit as everything else on the form, so it travels with the reason for
      the edit and lands in the history beside it. Until Save is pressed the mark can be taken back.
    -->
    <div
      v-for="file in stored"
      :key="file.id"
      class="stored-files__entry"
      :class="{ 'stored-files__entry--removed': isRemoved(file) }"
    >
      <v-icon
        size="small"
        :icon="fileIcon(file.name, file.suffix, file.content_type)"
      />
      <span class="stored-files__name">{{ file.name }}</span>
      <span class="stored-files__meta">{{ formatBytes(file.size_bytes) }}</span>
      <v-btn
        size="x-small"
        variant="text"
        :prepend-icon="isRemoved(file) ? 'mdi-undo' : 'mdi-close'"
        :aria-label="isRemoved(file) ? `Keep ${file.name}` : `Remove ${file.name}`"
        @click="toggle(file)"
      >
        {{ isRemoved(file) ? 'UNDO' : 'REMOVE' }}
      </v-btn>
    </div>

    <p
      v-if="removedCount > 0"
      class="stored-files__warning"
    >
      {{ removedCount }} file(s) will be detached when this edit is saved, and the change is recorded in the
      edit history.
    </p>
  </div>
</template>

<script lang="ts">
import type { Artifact } from '@/models/common'
import { fileIcon, formatBytes } from '@skyscanner/sky-ui'

interface Props {
  /** Everything the owner holds today, which is what the list renders. */
  stored: Artifact[]
  /** The files that will survive the edit, which is what the form submits. */
  modelValue: Artifact[]
  label?: string
}

interface Emits {
  (event: 'update:modelValue', files: Artifact[]): void
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<Props>(), { label: 'Attached files' })
const emit = defineEmits<Emits>()

const keptIds = computed<Set<string>>(() => new Set(props.modelValue.map((file) => file.id)))

const removedCount = computed<number>(() => props.stored.length - props.modelValue.length)

const isRemoved = (file: Artifact): boolean => !keptIds.value.has(file.id)

/*
 * The kept list is rebuilt out of the stored order rather than by pushing onto the end of itself, so undoing
 * a removal puts the file back where it was instead of at the bottom of the list.
 */
const toggle = (file: Artifact) => {
  const kept = new Set(keptIds.value)
  if (kept.has(file.id)) {
    kept.delete(file.id)
  } else {
    kept.add(file.id)
  }

  emit(
    'update:modelValue',
    props.stored.filter((candidate) => kept.has(candidate.id)),
  )
}
</script>

<style scoped>
.stored-files {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  inline-size: 100%;
}

.stored-files__head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stored-files__title {
  font-size: 0.9375rem;
  font-weight: 500;
}

.stored-files__count {
  margin-inline-start: auto;
  font-size: 0.75rem;
  opacity: 0.6;
}

.stored-files__entry {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
  padding-inline: 0.625rem;
  padding-block: 0.25rem;
  font-size: 0.8125rem;
  min-inline-size: 0;
}

/* A file marked for removal is struck through rather than taken off screen, so the mark can be taken back. */
.stored-files__entry--removed {
  opacity: 0.55;
}

.stored-files__entry--removed .stored-files__name {
  text-decoration: line-through;
}

.stored-files__name {
  flex: 1 1 auto;
  min-inline-size: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stored-files__meta {
  flex: 0 0 auto;
  opacity: 0.6;
  font-size: 0.75rem;
}

.stored-files__empty {
  font-size: 0.8125rem;
  opacity: 0.7;
}

.stored-files__warning {
  font-size: 0.8125rem;
  color: rgb(var(--v-theme-warning));
}
</style>
