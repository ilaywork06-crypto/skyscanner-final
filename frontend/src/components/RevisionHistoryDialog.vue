<template>
  <v-dialog
    :model-value="modelValue"
    max-width="52rem"
    scrollable
    @update:model-value="close"
  >
    <v-card class="history">
      <v-card-title class="history__title">
        <v-icon
          size="small"
          icon="mdi-history"
        />
        <span>{{ heading }}</span>
        <v-spacer />
        <v-btn
          icon="mdi-close"
          variant="text"
          density="comfortable"
          aria-label="Close the history"
          @click="close"
        />
      </v-card-title>

      <v-card-text class="history__body">
        <div
          v-if="loading"
          class="history__centre"
        >
          <v-progress-circular
            indeterminate
            color="primary"
            size="32"
          />
        </div>

        <p
          v-else-if="revisions.length === 0"
          class="history__empty"
        >
          Nothing was edited yet. Every change from here on is recorded with its reason and its author.
        </p>

        <!--
          A version is only meaningful next to the one before it, so each entry carries the values it moved
          rather than a snapshot the reader would have to compare themselves.
        -->
        <ol
          v-else
          class="history__list"
        >
          <li
            v-for="revision in revisions"
            :key="revision.id"
            class="history__entry"
          >
            <div class="history__entry-head">
              <SkyChip
                :label="`v${revision.version}`"
                token="chip-platform"
              />
              <span
                v-if="revision.entity_id !== null"
                class="history__entry-target"
              >{{ revision.entity_name }}</span>
              <span
                v-else
                class="history__entry-target"
              >The event</span>
              <v-spacer />
              <span class="history__entry-meta">
                {{ revision.changed_by }} · {{ formatDateTime(revision.changed_at) }}
              </span>
            </div>

            <p
              v-if="revision.reason.length > 0"
              class="history__reason"
            >
              {{ revision.reason }}
            </p>

            <div class="history__changes">
              <div
                v-for="change in revision.changes"
                :key="change.key"
                class="history__change"
              >
                <span class="history__change-field">{{ change.label }}</span>
                <span class="history__change-before">{{ render(change.before) }}</span>
                <v-icon
                  class="history__change-arrow"
                  size="x-small"
                  icon="mdi-arrow-right"
                />
                <span class="history__change-after">{{ render(change.after) }}</span>
              </div>
            </div>
          </li>
        </ol>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import type { JsonValue } from '@/models/common'
import { EMPTY_PLACEHOLDER, SkyChip, formatDateTime } from '@skyscanner/sky-ui'
import type { Revision } from '@/models/revision'

interface Props {
  modelValue: boolean
  eventId: string
  entityId?: string | null
  title?: string
}

interface Emits {
  (event: 'update:modelValue', value: boolean): void
}
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useSnackbar } from '@/composables/useSnackbar'
import { listEntityRevisions, listEventRevisions } from '@/requests/revisions'

const props = withDefaults(defineProps<Props>(), { entityId: null, title: 'Edit history' })
const emit = defineEmits<Emits>()

const { reportError } = useSnackbar()

const revisions = ref<Revision[]>([])
const loading = ref<boolean>(false)

const heading = computed<string>(() => props.title)

/**
 * Render one recorded value as the text the history shows, spelling out an empty value rather than hiding it.
 */
const render = (value: JsonValue): string => {
  if (value === null || value === undefined || value === '') {
    return EMPTY_PLACEHOLDER
  }

  if (Array.isArray(value)) {
    return value.length === 0 ? EMPTY_PLACEHOLDER : value.map((item) => String(item)).join(', ')
  }

  if (typeof value === 'object') {
    return JSON.stringify(value)
  }

  return String(value)
}

const load = async (): Promise<void> => {
  loading.value = true
  try {
    revisions.value =
      props.entityId === null
        ? await listEventRevisions(props.eventId)
        : await listEntityRevisions(props.eventId, props.entityId)
  } catch (error) {
    reportError(error)
    revisions.value = []
  } finally {
    loading.value = false
  }
}

const close = () => {
  emit('update:modelValue', false)
}

watch(
  () => [props.modelValue, props.eventId, props.entityId] as const,
  ([open]) => {
    if (open) {
      void load()
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.history {
  background-color: rgb(var(--v-theme-surface));
}

.history__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
}

.history__body {
  max-block-size: 65vh;
}

.history__centre {
  display: flex;
  justify-content: center;
  padding-block: 2rem;
}

.history__empty {
  opacity: 0.7;
  padding-block: 1rem;
}

.history__list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  list-style: none;
  padding: 0;
}

.history__entry {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
  padding: 0.875rem 1rem;
}

.history__entry-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.history__entry-target {
  font-weight: 600;
}

.history__entry-meta {
  font-size: 0.8125rem;
  opacity: 0.7;
  white-space: nowrap;
}

.history__reason {
  font-size: 0.875rem;
  font-style: italic;
  opacity: 0.85;
}

.history__changes {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

/*
 * The before and the after of one attribute belong on the same line so the eye can compare them, and each of
 * them scrolls inside its own cell when the value is longer than the row.
 */
.history__change {
  display: grid;
  grid-template-columns: minmax(6rem, 10rem) minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: baseline;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.history__change-field {
  font-weight: 600;
  opacity: 0.8;
}

.history__change-before {
  color: rgb(var(--v-theme-status-negative));
  text-decoration: line-through;
  overflow-wrap: anywhere;
}

.history__change-after {
  color: rgb(var(--v-theme-status-positive));
  overflow-wrap: anywhere;
}

.history__change-arrow {
  opacity: 0.6;
}

@media (max-width: 40rem) {
  .history__change {
    grid-template-columns: 1fr;
  }

  .history__change-arrow {
    display: none;
  }
}
</style>
