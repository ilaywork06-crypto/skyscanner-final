<template>
  <div class="toolbar">
    <div class="toolbar__search">
      <v-text-field
        :model-value="search"
        class="toolbar__field"
        :placeholder="t('register.searchPlaceholder')"
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
            :aria-label="t('register.chooseColumns')"
            :title="t('register.chooseColumns')"
          />
        </template>
        <v-card class="toolbar__columns">
          <v-card-title class="toolbar__columns-title">
            {{ t('register.columns') }}
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

      <!--
        Restoring a bundle is offered whatever the table currently holds - an empty register is exactly the
        one a bundle is most often restored into.
      -->
      <v-btn
        variant="tonal"
        prepend-icon="mdi-upload-outline"
        @click="emit('import')"
      >
        {{ t('register.import') }}
      </v-btn>

      <!--
        The two exports answer two different questions, so they are two entries rather than one button with
        a format hidden inside it: one is the view somebody is looking at, written for a person to read, and
        the other is the register itself, written to be read back in.
      -->
      <v-menu location="bottom end">
        <template #activator="{ props: activator }">
          <v-btn
            v-bind="activator"
            variant="tonal"
            prepend-icon="mdi-download-outline"
            :loading="exporting"
          >
            {{ t('register.export') }}
          </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item
            :title="t('register.exportSheet')"
            prepend-icon="mdi-file-table-outline"
            :disabled="total === 0"
            @click="emit('export')"
          />
          <v-list-item
            :title="t('register.exportBundle')"
            prepend-icon="mdi-package-variant-closed"
            @click="emit('export-bundle')"
          />
        </v-list>
      </v-menu>

      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="emit('create')"
      >
        {{ t('register.newAssumption') }}
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
  /** Whether a bundle is currently being gathered, which is one reading per row the register has not read. */
  exporting?: boolean
}

interface Emits {
  (event: 'update:search', term: string): void
  (event: 'toggle-column', colId: string, visible: boolean): void
  (event: 'create'): void
  (event: 'export'): void
  (event: 'export-bundle'): void
  (event: 'import'): void
}

/** The column that holds the chevron has no heading and nothing to choose, so it is never offered. */
const STRUCTURAL_COLUMNS: string[] = ['expand']
</script>

<script setup lang="ts">
import { useLanguage } from '@truth-platform/core-ui'
import { computed } from 'vue'

const props = withDefaults(defineProps<Props>(), { exporting: false })
const emit = defineEmits<Emits>()

const { t } = useLanguage()

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
