<template>
  <div class="sky-page">
    <AppHeader />

    <div class="sky-page__content types">
      <div class="types__heading">
        <h1 class="types__title">
          Types
        </h1>
        <v-spacer />
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="dialog = true"
        >
          Declare a type
        </v-btn>
      </div>

      <p class="types__hint">
        An event needs at least one event type before it can be uploaded, and an entity needs an entity type
        to be grouped under. A system that was never filled starts without any, so the first ones are declared here.
      </p>

      <div class="types__filters">
        <v-select
          v-model="kind"
          :items="KIND_ITEMS"
          item-title="title"
          item-value="value"
          label="Kind"
        />
        <v-select
          v-model="industry"
          :items="industryItems"
          item-title="title"
          item-value="value"
          label="Industry"
        />
      </div>

      <v-table class="types__table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Key</th>
            <th>Description</th>
            <th>Industry</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="declared in types"
            :key="declared.id"
          >
            <td>{{ declared.name }}</td>
            <td><code>{{ declared.key }}</code></td>
            <td>{{ declared.description.length > 0 ? declared.description : '—' }}</td>
            <td>{{ declared.industry ?? 'shared' }}</td>
            <td class="types__row-actions">
              <v-btn
                icon="mdi-delete-outline"
                size="x-small"
                variant="text"
                :aria-label="`Remove ${declared.name}`"
                @click="onDelete(declared.id)"
              />
            </td>
          </tr>
          <tr v-if="types.length === 0">
            <td
              colspan="5"
              class="types__empty"
            >
              No types were declared yet.
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <v-dialog
      v-model="dialog"
      max-width="34rem"
    >
      <v-card>
        <v-card-title>Declare a type</v-card-title>
        <v-card-text class="types__dialog">
          <v-select
            v-model="draftKind"
            :items="KIND_ITEMS"
            item-title="title"
            item-value="value"
            label="Kind"
          />
          <v-text-field
            v-model="draftName"
            label="Name"
            @update:model-value="onNameChange"
          />
          <v-text-field
            v-model="draftKey"
            label="Key"
          />
          <v-text-field
            v-model="draftDescription"
            label="Description"
          />
          <v-select
            v-model="draftIndustry"
            :items="industryItems"
            item-title="title"
            item-value="value"
            label="Industry"
          />
          <v-text-field
            v-if="draftKind === 'entity'"
            v-model="draftIcon"
            label="Icon"
            placeholder="mdi-chart-line"
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
            Declare
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import type { EntityType } from '@/models/entity'
import { slugify } from '@skyscanner/sky-ui'
import type { EventType } from '@/models/event'

type TypeKind = 'event' | 'entity'

interface KindItem {
  title: string
  value: TypeKind
}

interface IndustryItem {
  title: string
  value: string | null
}

interface DeclaredType {
  id: string
  key: string
  name: string
  description: string
  industry: string | null
}

const KIND_ITEMS: KindItem[] = [
  { title: 'Event types', value: 'event' },
  { title: 'Entity types', value: 'entity' },
]

const DEFAULT_ORDER = 100
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import { useSnackbar } from '@/composables/useSnackbar'
import { useIndustries } from '@/composables/useIndustries'
import {
  createEntityType,
  createEventType,
  deleteType,
  listEntityTypes,
  listEventTypes,
} from '@/requests/schema'

const { industries } = useIndustries()
const { notify, reportError } = useSnackbar()

const kind = ref<TypeKind>('event')
const industry = ref<string | null>(null)
const types = ref<DeclaredType[]>([])

const dialog = ref<boolean>(false)
const saving = ref<boolean>(false)
const draftKind = ref<TypeKind>('event')
const draftName = ref<string>('')
const draftKey = ref<string>('')
const draftDescription = ref<string>('')
const draftIndustry = ref<string | null>(null)
const draftIcon = ref<string>('')

const industryItems = computed<IndustryItem[]>(() => [
  { title: 'Shared', value: null },
  ...industries.value.map((candidate) => ({ title: candidate.name, value: candidate.key })),
])

const canSave = computed<boolean>(() => draftName.value.length > 0 && draftKey.value.length > 0)

const toDeclared = (declared: EventType | EntityType): DeclaredType => ({
  id: declared.id,
  key: declared.key,
  name: declared.name,
  description: declared.description,
  industry: declared.industry,
})

const load = async (): Promise<void> => {
  try {
    const loaded =
      kind.value === 'event' ? await listEventTypes(industry.value) : await listEntityTypes(industry.value)
    types.value = loaded.map(toDeclared)
  } catch (error) {
    reportError(error)
  }
}

const onNameChange = (value: string) => {
  draftKey.value = slugify(value)
}

const onSave = async (): Promise<void> => {
  saving.value = true
  try {
    const draft = {
      key: draftKey.value,
      name: draftName.value,
      description: draftDescription.value,
      industry: draftIndustry.value,
      order: DEFAULT_ORDER,
    }
    if (draftKind.value === 'event') {
      await createEventType(draft)
    } else {
      await createEntityType({ ...draft, icon: draftIcon.value.length > 0 ? draftIcon.value : null })
    }

    dialog.value = false
    draftName.value = ''
    draftKey.value = ''
    draftDescription.value = ''
    draftIcon.value = ''
    kind.value = draftKind.value
    await load()
    notify('The type was declared', 'success')
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}

const onDelete = async (typeId: string): Promise<void> => {
  try {
    await deleteType(typeId)
    await load()
    notify('The type was removed', 'success')
  } catch (error) {
    reportError(error)
  }
}

onMounted(load)
watch([kind, industry], load)
</script>

<style scoped>
.types {
  gap: 1rem;
}

.types__heading {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-block: 1.5rem 0.5rem;
}

.types__title {
  font-size: 1.5rem;
  font-weight: 700;
}

.types__hint {
  opacity: 0.7;
  max-inline-size: 60rem;
}

.types__filters {
  display: flex;
  gap: 1rem;
  max-inline-size: 32rem;
}

.types__table {
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
}

.types__row-actions {
  text-align: end;
}

.types__empty {
  text-align: center;
  opacity: 0.6;
  padding-block: 2rem;
}

.types__dialog {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
</style>
