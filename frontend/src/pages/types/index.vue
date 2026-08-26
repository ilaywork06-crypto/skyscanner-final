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
          @click="openDialog"
        >
          {{ kind === 'field' ? 'Declare an event field' : 'Declare a type' }}
        </v-btn>
      </div>

      <p class="types__hint">
        An event needs at least one event type before it can be uploaded, an entity needs an entity type to be
        grouped under, and every event names the platforms it ran on out of the ones declared here. A system
        that was never filled starts without any, so the first ones are declared here. An event field declared
        here is a question of your own that an event type may then ask on the create form.
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

      <!--
        A declared event field describes itself with what it holds rather than with the industries it serves,
        so the two listings do not share a header row.
      -->
      <v-table
        v-if="kind === 'field'"
        class="types__table"
      >
        <thead>
          <tr>
            <th>Name</th>
            <th>Key</th>
            <th>Type</th>
            <th>Industry</th>
            <th>Allowed values</th>
            <th>Required</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="field in eventFields"
            :key="field.id"
          >
            <td>{{ field.name }}</td>
            <td><code>{{ field.key }}</code></td>
            <td>{{ field.type }}</td>
            <td>{{ field.industry ?? SHARED_LABEL }}</td>
            <td>{{ field.metadata.options.length > 0 ? field.metadata.options.join(', ') : '—' }}</td>
            <td>{{ field.required ? 'yes' : 'no' }}</td>
            <td class="types__row-actions">
              <v-btn
                icon="mdi-delete-outline"
                size="x-small"
                variant="text"
                :aria-label="`Remove ${field.name}`"
                @click="onDeleteField(field.id)"
              />
            </td>
          </tr>
          <tr v-if="eventFields.length === 0">
            <td
              colspan="7"
              class="types__empty"
            >
              No event fields were declared yet.
            </td>
          </tr>
        </tbody>
      </v-table>

      <v-table
        v-else
        class="types__table"
      >
        <thead>
          <tr>
            <th>Name</th>
            <th>Key</th>
            <th>Description</th>
            <th>Industries</th>
            <th>Extra fields</th>
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
        <v-card-title>{{ draftKind === 'field' ? 'Declare an event field' : 'Declare a type' }}</v-card-title>
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
            v-if="draftKind !== 'field'"
            v-model="draftDescription"
            label="Description"
          />

          <!--
            An event field is a question of its own: what it is called, what kind of answer it takes, and
            whether an event may be filed without one. It is declared once here and then asked for by every
            event type that names it, which is what keeps two people describing the same thing from
            inventing two spellings of the same key.
          -->
          <template v-if="draftKind === 'field'">
            <v-select
              v-model="draftFieldType"
              :items="FIELD_TYPE_OPTIONS"
              label="Type"
            />
            <v-combobox
              v-if="draftFieldType === 'enum'"
              v-model="draftOptions"
              label="Allowed values"
              :hint="ENTER_TO_ADD_HINT"
              persistent-hint
              multiple
              chips
              closable-chips
            />
            <v-select
              v-model="draftIndustry"
              :items="industryItems"
              item-title="title"
              item-value="value"
              label="Industry"
              hint="Leave on all industries to declare the field for every one of them."
              persistent-hint
            />
            <v-textarea
              v-model="draftDescription"
              label="Explanation"
              rows="2"
              hint="Shown next to the field on the information icon, so a filler knows what it means."
              persistent-hint
            />
            <v-checkbox
              v-model="draftRequired"
              label="Required"
              hide-details
            />
            <v-checkbox
              v-model="draftVisible"
              label="Shown as a column in the inventory by default"
              hide-details
            />
          </template>

          <template v-else>
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
              And the ones nobody built in: the event fields declared on this page, which a type picks from
              exactly the way it picks the built in ones.
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
          </template>
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
import type { FieldType, OptionalEventField } from '@/models/common'
import type { EntityType } from '@/models/entity'
import { humanizeKey, slugify } from '@skyscanner/sky-ui'
import type { EventType } from '@/models/event'
import type { FieldDefinition } from '@/models/field'
import type { Platform } from '@/models/platform'

/** What the page declares, where a field is not a type at all but is declared from the very same place. */
type TypeKind = 'event' | 'entity' | 'platform' | 'field'

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
}

const KIND_ITEMS: KindItem[] = [
  { title: 'Event types', value: 'event' },
  { title: 'Entity types', value: 'entity' },
  { title: 'Platforms', value: 'platform' },
  { title: 'Event fields', value: 'field' },
]

/* The built in event fields a type may switch on, which is the whole vocabulary the service understands. */
const FIELD_ITEMS: FieldItem[] = [
  { title: 'Reference ID', value: 'reference_id' },
  { title: 'Event date', value: 'event_date' },
  { title: 'Experiment result', value: 'experiment_result' },
  { title: 'Information', value: 'notes' },
]

/*
 * What a declared event field may hold. A file needs a place to put the bytes and an entity type to hang
 * off, neither of which an event form has, so it is not offered here.
 */
const FIELD_TYPE_OPTIONS: FieldType[] = [
  'string',
  'text',
  'number',
  'integer',
  'boolean',
  'date',
  'datetime',
  'enum',
  'json',
  'coordinate',
]

/*
 * What a new event type asks for unless it is told otherwise: everything but the experiment result, which is
 * the one built in field that only makes sense on a type describing an experiment.
 */
const DEFAULT_FIELDS: OptionalEventField[] = ['reference_id', 'event_date', 'notes']

const DEFAULT_ORDER = 100

/** How a declaration that belongs to nobody in particular reads in a listing. */
const SHARED_LABEL = 'shared'
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import { useSnackbar } from '@/composables/useSnackbar'
import { useIndustries } from '@/composables/useIndustries'
import {
  createEntityType,
  createEventType,
  createField,
  createPlatform,
  deleteField,
  deleteType,
  listEntityTypes,
  listEventTypes,
  listFields,
  listPlatforms,
} from '@/requests/schema'
import { ENTER_TO_ADD_HINT } from '@/utils/hints'

const { industries } = useIndustries()
const { notify, reportError } = useSnackbar()

const kind = ref<TypeKind>('event')
const industry = ref<string | null>(null)
const types = ref<DeclaredType[]>([])

/* Every event field that was declared, which the listing shows and the event type dialog picks from. */
const eventFields = ref<FieldDefinition[]>([])

const dialog = ref<boolean>(false)
const saving = ref<boolean>(false)
const draftKind = ref<TypeKind>('event')
const draftName = ref<string>('')
const draftKey = ref<string>('')
const draftDescription = ref<string>('')
const draftIndustries = ref<string[]>([])
const draftIndustry = ref<string | null>(null)
const draftFields = ref<OptionalEventField[]>([...DEFAULT_FIELDS])
const draftCustomFields = ref<string[]>([])
const draftIcon = ref<string>('')
const draftFieldType = ref<FieldType>('string')
const draftOptions = ref<string[]>([])
const draftRequired = ref<boolean>(false)
const draftVisible = ref<boolean>(true)

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
    ? 'No event field has been declared yet. Declare one under the Event fields kind and it appears here.'
    : 'The fields declared on this page that the create form asks for when this type is chosen.',
)

const canSave = computed<boolean>(() => draftName.value.length > 0 && draftKey.value.length > 0)

const toDeclared = (declared: EventType | EntityType | Platform): DeclaredType => ({
  id: declared.id,
  key: declared.key,
  name: declared.name,
  description: declared.description,
  industries: declared.industries,
  fields: 'fields' in declared ? declared.fields : [],
  customFields: 'custom_fields' in declared ? declared.custom_fields : [],
})

/** Name the extra fields of a type, whether they were built in or declared on this very page. */
const extraFieldsLabel = (declared: DeclaredType): string => {
  const named = [...declared.fields.map(humanizeKey), ...declared.customFields.map(nameOfField)]

  return named.length > 0 ? named.join(', ') : '—'
}

/** Read what a declared field is called, falling back to its key while the declarations are still loading. */
const nameOfField = (key: string): string =>
  eventFields.value.find((candidate) => candidate.key === key)?.name ?? humanizeKey(key)

const readKind = async (): Promise<(EventType | EntityType | Platform)[]> => {
  if (kind.value === 'event') {
    return listEventTypes(industry.value)
  }

  return kind.value === 'entity' ? listEntityTypes(industry.value) : listPlatforms(industry.value)
}

/**
 * Read the declared event fields, which both the listing and the event type dialog need at all times.
 */
const loadEventFields = async (): Promise<void> => {
  eventFields.value = await listFields({ scope: 'event', industry: industry.value })
}

const load = async (): Promise<void> => {
  try {
    await loadEventFields()
    types.value = kind.value === 'field' ? [] : (await readKind()).map(toDeclared)
  } catch (error) {
    reportError(error)
  }
}

const onNameChange = (value: string) => {
  draftKey.value = slugify(value)
}

const openDialog = () => {
  draftKind.value = kind.value
  dialog.value = true
}

/**
 * Empty the form once a declaration has landed, keeping the kind so that declaring several in a row is easy.
 */
const resetDraft = () => {
  draftName.value = ''
  draftKey.value = ''
  draftDescription.value = ''
  draftIcon.value = ''
  draftFields.value = [...DEFAULT_FIELDS]
  draftCustomFields.value = []
  draftOptions.value = []
  draftFieldType.value = 'string'
  draftRequired.value = false
  draftVisible.value = true
}

/**
 * Declare one event field, which is a declaration of the dynamic schema rather than a type of its own.
 */
const saveField = async (): Promise<void> => {
  await createField({
    name: draftName.value,
    key: draftKey.value,
    type: draftFieldType.value,
    array: false,
    default: null,
    required: draftRequired.value,
    scope: 'event',
    industry: draftIndustry.value,
    entity_type: null,
    additional: false,
    metadata: {
      allowed_file_types: [],
      options: draftFieldType.value === 'enum' ? [...draftOptions.value] : [],
      unit: null,
      description: draftDescription.value.length > 0 ? draftDescription.value : null,
      placeholder: null,
      group: null,
    },
    constraints: [],
    depends_on: [],
    filterable: true,
    sortable: true,
    editable: true,
    visible: draftVisible.value,
    order: DEFAULT_ORDER,
  })
}

const onSave = async (): Promise<void> => {
  saving.value = true
  try {
    if (draftKind.value === 'field') {
      await saveField()
    } else {
      const draft = {
        key: draftKey.value,
        name: draftName.value,
        description: draftDescription.value,
        industries: [...draftIndustries.value],
        order: DEFAULT_ORDER,
      }
      if (draftKind.value === 'event') {
        await createEventType({
          ...draft,
          fields: [...draftFields.value],
          custom_fields: [...draftCustomFields.value],
        })
      } else if (draftKind.value === 'entity') {
        await createEntityType({ ...draft, icon: draftIcon.value.length > 0 ? draftIcon.value : null })
      } else {
        await createPlatform(draft)
      }
    }

    dialog.value = false
    resetDraft()
    kind.value = draftKind.value
    await load()
    notify(draftKind.value === 'field' ? 'The event field was declared' : 'The type was declared', 'success')
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

const onDeleteField = async (fieldId: string): Promise<void> => {
  try {
    await deleteField(fieldId)
    await load()
    notify('The event field was removed', 'success')
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
