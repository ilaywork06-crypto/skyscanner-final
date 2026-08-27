<template>
  <div class="file-list">
    <div
      v-for="group in groups"
      :key="group.name"
      class="file-list__group"
    >
      <v-btn
        v-if="group.name.length > 0"
        class="file-list__folder"
        variant="text"
        @click.stop="toggleFolder(group.name)"
      >
        <v-icon
          size="small"
          icon="mdi-folder-outline"
        />
        <span class="file-list__label">{{ group.name }}</span>
        <v-icon
          size="x-small"
          :icon="isOpen(group.name) ? 'mdi-chevron-down' : 'mdi-chevron-up'"
        />
      </v-btn>

      <!--
        Opening a file and taking a copy of it are two different intentions, so they are two different
        controls: the name opens the viewer, the icon beside it downloads.
      -->
      <div
        v-if="group.name.length === 0 || isOpen(group.name)"
        class="file-list__files"
      >
        <div
          v-for="file in group.files"
          :key="file.id"
          class="file-list__entry"
          :class="{ 'file-list__entry--active': file.id === activeId }"
        >
          <v-btn
            class="file-list__file"
            variant="text"
            :aria-label="`Open ${file.name}`"
            @click.stop="emit('open', file)"
          >
            <v-icon
              size="small"
              :icon="iconOf(file)"
            />
            <!-- When a file arrived and who brought it belong to the file, but never above its name. -->
            <span class="file-list__text">
              <span class="file-list__label">
                <HighlightedText
                  v-if="isMatch(file)"
                  :text="file.name"
                  :term="search"
                />
                <template v-else>{{ file.name }}</template>
              </span>
              <span
                v-if="showUpload"
                class="file-list__meta"
              >{{ uploadedLine(file) }}</span>
            </span>
            <SkyTooltip>{{ file.name }}</SkyTooltip>
          </v-btn>
          <v-btn
            class="file-list__download"
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

    <span
      v-if="files.length === 0"
      class="file-list__empty"
    >{{ EMPTY_PLACEHOLDER }}</span>
  </div>
</template>

<script lang="ts">
import type { Artifact } from '@/models/common'
import { EMPTY_PLACEHOLDER, SkyTooltip, fileIcon, formatDateTime } from '@skyscanner/sky-ui'

interface Props {
  files: Artifact[]
  startOpen?: boolean
  activeId?: string | null
  /**
   * Whether each file also says when it was uploaded and by whom.
   *
   * That is a second line per file, which a row of the inventory has no room for: the grid gives every row
   * the same height, so a list that grows there is a list that is cut off. The surfaces that let a row grow
   * ask for it, and the ones that do not, do not.
   */
  showUpload?: boolean
  /**
   * What the rows the list is shown inside were searched for, so that a matched file name says so.
   *
   * The name of a file is one of the paths the inventory searches, which makes a file the reason its whole
   * event is on screen - and a list that paints nothing leaves the reader to find that file by eye. The
   * surfaces that were never searched leave this alone and the list renders its names untouched.
   */
  search?: string
  /**
   * Whether the folders the files were uploaded under are shown at all.
   *
   * A column that is already called RAW FILES has nothing to gain from a folder inside it called raw_files:
   * the reader would have to open a folder to reach a list the column heading already named. The surfaces
   * that hold every file of an object at once - the tree of the event page - keep the folders, because there
   * the folder is the only thing telling one half of the files from the other.
   */
  flat?: boolean
}

interface Emits {
  (event: 'open', artifact: Artifact): void
  (event: 'download', artifact: Artifact): void
}

interface FileGroup {
  name: string
  files: Artifact[]
}
</script>

<script setup lang="ts">
import { computed, ref } from 'vue'

import HighlightedText from '@/components/HighlightedText.vue'
import { matchesTerm } from '@/utils/highlight'

const props = withDefaults(defineProps<Props>(), {
  startOpen: false,
  activeId: null,
  showUpload: false,
  search: '',
  flat: false,
})
const emit = defineEmits<Emits>()

const openFolders = ref<string[]>([])

const groups = computed<FileGroup[]>(() => {
  if (props.flat) {
    return props.files.length === 0 ? [] : [{ name: '', files: props.files }]
  }

  const byFolder = new Map<string, Artifact[]>()
  props.files.forEach((file) => {
    const key = file.folder ?? ''
    const bucket = byFolder.get(key) ?? []
    bucket.push(file)
    byFolder.set(key, bucket)
  })

  return [...byFolder.entries()].map(([name, files]) => ({ name, files }))
})

const iconOf = (file: Artifact): string => fileIcon(file.name, file.suffix, file.content_type)

const isMatch = (file: Artifact): boolean => matchesTerm(file.name, props.search)

/**
 * Say when a file was uploaded and by whom, in the dash the system uses for what it was never told.
 *
 * A file stored before the uploader was recorded carries neither of the two, and reading a dash there is
 * what tells a reader that nobody was recorded rather than that the line means something else.
 */
const uploadedLine = (file: Artifact): string =>
  `${formatDateTime(file.created_at)} · ${file.uploaded_by ?? EMPTY_PLACEHOLDER}`

const isOpen = (name: string): boolean => props.startOpen || openFolders.value.includes(name)

const toggleFolder = (name: string) => {
  openFolders.value = openFolders.value.includes(name)
    ? openFolders.value.filter((candidate) => candidate !== name)
    : [...openFolders.value, name]
}
</script>

<style scoped>
.file-list {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  inline-size: 100%;
  padding-block: 0.25rem;
}

.file-list__group {
  display: flex;
  flex-direction: column;
}

/*
 * A v-btn sizes its middle grid track from its content, so a full width row has to become a plain flex box
 * before the label can take the free space and ellipsise.
 */
/*
 * The file tree is read far more often than it is clicked, so the rows carry the ordinary body size rather
 * than the smaller one a dense control would use, and the icons are sized to match.
 */
.file-list__folder.v-btn,
.file-list__file.v-btn {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.5rem;
  background: none;
  border: none;
  padding: 0;
  color: inherit;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 400;
  letter-spacing: normal;
  text-transform: none;
  text-align: start;
  block-size: auto;
  min-block-size: 1.75rem;
  min-inline-size: 0;
  inline-size: 100%;
}

.file-list__folder.v-btn {
  font-weight: 600;
}

.file-list__folder.v-btn :deep(.v-icon),
.file-list__file.v-btn :deep(.v-icon) {
  font-size: 1.125rem;
}

.file-list__folder.v-btn :deep(.v-btn__content),
.file-list__file.v-btn :deep(.v-btn__content) {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  justify-content: flex-start;
  gap: 0.375rem;
  min-inline-size: 0;
}

.file-list__file.v-btn:hover .file-list__label {
  text-decoration: underline;
}

.file-list__files {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.file-list__entry {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  border-radius: 0.25rem;
  min-inline-size: 0;
}

.file-list__entry--active {
  background-color: rgba(var(--v-theme-primary), 0.12);
}

/*
 * The download icon stays out of the way until the row is pointed at or reached by the keyboard, so that a
 * column of files reads as a list of names rather than as a column of buttons.
 */
.file-list__download.v-btn {
  flex: 0 0 auto;
  opacity: 0;
  transition: opacity 0.12s ease-in-out;
}

.file-list__entry:hover .file-list__download.v-btn,
.file-list__entry--active .file-list__download.v-btn,
.file-list__download.v-btn:focus-visible {
  opacity: 1;
}

.file-list__text {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  align-items: flex-start;
  min-inline-size: 0;
  max-inline-size: 100%;
}

.file-list__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1 1 auto;
  min-inline-size: 0;
  max-inline-size: 100%;
}

/* The upload details are read second, so they are set smaller and quieter than the name above them. */
.file-list__meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-inline-size: 100%;
  font-size: 0.6875rem;
  line-height: 1.2;
  opacity: 0.6;
}

.file-list__empty {
  opacity: 0.6;
}
</style>
