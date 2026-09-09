<template>
  <div class="sky-page">
    <AppHeader :industries="industries" />

    <div class="sky-page__content">
      <div class="industry__heading">
        <v-btn
          :icon="direction === 'rtl' ? 'mdi-chevron-right' : 'mdi-chevron-left'"
          variant="text"
          :aria-label="t('industries.back')"
          to="/industries"
        />
        <h1 class="industry__title">
          {{ industryName }}
        </h1>
      </div>

      <AssumptionsRegister :industry="industryId" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useLanguage } from '@truth-platform/core-ui'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import AssumptionsRegister from '@/components/AssumptionsRegister.vue'
import { useRegister } from '@/composables/useRegister'

const { t, direction } = useLanguage()
const route = useRoute('/industries/[id]')
const { industries, findIndustry } = useRegister()

const industryId = computed<string>(() => route.params.id)
const industryName = computed<string>(() => findIndustry(industryId.value)?.name ?? t('industries.fallbackName'))
</script>

<style scoped>
.industry__heading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.industry__title {
  font-size: 1.75rem;
  font-weight: 600;
}
</style>
