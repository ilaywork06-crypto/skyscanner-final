<template>
  <!--
    The last thing between a filled in form and an accidental click on the backdrop. It sits above the dialog
    it guards, so it is deliberately narrow and says plainly what leaving costs.
  -->
  <v-dialog
    :model-value="modelValue"
    max-width="28rem"
    persistent
  >
    <v-card class="unsaved">
      <v-card-title class="unsaved__title">
        {{ t('common.unsavedTitle') }}
      </v-card-title>

      <v-card-text class="unsaved__body">
        {{ t('common.unsavedBody') }}
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          @click="emit('update:modelValue', false)"
        >
          {{ t('common.keepEditing') }}
        </v-btn>
        <v-btn
          color="error"
          @click="emit('discard')"
        >
          {{ t('common.discard') }}
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
  (event: 'update:modelValue', value: boolean): void
  (event: 'discard'): void
}
</script>

<script setup lang="ts">
import { useLanguage } from '../composables/useLanguage'

defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useLanguage()
</script>

<style scoped>
.unsaved {
  background-color: rgb(var(--v-theme-surface));
}

.unsaved__title {
  font-size: 1.125rem;
  font-weight: 600;
}

.unsaved__body {
  font-size: 0.9375rem;
  line-height: 1.5;
}
</style>
