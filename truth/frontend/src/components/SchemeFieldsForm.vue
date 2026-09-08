<template>
  <div class="scheme-form">
    <p
      v-if="fields.length === 0"
      class="scheme-form__empty"
    >
      This schema declares no attributes, so there is nothing to fill in for it.
    </p>

    <div class="scheme-form__fields">
      <div
        v-for="field in fields"
        :key="field.key"
        class="scheme-form__field"
      >
        <label
          class="scheme-form__label"
          :for="`field-${field.key}`"
        >
          <span
            v-if="field.required"
            class="scheme-form__required"
            aria-hidden="true"
          >*</span>
          {{ field.displayName }}
          <span
            v-if="boundsOf(field).length > 0"
            class="scheme-form__bounds"
          >({{ boundsOf(field) }})</span>
        </label>

        <!-- An enumerated field picks from the vocabulary its schema declared, one value or several. -->
        <v-select
          v-if="field.type === 'enum'"
          :id="`field-${field.key}`"
          :model-value="asChoice(values[field.key], field.array)"
          :items="field.options"
          :multiple="field.array"
          :chips="field.array"
          placeholder="Select"
          :error-messages="problems[field.key]"
          clearable
          @update:model-value="update(field.key, toJson($event))"
        />

        <!-- Yes or no, which is a single box whatever else the form is made of. -->
        <v-checkbox
          v-else-if="field.type === 'boolean' && !field.array"
          :id="`field-${field.key}`"
          :model-value="values[field.key] === true"
          :error-messages="problems[field.key]"
          density="compact"
          hide-details="auto"
          @update:model-value="update(field.key, $event === true)"
        />

        <!-- A field of several free values collects them as chips rather than as one comma separated line. -->
        <v-combobox
          v-else-if="field.array"
          :id="`field-${field.key}`"
          :model-value="asArray(values[field.key])"
          :placeholder="ENTER_TO_ADD_HINT"
          :error-messages="problems[field.key]"
          multiple
          chips
          closable-chips
          @update:model-value="update(field.key, toTypedArray(field, $event))"
        />

        <!--
          A confined number carries its own bounds and increment into the input, so the browser's own
          stepper moves it the way the schema declared rather than by one at a time.
        -->
        <v-text-field
          v-else
          :id="`field-${field.key}`"
          :model-value="asText(values[field.key])"
          :type="inputType(field.type)"
          :min="field.min ?? undefined"
          :max="field.max ?? undefined"
          :step="stepOf(field)"
          placeholder="Type here…"
          :error-messages="problems[field.key]"
          @update:model-value="update(field.key, castValue(field, $event))"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import type { JsonValue } from '@truth-platform/core-ui'

import type { SchemeField, SchemeFieldType } from '@/models/scheme'

interface Props {
  fields: SchemeField[]
  values: Record<string, JsonValue>
  problems?: Record<string, string>
}

interface Emits {
  (event: 'update:values', values: Record<string, JsonValue>): void
}

/** Which browser input each kind of attribute is typed into. */
const INPUT_TYPES: Partial<Record<SchemeFieldType, string>> = {
  confined_number: 'number',
  confined_float: 'number',
  date: 'date',
}

/** What a decimal field steps by when its schema did not say, which is to say: however finely you like. */
const ANY_STEP = 'any'
</script>

<script setup lang="ts">
import { ENTER_TO_ADD_HINT } from '@truth-platform/core-ui'

import { isNumeric } from '@/utils/scheme'

const props = withDefaults(defineProps<Props>(), { problems: () => ({}) })
const emit = defineEmits<Emits>()

const inputType = (type: SchemeFieldType): string => INPUT_TYPES[type] ?? 'text'

/**
 * Say what a number is bounded by, so the reader is told before being corrected rather than after.
 */
const boundsOf = (field: SchemeField): string => {
  if (!isNumeric(field.type)) {
    return ''
  }

  const said: string[] = []
  if (field.min !== null && field.max !== null) {
    said.push(`${field.min} to ${field.max}`)
  } else if (field.min !== null) {
    said.push(`${field.min} or more`)
  } else if (field.max !== null) {
    said.push(`${field.max} or less`)
  }
  if (field.step !== null) {
    said.push(`in steps of ${field.step}`)
  }

  return said.join(', ')
}

/**
 * What the input's own stepper moves by: what the schema declared, or a whole number where it declared none.
 */
const stepOf = (field: SchemeField): string | number | undefined => {
  if (!isNumeric(field.type)) {
    return undefined
  }

  if (field.step !== null) {
    return field.step
  }

  return field.type === 'confined_number' ? 1 : ANY_STEP
}

/**
 * Render one held value as the text an input shows.
 */
const asText = (value: JsonValue | undefined): string => {
  if (value === null || value === undefined) {
    return ''
  }

  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

/**
 * Read one held value as the list a multi valued input shows.
 */
const asArray = (value: JsonValue | undefined): string[] => {
  if (Array.isArray(value)) {
    return value.map((item) => String(item))
  }

  return value === null || value === undefined || value === '' ? [] : [String(value)]
}

/**
 * Render one held value as what a picker binds to, which is one string or a list of them and nothing else.
 */
const asChoice = (value: JsonValue | undefined, array: boolean): string | string[] | null => {
  if (array) {
    return asArray(value)
  }

  return value === null || value === undefined ? null : String(value)
}

/**
 * Read back what a picker handed over, which it types more loosely than the value actually is.
 */
const toJson = (value: unknown): JsonValue => {
  if (Array.isArray(value)) {
    return value.map((item) => String(item))
  }

  if (value === null || value === undefined) {
    return null
  }

  return typeof value === 'boolean' || typeof value === 'number' ? value : String(value)
}

/**
 * Store a list of typed values as the kind its field declared, so numbers come back as numbers.
 */
const toTypedArray = (field: SchemeField, typed: unknown): JsonValue => {
  const items = Array.isArray(typed) ? typed.map((item) => String(item)) : []

  if (!isNumeric(field.type)) {
    return field.type === 'boolean' ? items.map((item) => item.trim().toLowerCase() === 'true') : items
  }

  return items.map((item) => {
    const parsed = Number(item)

    return Number.isNaN(parsed) ? item : parsed
  })
}

/**
 * Turn what was typed into the kind of value the field declared, so a number is stored as one.
 *
 * A number that has not finished being typed - "1." on the way to "1.5", or a lone minus sign - is kept as
 * the text it currently is rather than being thrown away, and becomes a number as soon as it reads as one.
 */
const castValue = (field: SchemeField, typed: string): JsonValue => {
  if (typed.length === 0) {
    return null
  }

  if (isNumeric(field.type)) {
    const parsed = Number(typed)

    return Number.isNaN(parsed) ? typed : parsed
  }

  return typed
}

const update = (key: string, value: JsonValue) => {
  emit('update:values', { ...props.values, [key]: value })
}
</script>

<style scoped>
.scheme-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.scheme-form__empty {
  color: rgb(var(--v-theme-app-muted));
  font-size: 0.875rem;
}

/*
 * The fields flow into as many columns as the dialog has room for, which is what keeps a schema of a dozen
 * attributes from becoming a dozen rows of one input each on a wide screen. Each keeps its own height
 * rather than being stretched to match the tallest one beside it.
 */
.scheme-form__fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  align-items: start;
  gap: 0.875rem 1rem;
}

.scheme-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-inline-size: 0;
}

.scheme-form__label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 500;
}

.scheme-form__required {
  color: rgb(var(--v-theme-error));
}

.scheme-form__bounds {
  color: rgb(var(--v-theme-app-muted));
  font-weight: 400;
}
</style>
