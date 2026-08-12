<template>
  <!--
    The values of an entity - what it is called, where it came from, what was noted about it - are searched
    by the same box the events above are, so a cell inside an expanded row paints its matches exactly as the
    cells of the table around it do. On the event page nothing was searched, and every branch renders the
    plain value it always did.
  -->
  <SkyChip
    v-if="kind === 'chip'"
    :label="text"
    :token="chipToken"
  >
    <HighlightedText
      v-if="isMatch(text)"
      :text="text"
      :term="search"
    />
    <template v-else>
      {{ text }}
    </template>
  </SkyChip>
  <!-- A status is stored as a key and read out as a label, so the pen is given both spellings of it. -->
  <SkyChip
    v-else-if="kind === 'status'"
    :label="statusLabel"
    :token="statusChipToken"
  >
    <HighlightedText
      v-if="isStatusMatch"
      :text="statusLabel"
      :term="search"
      :stored="text"
    />
    <template v-else>
      {{ statusLabel }}
    </template>
  </SkyChip>
  <!-- A cell of one of the plain tables grows with what it holds, so the files may say where they came from. -->
  <FileList
    v-else-if="kind === 'files'"
    :files="artifacts"
    show-upload
    @open="emit('open', $event)"
    @download="emit('download', $event)"
  />
  <span
    v-else-if="kind === 'date'"
    class="dynamic-cell__text"
  >{{ dateLabel }}</span>
  <span
    v-else-if="isMatch(text)"
    class="dynamic-cell__text"
    :title="text"
  >
    <HighlightedText
      :text="text"
      :term="search"
    />
  </span>
  <span
    v-else
    class="dynamic-cell__text"
    :title="text"
  >{{ text.length > 0 ? text : EMPTY_PLACEHOLDER }}</span>
</template>

<script lang="ts">
import type { Artifact } from '@/models/common'
import { EMPTY_PLACEHOLDER, SkyChip, formatDate, formatDateTime, humanizeKey } from '@skyscanner/sky-ui'
import type { GeneratedColumn, GridRow } from '@/models/grid'
import type { Industry } from '@/models/industry'

interface Props {
  column: GeneratedColumn
  row: GridRow
  industries?: Industry[]
}

interface Emits {
  (event: 'open', artifact: Artifact): void
  (event: 'download', artifact: Artifact): void
}

type CellKind = 'chip' | 'status' | 'files' | 'date' | 'text'
</script>

<script setup lang="ts">
import { computed } from 'vue'

import FileList from '@/components/FileList.vue'
import HighlightedText from '@/components/HighlightedText.vue'
import { paletteToken, industryToken } from '@/utils/colors'
import { useSearchTerm } from '@/utils/grid-context'
import { matchesTerm } from '@/utils/highlight'
import { readArtifacts, readPath, readText } from '@/utils/rows'

const props = withDefaults(defineProps<Props>(), { industries: () => [] })
const emit = defineEmits<Emits>()

/*
 * Whatever the surface around this cell was searched for, which is nothing at all on the event page: the
 * same cell renders there and has no table above it that anybody searched.
 */
const search = useSearchTerm()

const kind = computed<CellKind>(() => {
  switch (props.column.cellRenderer) {
    case 'ChipCellRenderer':
      return 'chip'
    case 'StatusCellRenderer':
      return 'status'
    case 'FilesCellRenderer':
      return 'files'
    case 'DateCellRenderer':
      return 'date'
    default:
      return 'text'
  }
})

const text = computed<string>(() => readText(props.row, props.column.field))

/* The same column definition drives the grid and this cell, so a moment carries its clock in both. */
const dateLabel = computed<string>(() =>
  props.column.cellRendererParams.withTime === true ? formatDateTime(text.value) : formatDate(text.value),
)
const artifacts = computed<Artifact[]>(() => readArtifacts(readPath(props.row, props.column.field)))

const chipToken = computed<string>(() => {
  const palette = props.column.cellRendererParams.palette

  if (palette === 'platform') {
    return 'chip-platform'
  }

  if (palette === 'industry') {
    return industryToken(text.value, props.industries)
  }

  return 'chip-industry-violet'
})

const statusLabel = computed<string>(() => (text.value.length > 0 ? humanizeKey(text.value) : ''))

const statusChipToken = computed<string>(() => {
  const palette = props.column.cellRendererParams.palette

  return paletteToken(typeof palette === 'string' ? palette : undefined, text.value)
})

const isMatch = (value: string): boolean => matchesTerm(value, search.value)

const isStatusMatch = computed<boolean>(() => isMatch(statusLabel.value) || isMatch(text.value))
</script>

<style scoped>
.dynamic-cell__text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
