<template>
  <div class="scheme-form">
    <p
      v-if="fields.length === 0"
      class="scheme-form__empty"
    >
      This schema declares no attributes, so there is nothing to fill in for it.
    </p>

    <div
      v-for="group in groups"
      :key="group.name"
      class="scheme-form__group"
    >
      <h4
        v-if="group.name.length > 0"
        class="scheme-form__group-title"
      >
        {{ group.name }}
      </h4>

      <div class="scheme-form__fields">
        <div
          v-for="field in group.fields"
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
            {{ field.label }}
            <UiInfoIcon
              v-if="field.description !== null"
              :text="field.description"
            />
            <span
              v-if="field.unit !== null"
              class="scheme-form__unit"
            >({{ field.unit }})</span>
          </label>

          <!-- An enumerated field picks from the vocabulary its schema declared, one value or several. -->
          <v-select
            v-if="field.type === 'enum' && field.options.length > 0"
            :id="`field-${field.key}`"
            :model-value="asChoice(values[field.key], field.array)"
            :items="field.options"
            :multiple="field.array"
            :chips="field.array"
            :placeholder="field.placeholder ?? 'Select'"
            :error-messages="problems[field.key]"
            clearable
            @update:model-value="update(field.key, toJson($event))"
          />

          <!-- A field of several free values collects them as chips rather than as one comma separated line. -->
          <v-combobox
            v-else-if="field.array"
            :id="`field-${field.key}`"
            :model-value="asArray(values[field.key])"
            :items="field.options"
            :placeholder="field.placeholder ?? ENTER_TO_ADD_HINT"
            :error-messages="problems[field.key]"
            multiple
            chips
            closable-chips
            @update:model-value="update(field.key, toJson($event))"
          />

          <v-textarea
            v-else-if="field.type === 'text' || field.type === 'json'"
            :id="`field-${field.key}`"
            :model-value="asText(values[field.key])"
            :placeholder="field.placeholder ?? 'Type here…'"
            :error-messages="problems[field.key]"
            rows="3"
            auto-grow
            @update:model-value="update(field.key, $event)"
          />

          <v-checkbox
            v-else-if="field.type === 'boolean'"
            :id="`field-${field.key}`"
            :model-value="values[field.key] === true"
            :error-messages="problems[field.key]"
            density="compact"
            hide-details="auto"
            @update:model-value="update(field.key, $event === true)"
          />

          <v-text-field
            v-else
            :id="`field-${field.key}`"
            :model-value="asText(values[field.key])"
            :type="inputType(field.type)"
            :placeholder="field.placeholder ?? 'Type here…'"
            :error-messages="problems[field.key]"
            @update:model-value="update(field.key, castValue(field.type, $event))"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import type { FieldType, JsonValue } from '@truth-platform/core-ui'

import type { SchemeField } from '@/models/scheme'

interface Props {
  fields: SchemeField[]
  values: Record<string, JsonValue>
  problems?: Record<string, string>
}

interface Emits {
  (event: 'update:values', values: Record<string, JsonValue>): void
}

/** The fields of one section of the form, or of the unnamed section everything ungrouped falls into. */
interface FieldGroup {
  name: string
  fields: SchemeField[]
}

/** Which browser input each kind of value is typed into, where it is a plain one. */
const INPUT_TYPES: Partial<Record<FieldType, string>> = {
  number: 'number',
  integer: 'number',
  date: 'date',
  datetime: 'datetime-local',
}
</script>

<script setup lang="ts">
import { ENTER_TO_ADD_HINT, UiInfoIcon } from '@truth-platform/core-ui'
import { computed } from 'vue'

const props = withDefaults(defineProps<Props>(), { problems: () => ({}) })
const emit = defineEmits<Emits>()

/**
 * Lay the fields out in the sections their schema filed them under, keeping the ungrouped ones first.
 */
const groups = computed<FieldGroup[]>(() => {
  const collected = new Map<string, SchemeField[]>()
  props.fields.forEach((field) => {
    const name = field.group ?? ''
    collected.set(name, [...(collected.get(name) ?? []), field])
  })

  return [...collected.entries()]
    .sort(([left], [right]) => (left.length === 0 ? -1 : right.length === 0 ? 1 : left.localeCompare(right)))
    .map(([name, fields]) => ({ name, fields }))
})

const inputType = (type: FieldType): string => INPUT_TYPES[type] ?? 'text'

/**
 * Render one held value as the text an input shows.
 */
const asText = (value: JsonValue | undefined): string => {
  if (value === null || value === undefined) {
    return ''
  }

  return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
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
 * Read one held value as the list a multi valued input shows.
 */
const asArray = (value: JsonValue | undefined): string[] => {
  if (Array.isArray(value)) {
    return value.map((item) => String(item))
  }

  return value === null || value === undefined || value === '' ? [] : [String(value)]
}

/**
 * Turn what was typed into the kind of value the field declared, so a number is stored as one.
 *
 * A number that has not finished being typed - "1." on the way to "1.5", or a lone minus sign - is kept as
 * the text it currently is rather than being thrown away, and becomes a number as soon as it reads as one.
 */
const castValue = (type: FieldType, typed: string): JsonValue => {
  if (typed.length === 0) {
    return null
  }

  if (type === 'number' || type === 'integer') {
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

.scheme-form__group {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.scheme-form__group-title {
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgb(var(--v-theme-app-muted));
}

/*
 * The fields flow into as many columns as the dialog has room for, which is what keeps a schema of a dozen
 * attributes from becoming a dozen rows of one input each on a wide screen.
 */
.scheme-form__fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
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

.scheme-form__unit {
  color: rgb(var(--v-theme-app-muted));
  font-weight: 400;
}
</style>
