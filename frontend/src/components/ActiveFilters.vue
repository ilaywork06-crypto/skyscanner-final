<template>
  <!--
    A filtered table that does not say so reads as a table with missing rows. Every restriction currently
    narrowing the view is therefore named here, and every one of them can be lifted from the same place.
  -->
  <div
    v-if="chips.length > 0"
    class="active-filters"
  >
    <span class="active-filters__label">Filtered by</span>

    <button
      v-for="chip in chips"
      :key="chip.id"
      type="button"
      class="active-filters__chip"
      :aria-label="`Remove the filter ${chip.label}`"
      @click="emit('remove', chip)"
    >
      <span class="active-filters__chip-key">{{ chip.field }}:</span>
      <span class="active-filters__chip-value">{{ chip.value }}</span>
      <v-icon
        size="x-small"
        icon="mdi-close"
      />
    </button>

    <v-btn
      class="active-filters__clear"
      variant="text"
      size="small"
      prepend-icon="mdi-filter-remove-outline"
      @click="emit('clear')"
    >
      CLEAR ALL FILTERS
    </v-btn>
  </div>
</template>

<script lang="ts">
import type { ParseState } from '@/models/common'
import { humanizeKey } from '@skyscanner/sky-ui'
import type { GeneratedColumn } from '@/models/grid'
import type { FilterCondition } from '@/models/query'

/** What a single chip stands for, which decides what lifting it has to undo. */
type FilterKind = 'search' | 'parse' | 'column'

interface FilterChip {
  id: string
  kind: FilterKind
  field: string
  value: string
  label: string
  colId: string
}

interface Props {
  search: string
  parseState: ParseState
  filters: FilterCondition[]
  columns: GeneratedColumn[]
}

interface Emits {
  (event: 'remove', chip: FilterChip): void
  (event: 'clear'): void
}

const PARSE_LABELS: Record<ParseState, string> = {
  all: 'All',
  parsed: 'Parsed',
  not_parsed: 'Not parsed',
}

const OPERATOR_LABELS: Record<string, string> = {
  equals: 'is',
  not_equals: 'is not',
  contains: 'contains',
  not_contains: 'does not contain',
  starts_with: 'starts with',
  ends_with: 'ends with',
  greater_than: 'is above',
  greater_or_equal: 'is at least',
  less_than: 'is below',
  less_or_equal: 'is at most',
  in: 'is one of',
  not_in: 'is none of',
  between: 'is between',
  is_empty: 'is empty',
  is_not_empty: 'is filled',
}

export type { FilterChip }
</script>

<script setup lang="ts">
import { computed } from 'vue'


const props = defineProps<Props>()
const emit = defineEmits<Emits>()

/**
 * Read the header a column carries, so a chip names the field the way the table does.
 */
const headerOf = (key: string): string => {
  const column = props.columns.find((candidate) => candidate.colId === key)

  return column === undefined || column.headerName.length === 0 ? humanizeKey(key) : column.headerName
}

/**
 * Render the value of one condition, joining the list operators back into readable text.
 */
const valueOf = (condition: FilterCondition): string => {
  const operator = OPERATOR_LABELS[condition.operator] ?? condition.operator
  if (condition.operator === 'is_empty' || condition.operator === 'is_not_empty') {
    return operator
  }

  const rendered =
    condition.values.length > 0
      ? condition.values.map((value) => String(value)).join(', ')
      : String(condition.value ?? '')

  return condition.operator === 'equals' ? rendered : `${operator} ${rendered}`
}

const chips = computed<FilterChip[]>(() => {
  const collected: FilterChip[] = []

  if (props.search.length > 0) {
    collected.push({
      id: 'search',
      kind: 'search',
      field: 'Search',
      value: props.search,
      label: `Search: ${props.search}`,
      colId: '',
    })
  }

  if (props.parseState !== 'all') {
    const value = PARSE_LABELS[props.parseState]
    collected.push({
      id: 'parse',
      kind: 'parse',
      field: 'Show',
      value,
      label: `Show: ${value}`,
      colId: '',
    })
  }

  props.filters.forEach((condition) => {
    const field = headerOf(condition.key)
    const value = valueOf(condition)
    collected.push({
      id: `column:${condition.key}`,
      kind: 'column',
      field,
      value,
      label: `${field}: ${value}`,
      colId: condition.key,
    })
  })

  return collected
})
</script>

<style scoped>
.active-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding-block-end: 0.75rem;
}

.active-filters__label {
  font-size: 0.8125rem;
  opacity: 0.7;
}

.active-filters__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  border: 0.0625rem solid rgba(var(--v-theme-primary), 0.45);
  border-radius: 999rem;
  background-color: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-on-surface));
  padding-inline: 0.75rem;
  padding-block: 0.25rem;
  font-size: 0.8125rem;
  cursor: pointer;
  max-inline-size: 22rem;
}

.active-filters__chip:hover {
  background-color: rgba(var(--v-theme-primary), 0.2);
}

.active-filters__chip-key {
  opacity: 0.75;
  white-space: nowrap;
}

.active-filters__chip-value {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.active-filters__clear.v-btn {
  letter-spacing: normal;
}
</style>
