<template>
  <!--
    Every file the event carries in one place: the files attached to the event itself, and underneath them a
    branch per entity split by the role its files play. Before this the page only ever showed the additional
    files, so the telemetry products were reachable only by opening each entity in turn.
  -->
  <div class="file-tree">
    <div
      v-for="branch in branches"
      :key="branch.key"
      class="file-tree__branch"
    >
      <button
        type="button"
        class="file-tree__folder"
        :class="{ 'file-tree__folder--root': branch.depth === 0 }"
        :style="{ paddingInlineStart: `${branch.depth * 1.125}rem` }"
        :aria-expanded="isOpen(branch.key)"
        @click="toggle(branch.key)"
      >
        <v-icon
          size="small"
          :icon="isOpen(branch.key) ? 'mdi-folder-open-outline' : 'mdi-folder-outline'"
        />
        <span class="file-tree__label">{{ branch.name }}</span>
        <span class="file-tree__count">{{ branch.files.length }}</span>
        <v-icon
          size="x-small"
          :icon="isOpen(branch.key) ? 'mdi-chevron-down' : 'mdi-chevron-right'"
        />
      </button>

      <div
        v-if="isOpen(branch.key)"
        class="file-tree__files"
        :style="{ paddingInlineStart: `${(branch.depth + 1) * 1.125}rem` }"
      >
        <div
          v-for="file in branch.files"
          :key="file.id"
          class="file-tree__entry"
          :class="{ 'file-tree__entry--active': file.id === activeId }"
        >
          <button
            type="button"
            class="file-tree__file"
            :aria-label="`Open ${file.name}`"
            @click="emit('open', file)"
          >
            <v-icon
              size="small"
              :icon="iconOf(file)"
            />
            <!--
              Who put a file there and when is what a reader asks of a file they did not upload themselves,
              so it sits under the name rather than beside it: the name is what the row is found by.
            -->
            <span class="file-tree__text">
              <span class="file-tree__label">{{ file.name }}</span>
              <span class="file-tree__meta">{{ uploadedLine(file) }}</span>
            </span>
            <span class="file-tree__size">{{ formatBytes(file.size_bytes) }}</span>
          </button>
          <v-btn
            class="file-tree__download"
            icon="mdi-download"
            size="x-small"
            variant="text"
            density="compact"
            :aria-label="`Download ${file.name}`"
            @click.stop="emit('download', file)"
          />
        </div>
      </div>
    </div>

    <p
      v-if="branches.length === 0"
      class="file-tree__empty"
    >
      No files were attached to this event yet.
    </p>
  </div>
</template>

<script lang="ts">
import type { Artifact } from '@/models/common'
import { EMPTY_PLACEHOLDER, fileIcon, formatBytes, formatDateTime } from '@skyscanner/sky-ui'
import type { EntityResponse } from '@/models/entity'

interface Props {
  additionalFiles: Artifact[]
  entities: EntityResponse[]
  activeId?: string | null
}

interface Emits {
  (event: 'open', artifact: Artifact): void
  (event: 'download', artifact: Artifact): void
}

/** One folder of the tree, flattened so the template renders a list rather than recursing. */
interface FileBranch {
  key: string
  name: string
  depth: number
  files: Artifact[]
}

const FILE_SETS: { key: 'raw_files' | 'parsed_files' | 'parsed_additional_files'; label: string }[] = [
  { key: 'raw_files', label: 'Raw files' },
  { key: 'parsed_files', label: 'Parsed files' },
  { key: 'parsed_additional_files', label: 'Additional parsing products' },
]
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'


const props = withDefaults(defineProps<Props>(), { activeId: null })
const emit = defineEmits<Emits>()

const closed = ref<string[]>([])

const branches = computed<FileBranch[]>(() => {
  const collected: FileBranch[] = []

  if (props.additionalFiles.length > 0) {
    collected.push({
      key: 'additional',
      name: 'Additional files',
      depth: 0,
      files: props.additionalFiles,
    })
  }

  props.entities.forEach((entity) => {
    FILE_SETS.forEach((set) => {
      const files = entity[set.key]
      if (files.length === 0) {
        return
      }

      collected.push({
        key: `${entity.id}:${set.key}`,
        name: `${entity.object_type.name} · ${entity.name} · ${set.label}`,
        depth: 1,
        files,
      })
    })
  })

  return collected
})

/* Folders start open, because a reader who came to the file section came to see the files. */
const isOpen = (key: string): boolean => !closed.value.includes(key)

const toggle = (key: string) => {
  closed.value = isOpen(key) ? [...closed.value, key] : closed.value.filter((candidate) => candidate !== key)
}

const iconOf = (file: Artifact): string => fileIcon(file.name, file.suffix, file.content_type)

/**
 * Say when a file was uploaded and by whom, in the dash the system uses for what it was never told.
 *
 * Files stored before the uploader was recorded carry neither of the two, and those read as the dash rather
 * than as a gap, so that a row without them still lines up with the rows around it.
 */
const uploadedLine = (file: Artifact): string =>
  `${formatDateTime(file.created_at)} · ${file.uploaded_by ?? EMPTY_PLACEHOLDER}`

watch(() => props.entities, () => {
  closed.value = []
})
</script>

<style scoped>
.file-tree {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  inline-size: 100%;
}

.file-tree__branch {
  display: flex;
  flex-direction: column;
}

.file-tree__folder {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: none;
  background: none;
  padding-block: 0.375rem;
  color: inherit;
  font: inherit;
  font-size: 0.875rem;
  font-weight: 600;
  text-align: start;
  cursor: pointer;
  inline-size: 100%;
  min-inline-size: 0;
}

.file-tree__folder--root {
  font-size: 0.9375rem;
}

.file-tree__folder:hover {
  color: rgb(var(--v-theme-primary));
}

.file-tree__files {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.file-tree__entry {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  border-radius: 0.25rem;
  min-inline-size: 0;
}

.file-tree__entry--active {
  background-color: rgba(var(--v-theme-primary), 0.12);
}

.file-tree__file {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  gap: 0.5rem;
  border: none;
  background: none;
  padding-block: 0.3125rem;
  color: inherit;
  font: inherit;
  font-size: 0.875rem;
  text-align: start;
  cursor: pointer;
  min-inline-size: 0;
}

.file-tree__file:hover .file-tree__label,
.file-tree__file:focus-visible .file-tree__label {
  text-decoration: underline;
}

.file-tree__text {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-inline-size: 0;
}

.file-tree__label {
  flex: 1 1 auto;
  min-inline-size: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* The upload details are read second, so they are set smaller and quieter than the name above them. */
.file-tree__meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.6875rem;
  opacity: 0.6;
}

.file-tree__count,
.file-tree__size {
  flex: 0 0 auto;
  font-size: 0.75rem;
  font-weight: 400;
  opacity: 0.6;
}

/* The download stays out of the way until the row is pointed at, so the tree reads as a list of names. */
.file-tree__download.v-btn {
  flex: 0 0 auto;
  opacity: 0;
  transition: opacity 0.12s ease-in-out;
}

.file-tree__entry:hover .file-tree__download.v-btn,
.file-tree__entry--active .file-tree__download.v-btn,
.file-tree__download.v-btn:focus-visible {
  opacity: 1;
}

.file-tree__empty {
  opacity: 0.7;
  font-size: 0.875rem;
  padding-block: 0.5rem;
}
</style>
