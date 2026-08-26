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
          <!-- The arrow points the way the panel moves: down to open it, up to fold it away again. -->
          <v-btn
            v-if="column.colId === 'expander'"
            :icon="isExpanded(String(entity.id)) ? 'mdi-chevron-up' : 'mdi-chevron-down'"
            size="x-small"
            variant="text"
            :aria-label="
              isExpanded(String(entity.id))
                ? 'Hide the additional attributes of the entity'
                : 'Show the additional attributes of the entity'
            "
            :aria-expanded="isExpanded(String(entity.id))"
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

      <!--
        Everything the entity says about itself beyond the columns above: the fields its schema declares and
        the additional data written under keys nobody declared. The undeclared ones used to be stored and
        then shown nowhere at all, so they are built into columns of their own out of the value's own type.
      -->
      <div
        v-if="isExpanded(String(entity.id))"
        class="entity-table__detail"
      >
        <AttributesTable
          :columns="detailColumns(entity)"
          :row="entity"
          :industries="industries"
          title="Additional Entity Attributes"
          empty-text="This entity carries nothing beyond the columns above."
          @open="emit('open', $event)"
          @download="emit('download', $event)"
        />
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

import AttributesTable from '@/components/AttributesTable.vue'
import DynamicCell from '@/components/DynamicCell.vue'
import { attributeColumns } from '@/utils/grid-columns'
import { readText } from '@/utils/rows'

const props = withDefaults(defineProps<Props>(), { industries: () => [], downloading: false })
const emit = defineEmits<Emits>()

const expanded = ref<string[]>([])
const selected = ref<string[]>([])

const visibleColumns = computed<GeneratedColumn[]>(() =>
  props.columns.filter((column) => !column.hide && !column.dynamic),
)

/**
 * Build the columns of an expanded row: the declared ones first, then whatever else the entity holds.
 *
 * The event panel lays its own attributes out with exactly the same rule, so the two read alike and neither
 * of them owns a private idea of what an undeclared value looks like.
 */
const detailColumns = (entity: GridRow): GeneratedColumn[] => attributeColumns(props.columns, entity)

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

.entity-table__head {
  display: flex;
  align-items: center;
  background-color: rgb(var(--v-theme-table-header));
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}

.entity-table__row {
  display: flex;
  align-items: center;
  border-block-start: 0.0625rem solid rgb(var(--v-theme-app-border));
  background-color: rgb(var(--v-theme-table-row));
}

/* The panel is inset under the row it belongs to, and the table inside it draws its own frame. */
.entity-table__detail {
  margin-inline: 2rem 1rem;
  margin-block: 0.5rem 0.75rem;
  min-inline-size: 0;
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
