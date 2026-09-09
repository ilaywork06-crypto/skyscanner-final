<template>
  <v-dialog
    :model-value="modelValue"
    max-width="40rem"
    scrollable
    @update:model-value="close"
  >
    <v-card>
      <v-card-title>{{ t('import.title') }}</v-card-title>

      <v-card-text class="import">
        <p class="import__note">
          {{ t('import.note') }}
        </p>

        <v-file-input
          :model-value="picked"
          :label="t('import.pick')"
          accept=".zip,application/zip"
          prepend-icon=""
          prepend-inner-icon="mdi-package-variant-closed"
          :disabled="running"
          @update:model-value="onPick"
        />

        <!--
          A bundle carries its files, so it is the one upload of this system that is routinely enormous. The
          size is said before anything is sent, because the difference between a restore that takes a moment
          and one that takes twenty minutes is entirely in this number and nothing else on screen shows it.
        -->
        <p
          v-if="file !== null"
          class="import__muted"
        >
          {{ t('import.size', { size: formatBytes(file.size) }) }}
        </p>

        <v-progress-linear
          v-if="running"
          indeterminate
          color="primary"
          height="4"
          rounded
        />

        <p
          v-if="running"
          class="import__line"
        >
          {{ t('import.running') }}
        </p>

        <template v-if="summary !== null">
          <p class="import__line">
            {{
              t('import.done', {
                events: summary.events_created,
                files: summary.files_restored,
              })
            }}
          </p>
          <p
            v-if="declarationsCreated > 0"
            class="import__muted"
          >
            {{
              t('import.declarations', {
                industries: summary.industries_created,
                types: summary.types_created,
                platforms: summary.platforms_created,
                fields: summary.fields_created,
              })
            }}
          </p>
          <p
            v-if="summary.events_skipped > 0"
            class="import__muted"
          >
            {{ t('import.skipped', { count: summary.events_skipped }) }}
          </p>

          <!-- Every write that failed is named. A restore that half worked is only useful if it says which half. -->
          <div
            v-if="summary.failures.length > 0"
            class="import__failures"
          >
            <p class="import__failures-title">
              {{ t('import.failures') }}
            </p>
            <ul>
              <li
                v-for="failure in summary.failures"
                :key="failure"
              >
                {{ failure }}
              </li>
            </ul>
          </div>
        </template>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          :disabled="running"
          @click="close(false)"
        >
          {{ t('import.close') }}
        </v-btn>
        <v-btn
          color="primary"
          :loading="running"
          :disabled="file === null || running"
          @click="restore"
        >
          {{ t('import.restore') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
interface Props {
  modelValue: boolean
}

interface Emits {
  (event: 'update:modelValue', open: boolean): void
  /** Raised once something was written, so the inventory behind this reads itself again. */
  (event: 'restored'): void
}
</script>

<script setup lang="ts">
import { formatBytes, useLanguage, useSnackbar } from '@truth-platform/core-ui'
import { computed, ref, shallowRef, watch } from 'vue'

import { importEventBundle, type ImportSummary } from '@/requests/templates'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useLanguage()
const { notify, reportError } = useSnackbar()

/*
 * The file and the summary are held shallowly. Neither is ever written into - one is a handle the browser
 * gave us and the other is an answer - and making every field of either reactive buys nothing.
 */
const picked = shallowRef<File | File[] | null>(null)
const file = shallowRef<File | null>(null)
const summary = shallowRef<ImportSummary | null>(null)
const running = ref<boolean>(false)

const declarationsCreated = computed<number>(() => {
  const written = summary.value
  if (written === null) {
    return 0
  }

  return (
    written.industries_created +
    written.types_created +
    written.platforms_created +
    written.fields_created
  )
})

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      picked.value = null
      file.value = null
      summary.value = null
      running.value = false
    }
  },
)

const onPick = (value: File | File[] | null) => {
  picked.value = value
  file.value = Array.isArray(value) ? (value[0] ?? null) : value
  summary.value = null
}

/**
 * Hand the bundle to the service and report exactly what it wrote.
 *
 * The whole archive goes in one request rather than being unpacked here. Unpacking it in the browser would
 * mean the browser deciding what an event is, and then making one request per file and one per event - any
 * of which could be the one that fails halfway, with nothing on either side keeping count of what landed.
 */
const restore = async () => {
  const bundle = file.value
  if (bundle === null) {
    return
  }

  running.value = true
  summary.value = null
  notify(t('import.started'), 'info')

  try {
    const written = await importEventBundle(bundle)
    summary.value = written

    if (written.events_created > 0 || written.files_restored > 0) {
      emit('restored')
    }

    notify(
      t('import.done', { events: written.events_created, files: written.files_restored }),
      written.failures.length === 0 ? 'success' : 'warning',
    )
  } catch (error) {
    reportError(error)
  } finally {
    running.value = false
  }
}

const close = (open: boolean) => {
  if (running.value) {
    return
  }

  emit('update:modelValue', open)
}
</script>

<style scoped>
.import {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.import__note,
.import__muted {
  font-size: 0.8125rem;
  color: rgb(var(--v-theme-app-muted));
  line-height: 1.5;
}

.import__line {
  font-size: 0.875rem;
}

.import__failures {
  border: 0.0625rem solid rgba(var(--v-theme-error), 0.4);
  border-radius: 0.5rem;
  padding: 0.75rem;
  font-size: 0.8125rem;
  max-block-size: 12rem;
  overflow-y: auto;
}

.import__failures-title {
  font-weight: 600;
  padding-block-end: 0.25rem;
}

.import__failures ul {
  padding-inline-start: 1.25rem;
}
</style>
