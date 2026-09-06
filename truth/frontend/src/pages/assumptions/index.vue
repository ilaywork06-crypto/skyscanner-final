<template>
  <div class="sky-page">
    <AppHeader :industries="industries" />

    <div class="sky-page__content">
      <AssumptionsRegister />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
import AssumptionsRegister from '@/components/AssumptionsRegister.vue'
import { useRegister } from '@/composables/useRegister'

const { industries } = useRegister()
</script>

<style scoped>
</style>
