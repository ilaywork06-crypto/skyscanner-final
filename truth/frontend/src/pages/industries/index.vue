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
          <!--
            The listing of an assumption does not say which industries it belongs to, so a count is only
            complete once every assumption has been read on its own.
          -->
          <span
            v-if="completing"
            class="industries__pending"
          >counting…</span>
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
import { computed, ref } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import CreateIndustryDialog from '@/components/CreateIndustryDialog.vue'
import { useRegister } from '@/composables/useRegister'

const { industries, assumptions, loading, completing, load } = useRegister()
const { reportError } = useSnackbar()

const createOpen = ref<boolean>(false)

/**
 * How many assumptions name each industry, counted over the readings that have arrived.
 */
const counts = computed<Record<string, number>>(() => {
  const collected: Record<string, number> = {}
  assumptions.value.forEach((row) => {
    row.detail?.industries.forEach((industry) => {
      collected[industry.name] = (collected[industry.name] ?? 0) + 1
    })
  })

  return collected
})

const countOf = (name: string): number => counts.value[name] ?? 0

/**
 * Read the register again, so that a newly created industry appears with the rest of them.
 */
const onCreated = async () => {
  try {
    await load(true)
  } catch (error) {
    reportError(error)
  }
}
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
