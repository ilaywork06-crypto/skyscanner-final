<template>
  <v-dialog
    :model-value="modelValue"
    max-width="30rem"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title>Creating as</v-card-title>
      <v-card-text class="identity">
        <p class="identity__note">
          Every assumption, schema and industry is stored with the name of whoever created it. The service
          does not sign anybody in, so this is the name that travels with what you create here.
        </p>
        <v-text-field
          v-model="name"
          label="Your name"
          autofocus
          @keyup.enter="save"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          @click="emit('update:modelValue', false)"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          :disabled="name.trim().length === 0"
          @click="save"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
interface Props {
  modelValue: boolean
}

interface Emits {
  (event: 'update:modelValue', open: boolean): void
}
</script>

<script setup lang="ts">
import { ref, watch } from 'vue'

import { readCreator, writeCreator } from '@/utils/identity'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const name = ref<string>(readCreator())

/* Reopening the dialog shows what is stored now rather than what was typed and abandoned last time. */
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      name.value = readCreator()
    }
  },
)

const save = () => {
  if (name.value.trim().length === 0) {
    return
  }

  writeCreator(name.value)
  emit('update:modelValue', false)
}
</script>

<style scoped>
.identity {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.identity__note {
  color: rgb(var(--v-theme-app-muted));
  font-size: 0.875rem;
  line-height: 1.5;
}
</style>
