<template>
  <v-snackbar
    v-model="visible"
    :color="tone"
    location="bottom right"
    :timeout="TIMEOUT_MS"
  >
    {{ message }}
  </v-snackbar>
</template>

<script lang="ts">
const TIMEOUT_MS = 5000
</script>

<script setup lang="ts">
import { useSnackbar } from '@/composables/useSnackbar'

const { visible, message, tone } = useSnackbar()
</script>

<style scoped>
</style>
