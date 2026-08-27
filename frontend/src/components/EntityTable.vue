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

    <!--
      The head and the rows scroll together inside one frame. They used to be laid out straight into the
      table, so once the columns of an entity needed more room than the screen had, the ones at the end were
      simply cut off with no way of reaching them - and the entity table lives inside an expanded row of the
      inventory, which is exactly where the room runs out first.
    -->
    <div class="entity-table__scroll">
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
          :class="alignmentOf(column)"
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
            :class="alignmentOf(column)"
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

/** What a width declared in pixels by the backend is divided by to become the rem this table lays out in. */
const ROOT_FONT_SIZE = 16

/** What a column that declares no width at all is given, which no generated column currently is. */
const FIXED_COLUMN_WIDTH = 64

/** What a column that declares no floor falls back to. */
const DEFAULT_COLUMN_WIDTH = 96

/**
 * How much of its declared floor a column is actually held to.
 *
 * The floors are written for the inventory, which has the whole window to spend. This table is read inside an
 * expanded row of that inventory, indented and beside a panel, so holding every column to the full floor is
 * what pushed the last columns of a row off the screen. They are allowed to squeeze this far before the frame
 * gives up and scrolls, which is enough to keep a value readable and far more of them on one screen.
 */
const MIN_WIDTH_SHARE = 0.75
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

/**
 * Lay one column of the table out the way its own definition asks for.
 *
 * A column used to be given the width of its declaration as a floor and nothing else, which is how a table of
 * eleven columns ended up wider than any screen: every one of them held its floor and the sum of the floors
 * was the width of the table. The floor is honoured, the share of the free room is the flex the backend
 * declared, and a column that has run out of room now shrinks and ellipsises rather than pushing its
 * neighbours off the side - past the point where even that is readable, the frame around the table scrolls.
 */
const cellStyle = (column: GeneratedColumn): Record<string, string> => {
  if (column.flex === null) {
    const fixed = `${(column.width ?? FIXED_COLUMN_WIDTH) / ROOT_FONT_SIZE}rem`

    return { flex: `0 0 ${fixed}`, inlineSize: fixed }
  }

  const floor = (column.minWidth ?? DEFAULT_COLUMN_WIDTH) / ROOT_FONT_SIZE

  return { flex: `${column.flex} 1 ${floor}rem`, minInlineSize: `${floor * MIN_WIDTH_SHARE}rem` }
}

/**
 * Say which columns read at the end of themselves rather than at the start.
 *
 * A column of moments the system recorded is right aligned, heading included: a heading standing at the
 * other end of it would leave the table looking as though the values had slipped out from under their name.
 */
const alignmentOf = (column: GeneratedColumn): Record<string, boolean> => ({
  'entity-table__cell--stamp': column.cellRendererParams.stamp === true,
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
  min-inline-size: 0;
}

/*
 * The head and the rows are one scrolling column, so they can never disagree about where a column starts. On
 * a screen wide enough this scrolls nothing at all; on a narrow one it is the difference between reaching the
 * last columns of an entity and never knowing they were there.
 */
.entity-table__scroll {
  display: flex;
  flex-direction: column;
  overflow-x: auto;
  min-inline-size: 0;
  scrollbar-width: thin;
}

.entity-table__head {
  display: flex;
  align-items: stretch;
  background-color: rgb(var(--v-theme-table-header));
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.02em;
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

/*
 * Eleven columns of an entity used to be laid out with a full rem of padding at each side of every one of
 * them, which spent about a fifth of the table on empty space and pushed the columns at the end of the row
 * off the screen. The gap between two columns is what a reader needs to tell them apart and no more, and
 * every pixel it gives back is a pixel the values themselves get to use.
 */
.entity-table__cell {
  display: flex;
  align-items: center;
  padding-inline: 0.5rem;
  padding-block: 0.5rem;
  min-inline-size: 0;
  overflow: hidden;
}

.entity-table__cell > * {
  min-inline-size: 0;
  max-inline-size: 100%;
}

.entity-table__cell--head {
  align-items: center;
  padding-block: 0.5rem;
}

/* Both ends of a right aligned column - its heading and its values - stand at the same edge. */
.entity-table__cell--stamp {
  justify-content: flex-end;
  text-align: end;
}

.entity-table__cell--stamp > * {
  justify-content: flex-end;
}

/* The tick and the controls are fixed furniture of every row, so they never take part in the flexing columns. */
.entity-table__cell--tick,
.entity-table__cell--actions {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  padding-inline: 0.25rem;
  overflow: visible;
}

.entity-table__cell--actions {
  gap: 0.125rem;
  /*
   * The controls hold the end of the row. The margin that used to push them there took every pixel the
   * columns had not spent, which is what let a wide table leave a band of nothing in the middle of it; now
   * the columns spend the room and the controls simply follow them.
   */
  padding-inline-start: 0.5rem;
}

.entity-table__empty {
  padding: 1rem;
  opacity: 0.7;
  background-color: rgb(var(--v-theme-table-row));
}
</style>
