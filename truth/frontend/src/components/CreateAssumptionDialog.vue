<template>
  <v-dialog
    :model-value="modelValue"
    max-width="66rem"
    scrollable
    persistent
    @update:model-value="close"
  >
    <v-card class="wizard">
      <!-- The two stages of the design: what every assumption carries, then what its schemas ask for. -->
      <div class="wizard__steps">
        <div
          v-for="(label, index) in STEP_LABELS"
          :key="label"
          class="wizard__step"
        >
          <span
            class="wizard__dot"
            :class="{ 'wizard__dot--active': step >= index }"
          />
          <span class="wizard__step-label">{{ label }}</span>
        </div>
        <span class="wizard__rail" />
      </div>

      <v-card-title class="wizard__title">
        {{ duplicatedFrom === null ? 'Create An Assumption' : 'Duplicate An Assumption' }}
      </v-card-title>

      <v-card-text class="wizard__body">
        <template v-if="step === 0">
          <div class="wizard__fields">
            <div class="wizard__field">
              <label
                class="wizard__label"
                for="assumption-name"
              ><span class="wizard__required">*</span> Name</label>
              <v-text-field
                id="assumption-name"
                v-model="name"
                placeholder="What the assumption is called"
              />
            </div>

            <div class="wizard__field">
              <label
                class="wizard__label"
                for="assumption-party"
              ><span class="wizard__required">*</span> Proposing party</label>
              <v-combobox
                id="assumption-party"
                v-model="proposingParty"
                :items="knownParties"
                placeholder="Who is proposing it"
              />
            </div>

            <div class="wizard__field">
              <label
                class="wizard__label"
                for="assumption-industries"
              >Industries</label>
              <v-select
                id="assumption-industries"
                v-model="industryNames"
                :items="industryOptions"
                placeholder="Which industries it belongs to"
                multiple
                chips
                clearable
              />
            </div>

            <div class="wizard__field">
              <label
                class="wizard__label"
                for="assumption-tags"
              >Tags</label>
              <v-combobox
                id="assumption-tags"
                v-model="tags"
                :items="knownTags"
                :placeholder="ENTER_TO_ADD_HINT"
                multiple
                chips
                closable-chips
              />
            </div>

            <div class="wizard__field">
              <label
                class="wizard__label"
                for="assumption-validators"
              >Validation responsible parties</label>
              <v-combobox
                id="assumption-validators"
                v-model="validators"
                :items="knownValidators"
                :placeholder="ENTER_TO_ADD_HINT"
                multiple
                chips
                closable-chips
              />
            </div>
          </div>

          <div class="wizard__field">
            <label
              class="wizard__label"
              for="assumption-text"
            ><span class="wizard__required">*</span> Assumption</label>
            <v-textarea
              id="assumption-text"
              v-model="assumptionText"
              placeholder="State the condition, the figure or the behaviour being taken as true…"
              rows="4"
              auto-grow
            />
          </div>
        </template>

        <template v-else>
          <div class="wizard__field">
            <label
              class="wizard__label"
              for="assumption-schemas"
            >
              <span class="wizard__required">*</span> Schemas
              <UiInfoIcon text="A schema declares the attributes this assumption carries. Picking one adds its fields below." />
            </label>
            <v-select
              id="assumption-schemas"
              v-model="schemaIds"
              :items="schemaOptions"
              placeholder="Which schemas declare this assumption"
              multiple
              chips
              clearable
            />
          </div>

          <v-alert
            v-if="schemaIds.length === 0"
            type="info"
            variant="tonal"
            density="compact"
            class="wizard__note"
          >
            Pick at least one schema. Its declared attributes appear here to be filled in.
          </v-alert>

          <v-progress-linear
            v-if="loadingSchemes"
            indeterminate
            color="primary"
          />

          <SchemeFieldsForm
            v-else-if="fields.length > 0"
            :fields="fields"
            :values="values"
            :problems="problems"
            @update:values="values = $event"
          />
        </template>
      </v-card-text>

      <v-divider />

      <v-card-actions class="wizard__actions">
        <v-btn
          variant="text"
          @click="close"
        >
          Cancel
        </v-btn>
        <v-spacer />
        <v-btn
          v-if="step > 0"
          variant="outlined"
          @click="step = 0"
        >
          BACK
        </v-btn>
        <v-btn
          v-if="step === 0"
          color="primary"
          :disabled="!firstStepComplete"
          @click="step = 1"
        >
          NEXT
        </v-btn>
        <v-btn
          v-else
          color="primary"
          :loading="saving"
          :disabled="!canCreate"
          @click="create"
        >
          CREATE
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import type { JsonValue } from '@truth-platform/core-ui'

import type { AssumptionDetail } from '@/models/assumption'

interface Props {
  modelValue: boolean
  /** The assumption this one is being copied from, or nothing when it is being written from scratch. */
  duplicatedFrom?: AssumptionDetail | null
}

interface Emits {
  (event: 'update:modelValue', open: boolean): void
  (event: 'created', assumptionId: string): void
}

/** What the two stages of the wizard are called, in the order they are walked. */
const STEP_LABELS: string[] = ['Default Data', 'Schema Fields']
</script>

<script setup lang="ts">
import { ENTER_TO_ADD_HINT, UiInfoIcon, useSnackbar } from '@truth-platform/core-ui'
import { computed, ref, shallowRef, watch } from 'vue'

import SchemeFieldsForm from '@/components/SchemeFieldsForm.vue'
import { useRegister } from '@/composables/useRegister'
import type { SchemeConstraint, SchemeField } from '@/models/scheme'
import { createAssumption } from '@/requests/assumptions'
import { validateValues } from '@/utils/constraints'
import { readCreator } from '@/utils/identity'
import { mergeFields, readScheme } from '@/utils/scheme'

const props = withDefaults(defineProps<Props>(), { duplicatedFrom: null })
const emit = defineEmits<Emits>()

const { industries, schemas, assumptions, readSchemaDetail } = useRegister()
const { notify, reportError } = useSnackbar()

const step = ref<number>(0)
const saving = ref<boolean>(false)
const loadingSchemes = ref<boolean>(false)

const name = ref<string>('')
const assumptionText = ref<string>('')
const proposingParty = ref<string>('')
const industryNames = ref<string[]>([])
const tags = ref<string[]>([])
const validators = ref<string[]>([])
const schemaIds = ref<string[]>([])
const values = shallowRef<Record<string, JsonValue>>({})
const problems = ref<Record<string, string>>({})

/* The declarations of the picked schemas, read on demand and kept for as long as the dialog is open. */
const pickedFields = shallowRef<SchemeField[]>([])
const pickedConstraints = shallowRef<SchemeConstraint[]>([])

const industryOptions = computed<string[]>(() => industries.value.map((industry) => industry.name))
const schemaOptions = computed<{ title: string; value: string }[]>(() =>
  schemas.value.map((schema) => ({ title: `${schema.name} (rev ${schema.revision})`, value: schema.id })),
)

/**
 * Read one column of the register as the vocabulary a free text field offers to pick from.
 *
 * Nothing in this API declares who may propose an assumption or what it may be tagged with, so the register
 * itself is what the suggestions come from - which keeps a second spelling of the same party from creeping in.
 */
const knownValues = (read: (row: (typeof assumptions.value)[number]) => string[]): string[] => {
  const seen = new Set<string>()
  assumptions.value.forEach((row) => read(row).forEach((value) => value.length > 0 && seen.add(value)))

  return [...seen].sort((left, right) => left.localeCompare(right))
}

const knownParties = computed<string[]>(() => knownValues((row) => [row.proposing_party]))
const knownTags = computed<string[]>(() => knownValues((row) => row.tags))
const knownValidators = computed<string[]>(() => knownValues((row) => row.validation_responsible_parties))

const fields = computed<SchemeField[]>(() => pickedFields.value)

const firstStepComplete = computed<boolean>(
  () => name.value.trim().length > 0 && assumptionText.value.trim().length > 0 && proposingParty.value.trim().length > 0,
)

const canCreate = computed<boolean>(() => firstStepComplete.value && schemaIds.value.length > 0 && !saving.value)

/**
 * Read the declarations of every picked schema, so that its attributes can be filled in.
 */
const loadSchemes = async (ids: string[]): Promise<void> => {
  if (ids.length === 0) {
    pickedFields.value = []
    pickedConstraints.value = []

    return
  }

  loadingSchemes.value = true
  try {
    const details = await Promise.all(ids.map((id) => readSchemaDetail(id)))
    const schemes = details.map((detail) => readScheme(detail.scheme))
    pickedFields.value = mergeFields(schemes)
    pickedConstraints.value = schemes.flatMap((scheme) => scheme.constraints)
  } catch (error) {
    reportError(error)
  } finally {
    loadingSchemes.value = false
  }
}

watch(schemaIds, (ids) => {
  void loadSchemes(ids)
})

/**
 * Fill the form in from the assumption being copied, or empty it for one written from scratch.
 *
 * Duplicating carries everything across but the identity of the original: the copy is named as a copy so
 * that two assumptions of the same name do not appear in the register without anybody meaning them to.
 */
const reset = () => {
  const source = props.duplicatedFrom
  step.value = 0
  problems.value = {}
  saving.value = false

  if (source === null) {
    name.value = ''
    assumptionText.value = ''
    proposingParty.value = ''
    industryNames.value = []
    tags.value = []
    validators.value = []
    schemaIds.value = []
    values.value = {}

    return
  }

  name.value = `${source.name} (copy)`
  assumptionText.value = source.assumption_text
  proposingParty.value = source.proposing_party
  industryNames.value = source.industries.map((industry) => industry.name)
  tags.value = [...source.tags]
  validators.value = [...source.validation_responsible_parties]
  schemaIds.value = source.schemas.map((schema) => schema.id)
  values.value = { ...source.values }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      reset()
    }
  },
)

const close = () => {
  emit('update:modelValue', false)
}

/**
 * Store the assumption, once what was filled in satisfies the restrictions its schemas declare.
 */
const create = async () => {
  problems.value = validateValues(fields.value, pickedConstraints.value, values.value)
  if (Object.keys(problems.value).length > 0) {
    return
  }

  saving.value = true
  try {
    const assumptionId = await createAssumption({
      name: name.value.trim(),
      assumption_text: assumptionText.value.trim(),
      proposing_party: proposingParty.value.trim(),
      schemas: schemaIds.value,
      values: values.value,
      tags: tags.value,
      validation_responsible_parties: validators.value,
      creator: readCreator(),
      industries: industryNames.value,
      /* Nothing in the API says what may go in here, so it is sent as the empty object it is documented as. */
      special_fields: {},
    })

    notify(`${name.value.trim()} was created`, 'success')
    emit('created', assumptionId)
    close()
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.wizard {
  display: flex;
  flex-direction: column;
}

/*
 * The two stages are drawn as dots on a rail, which is the progress indicator of the design. The rail sits
 * behind them rather than between them, so the dots keep their spacing whatever the labels are.
 */
.wizard__steps {
  position: relative;
  display: flex;
  justify-content: center;
  gap: 22%;
  padding-block: 1.25rem 0.5rem;
}

.wizard__step {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
}

.wizard__dot {
  inline-size: 1rem;
  block-size: 1rem;
  border-radius: 50%;
  background-color: rgb(var(--v-theme-control-border));
  transition: background-color 0.2s ease-in-out;
}

.wizard__dot--active {
  background-color: rgb(var(--v-theme-primary));
}

.wizard__step-label {
  font-size: 0.75rem;
  color: rgb(var(--v-theme-app-muted));
}

.wizard__rail {
  position: absolute;
  inset-block-start: 1.75rem;
  /* Centred on the row so that it runs between the two dots whatever their labels are called. */
  inset-inline-start: 50%;
  transform: translateX(-50%);
  inline-size: 30%;
  block-size: 0.0625rem;
  background-color: rgb(var(--v-theme-control-border));
}

.wizard__title {
  text-align: center;
  font-size: 1.5rem;
  font-weight: 700;
}

.wizard__body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/*
 * The fields flow into as many columns as the dialog has room for, so the form is one column on a laptop in
 * a narrow window and four across on a wide screen without either being written down as a breakpoint.
 */
.wizard__fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: 0.875rem 1rem;
}

.wizard__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-inline-size: 0;
}

.wizard__label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 500;
}

.wizard__required {
  color: rgb(var(--v-theme-error));
}

.wizard__note {
  font-size: 0.875rem;
}

.wizard__actions {
  padding-inline: 1.5rem;
  padding-block: 0.75rem;
}
</style>
