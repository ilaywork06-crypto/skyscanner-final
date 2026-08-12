<template>
  <div class="sky-page">
    <AppHeader>
      <template #tabs>
        <IndustryTabs
          :industries="industries"
          :model-value="activeIndustry"
          @update:model-value="onIndustryChange"
        />
      </template>
    </AppHeader>

    <div class="sky-page__content">
      <EventsInventory
        :key="activeIndustry ?? 'all'"
        :industry="activeIndustry"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import EventsInventory from '@/components/EventsInventory.vue'
import IndustryTabs from '@/components/IndustryTabs.vue'
import { useIndustries } from '@/composables/useIndustries'

const route = useRoute()
const router = useRouter()
const { industries } = useIndustries()

const activeIndustry = computed<string | null>(() => {
  const value = route.query.industry

  return typeof value === 'string' && value.length > 0 ? value : null
})

const onIndustryChange = (industry: string | null) => {
  void router.replace({ query: industry === null ? {} : { industry } })
}
</script>

<style scoped>
</style>
