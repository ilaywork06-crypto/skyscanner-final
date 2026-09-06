<template>
  <div class="toolbar">
    <div class="toolbar__search">
      <v-text-field
        :model-value="search"
        class="toolbar__field"
        placeholder="Search"
        prepend-inner-icon="mdi-magnify"
        clearable
        rounded="pill"
        hide-details
        @update:model-value="emit('update:search', $event ?? '')"
      />

      <!--
        The columns of this table are declared by the schemas rather than written down, so which of them a
        reader wants on screen is a choice that has to be offered rather than decided in advance.
      -->
      <v-menu
        :close-on-content-click="false"
        location="bottom start"
      >
        <template #activator="{ props: activator }">
          <v-btn
            v-bind="activator"
            class="toolbar__icon"
            icon="mdi-sort-variant"
            variant="tonal"
            aria-label="Choose the columns"
            title="Choose the columns"
          />
        </template>
        <v-card class="toolbar__columns">
          <v-card-title class="toolbar__columns-title">
            Columns
          </v-card-title>
          <v-divider />
          <div class="toolbar__columns-list">
            <v-checkbox
              v-for="column in choosableColumns"
              :key="column.colId"
              :model-value="!hiddenColumns.includes(column.colId)"
              :label="column.headerName"
              density="compact"
              hide-details
              @update:model-value="emit('toggle-column', column.colId, $event === true)"
            />
          </div>
        </v-card>
      </v-menu>
    </div>

    <div class="toolbar__actions">
      <slot name="actions" />

      <v-btn
        variant="tonal"
        prepend-icon="mdi-download-outline"
        :disabled="total === 0"
        @click="emit('export')"
      >
        Export
      </v-btn>

      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="emit('create')"
      >
        ASSUMPTION
      </v-btn>
    </div>
  </div>
</template>

<script lang="ts">
import type { GeneratedColumn } from '@truth-platform/core-ui'

interface Props {
  search: string
  columns: GeneratedColumn[]
  hiddenColumns: string[]
  total: number
}

interface Emits {
  (event: 'update:search', term: string): void
  (event: 'toggle-column', colId: string, visible: boolean): void
  (event: 'create'): void
  (event: 'export'): void
}

/** The column that holds the chevron has no heading and nothing to choose, so it is never offered. */
const STRUCTURAL_COLUMNS: string[] = ['expand']
</script>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const choosableColumns = computed<GeneratedColumn[]>(() =>
  props.columns.filter((column) => !STRUCTURAL_COLUMNS.includes(column.colId) && column.headerName.length > 0),
)
</script>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.toolbar__search {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1 1 20rem;
  min-inline-size: 0;
}

.toolbar__field {
  flex: 1 1 auto;
  max-inline-size: 32rem;
}

.toolbar__icon {
  flex: 0 0 auto;
}

.toolbar__columns {
  inline-size: 18rem;
}

.toolbar__columns-title {
  font-size: 0.9375rem;
}

/*
 * A register with many schemas has many columns, so the list is given a ceiling and scrolls inside the menu
 * rather than growing past the bottom of the window.
 */
.toolbar__columns-list {
  display: flex;
  flex-direction: column;
  max-block-size: 24rem;
  overflow-y: auto;
  padding-inline: 0.75rem;
  padding-block: 0.5rem;
}

.toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}
</style>
