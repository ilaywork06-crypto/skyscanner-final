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

    <!--
      Moving through a file that was never pulled over. What is on screen is one stretch of the bytes, and
      these are how a reader reaches the rest of them - including the end of a file far too large to scroll
      to, which used to be the one place a reader could never get to at all.
    -->
    <div
      v-if="windowed && failure.length === 0"
      class="file-preview__window"
    >
      <v-btn
        size="small"
        variant="text"
        icon="mdi-page-first"
        aria-label="Back to the start of the file"
        :disabled="atFileStart"
        @click="moveWindow(0)"
      />
      <v-btn
        size="small"
        variant="text"
        icon="mdi-chevron-left"
        aria-label="Back one stretch"
        :disabled="atFileStart"
        @click="stepWindow(-1)"
      />
      <v-slider
        class="file-preview__slider"
        :model-value="windowStart"
        :min="0"
        :max="lastWindowStart"
        :step="1"
        hide-details
        density="compact"
        aria-label="Where in the file to read"
        @end="moveWindow($event)"
      />
      <span class="file-preview__note">{{ windowLabel }}</span>
      <v-btn
        size="small"
        variant="text"
        icon="mdi-chevron-right"
        aria-label="On one stretch"
        :disabled="atFileEnd"
        @click="stepWindow(1)"
      />
      <v-btn
        size="small"
        variant="text"
        icon="mdi-page-last"
        aria-label="On to the end of the file"
        :disabled="atFileEnd"
        @click="moveWindow(lastWindowStart)"
      />
    </div>

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
import type { SheetContent } from '@truth-platform/core-ui'

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

/** Past this a text shaped file is read a window at a time rather than pulled into the browser whole. */
const TEXT_PREVIEW_LIMIT = 2 * 1024 * 1024

/** Largest workbook that is pulled into the browser, in bytes. A workbook is compressed, so it may be read further. */
const WORKBOOK_PREVIEW_LIMIT = 16 * 1024 * 1024

/** Most data rows of a sheet that are put into the document, however many the window holds. */
const TABLE_ROW_LIMIT = 500

/**
 * How much of a very large file is pulled over at a time.
 *
 * A telemetry sheet is measured in gigabytes and the reader is looking at a few hundred rows of it, so the
 * viewer asks for the stretch it is about to render rather than for the file. A megabyte is a few thousand
 * rows of an ordinary sheet - comfortably more than the row limit above ever puts on screen - and it arrives
 * fast enough on a slow link that moving through a file does not feel like waiting for one.
 */
const WINDOW_BYTES = 1024 * 1024

/** How much of the start of a sheet is read to find the row its columns are named in. */
const HEADING_BYTES = 64 * 1024

/** What a file too large to be shown says, which now only ever applies to a workbook. */
const TOO_LARGE_WORKBOOK = 'This workbook is too large to be opened in the browser.'

const EMPTY_SHEET: SheetContent = { rows: [], truncated: false }
const READ_FAILURE = 'The file could not be read.'
const EMPTY_WORKBOOK = 'This workbook holds no rows to show.'
const UNSUPPORTED = 'This file cannot be shown in the browser.'
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { buildContentUrl, readArtifactWindow } from '@/requests/storage'
import { delimiterOf, formatBytes, parseDelimited, readWorkbook, wholeLines } from '@truth-platform/core-ui'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const text = ref<string>('')
const sheet = ref<SheetContent>(EMPTY_SHEET)
const loading = ref<boolean>(false)
const failure = ref<string>('')
const showRaw = ref<boolean>(false)

/* Where in a very large file the stretch on screen begins, in bytes. Always zero for a file read whole. */
const windowStart = ref<number>(0)

/* The row a windowed sheet names its columns in, read once out of the first stretch of the file. */
const windowHeading = ref<string[]>([])

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

/*
 * A workbook is the one shape still capped. It is compressed and its rows are not laid out in the order the
 * file stores them, so there is no window of the bytes that answers to a window of the rows: the whole of it
 * has to arrive before any of it can be read.
 */
const oversized = computed<boolean>(() => isWorkbook.value && props.artifact.size_bytes > WORKBOOK_PREVIEW_LIMIT)

/*
 * Whether the file is read a stretch at a time. Anything text shaped past the cap used to be refused outright
 * - a reader with a four gigabyte sheet was told to download it and find something else to open it with -
 * and it is now read by asking the service for the window that is about to be rendered.
 */
const windowed = computed<boolean>(
  () =>
    !isWorkbook.value
    && (shape.value === 'text' || shape.value === 'table')
    && props.artifact.size_bytes > TEXT_PREVIEW_LIMIT,
)

const mode = computed<PreviewMode>(() => (oversized.value ? 'unsupported' : shape.value))

const contentUrl = computed<string>(() => buildContentUrl(props.artifact.path, true))

/*
 * A windowed sheet names its columns in the first row of the file rather than in the first row of whatever
 * stretch is on screen, so the heading is read once out of the beginning and kept while the reader moves.
 */
const headerRow = computed<string[]>(() =>
  windowed.value ? windowHeading.value : (sheet.value.rows[0] ?? []),
)

/* Only the very first stretch of a file opens with the heading; every later one is rows all the way down. */
const leadsWithHeading = computed<boolean>(() => !windowed.value || windowStart.value === 0)

/* Rows of a sheet are ragged, and a row shorter than the header would otherwise pull the table apart. */
const bodyRows = computed<string[][]>(() =>
  (leadsWithHeading.value ? sheet.value.rows.slice(1) : sheet.value.rows).map((row) => [
    ...row,
    ...Array<string>(Math.max(headerRow.value.length - row.length, 0)).fill(''),
  ]),
)

/** How far into a very large file the stretch on screen sits, as the share of it that stands behind. */
const windowShare = computed<number>(() =>
  props.artifact.size_bytes === 0 ? 0 : Math.round((windowStart.value / props.artifact.size_bytes) * 100),
)

const atFileStart = computed<boolean>(() => windowStart.value <= 0)

const atFileEnd = computed<boolean>(() => windowStart.value + WINDOW_BYTES >= props.artifact.size_bytes)

/** What the controls say about where in the file the reader currently is. */
const windowLabel = computed<string>(
  () => `${formatBytes(windowStart.value)} of ${formatBytes(props.artifact.size_bytes)}`,
)

/** The furthest the stretch on screen can begin, which is a whole stretch back from the end of the file. */
const lastWindowStart = computed<number>(() => Math.max(props.artifact.size_bytes - WINDOW_BYTES, 0))

const tableNote = computed<string>(() => {
  if (windowed.value) {
    return `${bodyRows.value.length} rows, ${windowShare.value}% into the file`
  }

  return sheet.value.truncated
    ? `The first ${TABLE_ROW_LIMIT} rows of a longer file are shown.`
    : `${bodyRows.value.length} rows`
})

const fallbackMessage = computed<string>(() => {
  if (failure.value.length > 0) {
    return failure.value
  }

  return oversized.value ? TOO_LARGE_WORKBOOK : UNSUPPORTED
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
    } else if (windowed.value) {
      await readWindow(read)
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

/**
 * Read the stretch of a very large file that is about to be shown, and the heading it is read under.
 *
 * The heading comes out of the beginning of the file rather than out of the stretch, because a sheet names
 * its columns once and a reader ten gigabytes into it still needs to know which column is which. It is read
 * on the first stretch and kept from then on.
 *
 * :param read: Which read this is, so the answer of an abandoned one is thrown away rather than shown.
 */
const readWindow = async (read: number): Promise<void> => {
  const size = props.artifact.size_bytes
  const start = Math.min(Math.max(windowStart.value, 0), Math.max(size - 1, 0))
  const end = Math.min(start + WINDOW_BYTES - 1, size - 1)

  if (mode.value === 'table' && windowHeading.value.length === 0) {
    const opening = await readArtifactWindow(props.artifact.path, 0, Math.min(HEADING_BYTES, size) - 1)
    if (read !== currentRead) {
      return
    }
    windowHeading.value = parseDelimited(opening, delimiterOf(suffix.value, opening), 1).rows[0] ?? []
  }

  const raw = await readArtifactWindow(props.artifact.path, start, end)
  if (read !== currentRead) {
    return
  }

  /* A stretch taken by byte offset opens and closes mid row, and half a row is worse than one row fewer. */
  const body = wholeLines(raw, start === 0, end >= size - 1).text
  text.value = body

  if (mode.value === 'table') {
    sheet.value = parseDelimited(body, delimiterOf(suffix.value, body), TABLE_ROW_LIMIT + 1)
    showRaw.value = sheet.value.rows.length === 0
  }
}

/**
 * Move the stretch on screen through a very large file.
 *
 * :param to: Where the new stretch begins, in bytes, which is clamped to the file.
 */
const moveWindow = (to: number): void => {
  windowStart.value = Math.min(Math.max(to, 0), lastWindowStart.value)
  void load()
}

/** Move one stretch back or on, whichever way the reader pressed. */
const stepWindow = (direction: number): void => {
  moveWindow(windowStart.value + direction * WINDOW_BYTES)
}

/* Picking a different file starts a different reading, so nothing of the last one is carried into it. */
watch(
  () => props.artifact,
  () => {
    windowStart.value = 0
    windowHeading.value = []
    void load()
  },
  { immediate: true },
)
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

/* The controls of a file read a stretch at a time, which only appear for a file too large to be read whole. */
.file-preview__window {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-inline: 0.25rem;
}

.file-preview__slider {
  flex: 1 1 auto;
  min-inline-size: 6rem;
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
