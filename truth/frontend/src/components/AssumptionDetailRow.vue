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
        {{ t('detail.gone') }}
      </div>

      <template v-else>
        <!--
          The reading of an assumption is a request of its own and lands after the row it belongs to, so a panel
          opened early says what it is waiting for instead of showing an assumption with no values.
        -->
        <div
          v-if="row.complete !== true"
          class="detail-row__loading"
        >
          <v-progress-circular
            indeterminate
            size="20"
            width="2"
            color="primary"
          />
          <span>{{ t('detail.reading') }}</span>
        </div>

        <template v-else>
          <section class="detail-row__section">
            <header class="detail-row__heading">
              <h3 class="detail-row__title">
                {{ t('detail.industryDetails') }}
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
                {{ t('detail.noIndustry') }}
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
              {{ t('detail.noAttributes') }}
            </p>
          </section>

          <section class="detail-row__section">
            <header class="detail-row__heading">
              <h3 class="detail-row__title">
                {{ t('detail.validation') }}
              </h3>
            </header>

            <!--
              Every party this assumption is validated by, as a list that can be searched and picked from.
              A panel is where a reader finally sees what a row is filed under, and the question they ask
              next is "show me the others like this" - so each of them narrows the register to itself, and
              a row validated by more parties than can be read at a glance gets a box to find one in.
            -->
            <div
              v-if="validations.length > 0"
              class="detail-row__validations"
            >
              <v-text-field
                v-if="validations.length >= SEARCHABLE_FROM"
                v-model="validationTerm"
                :placeholder="t('detail.searchValidations')"
                prepend-inner-icon="mdi-magnify"
                density="compact"
                variant="outlined"
                hide-details
                clearable
              />

              <div class="detail-row__validation-list">
                <button
                  v-for="party in matchingValidations"
                  :key="party"
                  type="button"
                  class="detail-row__validation"
                  :class="{ 'detail-row__validation--active': isNarrowedTo(party) }"
                  :title="t('detail.filterByValidation', { party })"
                  dir="auto"
                  @click.stop="toggleValidation(party)"
                >
                  <v-icon
                    size="x-small"
                    :icon="isNarrowedTo(party) ? 'mdi-filter' : 'mdi-filter-outline'"
                  />
                  <span class="detail-row__validation-label">{{ party }}</span>
                </button>

                <p
                  v-if="matchingValidations.length === 0"
                  class="detail-row__muted"
                >
                  {{ t('filters.noMatch', { term: validationTerm ?? '' }) }}
                </p>
              </div>
            </div>

            <p
              v-else
              class="detail-row__muted"
            >
              {{ t('detail.noValidations') }}
            </p>

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
              {{ t('detail.open') }}
            </v-btn>
            <v-btn
              variant="text"
              size="small"
              prepend-icon="mdi-chevron-up"
              @click="collapse"
            >
              {{ t('detail.collapse') }}
            </v-btn>
          </div>
        </template>
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

/** Past this many parties the list is one a reader searches rather than one they simply read. */
const SEARCHABLE_FROM = 6

/** The column the validation parties are narrowed through, which is the one the table shows them in. */
const VALIDATION_COLUMN = 'validation_responsible_parties'

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
  useLanguage,
} from '@truth-platform/core-ui'
import { computed, onBeforeUnmount, onMounted, ref, toRef } from 'vue'

import { narrowedValues } from '@/composables/useAssumptionsGrid'
import { useRegister } from '@/composables/useRegister'

const props = defineProps<Props>()

const { t } = useLanguage()

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

const validationTerm = ref<string>('')

/** Every party this assumption is validated by, which is what the list is drawn from. */
const validations = computed<string[]>(() => readList(VALIDATION_COLUMN))

const matchingValidations = computed<string[]>(() => {
  const needle = (validationTerm.value ?? '').trim().toLowerCase()
  if (needle.length === 0) {
    return validations.value
  }

  return validations.value.filter((party) => party.toLowerCase().includes(needle))
})

/*
 * Which parties the table is currently narrowed to. Read off the conditions the table is actually running
 * rather than remembered here, so an entry marked in this panel and the chip above the table can never
 * disagree - lifting the chip unmarks the entry, and there is only one place the answer lives.
 */
const narrowedTo = computed<string[]>(() => narrowedValues(VALIDATION_COLUMN))

/** Whether the table is currently narrowed to one party, which is what its entry is marked by. */
const isNarrowedTo = (party: string): boolean => narrowedTo.value.includes(party)

/**
 * Narrow the register to one validating party, or lift that narrowing when it is already the one in force.
 *
 * Picking a second party widens the narrowing to both rather than replacing the first, because a filter
 * over a list of values is a question about any of them - which is the same thing the column's own filter
 * does when two values are ticked in it.
 */
const toggleValidation = (party: string) => {
  const current = narrowedTo.value
  const next = current.includes(party)
    ? current.filter((candidate) => candidate !== party)
    : [...current, party]

  context.value.filterBy(VALIDATION_COLUMN, next)
}

const validationFacts = computed<ValidationFact[]>(() => [
  {
    label: t('detail.responsible'),
    values: readList('validation_responsible_parties'),
    text: '',
  },
  {
    label: t('column.proposingParty'),
    values: [],
    text: String(row.value?.proposing_party ?? ''),
  },
  {
    label: t('column.revision'),
    values: [],
    text: `${String(row.value?.revision ?? 0)}${
      String(row.value?.revision_reason ?? '').length > 0 ? ` — ${String(row.value?.revision_reason)}` : ''
    }`,
  },
  {
    label: t('column.createdAt'),
    values: [],
    text: t('detail.createdBy', {
      moment: formatDateTime(String(row.value?.created_at ?? '')),
      creator: String(row.value?.creator ?? ''),
    }),
  },
  {
    label: t('detail.state'),
    values: [
      row.value?.deleted === true
        ? t('detail.removed')
        : row.value?.archived === true
          ? t('detail.archived')
          : t('detail.active'),
    ],
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

.detail-row__loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: rgb(var(--v-theme-app-muted));
  font-size: 0.875rem;
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
/*
 * The validations of a row, as a list that is picked from rather than only read. Each entry is a control,
 * so it reads as one: a filter mark, the name, and a background once the table is actually narrowed to it.
 */
.detail-row__validations {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-inline-size: 28rem;
}

.detail-row__validation-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  max-block-size: 11rem;
  overflow-y: auto;
}

.detail-row__validation {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: 0.0625rem solid rgb(var(--v-theme-control-border));
  border-radius: 999rem;
  background-color: rgb(var(--v-theme-control-surface));
  color: rgb(var(--v-theme-on-surface));
  padding-inline: 0.625rem;
  padding-block: 0.25rem;
  font: inherit;
  font-size: 0.8125rem;
  cursor: pointer;
  max-inline-size: 100%;
}

.detail-row__validation:hover {
  background-color: rgb(var(--v-theme-control-surface-hover));
}

/* An entry the table is already narrowed to is marked as one, so a second press reads as lifting it. */
.detail-row__validation--active {
  border-color: rgba(var(--v-theme-primary), 0.55);
  background-color: rgba(var(--v-theme-primary), 0.14);
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}

.detail-row__validation-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

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
