<template>
  <div class="sky-page">
    <AppHeader />

    <div class="sky-page__content schema">
      <div class="schema__heading">
        <h1 class="schema__title">
          Schema
        </h1>
        <v-spacer />
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="openCreate"
        >
          Declare a field
        </v-btn>
      </div>

      <div class="schema__filters">
        <v-select
          v-model="section"
          :items="SECTION_ITEMS"
          item-title="title"
          item-value="value"
          label="Section"
        />
        <v-select
          v-model="industry"
          :items="industryItems"
          item-title="title"
          item-value="value"
          label="Industry"
        />
      </div>

      <v-table class="schema__table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Key</th>
            <th>Type</th>
            <th>Industry</th>
            <th>Entity type</th>
            <th>Section</th>
            <th>Required</th>
            <th>Visible</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="field in fields"
            :key="field.id"
          >
            <td>{{ field.name }}</td>
            <td><code>{{ field.key }}</code></td>
            <td>{{ field.type }}{{ field.array ? '[]' : '' }}</td>
            <td>{{ field.industry ?? 'shared' }}</td>
            <td>{{ field.entity_type ?? '—' }}</td>
            <td>{{ sectionLabel(field) }}</td>
            <td>{{ field.required ? 'yes' : 'no' }}</td>
            <td>{{ field.visible ? 'yes' : 'no' }}</td>
            <td class="schema__row-actions">
              <v-btn
                icon="mdi-pencil-outline"
                size="x-small"
                variant="text"
                :aria-label="`Edit ${field.name}`"
                @click="openEdit(field)"
              />
              <v-btn
                icon="mdi-delete-outline"
                size="x-small"
                variant="text"
                :aria-label="`Remove ${field.name}`"
                @click="onDelete(field.id)"
              />
            </td>
          </tr>
          <tr v-if="fields.length === 0">
            <td
              colspan="9"
              class="schema__empty"
            >
              {{ emptyText }}
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <v-dialog
      v-model="dialog"
      max-width="40rem"
    >
      <v-card>
        <v-card-title>{{ edited === null ? 'Declare a field' : `Edit ${edited.name}` }}</v-card-title>
        <v-card-text class="schema__dialog">
          <v-text-field
            v-model="draftName"
            :label="t('schema.name')"
            @update:model-value="onNameChange"
          />
          <!--
            What this field is called when the interface is read in Hebrew. A declaration that carries none
            keeps the name it was declared under in both languages, which is the honest answer: the name is
            the vocabulary of whoever declared it rather than a word this system ships, so there is nowhere
            else a Hebrew one could come from.
          -->
          <v-text-field
            v-model="draftNameHebrew"
            :label="t('schema.nameHebrew')"
            :hint="t('schema.nameHebrewHint')"
            persistent-hint
            dir="rtl"
          />
          <!--
            The key is where every value answering this field is actually stored - twice over, in the list
            the schema reads and in the flat sub document the columns are filtered over - so changing one
            moves every value ever written under it. It is held behind a deliberate act, and what the change
            would cost is read from the service and shown before anybody commits to it.
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
          <v-select
            v-model="draftType"
            :items="TYPE_OPTIONS"
            label="Type"
          />
          <!--
            Which half of the entity form the field belongs to. The additional data used to be a free for all
            of keys people invented as they went; declaring one here is what turns a key two people would
            have spelled differently into the same field on both of their forms.
          -->
          <v-select
            v-model="draftSection"
            :items="SECTION_ITEMS"
            item-title="title"
            item-value="value"
            label="Section"
          />
          <!--
            A field of an entity belongs to one kind of entity, so the type is picked from the ones that
            were declared rather than typed from memory. Leaving it empty gives every entity the field.
          -->
          <v-select
            v-if="!draftIsEventScope"
            v-model="draftEntityType"
            :items="entityTypeItems"
            item-title="title"
            item-value="value"
            label="Entity type"
            hint="Leave on every entity type to declare the field for all of them."
            persistent-hint
          />
          <!--
            An entity type already belongs to an industry, so asking for the industry a second time only
            offers the chance to disagree with it. The question is therefore only asked where there is
            nothing to read the answer off, and the answer that was read off is spelled out below.
          -->
          <v-select
            v-if="industryIsAsked"
            v-model="draftIndustry"
            :items="industryItems"
            item-title="title"
            item-value="value"
            label="Industry"
            hint="The field applies to every entity of this industry."
            persistent-hint
          />
          <p
            v-else
            class="schema__derived"
          >
            {{ derivedIndustryNote }}
          </p>
          <!--
            The values an enum offers are collected one at a time, and a box that only turns what is typed
            into a chip on Enter has to say so - otherwise the last value typed is quietly dropped.
          -->
          <v-combobox
            v-if="draftType === 'enum'"
            v-model="draftOptions"
            label="Allowed values"
            :hint="t('input.enterToAdd')"
            persistent-hint
            multiple
            chips
            closable-chips
          />
          <v-textarea
            v-model="draftDescription"
            label="Explanation"
            rows="2"
            hint="Information about the field that will be shown near it when filling."
            persistent-hint
          />

          <!--
            A field may only apply once another one holds a value, which is what the requirements called a
            depends on. Every condition declared here has to hold before the field is asked for at all, and
            only fields the form can actually read are offered - a condition on anything else never holds.

            The conditions describe one entity form, so an event field is not offered them: there is no form
            for it to point into, and a condition that can never hold is a condition nobody should declare.
          -->
          <div
            v-if="!draftIsEventScope"
            class="schema__dependencies"
          >
            <div class="schema__dependencies-head">
              <span class="schema__dependencies-title">Depends on</span>
              <v-btn
                size="x-small"
                variant="text"
                prepend-icon="mdi-plus"
                :disabled="dependencyCandidates.length === 0"
                @click="addDependency"
              >
                ADD CONDITION
              </v-btn>
            </div>
            <p
              v-if="draftDependencies.length === 0"
              class="schema__dependencies-empty"
            >
              {{
                dependencyCandidates.length === 0
                  ? 'There are no other fields so dependencies can not be created.'
                  : DEPENDENCIES_HINT
              }}
            </p>
            <div
              v-for="(dependency, index) in draftDependencies"
              :key="index"
              class="schema__dependency"
            >
              <v-select
                v-model="dependency.field"
                :items="dependencyCandidates"
                item-title="title"
                item-value="value"
                label="Field"
                density="compact"
              />
              <v-select
                v-model="dependency.operator"
                :items="DEPENDENCY_OPERATORS"
                item-title="title"
                item-value="value"
                label="Condition"
                density="compact"
              />
              <v-combobox
                v-if="dependency.operator !== 'has_value' && dependency.operator !== 'is_empty'"
                v-model="dependency.values"
                label="Values"
                density="compact"
                :hint="t('input.enterToAdd')"
                persistent-hint
                multiple
                chips
                closable-chips
              />
              <v-btn
                icon="mdi-close"
                size="x-small"
                variant="text"
                aria-label="Remove this condition"
                @click="removeDependency(index)"
              />
            </div>
          </div>
          <v-checkbox
            v-model="draftRequired"
            label="Required"
            hide-details
          />
          <v-checkbox
            v-model="draftVisible"
            label="Shown in the table by default"
            hide-details
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
import type { FieldType } from '@/models/common'
import { slugify, useLanguage } from '@truth-platform/core-ui'
import type { EntityType } from '@/models/entity'
import type { DependencyOperator, FieldDefinition, FieldDependency } from '@truth-platform/core-ui'
import type { RenameResult } from '@/requests/schema'

interface SelectItem {
  title: string
  value: string | null
}

/**
 * What the page is showing.
 *
 * The two halves of the entity form have always been here. The event fields joined them: they are the same
 * kind of thing declared the same way - a name, a type, its allowed values and the industry it belongs to -
 * and they were being declared on the Types page, which is a page about the shapes an event and an entity
 * take rather than about the questions they answer. A field is a question. It belongs here.
 */
type FieldSection = 'event' | 'own' | 'additional'

interface SectionItem {
  title: string
  value: FieldSection
}

interface OperatorItem {
  title: string
  value: DependencyOperator
}

const DEPENDENCY_OPERATORS: OperatorItem[] = [
  { title: 'has any value', value: 'has_value' },
  { title: 'is empty', value: 'is_empty' },
  { title: 'is one of', value: 'one_of' },
  { title: 'is not one of', value: 'not_equals' },
]

/** How an industry that belongs to nobody in particular reads in a selector. */
const SHARED_LABEL = 'shared'
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import { useSnackbar } from '@truth-platform/core-ui'
import { useIndustries } from '@/composables/useIndustries'
import {
  createField,
  deleteField,
  listEntityTypes,
  listFields,
  previewFieldRename,
  updateField,
} from '@/requests/schema'

const { t } = useLanguage()

/*
 * The two halves of an entity form. Both are stored in the same place and both become columns of the entity
 * table, so the only thing the section decides is where the field is asked for.
 */
const SECTION_ITEMS: SectionItem[] = [
  { title: 'Event fields', value: 'event' },
  { title: 'Entity fields', value: 'own' },
  { title: 'Additional data', value: 'additional' },
]

const TYPE_OPTIONS: FieldType[] = [
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

const { industries, load } = useIndustries()
const { notify, reportError } = useSnackbar()

const section = ref<FieldSection>('event')
const industry = ref<string | null>(null)
const fields = ref<FieldDefinition[]>([])
const dialog = ref<boolean>(false)
const saving = ref<boolean>(false)

/* The declaration being changed, or nothing while a new one is being written. */
const edited = ref<FieldDefinition | null>(null)

/* Whether the key of a stored declaration is being changed, which is a deliberate act rather than a typo. */
const renaming = ref<boolean>(false)
const renamePreview = ref<RenameResult | null>(null)

const draftName = ref<string>('')
const draftNameHebrew = ref<string>('')
const draftKey = ref<string>('')
const draftType = ref<FieldType>('string')
const draftSection = ref<FieldSection>('event')
const draftIndustry = ref<string | null>(null)
const draftEntityType = ref<string | null>(null)
const draftOptions = ref<string[]>([])
const draftDescription = ref<string>('')
const draftDependencies = ref<FieldDependency[]>([])
const entityTypes = ref<EntityType[]>([])
const draftRequired = ref<boolean>(false)
const draftVisible = ref<boolean>(true)
const ownScopeFields = ref<FieldDefinition[]>([])

const industryItems = computed<SelectItem[]>(() => {
  const offered =
    typeIndustries.value.length > 0
      ? industries.value.filter((candidate) => typeIndustries.value.includes(candidate.key))
      : industries.value

  return [
    { title: 'Shared', value: null },
    ...offered.map((candidate) => ({ title: candidate.name, value: candidate.key })),
  ]
})

/**
 * Name one industry the way the user knows it, falling back to the key of an industry nobody registered.
 */
const industryLabel = (key: string | null): string => {
  if (key === null) {
    return SHARED_LABEL
  }

  return industries.value.find((candidate) => candidate.key === key)?.name ?? key
}

/**
 * Name the industries a declaration belongs to, where belonging to none means belonging to all of them.
 */
const industriesLabel = (keys: string[]): string =>
  keys.length === 0 ? SHARED_LABEL : keys.map(industryLabel).join(', ')

/* Every declared entity type is offered, each one saying which industries it drags along with it. */
const entityTypeItems = computed<SelectItem[]>(() => [
  { title: 'Every entity type', value: null },
  ...entityTypes.value.map((candidate) => ({
    title: `${candidate.name} (${industriesLabel(candidate.industries)})`,
    value: candidate.key,
  })),
])

/* An event field is declared for the event itself; the other two sections describe the entities inside it. */
const isEventScope = computed<boolean>(() => section.value === 'event')

const draftIsEventScope = computed<boolean>(() => draftSection.value === 'event')

const chosenEntityType = computed<EntityType | null>(
  () => entityTypes.value.find((candidate) => candidate.key === draftEntityType.value) ?? null,
)

/* The industries the chosen type belongs to, which is what the field may be declared for at all. */
const typeIndustries = computed<string[]>(() => chosenEntityType.value?.industries ?? [])

/*
 * A field belongs to one industry, so the question is only skipped where the answer is already settled: a
 * type shared by everybody leaves the field shared, and a type of a single industry hands that one over. A
 * type that serves several is the one case where the answer still has to be picked out of them.
 */
const industryIsAsked = computed<boolean>(
  () => draftIsEventScope.value || chosenEntityType.value === null || typeIndustries.value.length > 1,
)

const resolvedIndustry = computed<string | null>(() =>
  industryIsAsked.value ? draftIndustry.value : (typeIndustries.value[0] ?? null),
)

/** What the service said a rename would move, put into a sentence. */
const renameSummary = computed<string>(() => {
  const preview = renamePreview.value
  if (preview === null) {
    return ''
  }

  const counted = Object.entries(preview.affected).filter(([, amount]) => amount > 0)
  if (counted.length === 0) {
    return `Nothing was ever stored under ${preview.previous_key}, so this rename only changes the declaration.`
  }

  const parts = counted.map(([collection, amount]) => `${amount} ${collection}`)

  return `Saving moves every value in ${parts.join(', ')} from ${preview.previous_key} to ${preview.key}.`
})

/** What the listing says when the chosen section holds nothing yet. */
const emptyText = computed<string>(() =>
  isEventScope.value
    ? 'No event field was declared yet. An event type asks for the ones declared here.'
    : 'No fields were declared for this scope yet.',
)

/** Which section a stored declaration belongs to, read back the way the selector spells it. */
const sectionLabel = (field: FieldDefinition): string => {
  if (field.scope === 'event') {
    return 'event fields'
  }

  return field.additional ? 'additional data' : 'entity fields'
}

const keyHint = computed<string>(() => {
  if (edited.value === null) {
    return 'How every value answering this field is stored.'
  }

  return renaming.value
    ? 'Every value ever written under the old key is moved onto the new one when you save.'
    : 'Every value answering this field is stored under it, so changing it rewrites those values.'
})

const derivedIndustryNote = computed<string>(() => {
  const type = chosenEntityType.value?.name ?? ''

  return typeIndustries.value.length === 0
    ? `The entity type ${type} is shared, so the field is declared for every industry.`
    : `The entity type ${type} belongs to ${industryLabel(resolvedIndustry.value)}, so the field is declared there.`
})

/*
 * A condition may point at any other field of the same entity form, whichever of its two halves that field
 * was declared in: both halves are filled in together and both end up in the same set of values.
 */
const dependencyCandidates = computed<SelectItem[]>(() =>
  ownScopeFields.value
    .filter((candidate) => candidate.key !== draftKey.value)
    .map((candidate) => ({ title: candidate.name, value: candidate.key })),
)

const DEPENDENCIES_HINT =
  'The field always applies. Add a condition to make it appear only for some entities.'

const addDependency = () => {
  const first = dependencyCandidates.value[0]?.value
  if (first === undefined || first === null) {
    return
  }

  draftDependencies.value = [...draftDependencies.value, { field: first, operator: 'has_value', values: [] }]
}

const removeDependency = (index: number) => {
  draftDependencies.value = draftDependencies.value.filter((_, candidate) => candidate !== index)
}

const reload = async (): Promise<void> => {
  try {
    /* The listing follows the filters, while the entity types are read whole: the dialog reads the
       industry off the type the user picks, so it may not only offer the types of one industry. */
    const [declared, types] = await Promise.all([
      isEventScope.value
        ? listFields({ scope: 'event', industry: industry.value })
        : listFields({ scope: 'entity', industry: industry.value, additional: section.value === 'additional' }),
      listEntityTypes(),
    ])
    fields.value = declared
    entityTypes.value = types
  } catch (error) {
    reportError(error)
  }
}

/**
 * Read the fields a condition of the current draft may point at, which is not what the listing shows.
 *
 * The listing follows the filters of the page, and a condition that points at a field of another form can
 * never hold - which is exactly how a dependency that does nothing gets declared. The candidates therefore
 * follow the draft itself: its own scope and industry, plus the event of an entity.
 */
const loadCandidates = async (): Promise<void> => {
  if (draftIsEventScope.value) {
    ownScopeFields.value = []

    return
  }

  const owner = resolvedIndustry.value
  try {
    const entityFields = await listFields({
      scope: 'entity',
      industry: owner,
      entityType: draftEntityType.value,
    })
    /* A field declared for every entity type shares its form with the fields of no single type only. */
    ownScopeFields.value =
      draftEntityType.value === null
        ? entityFields.filter((candidate) => candidate.entity_type === null)
        : entityFields
  } catch (error) {
    reportError(error)
  }
}

/**
 * Follow the draft with the candidates it may depend on, dropping conditions the new scope cannot hold.
 */
const refreshCandidates = async (): Promise<void> => {
  if (!dialog.value) {
    return
  }

  await loadCandidates()
  const offered = new Set(dependencyCandidates.value.map((candidate) => candidate.value))
  draftDependencies.value = draftDependencies.value.filter((dependency) => offered.has(dependency.field))
}

/* The key follows the name while a new field is written, and a stored one is left exactly as it is. */
const onNameChange = (value: string) => {
  if (edited.value === null) {
    draftKey.value = slugify(value)
  }
}

/** Put the form back to an empty declaration of whatever section the page is showing. */
const resetDraft = () => {
  edited.value = null
  renaming.value = false
  renamePreview.value = null
  draftName.value = ''
  draftNameHebrew.value = ''
  draftKey.value = ''
  draftType.value = 'string'
  draftSection.value = section.value
  draftIndustry.value = industry.value
  draftEntityType.value = null
  draftOptions.value = []
  draftDescription.value = ''
  draftDependencies.value = []
  draftRequired.value = false
  draftVisible.value = true
}

const openCreate = () => {
  resetDraft()
  dialog.value = true
}

/**
 * Open a stored declaration for changing, with its key held back behind a deliberate act.
 */
const openEdit = (field: FieldDefinition) => {
  resetDraft()
  edited.value = field
  draftName.value = field.name
  draftNameHebrew.value = field.metadata.name_he ?? ''
  draftKey.value = field.key
  draftType.value = field.type
  draftSection.value = field.scope === 'event' ? 'event' : field.additional ? 'additional' : 'own'
  draftIndustry.value = field.industry
  draftEntityType.value = field.entity_type
  draftOptions.value = [...field.metadata.options]
  draftDescription.value = field.metadata.description ?? ''
  draftDependencies.value = field.depends_on.map((dependency) => ({ ...dependency }))
  draftRequired.value = field.required
  draftVisible.value = field.visible
  dialog.value = true
}

/**
 * Unlock the key and ask the service what changing it would cost before anybody commits to it.
 */
const startRename = async (): Promise<void> => {
  renaming.value = true
  const field = edited.value
  if (field === null) {
    return
  }

  try {
    renamePreview.value = await previewFieldRename(field.id, field.key)
  } catch (error) {
    reportError(error)
  }
}

/** The descriptors a declaration renders with, which both writing and changing one hand over. */
const draftMetadata = () => ({
  allowed_file_types: [],
  name_he: draftNameHebrew.value.length > 0 ? draftNameHebrew.value : null,
  options: draftOptions.value,
  unit: null,
  description: draftDescription.value.length > 0 ? draftDescription.value : null,
  placeholder: null,
  group: null,
})

const onSave = async (): Promise<void> => {
  saving.value = true
  try {
    const field = edited.value
    if (field === null) {
      await createField({
        name: draftName.value,
        key: draftKey.value,
        type: draftType.value,
        array: false,
        default: null,
        required: draftRequired.value,
        scope: draftIsEventScope.value ? 'event' : 'entity',
        industry: resolvedIndustry.value,
        entity_type: draftIsEventScope.value ? null : draftEntityType.value,
        additional: draftSection.value === 'additional',
        metadata: draftMetadata(),
        constraints: [],
        depends_on: draftDependencies.value,
        filterable: true,
        sortable: true,
        editable: true,
        visible: draftVisible.value,
        order: 100,
      })
      notify('The field was declared', 'success')
    } else {
      const moved = draftKey.value.trim() !== field.key
      const changed = await updateField(field.id, {
        key: moved ? draftKey.value.trim() : undefined,
        name: draftName.value,
        type: draftType.value,
        required: draftRequired.value,
        visible: draftVisible.value,
        metadata: draftMetadata(),
        depends_on: draftDependencies.value,
      })
      notify(moved ? `Every value is now stored under ${changed.key}` : 'The field was changed', 'success')
    }

    dialog.value = false
    resetDraft()
    await reload()
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}

const onDelete = async (fieldId: string): Promise<void> => {
  try {
    await deleteField(fieldId)
    notify('The field declaration was removed', 'success')
    await reload()
  } catch (error) {
    reportError(error)
  }
}

onMounted(async () => {
  await load()
  await reload()
})

watch([section, industry], reload)
watch([dialog, draftIndustry, draftEntityType], refreshCandidates)
</script>

<style scoped>
.schema {
  gap: 1rem;
}

.schema__heading {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-block: 1.5rem 0.5rem;
}

.schema__title {
  font-size: 1.75rem;
  font-weight: 600;
}

.schema__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  max-inline-size: 36rem;
}

.schema__table {
  background-color: rgb(var(--v-theme-surface));
  border-radius: 0.75rem;
  overflow: hidden;
}

.schema__row-actions {
  text-align: end;
}

.schema__empty {
  opacity: 0.7;
  text-align: center;
}

.schema__dialog {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* The industry that was read off the entity type stands where its selector would have stood. */
.schema__derived {
  font-size: 0.8125rem;
  opacity: 0.8;
  padding-inline-start: 0.25rem;
}

.schema__dependencies {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
  padding: 0.75rem;
}

.schema__dependencies-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.schema__dependencies-title {
  font-size: 0.875rem;
  font-weight: 600;
}

.schema__dependencies-empty {
  font-size: 0.8125rem;
  opacity: 0.7;
}

/* One condition reads as a sentence across the row: this field, tested this way, against these values. */
.schema__dependency {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) auto;
  align-items: start;
  gap: 0.5rem;
}

@media (max-width: 40rem) {
  .schema__dependency {
    grid-template-columns: 1fr;
  }
}
</style>
