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
          @click="openCreate"
        >
          Declare a type
        </v-btn>
      </div>

      <p class="types__hint">
        An <strong>event type</strong> is the shape an event takes - what the create wizard asks for when it is
        chosen. An <strong>entity type</strong> is the shape of the things nested inside an event, each with a
        schema of its own. Both can be shared across every industry or belong to a few of them.
      </p>
      <p class="types__hint types__hint--quiet">
        The fields a type asks for are declared on the <RouterLink to="/schema">
          Schema
        </RouterLink> page, and the
        platforms an event runs on are declared on the <RouterLink to="/platforms">
          Platforms
        </RouterLink> page.
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
            <th>Industries</th>
            <th>Asks for</th>
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
            <td>{{ declared.industries.length > 0 ? declared.industries.join(', ') : SHARED_LABEL }}</td>
            <td>{{ extraFieldsLabel(declared) }}</td>
            <td class="types__row-actions">
              <v-btn
                icon="mdi-pencil-outline"
                size="x-small"
                variant="text"
                :aria-label="`Edit ${declared.name}`"
                @click="openEdit(declared)"
              />
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
              colspan="6"
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
        <v-card-title>{{ edited === null ? 'Declare a type' : `Edit ${edited.name}` }}</v-card-title>
        <v-card-text class="types__dialog">
          <!--
            What kind of thing is being declared is decided once. Changing a stored declaration from an event
            type into an entity type is not an edit, it is a different declaration entirely.
          -->
          <v-select
            v-if="edited === null"
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

          <!--
            The key is what every event filed under this type actually stores, so changing one is a write
            across the inventory rather than an edit to this row. It is held behind a deliberate act, and
            what the change would cost is read from the service and shown before anybody commits to it.
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

          <!--
            A declaration may serve several industries at once, and one that names none is offered to all of
            them, which is what "shared" used to mean when only a single industry could be picked.
          -->
          <v-select
            v-model="draftIndustries"
            :items="industryOptions"
            item-title="title"
            item-value="value"
            label="Industries"
            hint="Leave empty to share the declaration with every industry."
            persistent-hint
            multiple
            chips
          />

          <!--
            Not every event is asked the same questions. An experiment result means nothing on a type that
            does not describe an experiment, so the built in fields a type wants are declared here rather
            than being shown on every event form.
          -->
          <v-select
            v-if="draftKind === 'event'"
            v-model="draftFields"
            :items="FIELD_ITEMS"
            item-title="title"
            item-value="value"
            label="Extra event fields"
            hint="The built in fields the create form asks for on top of the brief, the industry and the platform."
            persistent-hint
            multiple
            chips
          />
          <!--
            And the ones nobody built in: the event fields declared on the Schema page, which a type picks
            from exactly the way it picks the built in ones.
          -->
          <v-select
            v-if="draftKind === 'event'"
            v-model="draftCustomFields"
            :items="customFieldItems"
            item-title="title"
            item-value="value"
            label="Declared event fields"
            :hint="customFieldsHint"
            persistent-hint
            multiple
            chips
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
            {{ edited === null ? 'Declare' : 'Save' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import type { OptionalEventField } from '@/models/common'
import type { EntityType } from '@/models/entity'
import { humanizeKey, slugify } from '@truth-platform/core-ui'
import type { EventType } from '@/models/event'
import type { FieldDefinition } from '@truth-platform/core-ui'
import type { RenameResult } from '@/requests/schema'

/**
 * What this page declares.
 *
 * It used to declare four things. A platform is a piece of equipment rather than a shape an event takes, and
 * an event field is a question rather than a shape either, so both went to pages of their own - the
 * platforms beside the industries, the event fields beside the rest of the schema. What is left is the two
 * things the page is actually named after.
 */
type TypeKind = 'event' | 'entity'

interface KindItem {
  title: string
  value: TypeKind
}

interface IndustryItem {
  title: string
  value: string | null
}

interface FieldItem {
  title: string
  value: OptionalEventField
}

interface CustomFieldItem {
  title: string
  value: string
}

interface DeclaredType {
  id: string
  key: string
  name: string
  description: string
  industries: string[]
  fields: OptionalEventField[]
  customFields: string[]
  icon: string | null
}

const KIND_ITEMS: KindItem[] = [
  { title: 'Event types', value: 'event' },
  { title: 'Entity types', value: 'entity' },
]

/* The built in event fields a type may switch on, which is the whole vocabulary the service understands. */
const FIELD_ITEMS: FieldItem[] = [
  { title: 'Event date', value: 'event_date' },
  { title: 'Experiment result', value: 'experiment_result' },
  { title: 'Information', value: 'notes' },
]

/*
 * What a new event type asks for unless it is told otherwise: everything but the experiment result, which is
 * the one built in field that only makes sense on a type describing an experiment.
 */
const DEFAULT_FIELDS: OptionalEventField[] = ['event_date', 'notes']

const DEFAULT_ORDER = 100

/** How a declaration that belongs to nobody in particular reads in a listing. */
const SHARED_LABEL = 'shared'
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { useSnackbar } from '@truth-platform/core-ui'
import { useIndustries } from '@/composables/useIndustries'
import {
  createEntityType,
  createEventType,
  deleteType,
  listEntityTypes,
  listEventTypes,
  listFields,
  previewTypeRename,
  updateEntityType,
  updateEventType,
} from '@/requests/schema'

const { industries } = useIndustries()
const { notify, reportError } = useSnackbar()

const kind = ref<TypeKind>('event')
const industry = ref<string | null>(null)
const types = ref<DeclaredType[]>([])

/* The event fields declared on the Schema page, which an event type picks the ones it asks for out of. */
const eventFields = ref<FieldDefinition[]>([])

const dialog = ref<boolean>(false)
const saving = ref<boolean>(false)

/* The declaration being changed, or nothing while a new one is being written. */
const edited = ref<DeclaredType | null>(null)

/* Whether the key of a stored declaration is being changed, which is a deliberate act rather than a typo. */
const renaming = ref<boolean>(false)
const renamePreview = ref<RenameResult | null>(null)

const draftKind = ref<TypeKind>('event')
const draftName = ref<string>('')
const draftKey = ref<string>('')
const draftDescription = ref<string>('')
const draftIndustries = ref<string[]>([])
const draftFields = ref<OptionalEventField[]>([...DEFAULT_FIELDS])
const draftCustomFields = ref<string[]>([])
const draftIcon = ref<string>('')

/* The filter above the table narrows to one industry, and the absent choice is every one of them. */
const industryItems = computed<IndustryItem[]>(() => [
  { title: 'All industries', value: null },
  ...industries.value.map((candidate) => ({ title: candidate.name, value: candidate.key })),
])

/* The declaration itself names industries rather than one of them, so shared is the absence of a choice. */
const industryOptions = computed<IndustryItem[]>(() =>
  industries.value.map((candidate) => ({ title: candidate.name, value: candidate.key })),
)

/* An event type picks its declared fields by key, and a key means nothing without the name beside it. */
const customFieldItems = computed<CustomFieldItem[]>(() =>
  eventFields.value.map((field) => ({ title: `${field.name} (${field.type})`, value: field.key })),
)

const customFieldsHint = computed<string>(() =>
  eventFields.value.length === 0
    ? 'No event field has been declared yet. Declare one on the Schema page and it appears here.'
    : 'The event fields declared on the Schema page that the create form asks for when this type is chosen.',
)

const canSave = computed<boolean>(() => draftName.value.trim().length > 0 && draftKey.value.trim().length > 0)

const keyHint = computed<string>(() => {
  if (edited.value === null) {
    return 'How the type is stored on every event filed under it.'
  }

  return renaming.value
    ? 'Every document naming this type is rewritten to the new key when you save.'
    : 'Stored on every event filed under this type, so changing it rewrites those events.'
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

const toDeclared = (declared: EventType | EntityType): DeclaredType => ({
  id: declared.id,
  key: declared.key,
  name: declared.name,
  description: declared.description,
  industries: declared.industries,
  fields: 'fields' in declared ? declared.fields : [],
  customFields: 'custom_fields' in declared ? declared.custom_fields : [],
  icon: 'icon' in declared ? declared.icon : null,
})

/** Read what a declared field is called, falling back to its key while the declarations are still loading. */
const nameOfField = (key: string): string =>
  eventFields.value.find((candidate) => candidate.key === key)?.name ?? humanizeKey(key)

/** Name the extra fields of a type, whether they were built in or declared on the Schema page. */
const extraFieldsLabel = (declared: DeclaredType): string => {
  const named = [...declared.fields.map(humanizeKey), ...declared.customFields.map(nameOfField)]

  return named.length > 0 ? named.join(', ') : '—'
}

const load = async (): Promise<void> => {
  try {
    const [declared, fields] = await Promise.all([
      kind.value === 'event' ? listEventTypes(industry.value) : listEntityTypes(industry.value),
      listFields({ scope: 'event', industry: industry.value }),
    ])
    types.value = declared.map(toDeclared)
    eventFields.value = fields
  } catch (error) {
    reportError(error)
  }
}

/* The key follows the name while a new type is written, and a stored one is left exactly as it is. */
const onNameChange = (value: string) => {
  if (edited.value === null) {
    draftKey.value = slugify(value)
  }
}

/** Put the form back to an empty declaration of whatever kind the page is showing. */
const resetDraft = () => {
  edited.value = null
  renaming.value = false
  renamePreview.value = null
  draftKind.value = kind.value
  draftName.value = ''
  draftKey.value = ''
  draftDescription.value = ''
  draftIndustries.value = []
  draftFields.value = [...DEFAULT_FIELDS]
  draftCustomFields.value = []
  draftIcon.value = ''
}

const openCreate = () => {
  resetDraft()
  dialog.value = true
}

/**
 * Open a stored declaration for changing, with its key held back behind a deliberate act.
 */
const openEdit = (declared: DeclaredType) => {
  resetDraft()
  edited.value = declared
  draftKind.value = kind.value
  draftName.value = declared.name
  draftKey.value = declared.key
  draftDescription.value = declared.description
  draftIndustries.value = [...declared.industries]
  draftFields.value = [...declared.fields]
  draftCustomFields.value = [...declared.customFields]
  draftIcon.value = declared.icon ?? ''
  dialog.value = true
}

/**
 * Unlock the key and ask the service what changing it would cost before anybody commits to it.
 */
const startRename = async (): Promise<void> => {
  renaming.value = true
  const declared = edited.value
  if (declared === null) {
    return
  }

  try {
    renamePreview.value = await previewTypeRename(declared.id, declared.key)
  } catch (error) {
    reportError(error)
  }
}

/**
 * Write a new declaration of whichever kind the form is set to.
 */
const create = async (): Promise<void> => {
  const draft = {
    key: draftKey.value.trim(),
    name: draftName.value.trim(),
    description: draftDescription.value.trim(),
    industries: [...draftIndustries.value],
    order: DEFAULT_ORDER,
  }

  if (draftKind.value === 'event') {
    await createEventType({
      ...draft,
      fields: [...draftFields.value],
      custom_fields: [...draftCustomFields.value],
    })

    return
  }

  await createEntityType({ ...draft, icon: draftIcon.value.length > 0 ? draftIcon.value : null })
}

/**
 * Change a stored declaration, sending the key only when it actually moved.
 */
const change = async (declared: DeclaredType): Promise<string> => {
  const moved = draftKey.value.trim() !== declared.key
  const draft = {
    key: moved ? draftKey.value.trim() : undefined,
    name: draftName.value.trim(),
    description: draftDescription.value.trim(),
    industries: [...draftIndustries.value],
  }

  const changed =
    draftKind.value === 'event'
      ? await updateEventType(declared.id, {
        ...draft,
        fields: [...draftFields.value],
        custom_fields: [...draftCustomFields.value],
      })
      : await updateEntityType(declared.id, {
        ...draft,
        icon: draftIcon.value.length > 0 ? draftIcon.value : null,
      })

  return moved ? `The type is now stored as ${changed.key}` : 'The type was changed'
}

const onSave = async (): Promise<void> => {
  saving.value = true
  try {
    const declared = edited.value
    if (declared === null) {
      await create()
      kind.value = draftKind.value
      notify('The type was declared', 'success')
    } else {
      notify(await change(declared), 'success')
    }

    dialog.value = false
    resetDraft()
    await load()
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

.types__hint--quiet {
  font-size: 0.875rem;
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
