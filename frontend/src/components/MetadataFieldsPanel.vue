<template>
  <!--
    The one place metadata is filled in, wherever it is being filled in: the declared fields of the schema
    first, and underneath them the room to record something the schema never anticipated. Both end up in the
    same value map, and both are compared field by field in the edit history.
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
        @update:model-value="patch(field.key, $event)"
      />
    </div>

    <p
      v-else-if="fields.length === 0"
      class="metadata-panel__empty"
    >
      No metadata fields are declared for this yet. Declare them on the Schema page, or record one below.
    </p>

    <p
      v-else
      class="metadata-panel__empty"
    >
      None of the declared fields apply to what has been filled in so far.
    </p>

    <div class="metadata-panel__custom">
      <div class="metadata-panel__custom-head">
        <span class="metadata-panel__custom-title">Additional metadata</span>
        <v-btn
          size="x-small"
          variant="text"
          prepend-icon="mdi-plus"
          @click="addCustom"
        >
          ADD FIELD
        </v-btn>
      </div>

      <p
        v-if="customEntries.length === 0"
        class="metadata-panel__empty"
      >
        Anything recorded here is stored and shown alongside the declared fields.
      </p>

      <div
        v-for="entry in customEntries"
        :key="entry.id"
        class="metadata-panel__custom-row"
      >
        <v-text-field
          :model-value="entry.key"
          label="Key"
          density="compact"
          hide-details
          @update:model-value="renameCustom(entry, $event)"
        />
        <v-text-field
          :model-value="String(modelValue[entry.key] ?? '')"
          label="Value"
          density="compact"
          hide-details
          @update:model-value="patch(entry.key, $event)"
        />
        <v-btn
          icon="mdi-close"
          size="x-small"
          variant="text"
          :aria-label="`Remove ${entry.key}`"
          @click="removeCustom(entry)"
        />
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import type { JsonValue } from '@/models/common'
import type { FieldDefinition } from '@/models/field'

interface Props {
  modelValue: Record<string, JsonValue>
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

/**
 * One row of the free form part of the panel.
 *
 * The row keeps an identity of its own rather than being keyed by the key the user is typing: a row keyed
 * by its own contents loses focus on every keystroke, because renaming the key replaces the row.
 */
interface CustomEntry {
  id: number
  key: string
}
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import DynamicFieldInput from '@/components/DynamicFieldInput.vue'
import { applicableFields } from '@/utils/dependencies'

const props = withDefaults(defineProps<Props>(), {
  title: 'Metadata fields',
  context: () => ({}),
})
const emit = defineEmits<Emits>()

const customEntries = ref<CustomEntry[]>([])
let nextId = 0

const declaredKeys = computed<string[]>(() => props.fields.map((field) => field.key))

const filterFields: FieldFilter = applicableFields

const visibleFields = computed<FieldDefinition[]>(() =>
  filterFields(props.fields, props.modelValue, props.context),
)

const filledCount = computed<number>(
  () =>
    Object.entries(props.modelValue).filter(
      ([, value]) => value !== null && value !== undefined && value !== '',
    ).length,
)

const patch = (key: string, value: JsonValue) => {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

const addCustom = () => {
  nextId += 1
  customEntries.value = [...customEntries.value, { id: nextId, key: '' }]
}

/**
 * Move a value from the key it was recorded under to the one the user is now typing.
 */
const renameCustom = (entry: CustomEntry, key: string) => {
  const values = { ...props.modelValue }
  const carried = values[entry.key]
  delete values[entry.key]
  if (key.length > 0) {
    values[key] = carried ?? ''
  }
  entry.key = key
  emit('update:modelValue', values)
}

const removeCustom = (entry: CustomEntry) => {
  const values = { ...props.modelValue }
  delete values[entry.key]
  customEntries.value = customEntries.value.filter((candidate) => candidate.id !== entry.id)
  emit('update:modelValue', values)
}

/*
 * Values that arrived from a stored object under a key the schema does not declare are shown as free form
 * rows, so that editing an entity never silently drops what a script wrote into it.
 */
watch(
  () => [props.modelValue, props.fields] as const,
  () => {
    const undeclared = Object.keys(props.modelValue).filter((key) => !declaredKeys.value.includes(key))
    const known = customEntries.value.map((entry) => entry.key)
    const missing = undeclared.filter((key) => !known.includes(key))
    if (missing.length === 0) {
      return
    }

    customEntries.value = [
      ...customEntries.value,
      ...missing.map((key) => {
        nextId += 1

        return { id: nextId, key }
      }),
    ]
  },
  { immediate: true, deep: true },
)
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

.metadata-panel__custom {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-block-start: 0.0625rem solid rgb(var(--v-theme-app-border));
  padding-block-start: 0.875rem;
}

.metadata-panel__custom-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.metadata-panel__custom-title {
  font-size: 0.875rem;
  font-weight: 600;
}

.metadata-panel__custom-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) auto;
  align-items: center;
  gap: 0.5rem;
}

@media (max-width: 40rem) {
  .metadata-panel__custom-row {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  }
}
</style>
