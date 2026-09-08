<template>
  <div class="sky-page">
    <AppHeader />

    <div class="sky-page__content">
      <div class="platforms__heading">
        <h1 class="platforms__title">
          Platforms
        </h1>
        <v-spacer />
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="openCreate"
        >
          Declare a platform
        </v-btn>
      </div>
      <p class="platforms__subtitle">
        A platform is the rig, the aircraft or the bench an event was produced on. Declare one here and the
        create wizard offers it to every industry it belongs to.
      </p>

      <p
        v-if="!loading && platforms.length === 0"
        class="platforms__empty"
      >
        No platform was declared yet. An event names the platforms it ran on, so declare the first one here.
      </p>

      <div class="platforms__grid">
        <article
          v-for="platform in platforms"
          :key="platform.id"
          class="platforms__card"
        >
          <div class="platforms__card-head">
            <UiChip
              :label="platform.name"
              token="chip-platform"
            />
            <code class="platforms__key">{{ platform.key }}</code>
          </div>
          <p class="platforms__description">
            {{ platform.description.length > 0 ? platform.description : 'No description yet.' }}
          </p>
          <span class="platforms__industries">
            {{
              platform.industries.length > 0
                ? `Industries: ${platform.industries.join(', ')}`
                : 'Offered to every industry'
            }}
          </span>
          <div class="platforms__card-actions">
            <v-btn
              size="x-small"
              variant="text"
              prepend-icon="mdi-pencil-outline"
              :aria-label="`Edit ${platform.name}`"
              @click="openEdit(platform)"
            >
              EDIT
            </v-btn>
            <v-btn
              size="x-small"
              variant="text"
              color="error"
              prepend-icon="mdi-delete-outline"
              :aria-label="`Remove ${platform.name}`"
              @click="askRemove(platform)"
            >
              REMOVE
            </v-btn>
          </div>
        </article>
      </div>

      <div
        v-if="loading"
        class="platforms__loading"
      >
        <v-progress-circular
          indeterminate
          color="primary"
          size="32"
        />
      </div>
    </div>

    <v-dialog
      v-model="dialog"
      max-width="32rem"
    >
      <v-card>
        <v-card-title>{{ edited === null ? 'Declare a platform' : `Edit ${edited.name}` }}</v-card-title>
        <v-card-text class="platforms__dialog">
          <v-text-field
            v-model="draftName"
            label="Name"
            @update:model-value="onNameChange"
          />

          <!--
            The key is what every event that ran on this platform actually stores, so changing one is a write
            across the inventory rather than an edit to this row. It is therefore held behind a deliberate
            act, and what the change would cost is read from the service and shown before it is made.
          -->
          <v-text-field
            v-model="draftKey"
            label="Key"
            :disabled="edited !== null && !renaming"
            :hint="keyHint"
            persistent-hint
          >
            <template
              v-if="edited !== null && !renaming"
              #append-inner
            >
              <v-btn
                size="x-small"
                variant="text"
                @click="startRename"
              >
                CHANGE
              </v-btn>
            </template>
          </v-text-field>

          <v-alert
            v-if="renamePreview !== null"
            type="warning"
            variant="tonal"
            density="compact"
          >
            {{ renameSummary }}
          </v-alert>

          <v-text-field
            v-model="draftDescription"
            label="Description"
          />
          <v-select
            v-model="draftIndustries"
            :items="industryOptions"
            item-title="title"
            item-value="value"
            label="Industries"
            hint="Leave empty to offer the platform to every industry."
            persistent-hint
            multiple
            chips
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="dialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :disabled="!canSave"
            :loading="saving"
            @click="onSave"
          >
            {{ edited === null ? 'Declare' : 'Save' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog
      v-model="removeDialog"
      max-width="28rem"
    >
      <v-card>
        <v-card-title>Remove this platform?</v-card-title>
        <v-card-text>
          It stops being offered by the create wizard. The events that already named it keep naming it, and
          nothing about them changes.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="removeDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="saving"
            @click="onRemove"
          >
            Remove
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import type { Platform } from '@/models/platform'
import type { RenameResult } from '@/requests/schema'

interface IndustryOption {
  title: string
  value: string
}

const DEFAULT_ORDER = 100
</script>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import { UiChip, slugify, useSnackbar } from '@truth-platform/core-ui'
import { useIndustries } from '@/composables/useIndustries'
import {
  createPlatform,
  deletePlatform,
  listPlatforms,
  previewPlatformRename,
  updatePlatform,
} from '@/requests/schema'

const { industries } = useIndustries()
const { notify, reportError } = useSnackbar()

const platforms = ref<Platform[]>([])
const loading = ref<boolean>(false)
const saving = ref<boolean>(false)

const dialog = ref<boolean>(false)
const removeDialog = ref<boolean>(false)
const edited = ref<Platform | null>(null)
const draftName = ref<string>('')
const draftKey = ref<string>('')
const draftDescription = ref<string>('')
const draftIndustries = ref<string[]>([])

/* Whether the key of a stored platform is being changed, which is a deliberate act rather than a typo. */
const renaming = ref<boolean>(false)
const renamePreview = ref<RenameResult | null>(null)

const industryOptions = computed<IndustryOption[]>(() =>
  industries.value.map((industry) => ({ title: industry.name, value: industry.key })),
)

const canSave = computed<boolean>(() => draftName.value.trim().length > 0 && draftKey.value.trim().length > 0)

const keyHint = computed<string>(() => {
  if (edited.value === null) {
    return 'How the platform is stored on every event that names it.'
  }

  return renaming.value
    ? 'Every event that ran on this platform is rewritten to the new key when you save.'
    : 'Stored on every event that names this platform, so changing it rewrites those events.'
})

/** What the service said a rename would move, put into a sentence. */
const renameSummary = computed<string>(() => {
  const preview = renamePreview.value
  if (preview === null) {
    return ''
  }

  const counted = Object.entries(preview.affected).filter(([, amount]) => amount > 0)
  if (counted.length === 0) {
    return `Nothing else names ${preview.previous_key}, so this rename only changes the declaration.`
  }

  const parts = counted.map(([collection, amount]) => `${amount} ${collection}`)

  return `Saving rewrites ${parts.join(', ')} from ${preview.previous_key} to ${preview.key}.`
})

/**
 * Keep the key following the name while a new platform is being written, and leave a stored one alone.
 */
const onNameChange = (value: string) => {
  if (edited.value === null) {
    draftKey.value = slugify(value)
  }
}

const load = async (): Promise<void> => {
  loading.value = true
  try {
    platforms.value = await listPlatforms()
  } catch (error) {
    reportError(error)
  } finally {
    loading.value = false
  }
}

const reset = () => {
  renaming.value = false
  renamePreview.value = null
}

const openCreate = () => {
  edited.value = null
  draftName.value = ''
  draftKey.value = ''
  draftDescription.value = ''
  draftIndustries.value = []
  reset()
  dialog.value = true
}

const openEdit = (platform: Platform) => {
  edited.value = platform
  draftName.value = platform.name
  draftKey.value = platform.key
  draftDescription.value = platform.description
  draftIndustries.value = [...platform.industries]
  reset()
  dialog.value = true
}

/**
 * Unlock the key and ask the service what changing it would cost before anybody commits to it.
 */
const startRename = async (): Promise<void> => {
  renaming.value = true
  const platform = edited.value
  if (platform === null) {
    return
  }

  try {
    renamePreview.value = await previewPlatformRename(platform.id, platform.key)
  } catch (error) {
    reportError(error)
  }
}

const onSave = async (): Promise<void> => {
  saving.value = true
  try {
    const platform = edited.value
    if (platform === null) {
      await createPlatform({
        key: draftKey.value.trim(),
        name: draftName.value.trim(),
        description: draftDescription.value.trim(),
        industries: [...draftIndustries.value],
        order: DEFAULT_ORDER,
      })
      notify('The platform was declared')
    } else {
      const changed = draftKey.value.trim() !== platform.key
      const result = await updatePlatform(platform.id, {
        key: changed ? draftKey.value.trim() : undefined,
        name: draftName.value.trim(),
        description: draftDescription.value.trim(),
        industries: [...draftIndustries.value],
      })
      notify(changed ? `The platform is now stored as ${result.key}` : 'The platform was changed')
    }
    dialog.value = false
    await load()
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}

const askRemove = (platform: Platform) => {
  edited.value = platform
  removeDialog.value = true
}

const onRemove = async (): Promise<void> => {
  const platform = edited.value
  if (platform === null) {
    return
  }

  saving.value = true
  try {
    await deletePlatform(platform.id)
    notify('The platform was removed')
    removeDialog.value = false
    await load()
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.platforms__heading {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.platforms__title {
  font-size: 1.5rem;
  font-weight: 700;
}

.platforms__subtitle {
  font-size: 0.875rem;
  opacity: 0.75;
  max-inline-size: 46rem;
}

.platforms__empty {
  font-size: 0.875rem;
  opacity: 0.7;
  padding-block: 1rem;
}

.platforms__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: 1rem;
  margin-block-start: 1rem;
}

.platforms__card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background-color: rgb(var(--v-theme-surface));
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.75rem;
  padding: 1rem;
}

.platforms__card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.platforms__key {
  font-size: 0.75rem;
  opacity: 0.7;
}

.platforms__description {
  font-size: 0.875rem;
}

.platforms__industries {
  font-size: 0.75rem;
  opacity: 0.7;
}

.platforms__card-actions {
  display: flex;
  gap: 0.25rem;
  margin-block-start: auto;
  padding-block-start: 0.5rem;
}

.platforms__dialog {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.platforms__loading {
  display: flex;
  justify-content: center;
  padding-block: 2rem;
}
</style>
