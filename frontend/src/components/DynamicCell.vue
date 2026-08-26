<template>
  <!--
    The values of an entity - what it is called, where it came from, what was noted about it - are searched
    by the same box the events above are, so a cell inside an expanded row paints its matches exactly as the
    cells of the table around it do. On the event page nothing was searched, and every branch renders the
    plain value it always did.
  -->
  <!-- A value that is a list of its own is painted chip by chip, which is how the platforms of an event read. -->
  <span
    v-if="kind === 'chips'"
    class="dynamic-cell__chips"
  >
    <SkyChip
      v-for="item in items"
      :key="item"
      :label="item"
      :token="chipToken"
    >
      <HighlightedText
        v-if="isMatch(item)"
        :text="item"
        :term="search"
      />
      <template v-else>
        {{ item }}
      </template>
    </SkyChip>
    <span v-if="items.length === 0">{{ EMPTY_PLACEHOLDER }}</span>
  </span>
  <SkyChip
    v-else-if="kind === 'chip' && text.length > 0"
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
  <!-- A truth value reads as the tick or the cross it is, which is quicker to scan than the word for it. -->
  <span
    v-else-if="kind === 'boolean'"
    class="dynamic-cell__text"
  >
    <v-icon
      v-if="isTrue !== null"
      size="small"
      :icon="isTrue ? 'mdi-check-circle-outline' : 'mdi-close-circle-outline'"
      :color="isTrue ? 'success' : 'app-muted'"
    />
    <template v-else>{{ EMPTY_PLACEHOLDER }}</template>
  </span>
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
  <!-- A point is read as its numbers here; the tables that offer the map are the ones the grid renders. -->
  <span
    v-else-if="kind === 'coordinate'"
    class="dynamic-cell__text"
  >{{ coordinateLabel }}</span>
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
  >
    <HighlightedText
      :text="text"
      :term="search"
    />
  </span>
  <span
    v-else
    class="dynamic-cell__text"
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

type CellKind = 'chip' | 'chips' | 'status' | 'files' | 'date' | 'coordinate' | 'boolean' | 'text'
</script>

<script setup lang="ts">
import { computed } from 'vue'

import FileList from '@/components/FileList.vue'
import HighlightedText from '@/components/HighlightedText.vue'
import { paletteToken, industryToken } from '@/utils/colors'
import { formatCoordinate, toCoordinate } from '@/utils/coordinates'
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
    case 'ChipListCellRenderer':
      return 'chips'
    case 'CoordinateCellRenderer':
      return 'coordinate'
    case 'BooleanCellRenderer':
      return 'boolean'
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

/* The items of a list valued cell, read out of the value itself rather than off the flattened text. */
const items = computed<string[]>(() => {
  const value = readPath(props.row, props.column.field)

  if (Array.isArray(value)) {
    return value.filter((item) => item !== null && item !== '').map((item) => String(item))
  }

  return text.value.length > 0 ? [text.value] : []
})

/* Which of the three a truth valued cell is in: true, false, or never filled in at all. */
const isTrue = computed<boolean | null>(() => {
  const value = readPath(props.row, props.column.field)

  return value === null || value === undefined || value === '' ? null : value === true || value === 'true'
})

const coordinateLabel = computed<string>(() => {
  const point = toCoordinate(readPath(props.row, props.column.field))

  return point === null ? EMPTY_PLACEHOLDER : formatCoordinate(point)
})

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
.dynamic-cell__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  min-inline-size: 0;
}

.dynamic-cell__text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
