<template>
  <div class="entity-table">
    <!--
      Downloading the files of several entities is one archive rather than one download per file, so the bar
      only appears once something is ticked and says how much it is about to pack.
    -->
    <div
      v-if="selected.length > 0"
      class="entity-table__bar"
    >
      <span class="entity-table__bar-text">{{ selected.length }} selected</span>
      <v-btn
        size="small"
        variant="text"
        prepend-icon="mdi-folder-zip-outline"
        :loading="downloading"
        @click="emit('download-entities', [...selected])"
      >
        DOWNLOAD FILES
      </v-btn>
      <v-btn
        size="small"
        variant="text"
        @click="selected = []"
      >
        CLEAR
      </v-btn>
    </div>

    <div class="entity-table__head">
      <div class="entity-table__cell entity-table__cell--head entity-table__cell--tick">
        <v-checkbox-btn
          :model-value="allSelected"
          :indeterminate="someSelected"
          density="compact"
          aria-label="Select every entity"
          @update:model-value="toggleAll"
        />
      </div>
      <div
        v-for="column in visibleColumns"
        :key="column.colId"
        class="entity-table__cell entity-table__cell--head"
        :style="cellStyle(column)"
      >
        {{ column.headerName }}
      </div>
      <div class="entity-table__cell entity-table__cell--head entity-table__cell--actions">
        ACTIONS
      </div>
    </div>

    <div
      v-for="entity in rows"
      :key="String(entity.id)"
      class="entity-table__group"
    >
      <div class="entity-table__row">
        <div class="entity-table__cell entity-table__cell--tick">
          <v-checkbox-btn
            :model-value="isSelected(String(entity.id))"
            density="compact"
            :aria-label="`Select ${nameOf(entity)}`"
            @update:model-value="toggleSelected(String(entity.id))"
          />
        </div>
        <div
          v-for="column in visibleColumns"
          :key="column.colId"
          class="entity-table__cell"
          :style="cellStyle(column)"
        >
          <v-btn
            v-if="column.colId === 'expander'"
            :icon="isExpanded(String(entity.id)) ? 'mdi-chevron-down' : 'mdi-chevron-up'"
            size="x-small"
            variant="text"
            aria-label="Toggle the dynamic values of the entity"
            @click="toggle(String(entity.id))"
          />
          <DynamicCell
            v-else
            :column="column"
            :row="entity"
            :industries="industries"
            @open="emit('open', $event)"
            @download="emit('download', $event)"
          />
        </div>
        <div class="entity-table__cell entity-table__cell--actions">
          <v-btn
            icon="mdi-download"
            size="x-small"
            variant="text"
            :disabled="downloading"
            :aria-label="`Download the files of ${nameOf(entity)}`"
            @click="emit('download-entities', [String(entity.id)])"
          />
          <v-btn
            icon="mdi-pencil"
            size="x-small"
            variant="text"
            :aria-label="`Edit ${nameOf(entity)}`"
            @click="emit('edit', String(entity.id))"
          />
        </div>
      </div>

      <div
        v-if="isExpanded(String(entity.id))"
        class="entity-table__detail"
      >
        <div class="entity-table__detail-head">
          <div
            v-for="column in dynamicColumns"
            :key="column.colId"
            class="entity-table__cell entity-table__cell--head"
          >
            {{ column.headerName }}
          </div>
          <div
            v-if="dynamicColumns.length === 0"
            class="entity-table__cell entity-table__cell--head"
          >
            DETAILS
          </div>
        </div>
        <div class="entity-table__detail-row">
          <div
            v-for="column in dynamicColumns"
            :key="column.colId"
            class="entity-table__cell"
          >
            <DynamicCell
              :column="column"
              :row="entity"
              :industries="industries"
              @open="emit('open', $event)"
              @download="emit('download', $event)"
            />
          </div>
          <div
            v-if="dynamicColumns.length === 0"
            class="entity-table__cell"
          >
            {{ EMPTY_PLACEHOLDER }}
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="rows.length === 0"
      class="entity-table__empty"
    >
      No entities were attached to this event yet.
    </div>
  </div>
</template>

<script lang="ts">
import type { Artifact } from '@/models/common'
import { EMPTY_PLACEHOLDER } from '@skyscanner/sky-ui'
import type { GeneratedColumn, GridRow } from '@/models/grid'
import type { Industry } from '@/models/industry'

interface Props {
  rows: GridRow[]
  columns: GeneratedColumn[]
  industries?: Industry[]
  /** Whether an archive is being packed already, which the download controls wait for. */
  downloading?: boolean
}

interface Emits {
  (event: 'open', artifact: Artifact): void
  (event: 'download', artifact: Artifact): void
  (event: 'edit', entityId: string): void
  (event: 'download-entities', entityIds: string[]): void
}
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import DynamicCell from '@/components/DynamicCell.vue'
import { readText } from '@/utils/rows'

const props = withDefaults(defineProps<Props>(), { industries: () => [], downloading: false })
const emit = defineEmits<Emits>()

const expanded = ref<string[]>([])
const selected = ref<string[]>([])

const visibleColumns = computed<GeneratedColumn[]>(() =>
  props.columns.filter((column) => !column.hide && !column.dynamic),
)

const dynamicColumns = computed<GeneratedColumn[]>(() => props.columns.filter((column) => column.dynamic))

const cellStyle = (column: GeneratedColumn): Record<string, string> => ({
  flex: column.flex === null ? '0 0 auto' : `${column.flex} 1 0`,
  minInlineSize: column.width === null ? '6rem' : `${column.width / 16}rem`,
})

const allSelected = computed<boolean>(() => props.rows.length > 0 && selected.value.length === props.rows.length)

const someSelected = computed<boolean>(() => selected.value.length > 0 && !allSelected.value)

const isExpanded = (entityId: string): boolean => expanded.value.includes(entityId)

const toggle = (entityId: string) => {
  expanded.value = isExpanded(entityId)
    ? expanded.value.filter((candidate) => candidate !== entityId)
    : [...expanded.value, entityId]
}

const isSelected = (entityId: string): boolean => selected.value.includes(entityId)

const toggleSelected = (entityId: string) => {
  selected.value = isSelected(entityId)
    ? selected.value.filter((candidate) => candidate !== entityId)
    : [...selected.value, entityId]
}

const toggleAll = (value: boolean | null) => {
  selected.value = value === true ? props.rows.map((entity) => String(entity.id)) : []
}

/** What an entity is called, which is what the controls beside it name themselves after. */
const nameOf = (entity: GridRow): string => readText(entity, 'name')

/*
 * A tick belongs to the entity it was put on, and the rows change under it whenever the group is reloaded or
 * another tab is picked, so a selection is kept only for as long as the entities behind it are still shown.
 */
watch(
  () => props.rows,
  (rows) => {
    const present = new Set(rows.map((entity) => String(entity.id)))
    selected.value = selected.value.filter((entityId) => present.has(entityId))
  },
)
</script>

<style scoped>
.entity-table {
  display: flex;
  flex-direction: column;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
}

.entity-table__head,
.entity-table__detail-head {
  display: flex;
  align-items: center;
  background-color: rgb(var(--v-theme-table-header));
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}

.entity-table__row,
.entity-table__detail-row {
  display: flex;
  align-items: center;
  border-block-start: 0.0625rem solid rgb(var(--v-theme-app-border));
  background-color: rgb(var(--v-theme-table-row));
}

.entity-table__detail {
  margin-inline-start: 2rem;
  margin-block: 0.5rem;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
  overflow: hidden;
}

.entity-table__bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: rgba(var(--v-theme-primary), 0.12);
  padding-inline: 1rem;
  padding-block: 0.25rem;
}

.entity-table__bar-text {
  font-size: 0.8125rem;
  font-weight: 600;
}

.entity-table__cell {
  padding-inline: 1rem;
  padding-block: 0.75rem;
  min-inline-size: 0;
  overflow: hidden;
}

.entity-table__cell--head {
  padding-block: 0.625rem;
}

/* The tick and the controls are fixed furniture of every row, so they never take part in the flexing columns. */
.entity-table__cell--tick,
.entity-table__cell--actions {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  padding-inline: 0.5rem;
  overflow: visible;
}

.entity-table__cell--actions {
  gap: 0.25rem;
  margin-inline-start: auto;
}

.entity-table__empty {
  padding: 1rem;
  opacity: 0.7;
  background-color: rgb(var(--v-theme-table-row));
}
</style>
