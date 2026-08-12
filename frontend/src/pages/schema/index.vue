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
          @click="dialog = true"
        >
          Declare a field
        </v-btn>
      </div>

      <div class="schema__filters">
        <v-select
          v-model="scope"
          :items="SCOPE_ITEMS"
          item-title="title"
          item-value="value"
          label="Scope"
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
            <td>{{ field.required ? 'yes' : 'no' }}</td>
            <td>{{ field.visible ? 'yes' : 'no' }}</td>
            <td class="schema__row-actions">
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
              colspan="8"
              class="schema__empty"
            >
              No fields were declared for this scope yet.
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
        <v-card-title>Declare a field</v-card-title>
        <v-card-text class="schema__dialog">
          <v-text-field
            v-model="draftName"
            label="Name"
            @update:model-value="onNameChange"
          />
          <v-text-field
            v-model="draftKey"
            label="Key"
          />
          <v-select
            v-model="draftType"
            :items="TYPE_OPTIONS"
            label="Type"
          />
          <v-select
            v-model="draftScope"
            :items="SCOPE_ITEMS"
            item-title="title"
            item-value="value"
            label="Scope"
          />
          <!--
            A field of an entity belongs to one kind of entity, so the type is picked from the ones that
            were declared rather than typed from memory. Leaving it empty gives every entity the field.
          -->
          <v-select
            v-if="draftScope === 'entity'"
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
            :hint="draftScope === 'entity' ? 'The field applies to every entity of this industry.' : undefined"
            :persistent-hint="draftScope === 'entity'"
          />
          <p
            v-else
            class="schema__derived"
          >
            {{ derivedIndustryNote }}
          </p>
          <v-combobox
            v-if="draftType === 'enum'"
            v-model="draftOptions"
            label="Allowed values"
            multiple
            chips
          />
          <v-textarea
            v-model="draftDescription"
            label="Explanation"
            rows="2"
            hint="Shown next to the field on the information icon, so a filler knows what it means."
            persistent-hint
          />

          <!--
            A field may only apply once another one holds a value, which is what the requirements called a
            depends on. Every condition declared here has to hold before the field is asked for at all, and
            only fields the form can actually read are offered - a condition on anything else never holds.
          -->
          <div class="schema__dependencies">
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
                  ? 'No other field this one could wait for is declared yet.'
                  : dependenciesHint
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
                multiple
                chips
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
            @click="onCreate"
          >
            Declare
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import type { FieldScope, FieldType } from '@/models/common'
import { slugify } from '@skyscanner/sky-ui'
import type { EntityType } from '@/models/entity'
import type { DependencyOperator, FieldDefinition, FieldDependency } from '@/models/field'

interface SelectItem {
  title: string
  value: string | null
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

/** What a candidate of the surrounding event is called, so that it is never taken for a field of the form. */
const EVENT_FIELD_SUFFIX = 'of the event'

/** How an industry that belongs to nobody in particular reads in a selector. */
const SHARED_LABEL = 'shared'
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import { useSnackbar } from '@/composables/useSnackbar'
import { useIndustries } from '@/composables/useIndustries'
import { client } from '@/requests/client'
import { listEntityTypes, listFields } from '@/requests/schema'

const SCOPE_ITEMS: SelectItem[] = [
  { title: 'Events', value: 'event' },
  { title: 'Entities', value: 'entity' },
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
]

const { industries, load } = useIndustries()
const { notify, reportError } = useSnackbar()

const scope = ref<FieldScope>('event')
const industry = ref<string | null>(null)
const fields = ref<FieldDefinition[]>([])
const dialog = ref<boolean>(false)
const saving = ref<boolean>(false)

const draftName = ref<string>('')
const draftKey = ref<string>('')
const draftType = ref<FieldType>('string')
const draftScope = ref<FieldScope>('event')
const draftIndustry = ref<string | null>(null)
const draftEntityType = ref<string | null>(null)
const draftOptions = ref<string[]>([])
const draftDescription = ref<string>('')
const draftDependencies = ref<FieldDependency[]>([])
const entityTypes = ref<EntityType[]>([])
const draftRequired = ref<boolean>(false)
const draftVisible = ref<boolean>(true)
const ownScopeFields = ref<FieldDefinition[]>([])
const eventScopeFields = ref<FieldDefinition[]>([])

const industryItems = computed<SelectItem[]>(() => [
  { title: 'Shared', value: null },
  ...industries.value.map((candidate) => ({ title: candidate.name, value: candidate.key })),
])

/**
 * Name one industry the way the user knows it, falling back to the key of an industry nobody registered.
 */
const industryLabel = (key: string | null): string => {
  if (key === null) {
    return SHARED_LABEL
  }

  return industries.value.find((candidate) => candidate.key === key)?.name ?? key
}

/* Every declared entity type is offered, each one saying which industry it drags along with it. */
const entityTypeItems = computed<SelectItem[]>(() => [
  { title: 'Every entity type', value: null },
  ...entityTypes.value.map((candidate) => ({
    title: `${candidate.name} (${industryLabel(candidate.industry)})`,
    value: candidate.key,
  })),
])

const chosenEntityType = computed<EntityType | null>(
  () => entityTypes.value.find((candidate) => candidate.key === draftEntityType.value) ?? null,
)

/* Only a draft that names no entity type leaves the industry open, because nothing else answers it. */
const industryIsAsked = computed<boolean>(() => draftScope.value === 'event' || chosenEntityType.value === null)

const resolvedIndustry = computed<string | null>(() =>
  industryIsAsked.value ? draftIndustry.value : (chosenEntityType.value?.industry ?? null),
)

const derivedIndustryNote = computed<string>(() => {
  const type = chosenEntityType.value?.name ?? ''

  return chosenEntityType.value?.industry === null
    ? `The entity type ${type} is shared, so the field is declared for every industry.`
    : `The entity type ${type} belongs to ${industryLabel(resolvedIndustry.value)}, so the field is declared there.`
})

/*
 * A condition may point at a field of the same form, and a field of an entity may also point at a field of
 * the event that entity hangs under - that is the only other form whose values are known while it is filled
 * in. A key the entity declares itself always wins, so an event field it shadows is not offered twice.
 */
const dependencyCandidates = computed<SelectItem[]>(() => {
  const own = ownScopeFields.value.filter((candidate) => candidate.key !== draftKey.value)
  const ownKeys = new Set(own.map((candidate) => candidate.key))

  return [
    ...own.map((candidate) => ({ title: candidate.name, value: candidate.key })),
    ...eventScopeFields.value
      .filter((candidate) => !ownKeys.has(candidate.key))
      .map((candidate) => ({ title: `${candidate.name} (${EVENT_FIELD_SUFFIX})`, value: candidate.key })),
  ]
})

const dependenciesHint = computed<string>(() =>
  draftScope.value === 'entity'
    ? 'The field always applies. Add a condition to make it appear only for some entities, or only once the event says so.'
    : 'The field always applies. Add a condition to make it appear only in some cases.',
)

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
      listFields({ scope: scope.value, industry: industry.value }),
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
  const owner = resolvedIndustry.value
  try {
    if (draftScope.value === 'event') {
      ownScopeFields.value = await listFields({ scope: 'event', industry: owner })
      eventScopeFields.value = []

      return
    }

    const [entityFields, eventFields] = await Promise.all([
      listFields({ scope: 'entity', industry: owner, entityType: draftEntityType.value }),
      listFields({ scope: 'event', industry: owner }),
    ])
    /* A field declared for every entity type shares its form with the fields of no single type only. */
    ownScopeFields.value =
      draftEntityType.value === null
        ? entityFields.filter((candidate) => candidate.entity_type === null)
        : entityFields
    eventScopeFields.value = eventFields
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

const onNameChange = (value: string) => {
  draftKey.value = slugify(value)
}

const onCreate = async (): Promise<void> => {
  saving.value = true
  try {
    await client.post('/fields', {
      name: draftName.value,
      key: draftKey.value,
      type: draftType.value,
      array: false,
      default: null,
      required: draftRequired.value,
      scope: draftScope.value,
      industry: resolvedIndustry.value,
      entity_type: draftScope.value === 'entity' ? draftEntityType.value : null,
      metadata: {
        allowed_file_types: [],
        options: draftOptions.value,
        unit: null,
        description: draftDescription.value.length > 0 ? draftDescription.value : null,
        placeholder: null,
        group: null,
      },
      constraints: [],
      depends_on: draftDependencies.value,
      filterable: true,
      sortable: true,
      editable: true,
      visible: draftVisible.value,
      order: 100,
    })
    notify('The field was declared', 'success')
    dialog.value = false
    draftName.value = ''
    draftKey.value = ''
    draftOptions.value = []
    draftDescription.value = ''
    /* The conditions belonged to the field that was just declared, not to the next one typed into the form. */
    draftDependencies.value = []
    await reload()
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}

const onDelete = async (fieldId: string): Promise<void> => {
  try {
    await client.delete(`/fields/${fieldId}`)
    notify('The field was removed', 'success')
    await reload()
  } catch (error) {
    reportError(error)
  }
}

onMounted(async () => {
  await load()
  await reload()
})

watch([scope, industry], reload)
watch([dialog, draftScope, draftIndustry, draftEntityType], refreshCandidates)
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
