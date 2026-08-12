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
        Leave without saving?
      </v-card-title>

      <v-card-text class="unsaved__body">
        The form contains changes. If you close this screen they will not be saved.
        Are you sure you want to leave?
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          @click="emit('update:modelValue', false)"
        >
          Keep editing
        </v-btn>
        <v-btn
          color="error"
          @click="emit('discard')"
        >
          Discard changes
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
defineProps<Props>()
const emit = defineEmits<Emits>()
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
