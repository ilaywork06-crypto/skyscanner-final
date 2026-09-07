<template>
  <div class="sky-page">
    <AppHeader :industries="industries" />

    <div class="sky-page__content">
      <div class="schemas__heading">
        <h1 class="schemas__title">
          Schemas
        </h1>
        <v-spacer />
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="createOpen = true"
        >
          SCHEMA
        </v-btn>
      </div>

      <p class="schemas__note">
        A schema declares the attributes an assumption carries. Picking one while creating an assumption is
        what decides which fields there are to fill in.
      </p>

      <v-text-field
        v-model="search"
        class="schemas__search"
        placeholder="Search schemas"
        prepend-inner-icon="mdi-magnify"
        rounded="pill"
        clearable
        hide-details
      />

      <div
        v-if="loading"
        class="schemas__loading"
      >
        <v-progress-circular
          indeterminate
          color="primary"
        />
      </div>

      <div
        v-else-if="matched.length === 0"
        class="schemas__empty"
      >
        {{ schemas.length === 0 ? 'No schemas have been declared yet.' : 'No schemas match that search.' }}
      </div>

      <div
        v-else
        class="schemas__grid"
      >
        <v-card
          v-for="schema in matched"
          :key="schema.id"
          class="schemas__card"
          :to="`/schemas/${schema.id}`"
          link
        >
          <div class="schemas__card-head">
            <h2 class="schemas__card-title">
              {{ schema.name }}
            </h2>
            <UiChip
              :label="`rev ${schema.revision}`"
              token="chip-platform"
            />
          </div>
          <span class="schemas__meta">
            {{ fieldCount(schema.id) }} {{ fieldCount(schema.id) === 1 ? 'attribute' : 'attributes' }}
          </span>
          <span class="schemas__meta">
            {{ formatDateTime(schema.created_at) }} by {{ schema.creator }}
          </span>
        </v-card>
      </div>
    </div>

    <CreateSchemaDialog
      v-model="createOpen"
      @created="onCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { UiChip, formatDateTime, useSnackbar } from '@truth-platform/core-ui'
import { computed, ref } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import CreateSchemaDialog from '@/components/CreateSchemaDialog.vue'
import { useRegister } from '@/composables/useRegister'
import type { SchemaSummary } from '@/models/schema'
import { readScheme } from '@/utils/scheme'

const { industries, schemas, schemaDetails, loading, load } = useRegister()
const { reportError } = useSnackbar()

const search = ref<string>('')
const createOpen = ref<boolean>(false)

const matched = computed<SchemaSummary[]>(() => {
  const needle = search.value.trim().toLowerCase()
  if (needle.length === 0) {
    return schemas.value
  }

  return schemas.value.filter(
    (schema) => schema.name.toLowerCase().includes(needle) || schema.creator.toLowerCase().includes(needle),
  )
})

/** How many attributes a schema declares, out of the declaration already read for the register. */
const fieldCount = (schemaId: string): number => readScheme(schemaDetails.value.get(schemaId)?.scheme).fields.length

const onCreated = async () => {
  try {
    await load(true)
  } catch (error) {
    reportError(error)
  }
}
</script>

<style scoped>
.schemas__heading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.schemas__title {
  font-size: 1.75rem;
  font-weight: 600;
}

.schemas__note,
.schemas__empty,
.schemas__meta {
  color: rgb(var(--v-theme-app-muted));
  font-size: 0.875rem;
}

/*
 * Vuetify gives every input `flex: 1 1 auto`, which is what makes one fill the row it shares with others.
 * Laid straight into a column that rule fills the leftover *height* of the page instead: the box grew to
 * several hundred pixels while the text stayed at the top of it and the search icon floated in the middle.
 * The field is pinned to its own height, and keeps its ceiling on the width.
 */
.schemas__search {
  flex: 0 0 auto;
  max-inline-size: 32rem;
}

.schemas__empty,
.schemas__loading {
  display: flex;
  justify-content: center;
  padding-block: 3rem;
}

.schemas__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr));
  gap: 1rem;
}

.schemas__card {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 1rem;
  background-color: rgb(var(--v-theme-surface));
}

.schemas__card-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.schemas__card-title {
  font-size: 1rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}
</style>
