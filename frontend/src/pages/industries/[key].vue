<template>
  <!--
    The page grows with the table rather than handing it a height to fit into: the table renders the whole
    block of rows at its natural height and the browser scrolls the page, which is what gives an industry with
    many events the room of the whole window.
  -->
  <div class="sky-page">
    <AppHeader>
      <template #tabs>
        <IndustryTabs
          :industries="industries"
          :model-value="industryKey"
          @update:model-value="onIndustryChange"
        />
      </template>
    </AppHeader>

    <div class="sky-page__content">
      <div class="industry-page__heading">
        <v-btn
          icon="mdi-chevron-left"
          variant="text"
          aria-label="Back to the industries"
          to="/industries"
        />
        <h1 class="industry-page__title">
          {{ industryName }}
        </h1>
        <SkyChip
          :label="`${eventCount} events`"
          token="chip-platform"
        />
      </div>

      <EventsInventory
        :key="industryKey"
        :industry="industryKey"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SkyChip } from '@skyscanner/sky-ui'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import EventsInventory from '@/components/EventsInventory.vue'
import IndustryTabs from '@/components/IndustryTabs.vue'
import { useIndustries } from '@/composables/useIndustries'

const route = useRoute('/industries/[key]')
const router = useRouter()
const { industries, findIndustry } = useIndustries()

const industryKey = computed<string>(() => route.params.key)
const industryName = computed<string>(() => findIndustry(industryKey.value)?.name ?? industryKey.value)
const eventCount = computed<number>(() => findIndustry(industryKey.value)?.event_count ?? 0)

const onIndustryChange = (industry: string | null) => {
  void router.push(industry === null ? '/events' : `/industries/${industry}`)
}
</script>

<style scoped>
.industry-page__heading {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.75rem;
  /* The heading gives up the room it was padded with, because the table below it is what the page is for. */
  padding-block: 0.75rem 0;
}

.industry-page__title {
  font-size: 1.75rem;
  font-weight: 600;
}
</style>
