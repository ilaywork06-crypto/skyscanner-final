<template>
  <div class="builder">
    <section class="builder__section">
      <div class="builder__section-head">
        <h3 class="builder__title">
          Attributes
        </h3>
        <v-btn
          variant="tonal"
          size="small"
          prepend-icon="mdi-plus"
          @click="addField"
        >
          Add attribute
        </v-btn>
      </div>

      <p
        v-if="scheme.fields.length === 0"
        class="builder__empty"
      >
        A schema declares the attributes an assumption carries. Add the first one.
      </p>

      <div
        v-for="(field, index) in scheme.fields"
        :key="index"
        class="builder__field"
      >
        <v-text-field
          :model-value="field.key"
          label="Key"
          placeholder="stored_under"
          density="compact"
          @update:model-value="updateField(index, { key: $event, label: labelFor(field, $event) })"
        />
        <v-text-field
          :model-value="field.label"
          label="Label"
          density="compact"
          @update:model-value="updateField(index, { label: $event })"
        />
        <v-select
          :model-value="field.type"
          :items="TYPE_OPTIONS"
          label="Type"
          density="compact"
          @update:model-value="updateField(index, { type: $event })"
        />
        <v-combobox
          v-if="field.type === 'enum'"
          :model-value="field.options"
          label="Options"
          :placeholder="ENTER_TO_ADD_HINT"
          density="compact"
          multiple
          chips
          closable-chips
          @update:model-value="updateField(index, { options: $event })"
        />
        <v-text-field
          v-else
          :model-value="field.unit ?? ''"
          label="Unit"
          density="compact"
          @update:model-value="updateField(index, { unit: $event.length > 0 ? $event : null })"
        />
        <div class="builder__flags">
          <v-checkbox
            :model-value="field.required"
            label="Required"
            density="compact"
            hide-details
            @update:model-value="updateField(index, { required: $event === true })"
          />
          <v-checkbox
            :model-value="field.array"
            label="Many"
            density="compact"
            hide-details
            @update:model-value="updateField(index, { array: $event === true })"
          />
          <v-btn
            icon="mdi-delete-outline"
            variant="text"
            size="small"
            :aria-label="`Remove ${field.label}`"
            @click="removeField(index)"
          />
        </div>
      </div>
    </section>

    <section class="builder__section">
      <div class="builder__section-head">
        <h3 class="builder__title">
          Constraints
        </h3>
        <v-btn
          variant="tonal"
          size="small"
          prepend-icon="mdi-plus"
          :disabled="scheme.fields.length === 0"
          @click="addConstraint"
        >
          Add constraint
        </v-btn>
      </div>

      <p
        v-if="scheme.constraints.length === 0"
        class="builder__empty"
      >
        A constraint restricts what one attribute may hold. They are checked here before an assumption is
        sent, and by the service after it.
      </p>

      <div
        v-for="(constraint, index) in scheme.constraints"
        :key="index"
        class="builder__constraint"
      >
        <v-select
          :model-value="constraint.field"
          :items="fieldKeys"
          label="Attribute"
          density="compact"
          @update:model-value="updateConstraint(index, { field: $event })"
        />
        <v-select
          :model-value="constraint.rule"
          :items="RULE_OPTIONS"
          label="Rule"
          density="compact"
          @update:model-value="updateConstraint(index, { rule: $event })"
        />
        <v-text-field
          :model-value="valueText(constraint.value)"
          label="Value"
          density="compact"
          :disabled="constraint.rule === 'required'"
          @update:model-value="updateConstraint(index, { value: parseValue(constraint.rule, $event) })"
        />
        <v-text-field
          :model-value="constraint.message ?? ''"
          label="Message"
          density="compact"
          @update:model-value="updateConstraint(index, { message: $event.length > 0 ? $event : null })"
        />
        <v-btn
          icon="mdi-delete-outline"
          variant="text"
          size="small"
          aria-label="Remove this constraint"
          @click="removeConstraint(index)"
        />
      </div>
    </section>
  </div>
</template>

<script lang="ts">
import type { FieldType, JsonValue } from '@truth-platform/core-ui'

import type { ConstraintRule, Scheme, SchemeConstraint, SchemeField } from '@/models/scheme'

interface Props {
  scheme: Scheme
}

interface Emits {
  (event: 'update:scheme', scheme: Scheme): void
}

/** The kinds of value an attribute may be declared as. */
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

/** The restrictions this client can both write and enforce. */
const RULE_OPTIONS: ConstraintRule[] = [
  'required',
  'min',
  'max',
  'min_length',
  'max_length',
  'pattern',
  'one_of',
]

/** The rules whose value is a list rather than a single one. */
const LIST_RULES: ConstraintRule[] = ['one_of']

/** The rules whose value is a number. */
const NUMBER_RULES: ConstraintRule[] = ['min', 'max', 'min_length', 'max_length']
</script>

<script setup lang="ts">
import { ENTER_TO_ADD_HINT, humanizeKey } from '@truth-platform/core-ui'
import { computed } from 'vue'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const fieldKeys = computed<string[]>(() => props.scheme.fields.map((field) => field.key).filter((key) => key.length > 0))

/**
 * Keep the label following the key until somebody writes a label of their own.
 */
const labelFor = (field: SchemeField, key: string): string =>
  field.label.length === 0 || field.label === humanizeKey(field.key) ? humanizeKey(key) : field.label

const emitFields = (fields: SchemeField[]) => {
  emit('update:scheme', { ...props.scheme, fields })
}

const emitConstraints = (constraints: SchemeConstraint[]) => {
  emit('update:scheme', { ...props.scheme, constraints })
}

const addField = () => {
  emitFields([
    ...props.scheme.fields,
    {
      key: '',
      label: '',
      type: 'string',
      array: false,
      required: false,
      default: null,
      options: [],
      description: null,
      unit: null,
      placeholder: null,
      group: null,
      order: props.scheme.fields.length,
    },
  ])
}

const updateField = (index: number, change: Partial<SchemeField>) => {
  emitFields(props.scheme.fields.map((field, at) => (at === index ? { ...field, ...change } : field)))
}

const removeField = (index: number) => {
  emitFields(props.scheme.fields.filter((_, at) => at !== index))
}

/**
 * Write one constraint back into the raw shape it is stored as, so that what is sent is what is read back.
 */
const toRaw = (constraint: Omit<SchemeConstraint, 'raw'>): SchemeConstraint => ({
  ...constraint,
  raw: {
    field: constraint.field,
    rule: constraint.rule,
    value: constraint.value,
    ...(constraint.message === null ? {} : { message: constraint.message }),
  },
})

const addConstraint = () => {
  emitConstraints([
    ...props.scheme.constraints,
    toRaw({ field: fieldKeys.value[0] ?? '', rule: 'required', value: null, message: null }),
  ])
}

const updateConstraint = (index: number, change: Partial<Omit<SchemeConstraint, 'raw'>>) => {
  emitConstraints(
    props.scheme.constraints.map((constraint, at) =>
      at === index ? toRaw({ ...constraint, ...change }) : constraint,
    ),
  )
}

const removeConstraint = (index: number) => {
  emitConstraints(props.scheme.constraints.filter((_, at) => at !== index))
}

/**
 * Render the value of a constraint as the single line it is typed on.
 */
const valueText = (value: JsonValue): string => {
  if (value === null) {
    return ''
  }

  return Array.isArray(value) ? value.map((item) => String(item)).join(', ') : String(value)
}

/**
 * Read what was typed as the kind of value the chosen rule takes.
 */
const parseValue = (rule: ConstraintRule, typed: string): JsonValue => {
  if (typed.length === 0) {
    return null
  }

  if (LIST_RULES.includes(rule)) {
    return typed
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0)
  }

  if (NUMBER_RULES.includes(rule)) {
    const parsed = Number(typed)

    return Number.isNaN(parsed) ? typed : parsed
  }

  return typed
}
</script>

<style scoped>
.builder {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.builder__section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.builder__section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.builder__title {
  font-size: 0.9375rem;
  font-weight: 600;
}

.builder__empty {
  color: rgb(var(--v-theme-app-muted));
  font-size: 0.875rem;
}

/*
 * One attribute is a row of inputs that wraps rather than a fixed grid, so a narrow window stacks it into a
 * legible column instead of squeezing six inputs into the width of one.
 */
.builder__field,
.builder__constraint {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
}

.builder__field > *,
.builder__constraint > * {
  flex: 1 1 9rem;
  min-inline-size: 0;
}

.builder__flags {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.25rem;
}
</style>
