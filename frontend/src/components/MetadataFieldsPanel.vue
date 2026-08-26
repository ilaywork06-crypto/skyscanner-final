<template>
  <!--
    The one place metadata is filled in, wherever it is being filled in. It reads as the two halves the
    schema describes: the fields of the object itself, and underneath them the additional data, which the
    schema declares key by key exactly as it declares the half above it.
  -->
  <section class="metadata-panel">
    <header class="metadata-panel__head">
      <v-icon
        size="small"
        icon="mdi-tag-multiple-outline"
      />
      <h3 class="metadata-panel__title">
        {{ title }}
      </h3>
      <span class="metadata-panel__count">{{ filledCount }} filled</span>
    </header>

    <div
      v-if="visibleFields.length > 0"
      class="metadata-panel__grid"
    >
      <DynamicFieldInput
        v-for="field in visibleFields"
        :key="field.id"
        :field="field"
        :model-value="modelValue[field.key] ?? null"
        @update:model-value="patch(field, $event)"
      />
    </div>

    <p
      v-else-if="ownFields.length === 0"
      class="metadata-panel__empty"
    >
      {{ NOTHING_DECLARED }}
    </p>

    <p
      v-else
      class="metadata-panel__empty"
    >
      None of the declared fields apply to what has been filled in so far.
    </p>

    <div class="metadata-panel__additional">
      <span class="metadata-panel__additional-title">Additional data</span>

      <!--
        The declared half of the additional data. Declaring these keys is what makes two people describing
        the same kind of entity write the same thing, so they are asked for exactly like any other field.
        A key invented on the spot used to be accepted here too, which is where a column nobody remembered
        creating came from - so the block is a form now rather than a blank sheet.
      -->
      <div
        v-if="visibleAdditionalFields.length > 0"
        class="metadata-panel__grid"
      >
        <DynamicFieldInput
          v-for="field in visibleAdditionalFields"
          :key="field.id"
          :field="field"
          :model-value="modelValue[field.key] ?? null"
          @update:model-value="patch(field, $event)"
        />
      </div>

      <p
        v-else
        class="metadata-panel__empty"
      >
        {{ additionalFields.length > 0 ? NONE_APPLY : NOTHING_DECLARED }}
      </p>

      <!--
        Values that reached this object under a key no declaration covers - written before the rule existed,
        or by a script. They are shown rather than dropped, because an edit must never silently lose what is
        already stored, and they are read only because there is no declaration to measure a new value
        against. Taking one off is the way out, and declaring the field for it is the way to keep it.
      -->
      <div
        v-if="legacyEntries.length > 0"
        class="metadata-panel__legacy"
      >
        <p class="metadata-panel__legacy-head">
          <v-icon
            size="x-small"
            icon="mdi-alert-outline"
          />
          Recorded under keys nothing declares. Declare them on the Schema page to keep filling them in, or
          take them off here.
        </p>
        <div
          v-for="entry in legacyEntries"
          :key="entry.key"
          class="metadata-panel__legacy-row"
        >
          <code class="metadata-panel__legacy-key">{{ entry.key }}</code>
          <span class="metadata-panel__legacy-value">{{ entry.display }}</span>
          <v-btn
            size="x-small"
            variant="text"
            :aria-label="`Remove ${entry.key}`"
            @click="removeLegacy(entry.key)"
          >
            REMOVE
          </v-btn>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import type { FieldType, JsonValue } from '@/models/common'
import { EMPTY_PLACEHOLDER } from '@skyscanner/sky-ui'
import type { FieldDefinition } from '@/models/field'

interface Props {
  modelValue: Record<string, JsonValue>
  /** The type every value was recorded under, which a value stored before its declaration carries with it. */
  types?: Record<string, FieldType>
  fields: FieldDefinition[]
  title?: string
  /**
   * The values of the object these fields hang off, so that a field may depend on one of them: an entity
   * field asked for only when the event it belongs to says something in particular. The panel itself never
   * reads it, it only hands it to the rule that decides which fields apply.
   */
  context?: Record<string, JsonValue>
}

interface Emits {
  (event: 'update:modelValue', value: Record<string, JsonValue>): void
  (event: 'update:types', value: Record<string, FieldType>): void
}

/**
 * The shape the dependency rule is read through.
 *
 * The helper is being widened to take the owning object's values as a third argument, and a function that
 * accepts fewer arguments satisfies a type that offers more. Declaring the call this way therefore lets the
 * panel forward the context today and start honouring it the day the helper reads it, with nothing to change
 * here in between.
 */
type FieldFilter = (
  fields: FieldDefinition[],
  values: Record<string, JsonValue>,
  context?: Record<string, JsonValue>,
) => FieldDefinition[]

/** One value stored under a key no declaration covers, as the panel reads it back. */
interface LegacyEntry {
  key: string
  display: string
}

const NOTHING_DECLARED =
  'No field is declared for this yet. Declare one on the Schema page and it is asked for here.'

const NONE_APPLY = 'None of the declared fields apply to what has been filled in so far.'
</script>

<script setup lang="ts">
import { computed } from 'vue'

import DynamicFieldInput from '@/components/DynamicFieldInput.vue'
import { applicableFields } from '@/utils/dependencies'

const props = withDefaults(defineProps<Props>(), {
  title: 'Metadata fields',
  types: () => ({}),
  context: () => ({}),
})
const emit = defineEmits<Emits>()

const ownFields = computed<FieldDefinition[]>(() => props.fields.filter((field) => !field.additional))

const additionalFields = computed<FieldDefinition[]>(() => props.fields.filter((field) => field.additional))

const declaredKeys = computed<Set<string>>(() => new Set(props.fields.map((field) => field.key)))

const filterFields: FieldFilter = applicableFields

const visibleFields = computed<FieldDefinition[]>(() =>
  filterFields(ownFields.value, props.modelValue, props.context),
)

const visibleAdditionalFields = computed<FieldDefinition[]>(() =>
  filterFields(additionalFields.value, props.modelValue, props.context),
)

const filledCount = computed<number>(
  () =>
    Object.entries(props.modelValue).filter(
      ([, value]) => value !== null && value !== undefined && value !== '',
    ).length,
)

/** Render one stored value as the single line the read only row shows. */
const describe = (value: JsonValue): string => {
  if (value === null || value === undefined || value === '') {
    return EMPTY_PLACEHOLDER
  }

  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

const legacyEntries = computed<LegacyEntry[]>(() =>
  Object.entries(props.modelValue)
    .filter(([key]) => !declaredKeys.value.has(key))
    .map(([key, value]) => ({ key, display: describe(value) })),
)

/*
 * The type a value is stored under is the type its declaration names, rather than something chosen beside
 * the value, which is what makes a number come back a number however the input handed it over.
 */
const patch = (field: FieldDefinition, value: JsonValue) => {
  emit('update:modelValue', { ...props.modelValue, [field.key]: value })
  emit('update:types', { ...props.types, [field.key]: field.type })
}

const removeLegacy = (key: string) => {
  const values = { ...props.modelValue }
  const types = { ...props.types }
  delete values[key]
  delete types[key]
  emit('update:modelValue', values)
  emit('update:types', types)
}
</script>

<style scoped>
.metadata-panel {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  border: 0.0625rem solid rgb(var(--v-theme-app-border));
  border-radius: 0.75rem;
  padding: 1rem;
}

.metadata-panel__head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.metadata-panel__title {
  font-size: 0.9375rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.metadata-panel__count {
  margin-inline-start: auto;
  font-size: 0.75rem;
  opacity: 0.6;
}

.metadata-panel__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 1rem;
}

.metadata-panel__empty {
  font-size: 0.8125rem;
  opacity: 0.7;
}

.metadata-panel__additional {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border-block-start: 0.0625rem solid rgb(var(--v-theme-app-border));
  padding-block-start: 0.875rem;
}

.metadata-panel__additional-title {
  font-size: 0.875rem;
  font-weight: 600;
}

.metadata-panel__legacy {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  border: 0.0625rem dashed rgb(var(--v-theme-app-border));
  border-radius: 0.5rem;
  padding: 0.75rem;
}

.metadata-panel__legacy-head {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  opacity: 0.75;
}

/* One stored value reads across the row: the key it was written under and what it holds. */
.metadata-panel__legacy-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) auto;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.metadata-panel__legacy-key,
.metadata-panel__legacy-value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 48rem) {
  .metadata-panel__legacy-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }
}
</style>
