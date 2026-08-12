<template>
  <div class="sky-page">
    <AppHeader />

    <div class="sky-page__content">
      <div class="industries__heading">
        <h1 class="industries__title">
          Industries
        </h1>
        <v-spacer />
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="openCreate"
        >
          Declare an industry
        </v-btn>
      </div>
      <p class="industries__subtitle">
        Pick an industry to see only the events and the schema that belong to it.
      </p>

      <p
        v-if="!loading && industries.length === 0"
        class="industries__empty"
      >
        No industry was declared yet. An event always belongs to one, so declare the first industry here.
      </p>

      <div class="industries__grid">
        <RouterLink
          v-for="industry in industries"
          :key="industry.key"
          :to="`/industries/${industry.key}`"
          class="industries__card"
        >
          <div class="industries__card-head">
            <SkyChip
              :label="industry.name"
              :token="tokenFor(industry.key)"
            />
            <span class="industries__count">{{ industry.event_count }} events</span>
          </div>
          <p class="industries__description">
            {{ industry.description.length > 0 ? industry.description : 'No description yet.' }}
          </p>
          <span class="industries__origins">
            {{
              industry.entity_origins.length > 0
                ? `Origins: ${industry.entity_origins.join(', ')}`
                : 'No entity origins declared yet'
            }}
          </span>
          <div class="industries__card-actions">
            <span class="industries__link">Open the industry view →</span>
            <v-btn
              size="x-small"
              variant="text"
              prepend-icon="mdi-pencil-outline"
              :aria-label="`Edit ${industry.name}`"
              @click.stop.prevent="openEdit(industry)"
            >
              EDIT
            </v-btn>
          </div>
        </RouterLink>
      </div>

      <div
        v-if="loading"
        class="industries__loading"
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
        <v-card-title>{{ editedKey === null ? 'Declare an industry' : `Edit ${draftName}` }}</v-card-title>
        <v-card-text class="industries__dialog">
          <v-text-field
            v-model="draftName"
            label="Name"
            @update:model-value="onNameChange"
          />
          <v-text-field
            v-model="draftKey"
            label="Key"
            :disabled="editedKey !== null"
          />
          <v-text-field
            v-model="draftDescription"
            label="Description"
          />
          <v-select
            v-model="draftColor"
            :items="COLOR_ITEMS"
            item-title="title"
            item-value="value"
            label="Colour"
          />
          <!--
            The vocabulary an entity of this industry may name as its origin. Leaving it empty keeps origin
            an open text field, so an industry nobody has configured yet is never blocked.
          -->
          <v-combobox
            v-model="draftOrigins"
            label="Entity origins"
            hint="The values an entity may name as its origin. Leave empty to accept any text."
            persistent-hint
            multiple
            chips
            closable-chips
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
            {{ editedKey === null ? 'Declare' : 'Save' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import type { Industry } from '@/models/industry'
import { SkyChip, slugify } from '@skyscanner/sky-ui'

interface ColorItem {
  title: string
  value: string
}

const COLOR_ITEMS: ColorItem[] = [
  { title: 'Amber', value: 'chip-industry-amber' },
  { title: 'Blue', value: 'chip-industry-blue' },
  { title: 'Violet', value: 'chip-industry-violet' },
  { title: 'Rose', value: 'chip-industry-rose' },
  { title: 'Coral', value: 'chip-industry-coral' },
]
</script>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { useIndustries } from '@/composables/useIndustries'
import { useSnackbar } from '@/composables/useSnackbar'
import { createIndustry, updateIndustry } from '@/requests/schema'
import { industryToken } from '@/utils/colors'

const { industries, loading, load } = useIndustries()
const { notify, reportError } = useSnackbar()

const dialog = ref<boolean>(false)
const saving = ref<boolean>(false)
const editedKey = ref<string | null>(null)
const draftName = ref<string>('')
const draftKey = ref<string>('')
const draftDescription = ref<string>('')
const draftColor = ref<string>(COLOR_ITEMS[0].value)
const draftOrigins = ref<string[]>([])

const canSave = computed<boolean>(() => draftName.value.length > 0 && draftKey.value.length > 0)

const tokenFor = (key: string): string => industryToken(key, industries.value)

const onNameChange = (value: string) => {
  if (editedKey.value === null) {
    draftKey.value = slugify(value)
  }
}

const reset = () => {
  editedKey.value = null
  draftName.value = ''
  draftKey.value = ''
  draftDescription.value = ''
  draftColor.value = COLOR_ITEMS[0].value
  draftOrigins.value = []
}

const openCreate = () => {
  reset()
  dialog.value = true
}

const openEdit = (industry: Industry) => {
  editedKey.value = industry.key
  draftName.value = industry.name
  draftKey.value = industry.key
  draftDescription.value = industry.description
  draftColor.value = industry.color
  draftOrigins.value = [...industry.entity_origins]
  dialog.value = true
}

const onSave = async (): Promise<void> => {
  saving.value = true
  try {
    const origins = draftOrigins.value.map((origin) => origin.trim()).filter((origin) => origin.length > 0)
    if (editedKey.value === null) {
      await createIndustry({
        key: draftKey.value,
        name: draftName.value,
        description: draftDescription.value,
        color: draftColor.value,
        entity_origins: origins,
      })
      notify('The industry was declared', 'success')
    } else {
      await updateIndustry(editedKey.value, {
        name: draftName.value,
        description: draftDescription.value,
        color: draftColor.value,
        entity_origins: origins,
      })
      notify('The industry was updated', 'success')
    }

    dialog.value = false
    reset()
    await load(true)
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void load(true)
})
</script>

<style scoped>
.industries__heading {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-block: 1.5rem 0.25rem;
}

.industries__title {
  font-size: 1.75rem;
  font-weight: 600;
}

.industries__empty {
  opacity: 0.75;
  padding-block-end: 1rem;
}

.industries__dialog {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.industries__subtitle {
  opacity: 0.75;
  padding-block-end: 1.5rem;
}

.industries__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: 1rem;
}

.industries__card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background-color: rgb(var(--v-theme-surface));
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.75rem;
  padding: 1.25rem;
  text-decoration: none;
  color: inherit;
  transition: transform 0.15s ease-in-out, border-color 0.15s ease-in-out;
}

.industries__card:hover {
  transform: translateY(-0.125rem);
  border-color: rgb(var(--v-theme-primary));
}

.industries__card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.industries__count {
  font-size: 0.8125rem;
  opacity: 0.7;
}

.industries__description {
  font-size: 0.875rem;
  opacity: 0.8;
  flex: 1 1 auto;
}

.industries__origins {
  font-size: 0.8125rem;
  opacity: 0.7;
}

.industries__card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.industries__link {
  font-size: 0.875rem;
  color: rgb(var(--v-theme-primary));
}

.industries__loading {
  display: flex;
  justify-content: center;
  padding-block: 2rem;
}
</style>
