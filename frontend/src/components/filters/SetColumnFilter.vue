<template>
  <!--
    The filter of a column whose values are a vocabulary somebody declared. Nothing is typed here: the list is
    the vocabulary, so narrowing the table to two platforms is two ticks rather than remembering that Rig A is
    stored as rig_a. The search box above the list is for a vocabulary long enough to scroll, not for the query.
  -->
  <div class="set-filter">
    <!-- A vocabulary of five values is read at a glance; only a longer one is worth a box to search it. -->
    <div
      v-if="searchable"
      class="set-filter__search"
    >
      <v-text-field
        v-model="term"
        :placeholder="`Search ${headerName}`"
        prepend-inner-icon="mdi-magnify"
        density="compact"
        variant="outlined"
        hide-details
        autofocus
        clearable
      />
    </div>

    <div class="set-filter__actions">
      <v-btn
        class="set-filter__action"
        variant="text"
        size="small"
        :disabled="matching.length === 0"
        @click="selectAllMatching"
      >
        SELECT ALL
      </v-btn>
      <v-btn
        class="set-filter__action"
        variant="text"
        size="small"
        :disabled="picked.length === 0"
        @click="clear"
      >
        CLEAR
      </v-btn>
    </div>

    <div class="set-filter__list">
      <label
        v-for="option in matching"
        :key="option.value"
        class="set-filter__option"
      >
        <v-checkbox-btn
          :model-value="picked.includes(option.value)"
          density="compact"
          @update:model-value="toggle(option.value)"
        />
        <span class="set-filter__label">{{ option.label }}</span>
      </label>

      <p
        v-if="matching.length === 0"
        class="set-filter__empty"
      >
        No value matches "{{ term }}".
      </p>
    </div>
  </div>
</template>

<script lang="ts">
import type { IFilterParams } from 'ag-grid-community'
import { SET_FILTER_TYPE, type FilterOption } from '@skyscanner/ag-grid-ts'

/** What the parser hands every filter: the vocabulary of the column and the name it is known by. */
interface SetFilterParams extends IFilterParams {
  options?: FilterOption[]
  headerName?: string
}

interface Props {
  params: SetFilterParams
}

/**
 * The shape this filter keeps inside the filter model of the grid.
 *
 * It is the same shape the grid library reads a list of values out of and writes one back into, so a saved
 * view that narrowed a column to three platforms reopens with those three ticked.
 */
interface SetFilterModel {
  filterType: string
  values: string[]
}

</script>

<script setup lang="ts">
import { computed, ref } from 'vue'

/** Past this many values the list is one a reader searches rather than one they simply read. */
const SEARCHABLE_FROM = 8

const props = defineProps<Props>()

/** The values currently ticked, which is the whole of the state this filter holds. */
const picked = ref<string[]>([])
const term = ref<string>('')

const options = computed<FilterOption[]>(() => props.params.options ?? [])

const headerName = computed<string>(() => props.params.headerName ?? 'values')

const searchable = computed<boolean>(() => options.value.length >= SEARCHABLE_FROM)

const matching = computed<FilterOption[]>(() => {
  const needle = (term.value ?? '').trim().toLowerCase()
  if (needle.length === 0) {
    return options.value
  }

  return options.value.filter(
    (option) =>
      option.label.toLowerCase().includes(needle) || option.value.toLowerCase().includes(needle),
  )
})

const apply = () => {
  props.params.filterChangedCallback()
}

const toggle = (value: string) => {
  picked.value = picked.value.includes(value)
    ? picked.value.filter((candidate) => candidate !== value)
    : [...picked.value, value]
  apply()
}

/**
 * Tick everything the search currently shows, which is every value when nothing was searched for.
 */
const selectAllMatching = () => {
  const shown = matching.value.map((option) => option.value)
  picked.value = [...new Set([...picked.value, ...shown])]
  apply()
}

const clear = () => {
  picked.value = []
  apply()
}

/**
 * Say whether this filter is narrowing the table at all, which is what puts the mark on its header.
 */
const isFilterActive = (): boolean => picked.value.length > 0

/**
 * Let every row through.
 *
 * The rows of this table are read one page at a time and the backend has already answered the whole query,
 * so the block the grid holds is the answer rather than something still to be sifted. Deciding again here
 * would filter that answer a second time - against a flattened row whose list valued cells the grid reads
 * as text - and quietly drop rows the service had every reason to return.
 */
const doesFilterPass = (): boolean => true

const getModel = (): SetFilterModel | null =>
  picked.value.length === 0 ? null : { filterType: SET_FILTER_TYPE, values: [...picked.value] }

/**
 * Take the ticks of a saved view, of a quick filter or of a cleared filter model.
 */
const setModel = (model: SetFilterModel | null) => {
  picked.value = Array.isArray(model?.values) ? model.values.map((value) => String(value)) : []
}

/* The grid calls these on the component instance, which is what a filter of AG Grid is made of. */
defineExpose({ isFilterActive, doesFilterPass, getModel, setModel })
</script>

<!--
  The styles are deliberately not scoped. The grid mounts a filter of its own outside the tree of the
  application, into a popup it owns, and a component mounted that way never receives the attribute a scoped
  style is written against - which is why every component the grid renders in this system styles itself
  through its own namespaced class names instead.
-->
<style>
.set-filter {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.5rem;
  min-inline-size: 15rem;
  max-inline-size: 20rem;
  background-color: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
}

.set-filter__search {
  padding-block-end: 0.25rem;
}

.set-filter__actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding-block-end: 0.125rem;
}

.set-filter__action.v-btn {
  letter-spacing: normal;
  font-size: 0.6875rem;
  padding-inline: 0.5rem;
  min-inline-size: 0;
}

/* A vocabulary of thirty platforms scrolls inside the menu rather than growing it past the window. */
.set-filter__list {
  display: flex;
  flex-direction: column;
  max-block-size: 15rem;
  overflow-y: auto;
}

.set-filter__option {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  border-radius: 0.25rem;
  padding-inline-end: 0.5rem;
  cursor: pointer;
  min-inline-size: 0;
}

.set-filter__option:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

/*
 * A selection control of the library grows to fill the line it is on, which put every label underneath its
 * own tick rather than beside it. It is furniture of a fixed size here and the label takes the rest.
 */
.set-filter__option .v-selection-control {
  flex: 0 0 auto;
  min-block-size: 1.75rem;
}

.set-filter__label {
  flex: 1 1 auto;
  font-size: 0.8125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.set-filter__empty {
  padding: 0.5rem;
  font-size: 0.8125rem;
  opacity: 0.7;
}
</style>
