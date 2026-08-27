<template>
  <!--
    The handful of questions a reader asks of this table every day - which platform, which result, which
    industry - answered by picking rather than by typing. Everything here is a column whose values are a
    declared vocabulary, so the pills are built out of the table itself and no list of them is written twice:
    declaring a platform on the Types page is what puts it in here.

    Every pick is written into the filter of its own column, which is why it shows up as a chip under the
    toolbar, is lifted from there, and is saved with the view like any filter typed into a header.
  -->
  <div
    v-if="pills.length > 0"
    class="quick-filters"
  >
    <span class="quick-filters__label">
      <v-icon
        size="small"
        icon="mdi-lightning-bolt-outline"
      />
      Quick filters
    </span>

    <v-menu
      v-for="pill in pills"
      :key="pill.colId"
      :close-on-content-click="false"
      location="bottom start"
    >
      <template #activator="{ props: activator }">
        <v-btn
          v-bind="activator"
          class="quick-filters__pill"
          :class="{ 'quick-filters__pill--active': pill.picked.length > 0 }"
          variant="text"
        >
          <span class="quick-filters__pill-label">{{ pill.label }}</span>
          <!-- What the pill is currently narrowing to, so a filtered table says so from the pill itself. -->
          <span
            v-if="pill.picked.length > 0"
            class="quick-filters__pill-value"
          >{{ summaryOf(pill) }}</span>
          <v-icon
            size="small"
            icon="mdi-menu-down"
          />
        </v-btn>
      </template>

      <v-list
        density="compact"
        class="quick-filters__menu"
      >
        <v-list-item
          v-for="option in pill.options"
          :key="option.value"
          class="quick-filters__option"
          @click="toggle(pill, option.value)"
        >
          <template #prepend>
            <v-checkbox-btn
              :model-value="pill.picked.includes(option.value)"
              density="compact"
              @click.stop="toggle(pill, option.value)"
            />
          </template>
          <v-list-item-title>{{ option.label }}</v-list-item-title>
        </v-list-item>

        <template v-if="pill.picked.length > 0">
          <v-divider />
          <v-list-item
            title="Clear"
            prepend-icon="mdi-close"
            @click="emit('update', { colId: pill.colId, values: [] })"
          />
        </template>
      </v-list>
    </v-menu>

    <v-btn
      v-if="anyPicked"
      class="quick-filters__reset"
      variant="text"
      size="small"
      prepend-icon="mdi-filter-remove-outline"
      @click="clearAll"
    >
      CLEAR QUICK FILTERS
    </v-btn>
  </div>
</template>

<script lang="ts">
import type { FilterOption, GeneratedColumn } from '@/models/grid'
import type { FilterCondition } from '@/models/query'

interface Props {
  columns: GeneratedColumn[]
  /** The restrictions the table currently carries, which is where the ticks of every pill are read from. */
  filters: FilterCondition[]
}

/** One pill of the row: a column, the vocabulary behind it and whichever of its values are picked. */
interface QuickFilterPill {
  colId: string
  label: string
  options: FilterOption[]
  picked: string[]
}

interface QuickFilterChoice {
  colId: string
  values: string[]
}

interface Emits {
  (event: 'update', choice: QuickFilterChoice): void
}

/** Past this many picked values the pill counts them rather than naming them all. */
const MAX_NAMED_VALUES = 2

export type { QuickFilterChoice }
</script>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

/**
 * Read the values one column is currently narrowed to, taken from the conditions of the table itself.
 *
 * The pills hold no state of their own: they are a view of the filters the table is running, so a value
 * lifted from the chips under the toolbar unticks itself here, and a saved view opens with its pills filled.
 */
const pickedOf = (colId: string): string[] =>
  props.filters
    .filter((condition) => condition.key === colId && condition.operator === 'in')
    .flatMap((condition) => condition.values.map((value) => String(value)))

const pills = computed<QuickFilterPill[]>(() =>
  props.columns
    .filter((column) => column.quickFilter && column.filterOptions.length > 0)
    .map((column) => ({
      colId: column.colId,
      label: column.headerName,
      options: column.filterOptions,
      picked: pickedOf(column.colId),
    })),
)

const anyPicked = computed<boolean>(() => pills.value.some((pill) => pill.picked.length > 0))

/**
 * Say what a pill is narrowing to, naming the values while there are few enough of them to read.
 */
const summaryOf = (pill: QuickFilterPill): string => {
  const labels = pill.picked.map(
    (value) => pill.options.find((option) => option.value === value)?.label ?? value,
  )
  if (labels.length <= MAX_NAMED_VALUES) {
    return labels.join(', ')
  }

  return `${labels.length} picked`
}

const toggle = (pill: QuickFilterPill, value: string) => {
  const values = pill.picked.includes(value)
    ? pill.picked.filter((candidate) => candidate !== value)
    : [...pill.picked, value]

  emit('update', { colId: pill.colId, values })
}

const clearAll = () => {
  pills.value
    .filter((pill) => pill.picked.length > 0)
    .forEach((pill) => emit('update', { colId: pill.colId, values: [] }))
}
</script>

<style scoped>
.quick-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  padding-block-end: 0.5rem;
}

.quick-filters__label {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  letter-spacing: 0.02em;
  opacity: 0.7;
  padding-inline-end: 0.125rem;
}

/* The pills stand in the same language as the ones in the toolbar above them, one size quieter. */
.quick-filters__pill.v-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: 0.0625rem solid rgb(var(--v-theme-control-border));
  border-radius: 999rem;
  background-color: rgb(var(--v-theme-control-surface));
  color: rgb(var(--v-theme-on-surface));
  padding-inline: 0.625rem;
  font-size: 0.75rem;
  font-weight: 400;
  letter-spacing: normal;
  text-transform: none;
  block-size: auto;
  min-block-size: 1.875rem;
  min-inline-size: 0;
  white-space: nowrap;
}

.quick-filters__pill.v-btn:hover {
  background-color: rgb(var(--v-theme-control-surface-hover));
}

.quick-filters__pill.v-btn :deep(.v-btn__content) {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  min-inline-size: 0;
}

/* A pill that is narrowing the table is marked as one rather than only naming what it narrowed to. */
.quick-filters__pill--active.v-btn {
  border-color: rgba(var(--v-theme-primary), 0.55);
  background-color: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
}

.quick-filters__pill-label {
  opacity: 0.85;
}

/* A pill narrowed to a value with a long name is cut short rather than pushing the row onto a second line. */
.quick-filters__pill-value {
  font-weight: 600;
  max-inline-size: 9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-filters__menu {
  min-inline-size: 12rem;
  max-block-size: 20rem;
  overflow-y: auto;
}

/* The tick and the label of an option are one control, so the row carries no gap between them. */
.quick-filters__option :deep(.v-list-item__prepend) {
  inline-size: auto;
  margin-inline-end: 0.25rem;
}

.quick-filters__reset.v-btn {
  letter-spacing: normal;
  font-size: 0.6875rem;
}
</style>
