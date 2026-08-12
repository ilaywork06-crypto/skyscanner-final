<template>
  <div class="sky-page">
    <AppHeader />

    <div class="sky-page__content subscriptions">
      <div class="subscriptions__heading">
        <h1 class="subscriptions__title">
          Subscriptions
        </h1>
        <v-spacer />
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="dialog = true"
        >
          Follow an industry
        </v-btn>
      </div>

      <v-table class="subscriptions__table">
        <thead>
          <tr>
            <th>Mail</th>
            <th>Industry</th>
            <th>Event</th>
            <th>Triggers</th>
            <th>Last mail</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="subscription in subscriptions"
            :key="subscription.id"
          >
            <td>{{ subscription.email }}</td>
            <td>{{ subscription.industry ?? '—' }}</td>
            <td>{{ subscription.event_id ?? '—' }}</td>
            <td>{{ subscription.triggers.map(humanizeKey).join(', ') }}</td>
            <td>{{ formatDateTime(subscription.last_notified_at) }}</td>
            <td class="subscriptions__row-actions">
              <v-btn
                icon="mdi-delete-outline"
                size="x-small"
                variant="text"
                aria-label="Stop following"
                @click="onDelete(subscription.id)"
              />
            </td>
          </tr>
          <tr v-if="subscriptions.length === 0">
            <td
              colspan="6"
              class="subscriptions__empty"
            >
              You do not follow anything yet.
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <!--
      The dialog asks for the industry itself, which is what keeps every run of it offering the full list
      instead of silently reusing the industry the first subscription of the session was made for.
    -->
    <SubscribeDialog
      v-model="dialog"
      :industries="industries"
      target-label="an industry"
      @subscribed="reload"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { formatDateTime, humanizeKey } from '@skyscanner/sky-ui'

import AppHeader from '@/components/AppHeader.vue'
import SubscribeDialog from '@/components/SubscribeDialog.vue'
import { useSnackbar } from '@/composables/useSnackbar'
import { useIndustries } from '@/composables/useIndustries'
import type { Subscription } from '@/models/subscription'
import { deleteSubscription, listSubscriptions } from '@/requests/subscriptions'

const { industries, load } = useIndustries()
const { notify, reportError } = useSnackbar()

const subscriptions = ref<Subscription[]>([])
const dialog = ref<boolean>(false)

const reload = async (): Promise<void> => {
  try {
    subscriptions.value = await listSubscriptions()
  } catch (error) {
    reportError(error)
  }
}

const onDelete = async (subscriptionId: string): Promise<void> => {
  try {
    await deleteSubscription(subscriptionId)
    notify('You stopped following this target', 'success')
    await reload()
  } catch (error) {
    reportError(error)
  }
}

onMounted(async () => {
  await load()
  await reload()
})
</script>

<style scoped>
.subscriptions {
  gap: 1rem;
}

.subscriptions__heading {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-block: 1.5rem 0.5rem;
}

.subscriptions__title {
  font-size: 1.75rem;
  font-weight: 600;
}

.subscriptions__table {
  background-color: rgb(var(--v-theme-surface));
  border-radius: 0.75rem;
  overflow: hidden;
}

.subscriptions__row-actions {
  text-align: end;
}

.subscriptions__empty {
  opacity: 0.7;
  text-align: center;
}
</style>
