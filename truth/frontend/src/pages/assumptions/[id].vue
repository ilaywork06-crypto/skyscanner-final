<template>
  <div class="sky-page">
    <AppHeader :industries="industries" />

    <div class="sky-page__content">
      <div class="assumption__heading">
        <v-btn
          icon="mdi-chevron-left"
          variant="text"
          aria-label="Back to the register"
          to="/assumptions"
        />
        <h1 class="assumption__title">
          {{ detail?.name ?? 'Assumption' }}
        </h1>
        <UiChip
          v-if="detail !== null"
          :label="`rev ${detail.revision}`"
          token="chip-platform"
        />
        <v-spacer />
        <v-btn
          v-if="detail !== null"
          variant="tonal"
          prepend-icon="mdi-content-duplicate"
          @click="duplicateOpen = true"
        >
          Duplicate
        </v-btn>
      </div>

      <div
        v-if="loading"
        class="assumption__loading"
      >
        <v-progress-circular
          indeterminate
          color="primary"
        />
      </div>

      <v-alert
        v-else-if="detail === null"
        type="error"
        variant="tonal"
      >
        {{ errorMessage }}
      </v-alert>

      <template v-else>
        <v-card class="assumption__card">
          <h2 class="assumption__section">
            Assumption
          </h2>
          <p class="assumption__text">
            {{ detail.assumption_text }}
          </p>

          <div class="assumption__facts">
            <div
              v-for="fact in facts"
              :key="fact.label"
              class="assumption__fact"
            >
              <span class="assumption__label">{{ fact.label }}</span>
              <div
                v-if="fact.values.length > 0"
                class="assumption__values"
              >
                <UiChip
                  v-for="value in fact.values"
                  :key="value"
                  :label="value"
                  :token="hashedToken(value)"
                />
              </div>
              <span
                v-else-if="fact.text.length > 0"
                class="assumption__value"
              >{{ fact.text }}</span>
              <span
                v-else
                class="assumption__muted"
              >{{ EMPTY_PLACEHOLDER }}</span>
            </div>
          </div>
        </v-card>

        <!--
          The attributes are shown per schema rather than as one flat block, because which schema asked for a
          value is what tells a reader why the assumption carries it at all.
        -->
        <v-card
          v-for="schema in detail.schemas"
          :key="schema.id"
          class="assumption__card"
        >
          <div class="assumption__schema-head">
            <h2 class="assumption__section">
              {{ schema.name }}
            </h2>
            <UiChip
              :label="`rev ${schema.revision}`"
              token="chip-platform"
            />
            <v-spacer />
            <v-btn
              variant="text"
              size="small"
              :to="`/schemas/${schema.id}`"
            >
              Open schema
            </v-btn>
          </div>

          <p
            v-if="schema.description.length > 0"
            class="assumption__muted"
          >
            {{ schema.description }}
          </p>

          <div
            v-if="fieldsOf(schema.id).length > 0"
            class="assumption__facts"
          >
            <div
              v-for="field in fieldsOf(schema.id)"
              :key="field.key"
              class="assumption__fact"
            >
              <span class="assumption__label">{{ field.label }}</span>
              <span class="assumption__value">{{ renderValue(detail.values[field.key]) }}</span>
            </div>
          </div>
          <p
            v-else
            class="assumption__muted"
          >
            This schema declares no attributes.
          </p>
        </v-card>
      </template>
    </div>

    <CreateAssumptionDialog
      v-model="duplicateOpen"
      :duplicated-from="detail"
      @created="onDuplicated"
    />
  </div>
</template>

<script lang="ts">
/** One thing the register knows about an assumption, shown as a labelled value. */
interface AssumptionFact {
  label: string
  values: string[]
  text: string
}
</script>

<script setup lang="ts">
import { EMPTY_PLACEHOLDER, UiChip, formatDateTime, hashedToken, type JsonValue } from '@truth-platform/core-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import CreateAssumptionDialog from '@/components/CreateAssumptionDialog.vue'
import { useRegister } from '@/composables/useRegister'
import type { AssumptionDetail } from '@/models/assumption'
import type { SchemeField } from '@/models/scheme'
import { readLatestAssumption } from '@/requests/assumptions'
import { readScheme } from '@/utils/scheme'

const route = useRoute('/assumptions/[id]')
const router = useRouter()
const { industries } = useRegister()

const detail = ref<AssumptionDetail | null>(null)
const loading = ref<boolean>(true)
const errorMessage = ref<string>('')
const duplicateOpen = ref<boolean>(false)

const assumptionId = computed<string>(() => route.params.id)

/**
 * Read the assumption this page is showing, whenever the address changes to a different one.
 */
const load = async (): Promise<void> => {
  loading.value = true
  errorMessage.value = ''
  try {
    detail.value = await readLatestAssumption(assumptionId.value)
  } catch (error) {
    detail.value = null
    errorMessage.value = error instanceof Error ? error.message : 'The assumption could not be read'
  } finally {
    loading.value = false
  }
}

watch(assumptionId, () => void load(), { immediate: true })

const facts = computed<AssumptionFact[]>(() => {
  const held = detail.value
  if (held === null) {
    return []
  }

  return [
    { label: 'Proposing party', values: [held.proposing_party], text: '' },
    { label: 'Industries', values: held.industries.map((industry) => industry.name), text: '' },
    { label: 'Tags', values: held.tags, text: '' },
    { label: 'Validation by', values: held.validation_responsible_parties, text: '' },
    { label: 'Created', values: [], text: `${formatDateTime(held.created_at)} by ${held.creator}` },
    { label: 'Revision reason', values: [], text: held.revision_reason },
    {
      label: 'State',
      values: [held.deleted ? 'Deleted' : held.archived ? 'Archived' : 'Active'],
      text: '',
    },
  ]
})

/**
 * The attributes one schema of this assumption declares.
 */
const fieldsOf = (schemaId: string): SchemeField[] => {
  const schema = detail.value?.schemas.find((candidate) => candidate.id === schemaId)

  return schema === undefined ? [] : readScheme(schema.scheme).fields
}

/**
 * Render one stored value as the text this page shows for it.
 */
const renderValue = (value: JsonValue | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return EMPTY_PLACEHOLDER
  }

  if (Array.isArray(value)) {
    return value.length === 0 ? EMPTY_PLACEHOLDER : value.map((item) => String(item)).join(', ')
  }

  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

const onDuplicated = (createdId: string) => {
  void router.push(`/assumptions/${createdId}`)
}
</script>

<style scoped>
.assumption__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.assumption__title {
  font-size: 1.75rem;
  font-weight: 600;
}

.assumption__loading {
  display: flex;
  justify-content: center;
  padding-block: 3rem;
}

.assumption__card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.25rem;
  background-color: rgb(var(--v-theme-surface));
}

.assumption__schema-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.assumption__section {
  font-size: 1.0625rem;
  font-weight: 600;
}

.assumption__text {
  font-size: 1rem;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

/* The facts flow into as many columns as the card has room for rather than into a fixed number of them. */
.assumption__facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.875rem 1.5rem;
}

.assumption__fact {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-inline-size: 0;
}

.assumption__label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgb(var(--v-theme-app-muted));
}

.assumption__values {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.assumption__value {
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}

.assumption__muted {
  font-size: 0.875rem;
  color: rgb(var(--v-theme-app-muted));
}
</style>
