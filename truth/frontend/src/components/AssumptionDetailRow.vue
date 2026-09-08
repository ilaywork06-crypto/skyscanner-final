<template>
  <div class="detail-row">
    <div
      ref="content"
      class="detail-row__content"
    >
      <div
        v-if="row === undefined"
        class="detail-row__empty"
      >
        This assumption is no longer on the page.
      </div>

      <template v-else>
        <section class="detail-row__section">
          <header class="detail-row__heading">
            <h3 class="detail-row__title">
              Industry details
            </h3>
            <UiChip
              v-for="industry in industryNames"
              :key="industry"
              :label="industry"
              :token="taxonomyToken(industry, taxonomy)"
            />
            <span
              v-if="industryNames.length === 0"
              class="detail-row__muted"
            >
              This assumption is not filed under any industry.
            </span>
          </header>

          <AttributesTable
            v-if="valueColumns.length > 0"
            :columns="valueColumns"
            :row="row"
            :taxonomy="taxonomy"
          />
          <p
            v-else
            class="detail-row__muted"
          >
            The schemas of this assumption declare no attributes.
          </p>
        </section>

        <section class="detail-row__section">
          <header class="detail-row__heading">
            <h3 class="detail-row__title">
              Validation
            </h3>
          </header>

          <!--
              The API records who is responsible for validating an assumption but stores no validations
              themselves, so this is what the register actually knows about the validation of a row.
            -->
          <div class="detail-row__facts">
            <div
              v-for="fact in validationFacts"
              :key="fact.label"
              class="detail-row__fact"
            >
              <span class="detail-row__label">{{ fact.label }}</span>
              <div
                v-if="fact.values.length > 0"
                class="detail-row__values"
              >
                <UiChip
                  v-for="value in fact.values"
                  :key="value"
                  :label="value"
                  :token="fact.token ?? taxonomyToken(value, taxonomy)"
                />
              </div>
              <span
                v-else-if="fact.text.length > 0"
                class="detail-row__text"
              >{{ fact.text }}</span>
              <span
                v-else
                class="detail-row__muted"
              >{{ EMPTY_PLACEHOLDER }}</span>
            </div>
          </div>
        </section>

        <div class="detail-row__actions">
          <v-btn
            variant="text"
            size="small"
            prepend-icon="mdi-open-in-new"
            @click="open"
          >
            Open assumption
          </v-btn>
          <v-btn
            variant="text"
            size="small"
            prepend-icon="mdi-chevron-up"
            @click="collapse"
          >
            Collapse
          </v-btn>
        </div>
      </template>
    </div>
  </div>
</template>

<script lang="ts">
import type { GeneratedColumn, GridRow } from '@truth-platform/core-ui'
import type { ICellRendererParams } from 'ag-grid-community'

import type { AssumptionGridContext } from '@/components/AssumptionsGrid.vue'

interface Props {
  params: ICellRendererParams<GridRow>
}

/** One thing the register knows about the validation of an assumption. */
interface ValidationFact {
  label: string
  values: string[]
  text: string
  token?: string
}
</script>

<script setup lang="ts">
import {
  AttributesTable,
  EMPTY_PLACEHOLDER,
  UiChip,
  formatDateTime,
  provideSearchTerm,
  readContext,
  taxonomyToken,
} from '@truth-platform/core-ui'
import { computed, onBeforeUnmount, onMounted, ref, toRef } from 'vue'

import { useRegister } from '@/composables/useRegister'

const props = defineProps<Props>()

const content = ref<HTMLElement | null>(null)

/* The declarations are already held for the whole register, so the panel reads them rather than fetching. */
const { schemeOf } = useRegister()

const context = computed<AssumptionGridContext>(() => readContext(props.params) as AssumptionGridContext)
const parentId = computed<string>(() => String(props.params.data?.parentId ?? ''))
const row = computed<GridRow | undefined>(() => context.value.findRow(parentId.value))
const taxonomy = computed(() => context.value.taxonomy)

/* The panel is several components away from the table, so the search term travels with the row rather than
   being carried through every component in between. */
provideSearchTerm(toRef(() => context.value.search))

const industryNames = computed<string[]>(() => {
  const names = row.value?.industries

  return Array.isArray(names) ? names.map((name) => String(name)) : []
})

/**
 * The columns of the panel, which are exactly the schema declared ones of the table.
 *
 * The panel exists to show what a row could not fit, so it leaves out the fixed columns that were already
 * legible in the row above it. It also leaves out the attributes of every other schema in the register - an
 * assumption is not declared by those, so laying them out here would fill the panel with a row of dashes
 * for questions nobody asked of it.
 */
const declaredKeys = computed<Set<string>>(() => {
  const ids = row.value?.schema_ids

  if (!Array.isArray(ids)) {
    return new Set()
  }

  return new Set(ids.flatMap((id) => schemeOf(String(id)).fields.map((field) => field.key)))
})

const valueColumns = computed<GeneratedColumn[]>(() =>
  context.value.columns.filter((column) => column.dynamic && declaredKeys.value.has(column.colId)),
)

const readList = (key: string): string[] => {
  const value = row.value?.[key]

  return Array.isArray(value) ? value.map((item) => String(item)) : []
}

const validationFacts = computed<ValidationFact[]>(() => [
  {
    label: 'Responsible parties',
    values: readList('validation_responsible_parties'),
    text: '',
  },
  {
    label: 'Proposed by',
    values: [],
    text: String(row.value?.proposing_party ?? ''),
  },
  {
    label: 'Revision',
    values: [],
    text: `${String(row.value?.revision ?? 0)}${
      String(row.value?.revision_reason ?? '').length > 0 ? ` — ${String(row.value?.revision_reason)}` : ''
    }`,
  },
  {
    label: 'Created',
    values: [],
    text: `${formatDateTime(String(row.value?.created_at ?? ''))} by ${String(row.value?.creator ?? '')}`,
  },
  {
    label: 'State',
    values: [row.value?.deleted === true ? 'Deleted' : row.value?.archived === true ? 'Archived' : 'Active'],
    text: '',
    token: row.value?.deleted === true || row.value?.archived === true ? 'status-negative' : 'status-positive',
  },
])

const collapse = () => context.value.toggleExpanded(parentId.value)
const open = () => context.value.openRow(parentId.value)

/*
 * The row above was given a height before this panel was drawn, so the panel measures itself and says so.
 *
 * What is measured is the inner box rather than the outer one: the outer is pinned to whatever height the
 * row currently has, so it never changes size and would report the same wrong height forever. The inner box
 * grows as the reading of the assumption lands and as the window narrows under it, and every one of those
 * changes is a height the row underneath ought to have.
 */
let observer: ResizeObserver | null = null

const report = () => {
  const element = content.value
  if (element === null || parentId.value.length === 0) {
    return
  }

  context.value.reportDetailHeight(parentId.value, element.getBoundingClientRect().height)
}

onMounted(() => {
  const element = content.value
  if (element === null || typeof ResizeObserver === 'undefined') {
    return
  }

  observer = new ResizeObserver(report)
  observer.observe(element)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})
</script>

<!--
  The styles are deliberately not scoped. AG Grid mounts a cell renderer outside the render tree of the page,
  so the component never receives the attribute a scoped block keys its selectors on and not one of them would
  match. Every class below is prefixed for that reason.
-->
<style>
.detail-row {
  inline-size: 100%;
  block-size: 100%;
  /* A panel taller than the ceiling a single row may take scrolls inside itself rather than being cut off. */
  overflow: auto;
  background-color: rgb(var(--v-theme-table-row-alt));
  border-block-end: 0.0625rem solid rgb(var(--v-theme-app-border));
}

.detail-row__content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  inline-size: 100%;
  padding: 1rem 1.5rem 1.25rem;
}

.detail-row__section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-inline-size: 0;
}

.detail-row__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.detail-row__title {
  font-size: 0.9375rem;
  font-weight: 600;
}


.detail-row__empty,
.detail-row__muted {
  color: rgb(var(--v-theme-app-muted));
  font-size: 0.875rem;
}

/*
 * The facts are laid out in as many columns as the panel has room for rather than in a fixed number, so the
 * panel reads as one line on a narrow window and as a row of them on a wide one.
 */
.detail-row__facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.75rem 1.5rem;
}

.detail-row__fact {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-inline-size: 0;
}

.detail-row__label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgb(var(--v-theme-app-muted));
}

.detail-row__values {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.detail-row__text {
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}

.detail-row__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
