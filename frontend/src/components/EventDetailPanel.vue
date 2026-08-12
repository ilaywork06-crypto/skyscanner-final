<template>
  <div class="detail-panel">
    <!--
      Inside an industry tab the fields of that industry are already columns of the table above, so repeating
      them here would only say the same thing twice; the global view is the one that has nowhere else to show them.
    -->
    <section
      v-if="showIndustryFields"
      class="detail-panel__section"
    >
      <h3 class="detail-panel__title">
        INDUSTRY FIELDS
      </h3>
      <div class="detail-panel__table">
        <div class="detail-panel__head">
          <div
            v-for="column in industryColumns"
            :key="column.colId"
            class="detail-panel__cell"
          >
            {{ column.headerName }}
          </div>
        </div>
        <div class="detail-panel__row">
          <div
            v-for="column in industryColumns"
            :key="column.colId"
            class="detail-panel__cell"
          >
            <DynamicCell
              :column="column"
              :row="eventRow"
              :industries="industries"
              @open="emit('open', $event)"
              @download="emit('download', $event)"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- The groups wait for their schemas, so a table never appears for an instant without its columns. -->
    <template v-if="!loading">
      <section
        v-for="group in entityGroups"
        :key="group.key"
        class="detail-panel__section"
      >
        <h3 class="detail-panel__title">
          <v-btn
            class="detail-panel__add"
            icon="mdi-plus-circle"
            size="x-small"
            variant="text"
            color="primary"
            :aria-label="`Add a ${group.name} to this event`"
            @click.stop="openAddEntity(group.key)"
          />
          {{ group.name }}
        </h3>
        <EntityTable
          :rows="group.rows"
          :columns="columnsOf(group.key)"
          :industries="industries"
          :downloading="archiving"
          @open="emit('open', $event)"
          @download="emit('download', $event)"
          @edit="openEditEntity"
          @download-entities="onDownloadEntities"
        />
      </section>
    </template>

    <!--
      An event without a single entity would otherwise expand into nothing at all, so it says so and offers
      the same add action the populated groups carry in their heading.
    -->
    <div
      v-if="!loading && entityGroups.length === 0"
      class="detail-panel__empty"
    >
      <p class="detail-panel__empty-text">
        No entities were added yet. Be the first to add one.
      </p>
      <v-btn
        color="primary"
        variant="tonal"
        prepend-icon="mdi-plus"
        @click.stop="openAddEntity(null)"
      >
        ADD ENTITY
      </v-btn>
    </div>

    <div
      v-if="loading"
      class="detail-panel__loading"
    >
      <v-progress-circular
        indeterminate
        size="24"
      />
    </div>

    <AddEntityDialog
      v-if="eventDetail !== null"
      v-model="entityDialog"
      :event="eventDetail"
      :entity="editedEntity"
      :default-type-key="pendingTypeKey"
      @added="onEntitySaved"
    />
  </div>
</template>

<script lang="ts">
import type { Artifact } from '@/models/common'
import type { EntityResponse } from '@/models/entity'
import type { EventDetail } from '@/models/event'
import type { GeneratedColumn, GridRow } from '@/models/grid'

interface Props {
  eventId: string
  eventRow: GridRow
  industry: string
  entities?: EntityResponse[] | null
  /** The industry the inventory is narrowed to, or nothing while every industry is being shown. */
  industryFilter?: string | null
}

interface Emits {
  (event: 'open', artifact: Artifact): void
  (event: 'download', artifact: Artifact): void
}

interface EntityGroup {
  key: string
  name: string
  rows: GridRow[]
}
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AddEntityDialog from '@/components/AddEntityDialog.vue'
import DynamicCell from '@/components/DynamicCell.vue'
import EntityTable from '@/components/EntityTable.vue'
import { useSnackbar } from '@/composables/useSnackbar'
import { useIndustries } from '@/composables/useIndustries'
import { listEntities } from '@/requests/entities'
import { readEvent } from '@/requests/events'
import { readEntityColumns, readEventColumns } from '@/requests/grid'
import { downloadEntityArchive, toArchiveSources } from '@/requests/storage'
import { entityToRow, readText } from '@/utils/rows'

const props = withDefaults(defineProps<Props>(), { entities: null, industryFilter: null })
const emit = defineEmits<Emits>()

const { industries } = useIndustries()
const { notify, reportError } = useSnackbar()

const loading = ref<boolean>(false)
const loadedEntities = ref<EntityResponse[]>([])
const entityColumns = ref<Record<string, GeneratedColumn[]>>({})
const industryColumns = ref<GeneratedColumn[]>([])
const eventDetail = ref<EventDetail | null>(null)
const entityDialog = ref<boolean>(false)
const pendingTypeKey = ref<string | null>(null)
const editedEntity = ref<EntityResponse | null>(null)
const archiving = ref<boolean>(false)

const effectiveEntities = computed<EntityResponse[]>(() => props.entities ?? loadedEntities.value)

const showIndustryFields = computed<boolean>(
  () => props.industryFilter === null && industryColumns.value.length > 0,
)

/*
 * The entities are grouped by the key of their type rather than by its label, because the key is what
 * selects the schema of the group: a telemetry and a log collection describe themselves with different
 * fields and therefore render different columns.
 */
const entityGroups = computed<EntityGroup[]>(() => {
  const groups = new Map<string, EntityGroup>()
  effectiveEntities.value.forEach((entity) => {
    const key = entity.object_type_key.length > 0 ? entity.object_type_key : entity.object_type.name
    const group = groups.get(key) ?? { key, name: entity.object_type.name, rows: [] }
    group.rows.push(entityToRow(entity))
    groups.set(key, group)
  })

  return [...groups.values()]
})

const columnsOf = (typeKey: string): GeneratedColumn[] => entityColumns.value[typeKey] ?? []

/**
 * Read the column definitions of every entity type present, so each group follows its own declared schema.
 */
const loadEntityColumns = async (): Promise<void> => {
  const keys = entityGroups.value.map((group) => group.key)
  const configurations = await Promise.all(keys.map((key) => readEntityColumns(props.industry, key)))
  const byType: Record<string, GeneratedColumn[]> = {}
  keys.forEach((key, index) => {
    byType[key] = configurations[index]?.columns ?? []
  })
  entityColumns.value = byType
}

const load = async (): Promise<void> => {
  loading.value = true
  try {
    /* Inside an industry tab those fields are columns of the table already, so their schema is not read. */
    if (props.industryFilter === null) {
      const eventConfiguration = await readEventColumns(props.industry)
      industryColumns.value = eventConfiguration.columns.filter(
        (column) => column.dynamic && column.industry === props.industry,
      )
    }
    if (props.entities === null) {
      loadedEntities.value = await listEntities(props.eventId)
    }
    await loadEntityColumns()
  } catch (error) {
    reportError(error)
  } finally {
    loading.value = false
  }
}

/**
 * Open the entity dialog, loading the event it needs on the first use.
 *
 * The same dialog adds and edits: handed an entity it locks the type and asks why the change is being made,
 * and handed nothing it starts an empty one of the type the heading was pressed on.
 */
const openEntityDialog = async (typeKey: string | null, entity: EntityResponse | null): Promise<void> => {
  pendingTypeKey.value = typeKey
  editedEntity.value = entity
  try {
    if (eventDetail.value === null || eventDetail.value.id !== props.eventId) {
      eventDetail.value = await readEvent(props.eventId)
    }
    entityDialog.value = true
  } catch (error) {
    reportError(error)
  }
}

const openAddEntity = async (typeKey: string | null): Promise<void> => {
  await openEntityDialog(typeKey, null)
}

const openEditEntity = async (entityId: string): Promise<void> => {
  const entity = effectiveEntities.value.find((candidate) => candidate.id === entityId)
  if (entity === undefined) {
    return
  }

  await openEntityDialog(null, entity)
}

const onEntitySaved = async (): Promise<void> => {
  entityDialog.value = false
  editedEntity.value = null
  loadedEntities.value = await listEntities(props.eventId)
  await loadEntityColumns()
}

/**
 * Download the files of the picked entities as one archive named after the event they belong to.
 */
const onDownloadEntities = async (entityIds: string[]): Promise<void> => {
  const picked = effectiveEntities.value.filter((entity) => entityIds.includes(entity.id))
  if (picked.length === 0 || archiving.value) {
    return
  }

  archiving.value = true
  try {
    await downloadEntityArchive(
      readText(props.eventRow, 'event_id'),
      readText(props.eventRow, 'name'),
      toArchiveSources(picked),
    )
    notify('The archive was downloaded', 'success')
  } catch (error) {
    reportError(error)
  } finally {
    archiving.value = false
  }
}

onMounted(load)
watch(() => props.eventId, load)
</script>

<style scoped>
.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 1.5rem 1.5rem;
  background-color: rgb(var(--v-theme-table-row-alt));
}

.detail-panel__section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-panel__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9375rem;
  font-weight: 700;
}

.detail-panel__table {
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
  overflow: hidden;
}

.detail-panel__head {
  display: flex;
  background-color: rgb(var(--v-theme-table-header));
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}

.detail-panel__row {
  display: flex;
  background-color: rgb(var(--v-theme-table-row));
  border-block-start: 0.0625rem solid rgb(var(--v-theme-app-border));
}

.detail-panel__cell {
  flex: 1 1 0;
  min-inline-size: 0;
  padding-inline: 1rem;
  padding-block: 0.75rem;
  overflow: hidden;
}

.detail-panel__loading {
  display: flex;
  justify-content: center;
  padding-block: 1rem;
}

.detail-panel__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  border: 0.0625rem dashed rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
  padding-block: 1.5rem;
}

.detail-panel__empty-text {
  opacity: 0.7;
}
</style>
