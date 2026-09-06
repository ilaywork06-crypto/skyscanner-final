<template>
  <div class="sky-notes">
    <div
      v-for="(note, index) in rows"
      :key="index"
      class="sky-notes__row"
    >
      <v-text-field
        :model-value="note"
        :placeholder="placeholder"
        :aria-label="`Note ${index + 1}`"
        density="comfortable"
        hide-details
        @update:model-value="replace(index, $event)"
      />
      <v-btn
        icon="mdi-close"
        size="small"
        variant="text"
        :disabled="!canRemove"
        :aria-label="`Remove note ${index + 1}`"
        @click="remove(index)"
      />
    </div>

    <div class="sky-notes__actions">
      <v-btn
        size="small"
        variant="text"
        prepend-icon="mdi-plus"
        :disabled="!canAdd"
        @click="add"
      >
        {{ addLabel }}
      </v-btn>
    </div>
  </div>
</template>

<script lang="ts">
/**
 * A list of short notes typed one per row.
 *
 * The value stays a plain string on the wire so that nothing about the API or the stored documents has to
 * change: **the rows are joined with newline characters when emitted and split on newline characters when
 * read back**. That newline convention is the whole contract with the reading side, which renders the same
 * string as bullets without knowing this component exists.
 *
 * An empty value is one empty row, because a list nobody has typed into yet still has to offer somewhere
 * to type. A new row can only be added once the last one carries text, so the value never grows a trailing
 * empty line that would read as an empty bullet.
 */
interface Props {
  modelValue: string
  placeholder?: string
  addLabel?: string
}

interface Emits {
  (event: 'update:modelValue', value: string): void
}

const SEPARATOR = '\n'
</script>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Type here...',
  addLabel: 'ADD NOTE',
})
const emit = defineEmits<Emits>()

const rows = computed<string[]>(() => props.modelValue.split(SEPARATOR))

const lastRow = computed<string>(() => rows.value[rows.value.length - 1] ?? '')

/* Piling up empty rows would only produce empty bullets, so another row is offered once this one says something. */
const canAdd = computed<boolean>(() => lastRow.value.trim().length > 0)

/* The single row of an empty list is what the user types into, so it is never taken away. */
const canRemove = computed<boolean>(() => rows.value.length > 1 || props.modelValue.length > 0)

const publish = (notes: string[]) => {
  emit('update:modelValue', notes.join(SEPARATOR))
}

const replace = (index: number, note: string) => {
  publish(rows.value.map((current, candidate) => (candidate === index ? note : current)))
}

const add = () => {
  publish([...rows.value, ''])
}

const remove = (index: number) => {
  const remaining = rows.value.filter((_, candidate) => candidate !== index)
  publish(remaining.length > 0 ? remaining : [''])
}
</script>

<style scoped>
.sky-notes {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sky-notes__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.5rem;
}

.sky-notes__actions {
  display: flex;
  justify-content: flex-start;
}
</style>
