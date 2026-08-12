<template>
  <v-dialog
    :model-value="modelValue"
    max-width="30rem"
    @update:model-value="attemptClose"
  >
    <v-card>
      <v-card-title>Follow {{ targetLabel }}</v-card-title>
      <v-card-text class="subscribe__body">
        <v-text-field
          v-model="email"
          label="Mail address"
          type="email"
        />

        <!--
          Nobody hands the dialog a target when it is opened from the subscriptions page, so the industry is
          named here instead of by a picker the page shows once and never offers again.
        -->
        <v-select
          v-if="picksIndustry"
          v-model="selectedIndustry"
          :items="industries"
          item-title="name"
          item-value="key"
          label="Industry"
        />

        <v-select
          v-model="triggers"
          :items="triggerItems"
          item-title="title"
          item-value="value"
          label="Notify me on"
          multiple
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          @click="attemptClose"
        >
          Cancel
        </v-btn>
        <v-btn
          color="primary"
          :loading="saving"
          :disabled="!canFollow || saving"
          @click="submit"
        >
          Follow
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <UnsavedChangesDialog
    v-model="confirmOpen"
    @discard="discard"
  />
</template>

<script lang="ts">
import type { Industry } from '@/models/industry'
import type { SubscriptionTrigger } from '@/models/subscription'

interface Props {
  modelValue: boolean
  eventId?: string | null
  industry?: string | null
  /** The industries the dialog offers when it is opened without a target of its own. */
  industries?: Industry[]
  targetLabel: string
}

interface Emits {
  (event: 'update:modelValue', value: boolean): void
  (event: 'subscribed'): void
}

interface TriggerItem {
  title: string
  value: SubscriptionTrigger
}

/** The form as it looked when the dialog opened, so an untouched form closes without asking anything. */
interface FormSnapshot {
  email: string
  industry: string | null
  triggers: SubscriptionTrigger[]
}

const STORAGE_KEY = 'skyscanner.email'

const TRIGGER_ITEMS: TriggerItem[] = [
  { title: 'A new event is uploaded', value: 'event_created' },
  { title: 'An event is updated', value: 'event_updated' },
  { title: 'An entity is added', value: 'entity_added' },
  { title: 'An entity is parsed', value: 'entity_parsed' },
]

/*
 * An event that already exists is never uploaded a second time, so a subscription scoped to one event is
 * only offered the changes that can still reach it. The backend refuses the creation trigger there as well.
 */
const EVENT_TRIGGERS: SubscriptionTrigger[] = ['event_updated', 'entity_added', 'entity_parsed']

const EVENT_DEFAULT_TRIGGERS: SubscriptionTrigger[] = ['entity_added', 'entity_parsed']
const BROAD_DEFAULT_TRIGGERS: SubscriptionTrigger[] = ['event_created', 'entity_parsed']
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import UnsavedChangesDialog from '@/components/UnsavedChangesDialog.vue'
import { useDirtyGuard } from '@/composables/useDirtyGuard'
import { useSnackbar } from '@/composables/useSnackbar'
import { createSubscription } from '@/requests/subscriptions'

const props = withDefaults(defineProps<Props>(), {
  eventId: null,
  industry: null,
  industries: () => [],
})
const emit = defineEmits<Emits>()

const { notify, reportError } = useSnackbar()

const email = ref<string>('')
const selectedIndustry = ref<string | null>(null)
const triggers = ref<SubscriptionTrigger[]>([])
const saving = ref<boolean>(false)
const snapshot = ref<FormSnapshot>({ email: '', industry: null, triggers: [] })

const isEventScoped = computed<boolean>(() => props.eventId !== null)

const picksIndustry = computed<boolean>(() => !isEventScoped.value && props.industry === null)

const triggerItems = computed<TriggerItem[]>(() =>
  isEventScoped.value ? TRIGGER_ITEMS.filter((item) => EVENT_TRIGGERS.includes(item.value)) : TRIGGER_ITEMS,
)

const canFollow = computed<boolean>(
  () =>
    email.value.trim().length > 0 &&
    triggers.value.length > 0 &&
    (!picksIndustry.value || selectedIndustry.value !== null),
)

const sameTriggers = (chosen: SubscriptionTrigger[], opened: SubscriptionTrigger[]): boolean =>
  chosen.length === opened.length && chosen.every((trigger) => opened.includes(trigger))

const isDirty = (): boolean =>
  email.value !== snapshot.value.email ||
  selectedIndustry.value !== snapshot.value.industry ||
  !sameTriggers(triggers.value, snapshot.value.triggers)

/**
 * Put the form back into the state a freshly opened dialog starts from.
 *
 * Every field is filled from the scope the dialog was opened in rather than from what the previous run left
 * behind, so the second and every later subscription is offered the whole choice again.
 */
const reset = (): void => {
  email.value = window.localStorage.getItem(STORAGE_KEY) ?? ''
  selectedIndustry.value = null
  triggers.value = isEventScoped.value ? [...EVENT_DEFAULT_TRIGGERS] : [...BROAD_DEFAULT_TRIGGERS]
  snapshot.value = {
    email: email.value,
    industry: selectedIndustry.value,
    triggers: [...triggers.value],
  }
}

const close = (): void => {
  emit('update:modelValue', false)
}

const { confirmOpen, attemptClose, discard } = useDirtyGuard({ isDirty, close })

const submit = async (): Promise<void> => {
  if (!canFollow.value || saving.value) {
    return
  }

  saving.value = true
  try {
    await createSubscription({
      email: email.value.trim(),
      industry: props.industry ?? selectedIndustry.value,
      event_id: props.eventId,
      event_type_key: null,
      triggers: triggers.value,
    })
    window.localStorage.setItem(STORAGE_KEY, email.value.trim())
    notify('You will be notified by mail', 'success')
    emit('subscribed')
    close()
  } catch (error) {
    reportError(error)
  } finally {
    saving.value = false
  }
}

/*
 * A parent may mount the dialog with the flag already true, and a plain watcher would never run on that
 * first open, so the form would stay empty until the dialog had been closed and opened once.
 */
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      reset()
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.subscribe__body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
</style>
