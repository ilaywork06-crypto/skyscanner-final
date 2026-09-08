<template>
  <div class="sky-page">
    <AppHeader :industries="industries" />

    <div class="sky-page__content">
      <div class="industries__heading">
        <h1 class="industries__title">
          Industries
        </h1>
        <v-spacer />
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="createOpen = true"
        >
          INDUSTRY
        </v-btn>
      </div>

      <p class="industries__note">
        An industry holds the assumptions filed under it. Open one to read its own register.
      </p>

      <div
        v-if="loading"
        class="industries__loading"
      >
        <v-progress-circular
          indeterminate
          color="primary"
        />
      </div>

      <div
        v-else-if="industries.length === 0"
        class="industries__empty"
      >
        No industries have been created yet.
      </div>

      <div
        v-else
        class="industries__grid"
      >
        <v-card
          v-for="industry in industries"
          :key="industry.id"
          class="industries__card"
          :to="`/industries/${industry.id}`"
          link
        >
          <div class="industries__card-head">
            <UiChip
              :label="industry.name"
              :token="hashedToken(industry.name)"
            />
          </div>
          <div class="industries__count">
            {{ countOf(industry.name) }}
            <span class="industries__count-label">
              {{ countOf(industry.name) === 1 ? 'assumption' : 'assumptions' }}
            </span>
          </div>
        </v-card>
      </div>
    </div>

    <CreateIndustryDialog
      v-model="createOpen"
      @created="onCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { UiChip, hashedToken, useSnackbar } from '@truth-platform/core-ui'
import { onMounted, ref } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import CreateIndustryDialog from '@/components/CreateIndustryDialog.vue'
import { useRegister } from '@/composables/useRegister'
import { readIndustriesWithCounts } from '@/requests/industries'

const { industries, loading, load } = useRegister()
const { reportError } = useSnackbar()

const createOpen = ref<boolean>(false)

/*
 * How many assumptions name each industry, counted by the service in one pass over the register.
 *
 * This used to be counted here, over the assumptions the client had read - which made the number climb while
 * the page was open and settle on the truth only once the last reading had landed. It is asked for now, and
 * it is asked for separately from the industries themselves because counting is the expensive half.
 */
const counts = ref<Record<string, number>>({})

const loadCounts = async () => {
  try {
    const counted = await readIndustriesWithCounts()
    counts.value = Object.fromEntries(counted.map((industry) => [industry.name, industry.assumption_count ?? 0]))
  } catch (error) {
    reportError(error)
  }
}

const countOf = (name: string): number => counts.value[name] ?? 0

/**
 * Read the register again, so that a newly created industry appears with the rest of them.
 */
const onCreated = async () => {
  try {
    await load(true)
    await loadCounts()
  } catch (error) {
    reportError(error)
  }
}

onMounted(() => {
  void loadCounts()
})
</script>

<style scoped>
.industries__heading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.industries__title {
  font-size: 1.75rem;
  font-weight: 600;
}

.industries__note,
.industries__empty {
  color: rgb(var(--v-theme-app-muted));
  font-size: 0.875rem;
}

.industries__empty,
.industries__loading {
  display: flex;
  justify-content: center;
  padding-block: 3rem;
}

/* The cards flow into as many columns as the page has room for rather than into a fixed number of them. */
.industries__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
  gap: 1rem;
}

.industries__card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background-color: rgb(var(--v-theme-surface));
}

.industries__card-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.industries__count {
  font-size: 1.5rem;
  font-weight: 600;
}

.industries__count-label {
  font-size: 0.875rem;
  font-weight: 400;
  color: rgb(var(--v-theme-app-muted));
}

.industries__pending {
  font-size: 0.75rem;
  color: rgb(var(--v-theme-app-muted));
}
</style>
