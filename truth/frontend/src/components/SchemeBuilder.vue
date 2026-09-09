<template>
  <div class="builder">
    <div class="builder__head">
      <h3 class="builder__title">
        {{ t('schemas.attributes') }}
      </h3>
      <v-btn
        variant="tonal"
        size="small"
        prepend-icon="mdi-plus"
        @click="addField"
      >
        {{ t('schemas.addAttribute') }}
      </v-btn>
    </div>

    <p
      v-if="scheme.fields.length === 0"
      class="builder__empty"
    >
      {{ t('schemas.firstAttribute') }}
    </p>

    <div
      v-for="(field, index) in scheme.fields"
      :key="index"
      class="builder__field"
    >
      <div class="builder__row">
        <v-text-field
          :model-value="field.key"
          :label="t('schemas.key')"
          :placeholder="t('schemas.keyPlaceholder')"
          density="compact"
          :error-messages="keyProblem(field, index)"
          @update:model-value="updateField(index, { key: $event, displayName: nameFor(field, $event) })"
        />
        <v-text-field
          :model-value="field.displayName"
          :label="t('schemas.displayName')"
          density="compact"
          @update:model-value="updateField(index, { displayName: $event })"
        />
        <!--
          The Hebrew name of a declared attribute can only come from the declaration, because the attribute
          itself is somebody's own vocabulary rather than one this client ships words for. A schema that
          leaves this empty keeps its declared name in both languages, which is the honest answer.
        -->
        <v-text-field
          :model-value="field.displayNameHebrew"
          :label="t('schemas.hebrewName')"
          :hint="t('schemas.hebrewNameHint')"
          density="compact"
          dir="rtl"
          @update:model-value="updateField(index, { displayNameHebrew: $event })"
        />
        <v-select
          :model-value="field.type"
          :items="typeOptions(field.type)"
          :label="t('schemas.type')"
          density="compact"
          @update:model-value="changeType(index, $event)"
        />
        <div class="builder__flags">
          <v-checkbox
            :model-value="field.required"
            :label="t('schemas.required')"
            density="compact"
            hide-details
            @update:model-value="updateField(index, { required: $event === true })"
          />
          <v-checkbox
            :model-value="field.array"
            :label="t('schemas.many')"
            density="compact"
            hide-details
            @update:model-value="updateField(index, { array: $event === true })"
          />
          <v-btn
            icon="mdi-delete-outline"
            variant="text"
            size="small"
            :aria-label="
              t('schemas.removeAttribute', {
                name: field.displayName.length > 0 ? field.displayName : t('schemas.thisAttribute'),
              })
            "
            @click="removeField(index)"
          />
        </div>
      </div>

      <!-- What one kind of attribute needs beyond the five keys every attribute carries. -->
      <v-combobox
        v-if="field.type === 'enum'"
        :model-value="field.options"
        :label="t('schemas.options')"
        :placeholder="t('input.enterToAdd')"
        density="compact"
        :error-messages="field.options.length === 0 ? t('schemas.optionsRequired') : undefined"
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
          :label="t('schemas.min')"
          type="number"
          density="compact"
          :hint="t('schemas.optional')"
          persistent-hint
          @update:model-value="updateField(index, { min: asNumber(field.type, $event) })"
        />
        <v-text-field
          :model-value="asText(field.max)"
          :label="t('schemas.max')"
          type="number"
          density="compact"
          :hint="t('schemas.optional')"
          persistent-hint
          @update:model-value="updateField(index, { max: asNumber(field.type, $event) })"
        />
        <v-text-field
          :model-value="asText(field.step)"
          :label="t('schemas.step')"
          type="number"
          density="compact"
          :hint="t('schemas.optional')"
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
      {{ t('schemas.constraintsNote') }}
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

/**
 * The kinds of attribute this builder offers when a new one is declared.
 *
 * The values are the spellings that travel on the wire and never change; only what each is called on screen
 * is looked up, so a schema declared in Hebrew stores exactly the same types as one declared in English.
 *
 * The service accepts two kinds that are deliberately not here - an ultra enum and a multi field - because
 * what they carry beyond the five keys every field has is not written down yet, and a picker that offered
 * them would let somebody declare one that is missing whatever those are. They are still read, still shown,
 * and still written back exactly as they were found; they simply cannot be invented here yet.
 */
const OFFERED_TYPES: SchemeFieldType[] = [
  'string',
  'boolean',
  'confined_number',
  'confined_float',
  'enum',
  'date',
]

/** What each offered kind is called on screen. */
const TYPE_LABELS: Record<string, string> = {
  string: 'type.text',
  boolean: 'type.boolean',
  confined_number: 'type.integer',
  confined_float: 'type.decimal',
  enum: 'type.enum',
  ultra_enum: 'type.ultraEnum',
  date: 'type.date',
  multi_field: 'type.multiField',
}

/**
 * The kinds one field may be set to: the ones this builder offers, and the one the field already is.
 *
 * A field declared elsewhere as a kind this builder does not offer would otherwise open with an empty
 * picker - and a picker showing nothing is one keystroke away from writing that nothing back, which is how
 * a revision quietly turns somebody's multi field into a line of text. Its own kind is therefore always
 * among the choices, so it displays as what it is and stays that unless somebody deliberately changes it.
 */
const typeOptions = (current: SchemeFieldType): { title: string; value: SchemeFieldType }[] => {
  const offered = OFFERED_TYPES.includes(current) ? OFFERED_TYPES : [...OFFERED_TYPES, current]

  return offered.map((type) => ({ title: translate(TYPE_LABELS[type] ?? type), value: type }))
}
</script>

<script setup lang="ts">
import { humanizeKey, translate, useLanguage } from '@truth-platform/core-ui'

import { isNumeric } from '@/utils/scheme'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useLanguage()

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
    return t('schemas.keyRequired')
  }

  const duplicated = props.scheme.fields.some(
    (candidate, at) => at !== index && candidate.key.trim() === field.key.trim(),
  )

  return duplicated ? t('schemas.keyDuplicated') : undefined
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
      displayNameHebrew: '',
      /* A field declared here is this client's own, so it carries nothing it does not know about. */
      extras: {},
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
