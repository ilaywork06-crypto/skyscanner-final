<template>
  <div class="file-preview">
    <div
      v-if="loading"
      class="file-preview__centre"
    >
      <v-progress-circular
        indeterminate
        color="primary"
        size="36"
      />
    </div>

    <img
      v-else-if="mode === 'image'"
      :src="contentUrl"
      :alt="artifact.name"
      class="file-preview__image"
    >

    <iframe
      v-else-if="mode === 'frame'"
      :src="contentUrl"
      :title="artifact.name"
      class="file-preview__frame"
    />

    <template v-else-if="mode === 'table' && failure.length === 0">
      <!-- A sheet is read as a table, and the text it was written as stays one click away. -->
      <div class="file-preview__toolbar">
        <span class="file-preview__note">{{ tableNote }}</span>
        <v-spacer />
        <v-btn
          v-if="text.length > 0"
          size="small"
          variant="text"
          @click="showRaw = !showRaw"
        >
          {{ showRaw ? 'SHOW TABLE' : 'SHOW RAW TEXT' }}
        </v-btn>
      </div>

      <pre
        v-if="showRaw"
        class="file-preview__text"
      >{{ text }}</pre>

      <div
        v-else
        class="file-preview__scroll"
      >
        <table class="file-preview__table">
          <thead>
            <tr>
              <th
                v-for="(cell, index) in headerRow"
                :key="index"
                class="file-preview__head-cell"
              >
                {{ cell }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, rowIndex) in bodyRows"
              :key="rowIndex"
            >
              <td
                v-for="(cell, cellIndex) in row"
                :key="cellIndex"
                class="file-preview__cell"
                :title="cell"
              >
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <pre
      v-else-if="mode === 'text' && failure.length === 0"
      class="file-preview__text"
    >{{ text }}</pre>

    <div
      v-else
      class="file-preview__centre file-preview__fallback"
    >
      <v-icon
        size="48"
        icon="mdi-file-question-outline"
      />
      <p>{{ fallbackMessage }}</p>
      <v-btn
        color="primary"
        variant="tonal"
        prepend-icon="mdi-download"
        @click="emit('download', artifact)"
      >
        DOWNLOAD
      </v-btn>
    </div>
  </div>
</template>

<script lang="ts">
import type { Artifact } from '@/models/common'
import type { SheetContent } from '@/utils/sheets'

interface Props {
  artifact: Artifact
}

interface Emits {
  (event: 'download', artifact: Artifact): void
}

/** How a file is shown: as a picture, inside a frame, as a sheet, as plain text, or not at all. */
type PreviewMode = 'image' | 'frame' | 'table' | 'text' | 'unsupported'

const IMAGE_SUFFIXES: string[] = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'avif']
const FRAME_SUFFIXES: string[] = ['pdf', 'html', 'htm']
const DELIMITED_SUFFIXES: string[] = ['csv', 'tsv', 'tab']
const WORKBOOK_SUFFIXES: string[] = ['xlsx', 'xlsm', 'xls']
const TEXT_SUFFIXES: string[] = [
  'txt', 'log', 'json', 'yaml', 'yml', 'xml', 'md', 'ini', 'cfg', 'conf', 'py', 'js', 'ts', 'sql',
]

/** The types a workbook arrives under, which is what a browser reports for a file saved out of Excel. */
const WORKBOOK_CONTENT_TYPES: string[] = [
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-excel',
]

/** Largest text shaped file that is pulled into the browser to be shown, in bytes. */
const TEXT_PREVIEW_LIMIT = 2 * 1024 * 1024

/** Largest workbook that is pulled into the browser, in bytes. A workbook is compressed, so it may be read further. */
const WORKBOOK_PREVIEW_LIMIT = 16 * 1024 * 1024

/** Most data rows of a sheet that are put into the document, however many the file holds. */
const TABLE_ROW_LIMIT = 500

const EMPTY_SHEET: SheetContent = { rows: [], truncated: false }
const READ_FAILURE = 'The file could not be read.'
const EMPTY_WORKBOOK = 'This workbook holds no rows to show.'
const UNSUPPORTED = 'This file cannot be shown in the browser.'
const TOO_LARGE = 'This file is too large to be shown in the browser.'
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { buildContentUrl } from '@/requests/storage'
import { delimiterOf, parseDelimited, readWorkbook } from '@/utils/sheets'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const text = ref<string>('')
const sheet = ref<SheetContent>(EMPTY_SHEET)
const loading = ref<boolean>(false)
const failure = ref<string>('')
const showRaw = ref<boolean>(false)

/*
 * Which read the shown content came from. A reader who walks down a file tree starts a read per file, and
 * without this the answer of an abandoned one would overwrite the file that is now selected.
 */
let currentRead = 0

/**
 * Read the suffix of a file, preferring the recorded one over the tail of the name.
 */
const suffix = computed<string>(() => {
  const recorded = props.artifact.suffix.replace('.', '').toLowerCase()

  return recorded.length > 0 ? recorded : (props.artifact.name.split('.').pop() ?? '').toLowerCase()
})

const contentType = computed<string>(() => props.artifact.content_type.toLowerCase())

const isWorkbook = computed<boolean>(
  () => WORKBOOK_CONTENT_TYPES.includes(contentType.value) || WORKBOOK_SUFFIXES.includes(suffix.value),
)

/**
 * Decide what the file looks like, going by its content type first and by its suffix second.
 *
 * The content type of a stored file is whatever the browser of the uploader claimed, which for a csv is
 * anything from text/csv to application/octet-stream, so the suffix is asked whenever the type says nothing.
 */
const shape = computed<PreviewMode>(() => {
  if (contentType.value.startsWith('image/') || IMAGE_SUFFIXES.includes(suffix.value)) {
    return 'image'
  }
  if (contentType.value === 'application/pdf' || FRAME_SUFFIXES.includes(suffix.value)) {
    return 'frame'
  }
  if (isWorkbook.value || DELIMITED_SUFFIXES.includes(suffix.value) || contentType.value.includes('csv')) {
    return 'table'
  }
  if (
    contentType.value.startsWith('text/')
    || contentType.value.includes('json')
    || TEXT_SUFFIXES.includes(suffix.value)
  ) {
    return 'text'
  }

  return 'unsupported'
})

const sizeLimit = computed<number>(() => (isWorkbook.value ? WORKBOOK_PREVIEW_LIMIT : TEXT_PREVIEW_LIMIT))

/* A file that has to travel into the browser before it can be shown is only offered as a download past its cap. */
const oversized = computed<boolean>(
  () => (shape.value === 'text' || shape.value === 'table') && props.artifact.size_bytes > sizeLimit.value,
)

const mode = computed<PreviewMode>(() => (oversized.value ? 'unsupported' : shape.value))

const contentUrl = computed<string>(() => buildContentUrl(props.artifact.path, true))

const headerRow = computed<string[]>(() => sheet.value.rows[0] ?? [])

/* Rows of a sheet are ragged, and a row shorter than the header would otherwise pull the table apart. */
const bodyRows = computed<string[][]>(() =>
  sheet.value.rows
    .slice(1)
    .map((row) => [...row, ...Array<string>(Math.max(headerRow.value.length - row.length, 0)).fill('')]),
)

const tableNote = computed<string>(() =>
  sheet.value.truncated
    ? `The first ${TABLE_ROW_LIMIT} rows of a longer file are shown.`
    : `${bodyRows.value.length} rows`,
)

const fallbackMessage = computed<string>(() => {
  if (failure.value.length > 0) {
    return failure.value
  }

  return oversized.value ? TOO_LARGE : UNSUPPORTED
})

/**
 * Pull the bytes of the selected file through the service.
 */
const readContent = async (): Promise<Response> => {
  const response = await fetch(contentUrl.value)
  if (!response.ok) {
    throw new Error(READ_FAILURE)
  }

  return response
}

/**
 * Read a sheet or a text into the browser, so that it is shown formatted instead of handed to a download.
 *
 * A browser given a csv, a log or an unrecognised type inside a frame saves it to disk rather than rendering
 * it, which turned every click on such a file into a download nobody asked for. Reading the bytes here and
 * rendering them ourselves is what keeps opening a file and taking a copy of it two separate actions.
 */
const load = async (): Promise<void> => {
  currentRead += 1
  const read = currentRead

  text.value = ''
  sheet.value = EMPTY_SHEET
  failure.value = ''
  showRaw.value = false

  if (mode.value !== 'text' && mode.value !== 'table') {
    loading.value = false

    return
  }

  loading.value = true
  try {
    if (isWorkbook.value) {
      const buffer = await (await readContent()).arrayBuffer()
      const content = await readWorkbook(buffer, TABLE_ROW_LIMIT + 1)
      if (read !== currentRead) {
        return
      }
      sheet.value = content
      failure.value = content.rows.length === 0 ? EMPTY_WORKBOOK : ''
    } else {
      const body = await (await readContent()).text()
      if (read !== currentRead) {
        return
      }
      text.value = body
      if (mode.value === 'table') {
        sheet.value = parseDelimited(body, delimiterOf(suffix.value, body), TABLE_ROW_LIMIT + 1)
        /* A sheet nothing could be read out of is still a text, and the text is better than an empty table. */
        showRaw.value = sheet.value.rows.length === 0
      }
    }
  } catch {
    if (read === currentRead) {
      failure.value = READ_FAILURE
    }
  } finally {
    if (read === currentRead) {
      loading.value = false
    }
  }
}

watch(() => props.artifact, load, { immediate: true })
</script>

<style scoped>
.file-preview {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.5rem;
  min-block-size: 0;
  min-inline-size: 0;
  inline-size: 100%;
}

.file-preview__centre {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  text-align: center;
}

.file-preview__fallback {
  background-color: rgb(var(--v-theme-surface));
  border-radius: 0.5rem;
  padding: 1rem;
  opacity: 0.9;
}

.file-preview__image {
  max-inline-size: 100%;
  max-block-size: 100%;
  object-fit: contain;
  margin: auto;
}

.file-preview__frame {
  flex: 1 1 auto;
  inline-size: 100%;
  min-block-size: 0;
  border: none;
  border-radius: 0.5rem;
  background-color: #ffffff;
}

.file-preview__toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-block-size: 2rem;
}

.file-preview__note {
  font-size: 0.75rem;
  opacity: 0.7;
}

/* A wide sheet scrolls inside the pane rather than stretching whatever holds it. */
.file-preview__scroll {
  flex: 1 1 auto;
  overflow: auto;
  border-radius: 0.5rem;
  background-color: rgb(var(--v-theme-surface));
  min-block-size: 0;
}

.file-preview__table {
  border-collapse: collapse;
  inline-size: 100%;
  font-size: 0.8125rem;
}

.file-preview__head-cell,
.file-preview__cell {
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  padding-inline: 0.625rem;
  padding-block: 0.375rem;
  text-align: start;
  white-space: nowrap;
  max-inline-size: 24rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* The header stays in sight while a long sheet scrolls under it, which is what makes the columns readable. */
.file-preview__head-cell {
  position: sticky;
  inset-block-start: 0;
  z-index: 1;
  background-color: rgb(var(--v-theme-table-header));
  font-weight: 700;
}

.file-preview__cell {
  background-color: rgb(var(--v-theme-table-row));
}

.file-preview__text {
  flex: 1 1 auto;
  overflow: auto;
  margin: 0;
  border-radius: 0.5rem;
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 1rem;
  font-family: ui-monospace, 'SFMono-Regular', 'Consolas', monospace;
  font-size: 0.8125rem;
  line-height: 1.5;
  white-space: pre;
  tab-size: 2;
  min-block-size: 0;
}
</style>
