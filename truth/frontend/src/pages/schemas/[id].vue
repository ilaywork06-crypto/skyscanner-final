<template>
  <div class="sky-page">
    <AppHeader :industries="industries" />

    <div class="sky-page__content">
      <div class="schema__heading">
        <v-btn
          icon="mdi-chevron-left"
          variant="text"
          aria-label="Back to the schemas"
          to="/schemas"
        />
        <h1 class="schema__title">
          {{ detail?.name ?? 'Schema' }}
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
          prepend-icon="mdi-pencil-outline"
          @click="reviseOpen = true"
        >
          Revise
        </v-btn>
      </div>

      <div
        v-if="loading"
        class="schema__loading"
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
        <v-card class="schema__card">
          <p
            v-if="detail.description.length > 0"
            class="schema__description"
          >
            {{ detail.description }}
          </p>

          <div class="schema__facts">
            <div class="schema__fact">
              <span class="schema__label">Created</span>
              <span class="schema__value">{{ formatDateTime(detail.created_at) }} by {{ detail.creator }}</span>
            </div>
            <div class="schema__fact">
              <span class="schema__label">Revision reason</span>
              <span class="schema__value">{{ detail.revision_reason || EMPTY_PLACEHOLDER }}</span>
            </div>
            <div class="schema__fact">
              <span class="schema__label">Industries</span>
              <div
                v-if="detail.industries.length > 0"
                class="schema__values"
              >
                <UiChip
                  v-for="industry in detail.industries"
                  :key="industry.id"
                  :label="industry.name"
                  :token="hashedToken(industry.name)"
                />
              </div>
              <span
                v-else
                class="schema__value"
              >Every industry</span>
            </div>
            <div class="schema__fact">
              <span class="schema__label">State</span>
              <span class="schema__value">
                {{ detail.deleted ? 'Deleted' : detail.archived ? 'Archived' : 'Active' }}
                <template v-if="detail.latest_revision">— latest revision</template>
              </span>
            </div>
          </div>
        </v-card>

        <v-card class="schema__card">
          <h2 class="schema__section">
            Attributes
          </h2>
          <v-table
            v-if="scheme.fields.length > 0"
            density="compact"
          >
            <thead>
              <tr>
                <th>Key</th>
                <th>Display name</th>
                <th>Type</th>
                <th>Required</th>
                <th>Many</th>
                <th>Allowed</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="field in scheme.fields"
                :key="field.key"
              >
                <td><code>{{ field.key }}</code></td>
                <td>{{ field.displayName }}</td>
                <td><code>{{ field.type }}</code></td>
                <td>{{ field.required ? 'Yes' : 'No' }}</td>
                <td>{{ field.array ? 'Yes' : 'No' }}</td>
                <td>{{ allowedOf(field) }}</td>
              </tr>
            </tbody>
          </v-table>
          <p
            v-else
            class="schema__muted"
          >
            This schema declares no attributes.
          </p>
        </v-card>
      </template>
    </div>

    <CreateSchemaDialog
      v-model="reviseOpen"
      :revised-schema="detail"
      @created="onRevised"
    />
  </div>
</template>

<script setup lang="ts">
import { EMPTY_PLACEHOLDER, UiChip, formatDateTime, hashedToken } from '@truth-platform/core-ui'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import CreateSchemaDialog from '@/components/CreateSchemaDialog.vue'
import { useRegister } from '@/composables/useRegister'
import type { SchemaDetail } from '@/models/schema'
import type { Scheme, SchemeField } from '@/models/scheme'
import { readLatestSchema } from '@/requests/schemas'
import { readScheme } from '@/utils/scheme'

const route = useRoute('/schemas/[id]')
const { industries, load } = useRegister()

const detail = ref<SchemaDetail | null>(null)
const loading = ref<boolean>(true)
const errorMessage = ref<string>('')
const reviseOpen = ref<boolean>(false)

const schemaId = computed<string>(() => route.params.id)
const scheme = computed<Scheme>(() => readScheme(detail.value?.scheme))

/**
 * Read the schema this page is showing, whenever the address changes to a different one.
 */
const loadSchema = async (): Promise<void> => {
  loading.value = true
  errorMessage.value = ''
  try {
    detail.value = await readLatestSchema(schemaId.value)
  } catch (error) {
    detail.value = null
    errorMessage.value = error instanceof Error ? error.message : 'The schema could not be read'
  } finally {
    loading.value = false
  }
}

watch(schemaId, () => void loadSchema(), { immediate: true })

/**
 * Say what one attribute may hold - the vocabulary of an enumeration, or the bounds of a number.
 */
const allowedOf = (field: SchemeField): string => {
  if (field.type === 'enum') {
    return field.options.join(', ') || EMPTY_PLACEHOLDER
  }

  const said: string[] = []
  if (field.min !== null) {
    said.push(`min ${field.min}`)
  }
  if (field.max !== null) {
    said.push(`max ${field.max}`)
  }
  if (field.step !== null) {
    said.push(`step ${field.step}`)
  }

  return said.join(', ') || EMPTY_PLACEHOLDER
}

/**
 * Read the schema again after it was revised, and refresh the register so its columns follow the change.
 */
const onRevised = async () => {
  await loadSchema()
  await load(true)
}
</script>

<style scoped>
.schema__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.schema__title {
  font-size: 1.75rem;
  font-weight: 600;
}

.schema__loading {
  display: flex;
  justify-content: center;
  padding-block: 3rem;
}

.schema__card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.25rem;
  background-color: rgb(var(--v-theme-surface));
}

.schema__section {
  font-size: 1.0625rem;
  font-weight: 600;
}

.schema__description {
  line-height: 1.6;
}

.schema__facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.875rem 1.5rem;
}

.schema__fact {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-inline-size: 0;
}

.schema__label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgb(var(--v-theme-app-muted));
}

.schema__values {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.schema__value,
.schema__muted {
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}

.schema__muted {
  color: rgb(var(--v-theme-app-muted));
}

/* A wide table of attributes scrolls inside its own card rather than widening the page. */
.schema__card :deep(.v-table__wrapper) {
  overflow-x: auto;
}
</style>
