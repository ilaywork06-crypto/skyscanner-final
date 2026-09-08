<template>
  <div class="builder">
    <div class="builder__head">
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
      <div class="builder__row">
        <v-text-field
          :model-value="field.key"
          label="Key"
          placeholder="stored_under"
          density="compact"
          :error-messages="keyProblem(field, index)"
          @update:model-value="updateField(index, { key: $event, displayName: nameFor(field, $event) })"
        />
        <v-text-field
          :model-value="field.displayName"
          label="Display name"
          density="compact"
          @update:model-value="updateField(index, { displayName: $event })"
        />
        <v-select
          :model-value="field.type"
          :items="TYPE_OPTIONS"
          label="Type"
          density="compact"
          @update:model-value="changeType(index, $event)"
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
            :aria-label="`Remove ${field.displayName.length > 0 ? field.displayName : 'this attribute'}`"
            @click="removeField(index)"
          />
        </div>
      </div>

      <!-- What one kind of attribute needs beyond the five keys every attribute carries. -->
      <v-combobox
        v-if="field.type === 'enum'"
        :model-value="field.options"
        label="Options"
        :placeholder="ENTER_TO_ADD_HINT"
        density="compact"
        :error-messages="field.options.length === 0 ? 'An enumeration needs at least one option' : undefined"
        multiple
        chips
        closable-chips
        @update:model-value="updateField(index, { options: $event.map((option) => String(option)) })"
      />

      <div
        v-else-if="isNumeric(field.type)"
        class="builder__row"
      >
        <v-text-field
          :model-value="asText(field.min)"
          label="Min"
          type="number"
          density="compact"
          hint="Optional"
          persistent-hint
          @update:model-value="updateField(index, { min: asNumber(field.type, $event) })"
        />
        <v-text-field
          :model-value="asText(field.max)"
          label="Max"
          type="number"
          density="compact"
          hint="Optional"
          persistent-hint
          @update:model-value="updateField(index, { max: asNumber(field.type, $event) })"
        />
        <v-text-field
          :model-value="asText(field.step)"
          label="Step"
          type="number"
          density="compact"
          hint="Optional"
          persistent-hint
          @update:model-value="updateField(index, { step: asNumber(field.type, $event) })"
        />
      </div>
    </div>

    <!--
      Constraints are not declared here because the service does not support them yet, and an empty list is
      what every scheme is written with. Saying so is better than an editor whose contents are dropped.
    -->
    <p class="builder__note">
      Constraints are not supported by the service yet, so a schema is stored without them. What a field is
      required to hold, what it may be chosen from and what a number is bounded by are all declared above.
    </p>
  </div>
</template>

<script lang="ts">
import type { Scheme, SchemeField, SchemeFieldType } from '@/models/scheme'

interface Props {
  scheme: Scheme
}

interface Emits {
  (event: 'update:scheme', scheme: Scheme): void
}

/** The kinds of attribute the service accepts, with the name each one is offered under. */
const TYPE_OPTIONS: { title: string; value: SchemeFieldType }[] = [
  { title: 'Text', value: 'string' },
  { title: 'Yes / no', value: 'boolean' },
  { title: 'Whole number', value: 'confined_number' },
  { title: 'Decimal number', value: 'confined_float' },
  { title: 'One of a list', value: 'enum' },
  { title: 'Date', value: 'date' },
]
</script>

<script setup lang="ts">
import { ENTER_TO_ADD_HINT, humanizeKey } from '@truth-platform/core-ui'

import { isNumeric } from '@/utils/scheme'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

/**
 * Keep the display name following the key until somebody writes a name of their own.
 */
const nameFor = (field: SchemeField, key: string): string =>
  field.displayName.length === 0 || field.displayName === humanizeKey(field.key)
    ? humanizeKey(key)
    : field.displayName

/**
 * Say what is wrong with a key, so that a schema is not declared with an attribute nothing can be stored under.
 */
const keyProblem = (field: SchemeField, index: number): string | undefined => {
  if (field.key.trim().length === 0) {
    return 'A key is required'
  }

  const duplicated = props.scheme.fields.some(
    (candidate, at) => at !== index && candidate.key.trim() === field.key.trim(),
  )

  return duplicated ? 'Another attribute already uses this key' : undefined
}

/**
 * Render a bound as the text its input shows, leaving one that was never set empty.
 */
const asText = (value: number | null): string => (value === null ? '' : String(value))

/**
 * Read a typed bound, keeping a whole number whole and refusing anything that is not a number at all.
 */
const asNumber = (type: SchemeFieldType, typed: string): number | null => {
  if (typed.trim().length === 0) {
    return null
  }

  const parsed = Number(typed)
  if (Number.isNaN(parsed)) {
    return null
  }

  return type === 'confined_number' ? Math.round(parsed) : parsed
}

const emitFields = (fields: SchemeField[]) => {
  emit('update:scheme', { fields })
}

const addField = () => {
  emitFields([
    ...props.scheme.fields,
    {
      key: '',
      displayName: '',
      type: 'string',
      required: false,
      array: false,
      options: [],
      min: null,
      max: null,
      step: null,
      order: props.scheme.fields.length,
    },
  ])
}

const updateField = (index: number, change: Partial<SchemeField>) => {
  emitFields(props.scheme.fields.map((field, at) => (at === index ? { ...field, ...change } : field)))
}

/**
 * Change what kind of attribute one field is, dropping whatever the previous kind carried.
 *
 * The bounds of a number mean nothing to an enumeration and its options mean nothing to a number, so they
 * are cleared rather than kept and written out alongside a type that never asked for them.
 */
const changeType = (index: number, type: SchemeFieldType) => {
  updateField(index, { type, options: [], min: null, max: null, step: null })
}

const removeField = (index: number) => {
  emitFields(props.scheme.fields.filter((_, at) => at !== index))
}
</script>

<style scoped>
.builder {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.builder__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.builder__title {
  font-size: 0.9375rem;
  font-weight: 600;
}

.builder__empty,
.builder__note {
  color: rgb(var(--v-theme-app-muted));
  font-size: 0.8125rem;
  line-height: 1.5;
}

.builder__field {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 0.75rem;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
}

/*
 * One attribute is a row of inputs that wraps rather than a fixed grid, so a narrow window stacks it into a
 * legible column instead of squeezing five inputs into the width of one.
 */
.builder__row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.5rem;
}

.builder__row > * {
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
