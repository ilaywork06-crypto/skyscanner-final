<template>
  <div class="sky-page">
    <AppHeader />

    <div
      v-if="event !== null"
      class="sky-page__content event-page"
    >
      <div class="event-page__heading">
        <span class="event-page__badge">EVENT</span>
        <div class="event-page__heading-row">
          <v-btn
            icon="mdi-chevron-left"
            variant="text"
            aria-label="Back to the inventory"
            @click="goBack"
          />
          <h1 class="event-page__title">
            {{ event.name }}
          </h1>
          <v-menu location="bottom start">
            <template #activator="{ props: activator }">
              <v-btn
                v-bind="activator"
                variant="outlined"
                rounded="pill"
                append-icon="mdi-menu-down"
              >
                {{ humanizeKey(event.status) }}
              </v-btn>
            </template>
            <v-list density="compact">
              <v-list-item
                v-for="option in STATUS_OPTIONS"
                :key="option"
                :title="humanizeKey(option)"
                @click="onStatusChange(option)"
              />
            </v-list>
          </v-menu>
          <v-spacer />
          <v-btn
            icon="mdi-history"
            variant="tonal"
            aria-label="Show the edit history of this event"
            @click="historyDialog = true"
          />
          <!-- The bell follows the same flag as the rest of the feature, so it appears again with it. -->
          <v-btn
            v-if="SUBSCRIPTIONS_ENABLED"
            icon="mdi-bell-outline"
            color="secondary"
            aria-label="Follow this event"
            @click="subscribeDialog = true"
          />
          <v-btn
            icon="mdi-delete"
            color="error"
            aria-label="Delete this event"
            @click="deleteDialog = true"
          />
          <v-btn
            icon="mdi-pencil"
            color="primary"
            aria-label="Edit this event"
            @click="editDialog = true"
          />
        </div>
      </div>

      <section class="event-page__facts">
        <div class="event-page__fact">
          <span class="event-page__fact-label">ID</span>
          <span class="event-page__fact-value">{{ event.event_id }}</span>
        </div>
        <div
          v-if="event.reference_id.length > 0"
          class="event-page__fact"
        >
          <span class="event-page__fact-label">REFERENCE ID</span>
          <span class="event-page__fact-value">{{ event.reference_id }}</span>
        </div>
        <div class="event-page__fact">
          <span class="event-page__fact-label">TYPE</span>
          <span class="event-page__fact-value">{{ typeNames }}</span>
        </div>
        <div class="event-page__fact">
          <span class="event-page__fact-label">DATE</span>
          <span class="event-page__fact-value">
            <v-icon
              size="x-small"
              icon="mdi-calendar-blank-outline"
            />
            {{ formatDate(event.event_date) }}
          </span>
        </div>
        <div class="event-page__fact">
          <span class="event-page__fact-label">CREATED AT</span>
          <span class="event-page__fact-value">{{ formatDateTime(event.created_at) }}</span>
        </div>
        <div class="event-page__fact">
          <span class="event-page__fact-label">UPDATED AT</span>
          <span class="event-page__fact-value">{{ formatDateTime(event.updated_at) }}</span>
        </div>
        <div
          v-if="event.experiment_result !== null"
          class="event-page__fact"
        >
          <span class="event-page__fact-label">RESULT</span>
          <SkyChip
            :label="humanizeKey(event.experiment_result)"
            :token="experimentResultToken(event.experiment_result)"
          />
        </div>
        <div class="event-page__fact">
          <span class="event-page__fact-label">INDUSTRY</span>
          <SkyChip
            :label="event.industry"
            :token="industryChipToken"
          />
        </div>
        <!-- An event may have run on several platforms, so every one of them is named rather than the first. -->
        <div
          v-if="event.platforms.length > 0"
          class="event-page__fact"
        >
          <span class="event-page__fact-label">PLATFORM</span>
          <span class="event-page__fact-chips">
            <SkyChip
              v-for="platform in event.platforms"
              :key="platform"
              :label="platform"
              token="chip-platform"
            />
          </span>
        </div>
      </section>

      <section class="event-page__information">
        <span class="event-page__fact-label">INFORMATION</span>
        <!--
          The information of an event is free text. The breaks somebody typed into it are part of what they
          wrote, so the paragraph is laid out to keep them rather than to run them all into one line.
        -->
        <p
          v-if="event.notes.trim().length > 0"
          class="event-page__notes"
        >
          {{ event.notes }}
        </p>
        <p
          v-else
          class="event-page__notes event-page__notes--empty"
        >
          No information was added yet.
        </p>
      </section>

      <section class="event-page__files">
        <div class="event-page__files-heading">
          <h2 class="event-page__section-title">
            Event Files
          </h2>
          <v-btn
            variant="text"
            size="small"
            prepend-icon="mdi-folder-zip-outline"
            :loading="archiving"
            @click="onDownloadArchive"
          >
            DOWNLOAD ALL
          </v-btn>
        </div>
        <div class="event-page__files-body">
          <aside class="event-page__file-tree">
            <EventFileTree
              :additional-files="event.additional_files"
              :entities="event.objects"
              :active-id="selectedArtifact?.id ?? null"
              @open="onPreview"
              @download="onDownload"
            />
          </aside>
          <!--
            Picking a file shows it here rather than handing it to the browser, which is what the shared
            preview is for: it decides per file whether that means a picture, a frame, a sheet or a text.
          -->
          <div class="event-page__preview">
            <template v-if="selectedArtifact !== null">
              <v-btn
                class="event-page__preview-download"
                icon="mdi-download"
                variant="text"
                aria-label="Download the selected file"
                @click="onDownload(selectedArtifact)"
              />
              <FilePreview
                class="event-page__preview-file"
                :artifact="selectedArtifact"
                @download="onDownload"
              />
            </template>
            <span
              v-else
              class="event-page__preview-empty"
            >Pick a file on the left to preview it.</span>
          </div>
        </div>
      </section>

      <section class="event-page__entities">
        <div class="event-page__tabs">
          <v-btn
            v-for="group in entityGroups"
            :key="group.key"
            class="event-page__tab"
            :class="{ 'event-page__tab--active': activeTab === group.key }"
            variant="text"
            @click="activeTab = group.key"
          >
            {{ group.name }}
          </v-btn>
          <v-spacer />
          <v-btn
            variant="text"
            prepend-icon="mdi-plus"
            @click="openAddEntity"
          >
            Add entity
          </v-btn>
        </div>

        <EntityTable
          :rows="activeRows"
          :columns="entityColumns"
          :industries="industries"
          :downloading="entityArchiving"
          @open="onPreview"
          @download="onDownload"
          @edit="openEditEntity"
          @download-entities="onDownloadEntities"
        />
      </section>

      <EditEventDialog
        v-model="editDialog"
        :event="event"
        @saved="onSaved"
      />
      <!-- The same dialog attaches a new entity and changes one that is already there. -->
      <AddEntityDialog
        v-model="entityDialog"
        :event="event"
        :entity="editedEntity"
        @added="onEntitySaved"
      />
      <SubscribeDialog
        v-if="SUBSCRIPTIONS_ENABLED"
        v-model="subscribeDialog"
        :event-id="event.id"
        :target-label="event.name"
      />
      <RevisionHistoryDialog
        v-model="historyDialog"
        :event-id="event.id"
        :title="`Edit history of ${event.name}`"
      />

      <v-dialog
        v-model="deleteDialog"
        max-width="26rem"
      >
        <v-card>
          <v-card-title>Delete this event?</v-card-title>
          <v-card-text>Every entity and every file reference of the event is removed with it.</v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              variant="text"
              @click="deleteDialog = false"
            >
              Cancel
            </v-btn>
            <v-btn
              color="error"
              @click="onDelete"
            >
              Delete
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </div>

    <div
      v-else
      class="event-page__loading"
    >
      <v-progress-circular
        indeterminate
        color="primary"
        size="40"
      />
    </div>
  </div>
</template>

<script lang="ts">
import type { Artifact, EventStatus } from '@/models/common'
import { SkyChip, formatDate, formatDateTime, humanizeKey } from '@skyscanner/sky-ui'
import type { EntityResponse } from '@/models/entity'
import type { EventDetail } from '@/models/event'
import type { GeneratedColumn, GridRow } from '@/models/grid'

interface EntityGroup {
  key: string
  name: string
  rows: GridRow[]
}
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AddEntityDialog from '@/components/AddEntityDialog.vue'
import AppHeader from '@/components/AppHeader.vue'
import EditEventDialog from '@/components/EditEventDialog.vue'
import EntityTable from '@/components/EntityTable.vue'
import EventFileTree from '@/components/EventFileTree.vue'
import FilePreview from '@/components/FilePreview.vue'
import RevisionHistoryDialog from '@/components/RevisionHistoryDialog.vue'
import SubscribeDialog from '@/components/SubscribeDialog.vue'
import { useSnackbar } from '@/composables/useSnackbar'
import { useIndustries } from '@/composables/useIndustries'
import { SUBSCRIPTIONS_ENABLED } from '@/features'
import { deleteEvent, readEvent, updateEvent } from '@/requests/events'
import { readEntityColumns } from '@/requests/grid'
import { downloadArtifact, downloadEntityArchive, toArchiveSources } from '@/requests/storage'
import { downloadEventFiles } from '@/requests/templates'
import { downloadBlob } from '@/utils/download'
import { experimentResultToken, industryToken } from '@/utils/colors'
import { entityToRow } from '@/utils/rows'

const STATUS_OPTIONS: EventStatus[] = ['draft', 'raw', 'parsed', 'partial', 'failed', 'archived']

const route = useRoute('/events/[id]')
const router = useRouter()
const { industries } = useIndustries()
const { notify, reportError } = useSnackbar()

const event = ref<EventDetail | null>(null)
const entityColumns = ref<GeneratedColumn[]>([])
const activeTab = ref<string>('')
const selectedArtifact = ref<Artifact | null>(null)
const editDialog = ref<boolean>(false)
const deleteDialog = ref<boolean>(false)
const entityDialog = ref<boolean>(false)
const subscribeDialog = ref<boolean>(false)
const historyDialog = ref<boolean>(false)
const archiving = ref<boolean>(false)
const entityArchiving = ref<boolean>(false)
const editedEntity = ref<EntityResponse | null>(null)

const eventId = computed<string>(() => route.params.id)

const typeNames = computed<string>(() =>
  event.value === null ? '' : event.value.event_type.map((type) => type.name).join(', '),
)

const industryChipToken = computed<string>(() =>
  event.value === null ? 'chip-industry-violet' : industryToken(event.value.industry, industries.value),
)

const entityGroups = computed<EntityGroup[]>(() => {
  if (event.value === null) {
    return []
  }

  const groups = new Map<string, EntityGroup>()
  event.value.objects.forEach((entity) => {
    const key = entity.object_type.name
    const group = groups.get(key) ?? { key, name: key, rows: [] }
    group.rows.push(entityToRow(entity))
    groups.set(key, group)
  })

  return [...groups.values()]
})

const activeRows = computed<GridRow[]>(
  () => entityGroups.value.find((group) => group.key === activeTab.value)?.rows ?? [],
)

const reload = async (): Promise<void> => {
  try {
    const loaded = await readEvent(eventId.value)
    event.value = loaded
    entityColumns.value = (await readEntityColumns(loaded.industry, null)).columns
    if (activeTab.value.length === 0 || !entityGroups.value.some((group) => group.key === activeTab.value)) {
      activeTab.value = entityGroups.value[0]?.key ?? ''
    }
  } catch (error) {
    reportError(error)
  }
}

const goBack = () => {
  void router.push('/events')
}

/**
 * Show a file in the preview pane. Opening a file and downloading it are separate actions, so picking one
 * here never puts a copy of it on the disk of the user.
 */
const onPreview = (artifact: Artifact) => {
  selectedArtifact.value = artifact
}

const onDownload = (artifact: Artifact) => {
  downloadArtifact(artifact)
}

/**
 * Download every file of this event as one archive, laid out in the same folders the tree shows.
 */
const onDownloadArchive = async (): Promise<void> => {
  const current = event.value
  if (current === null) {
    return
  }

  archiving.value = true
  try {
    const archive = await downloadEventFiles({
      search: null,
      industry: current.industry,
      parse_state: 'all',
      filters: [],
      sort: [],
      page: 1,
      page_size: 1,
      columns: [],
      event_ids: [current.id],
    })
    downloadBlob(archive.blob, archive.name)
    notify('The archive was downloaded', 'success')
  } catch (error) {
    reportError(error)
  } finally {
    archiving.value = false
  }
}

const openAddEntity = () => {
  editedEntity.value = null
  entityDialog.value = true
}

/**
 * Open the entity dialog on one of the entities of this event, which switches it into its edit mode.
 */
const openEditEntity = (entityId: string) => {
  const entity = event.value?.objects.find((candidate) => candidate.id === entityId)
  if (entity === undefined) {
    return
  }

  editedEntity.value = entity
  entityDialog.value = true
}

const onEntitySaved = async (): Promise<void> => {
  editedEntity.value = null
  await reload()
}

/**
 * Download the files of the picked entities as one archive named after this event.
 */
const onDownloadEntities = async (entityIds: string[]): Promise<void> => {
  const current = event.value
  if (current === null || entityArchiving.value) {
    return
  }

  const picked = current.objects.filter((entity) => entityIds.includes(entity.id))
  if (picked.length === 0) {
    return
  }

  entityArchiving.value = true
  try {
    await downloadEntityArchive(String(current.event_id), current.name, toArchiveSources(picked))
    notify('The archive was downloaded', 'success')
  } catch (error) {
    reportError(error)
  } finally {
    entityArchiving.value = false
  }
}

/*
 * Changing the status from the header is a one click action, so it writes its own reason into the history
 * rather than stopping to ask for one - the reason is exactly what the click said.
 */
const onStatusChange = async (status: EventStatus): Promise<void> => {
  const current = event.value
  if (current === null || current.status === status) {
    return
  }

  try {
    event.value = await updateEvent(current.id, {
      status,
      reason: `Status changed from ${humanizeKey(current.status)} to ${humanizeKey(status)}`,
    })
    notify('The status was updated', 'success')
  } catch (error) {
    reportError(error)
  }
}

const onSaved = (updated: EventDetail) => {
  event.value = updated
}

const onDelete = async (): Promise<void> => {
  if (event.value === null) {
    return
  }

  try {
    await deleteEvent(event.value.id)
    notify('The event was removed', 'success')
    void router.push('/events')
  } catch (error) {
    reportError(error)
  } finally {
    deleteDialog.value = false
  }
}

onMounted(reload)
watch(eventId, reload)
</script>

<style scoped>
.event-page {
  gap: 1.25rem;
}

.event-page__heading {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding-block-start: 1rem;
}

.event-page__badge {
  align-self: flex-start;
  margin-inline-start: 2.5rem;
  background-color: rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 0.375rem;
  padding-inline: 0.625rem;
  padding-block: 0.125rem;
  font-size: 0.6875rem;
  letter-spacing: 0.08em;
}

.event-page__heading-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.event-page__title {
  font-size: 2rem;
  font-weight: 600;
}

.event-page__facts {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2rem;
  background-color: rgb(var(--v-theme-surface));
  border-radius: 0.5rem;
  padding: 1rem 1.5rem;
}

.event-page__fact {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-inline-size: 0;
}

/* Several platforms wrap inside the one fact rather than each of them becoming a fact of its own. */
.event-page__fact-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.event-page__fact-label {
  font-size: 0.6875rem;
  letter-spacing: 0.08em;
  opacity: 0.7;
}

.event-page__fact-value {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.9375rem;
}

.event-page__information {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  background-color: rgb(var(--v-theme-surface));
  border-radius: 0.5rem;
  padding: 1rem 1.5rem;
}

/*
 * Every break the user typed is kept: the information of an event is written in paragraphs often enough that
 * collapsing it the way a browser collapses ordinary text would read it back as one run on line.
 */
.event-page__notes {
  font-size: 0.9375rem;
  white-space: pre-wrap;
}

.event-page__notes--empty {
  opacity: 0.7;
}

.event-page__files-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.event-page__section-title {
  font-size: 1rem;
  font-weight: 700;
  padding-block-end: 0.5rem;
}

.event-page__files-body {
  display: grid;
  grid-template-columns: minmax(12rem, 1fr) minmax(0, 3fr);
  gap: 0.75rem;
  min-block-size: 18rem;
}

/*
 * Both panes scroll inside themselves rather than growing: an event of a hundred files and a sheet of five
 * hundred rows would otherwise push the entities of the event off the bottom of the page.
 */
.event-page__file-tree,
.event-page__preview {
  max-block-size: 32rem;
}

.event-page__file-tree {
  background-color: rgb(var(--v-theme-surface));
  border-radius: 0.5rem;
  padding: 1rem;
  overflow: auto;
}

/*
 * The pane holds whatever the preview decided to render, so it carries the ordinary surface behind it: a
 * sheet and a log are read here as often as a picture is looked at, and neither reads well on a dark ground.
 */
.event-page__preview {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgb(var(--v-theme-surface));
  border-radius: 0.5rem;
  padding: 0.75rem;
  min-block-size: 18rem;
  overflow: hidden;
}

.event-page__preview-download {
  position: absolute;
  inset-block-start: 0.5rem;
  inset-inline-end: 0.5rem;
  z-index: 2;
}

.event-page__preview-file {
  align-self: stretch;
  min-inline-size: 0;
}

/* The toolbar of a sheet ends before the download control above it rather than underneath it. */
.event-page__preview :deep(.file-preview__toolbar) {
  padding-inline-end: 2.5rem;
}

.event-page__preview-empty {
  opacity: 0.7;
}

.event-page__entities {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.event-page__tabs {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}

.event-page__tab {
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-block-end: none;
  border-start-start-radius: 0.5rem;
  border-start-end-radius: 0.5rem;
  background-color: transparent;
  color: inherit;
  padding-inline: 1.5rem;
  padding-block: 0.5rem;
  cursor: pointer;
}

.event-page__tab--active {
  background-color: rgb(var(--v-theme-surface));
  font-weight: 600;
}

.event-page__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 1 auto;
  min-block-size: 60vh;
}

@media (max-width: 60rem) {
  .event-page__files-body {
    grid-template-columns: 1fr;
  }
}
</style>
