<template>
  <div class="dynamic-field">
    <label
      class="dynamic-field__label"
      :for="inputId"
    >
      <span
        v-if="field.required"
        class="dynamic-field__required"
      >*</span>
      {{ field.name }}
      <span
        v-if="field.metadata.unit !== null"
        class="dynamic-field__unit"
      >({{ field.metadata.unit }})</span>
      <!--
        The explanation a field was declared with belongs next to the field, not in a manual. It rides on
        the information icon so it costs no room until somebody wants it.
      -->
      <SkyInfoIcon
        v-if="helpText.length > 0"
        :label="`What ${field.name} means`"
      >
        {{ helpText }}
      </SkyInfoIcon>
    </label>

    <v-select
      v-if="field.type === 'enum'"
      :id="inputId"
      :model-value="selectValue"
      :items="field.metadata.options"
      :multiple="field.array"
      :placeholder="placeholder"
      :rules="rules"
      @update:model-value="onSelect"
    />

    <v-checkbox
      v-else-if="field.type === 'boolean'"
      :id="inputId"
      :model-value="modelValue === true"
      hide-details
      @update:model-value="emit('update:modelValue', $event ?? false)"
    />

    <v-textarea
      v-else-if="field.type === 'text'"
      :id="inputId"
      :model-value="stringValue"
      :placeholder="placeholder"
      rows="3"
      :rules="rules"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <v-text-field
      v-else
      :id="inputId"
      :model-value="stringValue"
      :type="inputType"
      :placeholder="placeholder"
      :rules="rules"
      @update:model-value="onText"
    />
  </div>
</template>

<script lang="ts">
import type { JsonValue } from '@/models/common'
import { SkyInfoIcon } from '@skyscanner/sky-ui'
import type { FieldDefinition } from '@/models/field'

interface Props {
  field: FieldDefinition
  modelValue: JsonValue
}

interface Emits {
  (event: 'update:modelValue', value: JsonValue): void
}

type ValidationRule = (value: string | number | null) => true | string
</script>

<script setup lang="ts">
import { computed } from 'vue'


const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const inputId = computed<string>(() => `field-${props.field.key}`)

const helpText = computed<string>(() => props.field.metadata.description ?? '')

const inputType = computed<string>(() => {
  switch (props.field.type) {
    case 'number':
    case 'integer':
      return 'number'
    case 'date':
      return 'date'
    case 'datetime':
      return 'datetime-local'
    default:
      return 'text'
  }
})

/*
 * A placeholder is read inside the box it sits in and is clipped the moment it grows past it, so it stays a
 * short instruction. What the field means is explained on the information icon of the label instead, where
 * there is room for a whole sentence.
 */
const placeholder = computed<string>(() => props.field.metadata.placeholder ?? `Enter ${props.field.name}`)

const selectValue = computed<string | string[] | null>(() => {
  const value = props.modelValue
  if (value === null || value === undefined) {
    return props.field.array ? [] : null
  }

  return Array.isArray(value) ? value.map((item) => String(item)) : String(value)
})

const onSelect = (value: string | readonly string[] | null) => {
  if (value === null) {
    emit('update:modelValue', null)
    return
  }

  emit('update:modelValue', Array.isArray(value) ? [...value] : String(value))
}

const stringValue = computed<string>(() => {
  const value = props.modelValue

  return value === null || value === undefined ? '' : String(value)
})

const rules = computed<ValidationRule[]>(() => {
  if (!props.field.required) {
    return []
  }

  return [(value) => (value !== null && String(value).length > 0) || `${props.field.name} is required`]
})

const onText = (value: string) => {
  if (props.field.type === 'number' || props.field.type === 'integer') {
    emit('update:modelValue', value.length === 0 ? null : Number(value))
    return
  }

  emit('update:modelValue', value)
}
</script>

<style scoped>
.dynamic-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  min-inline-size: 0;
}

.dynamic-field__label {
  font-size: 0.875rem;
}

.dynamic-field__required {
  color: rgb(var(--v-theme-error));
  margin-inline-end: 0.125rem;
}

.dynamic-field__unit {
  opacity: 0.65;
  font-size: 0.75rem;
}
</style>
