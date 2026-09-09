<template>
  <v-dialog
    :model-value="modelValue"
    max-width="40rem"
    scrollable
    @update:model-value="close"
  >
    <v-card>
      <v-card-title>{{ t('import.title') }}</v-card-title>

      <v-card-text class="import">
        <p class="import__note">
          {{ t('import.note') }}
        </p>

        <v-file-input
          :model-value="picked"
          :label="t('import.pick')"
          accept="application/json,.json"
          prepend-icon=""
          prepend-inner-icon="mdi-package-variant-closed"
          :disabled="running"
          @update:model-value="onPick"
        />

        <v-alert
          v-if="problem.length > 0"
          type="error"
          variant="tonal"
          density="compact"
        >
          {{ problem }}
        </v-alert>

        <!--
          What the bundle holds and what restoring it would actually write are two different numbers, and
          both are said before anything is written. A restore that silently skipped what was already here
          would read as a restore that lost things.
        -->
        <template v-if="bundle !== null">
          <p class="import__line">
            {{
              t('import.summary', {
                industries: bundle.industries.length,
                schemas: bundle.schemas.length,
                assumptions: bundle.assumptions.length,
              })
            }}
          </p>
          <p class="import__line">
            {{
              t('import.willCreate', {
                industries: plan.industries.length,
                schemas: plan.schemas.length,
                assumptions: plan.assumptions.length,
              })
            }}
          </p>
          <p
            v-if="plan.skipped > 0"
            class="import__muted"
          >
            {{ t('import.alreadyHere', { count: plan.skipped }) }}
          </p>
        </template>

        <template v-if="running || finished">
          <v-progress-linear
            :model-value="percent"
            color="primary"
            height="4"
            rounded
          />
          <p class="import__line">
            {{
              running
                ? t('import.running', { done: done, total: total })
                : failures.length === 0
                  ? t('import.doneClean', { created: created, total: total })
                  : t('import.done', { created: created, total: total, failed: failures.length })
            }}
          </p>
        </template>

        <!-- Every write that failed is named. A restore that half worked is only useful if it says which half. -->
        <div
          v-if="failures.length > 0"
          class="import__failures"
        >
          <p class="import__failures-title">
            {{ t('import.failures') }}
          </p>
          <ul>
            <li
              v-for="failure in failures"
              :key="failure"
            >
              {{ failure }}
            </li>
          </ul>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          :disabled="running"
          @click="close(false)"
        >
          {{ t('import.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          :loading="running"
          :disabled="bundle === null || running || plan.total === 0"
          @click="restore"
        >
          {{ t('import.restore') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
interface Props {
  modelValue: boolean
}

interface Emits {
  (event: 'update:modelValue', open: boolean): void
  /** Raised once something was written, so the page around this reads the register again. */
  (event: 'restored'): void
}

/** What restoring the bundle would actually write, once what is already here has been taken out of it. */
interface RestorePlan {
  industries: BundledIndustry[]
  schemas: BundledSchema[]
  assumptions: BundledAssumption[]
  /** How many of the bundle's assumptions are already in the register and are therefore left alone. */
  skipped: number
  total: number
}
</script>

<script setup lang="ts">
import { useLanguage, useSnackbar } from '@truth-platform/core-ui'
import { computed, ref, shallowRef, watch } from 'vue'

import { useRegister } from '@/composables/useRegister'
import { createAssumption } from '@/requests/assumptions'
import { createIndustry } from '@/requests/industries'
import { createSchema } from '@/requests/schemas'
import {
  assumptionDraft,
  assumptionKey,
  nameResolver,
  readBundle,
  type Bundle,
  type BundledAssumption,
  type BundledIndustry,
  type BundledSchema,
} from '@/utils/bundle'
import { readCreator } from '@/utils/identity'

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useLanguage()
const { notify, reportError } = useSnackbar()
const { industries, schemas, assumptions, load } = useRegister()

const picked = shallowRef<File | File[] | null>(null)
/*
 * A bundle is a deep structure, and holding one in a plain `ref` would make Vue walk the whole of it to make
 * every field of every assumption reactive - for a value nothing ever writes into. It is read once and shown.
 */
const bundle = shallowRef<Bundle | null>(null)
const problem = ref<string>('')
const running = ref<boolean>(false)
const finished = ref<boolean>(false)
const done = ref<number>(0)
const created = ref<number>(0)
const failures = ref<string[]>([])

/*
 * What is already here, by name. A restore is a sequence of creations against an API that has no way of
 * being asked whether something exists and no way of changing it if it does, so the only thing that keeps a
 * bundle from being written twice is the register this client is already holding.
 */
const plan = computed<RestorePlan>(() => {
  const held = bundle.value
  if (held === null) {
    return { industries: [], schemas: [], assumptions: [], skipped: 0, total: 0 }
  }

  const heldIndustries = new Set(industries.value.map((industry) => industry.name))
  const heldSchemas = new Set(schemas.value.map((schema) => schema.name))
  const heldAssumptions = new Set(
    assumptions.value.map((row) => assumptionKey(row.name, row.assumption_text)),
  )

  const wantedIndustries = held.industries.filter((item) => !heldIndustries.has(item.name))
  const wantedSchemas = held.schemas.filter((item) => !heldSchemas.has(item.name))
  const wantedAssumptions = held.assumptions.filter(
    (item) => !heldAssumptions.has(assumptionKey(item.name, item.assumption_text)),
  )

  return {
    industries: wantedIndustries,
    schemas: wantedSchemas,
    assumptions: wantedAssumptions,
    skipped: held.assumptions.length - wantedAssumptions.length,
    total: wantedIndustries.length + wantedSchemas.length + wantedAssumptions.length,
  }
})

/*
 * How many writes the running restore set out to make.
 *
 * Taken once, when it starts, rather than read off the plan as it goes. The plan is a view of what the
 * register is still missing, and the restore reads the register again halfway through - so the plan shrinks
 * underneath a restore that is working exactly as intended, and a progress line drawn from it would count
 * downwards and end reporting more written than there ever were.
 */
const total = ref<number>(0)

const percent = computed<number>(() => (total.value === 0 ? 0 : (done.value / total.value) * 100))

/**
 * Put the dialog back the way it opens, so a second import does not start inside the report of the first.
 */
const reset = () => {
  picked.value = null
  bundle.value = null
  problem.value = ''
  running.value = false
  finished.value = false
  done.value = 0
  created.value = 0
  total.value = 0
  failures.value = []
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      reset()
    }
  },
)

/**
 * Read whatever was picked, and say plainly when it is not a bundle rather than reporting an empty one.
 */
const onPick = async (value: File | File[] | null) => {
  picked.value = value
  bundle.value = null
  problem.value = ''
  finished.value = false

  const file = Array.isArray(value) ? (value[0] ?? null) : value
  if (file === null) {
    return
  }

  const read = readBundle(await file.text())
  if (read === null) {
    problem.value = t('import.unreadable')

    return
  }

  bundle.value = read
}

/**
 * Run one write, counting it either way so that the progress reaches its end whatever happened.
 *
 * One failure does not stop the restore. A bundle is a hundred independent writes against an API that
 * cannot be asked to do them as one, so the only two honest behaviours are to stop at the first refusal and
 * leave a half restored register unexplained, or to write everything that can be written and say exactly
 * what could not. This does the second.
 */
const attempt = async (label: string, write: () => Promise<unknown>): Promise<void> => {
  try {
    await write()
    created.value += 1
  } catch (error) {
    failures.value = [...failures.value, `${label} — ${error instanceof Error ? error.message : ''}`]
  } finally {
    done.value += 1
  }
}

/**
 * Write the bundle into the register, in the order the API's own references require.
 *
 * The three passes are sequential because each names the one before it: an assumption names its schemas and
 * its industries by name, and a name that has not been created yet is a name the service will refuse.
 */
const restore = async () => {
  const wanted = plan.value
  const creator = readCreator()

  running.value = true
  finished.value = false
  done.value = 0
  created.value = 0
  total.value = wanted.total
  failures.value = []

  try {
    for (const industry of wanted.industries) {
      await attempt(industry.name, () =>
        createIndustry({
          name: industry.name,
          description: industry.description,
          creator: industry.creator.length > 0 ? industry.creator : creator,
        }),
      )
    }

    for (const schema of wanted.schemas) {
      await attempt(schema.name, () =>
        createSchema({
          name: schema.name,
          description: schema.description,
          type: schema.type,
          scheme: schema.scheme,
          creator: schema.creator.length > 0 ? schema.creator : creator,
          /*
           * The API wants industries here as numeric identifiers it never hands out, so an empty list is
           * sent and the schema is declared globally - the same thing the create dialog does.
           */
          industries: [],
        }),
      )
    }

    /*
     * The register is read again before the assumptions are written, because the two passes above have just
     * created industries and schemas whose identifiers this client had never seen. A bundle names things
     * rather than identifying them, and a name is the road least likely to be paved - so the names are
     * turned back into identifiers here, and only the ones that cannot be placed are sent as names.
     */
    if (wanted.industries.length > 0 || wanted.schemas.length > 0) {
      try {
        await load(true)
      } catch (error) {
        reportError(error)
      }
    }

    const resolve = {
      schema: nameResolver(schemas.value),
      industry: nameResolver(industries.value),
    }

    for (const assumption of wanted.assumptions) {
      await attempt(assumption.name, () =>
        createAssumption(assumptionDraft(assumption, creator, resolve)),
      )
    }
  } finally {
    running.value = false
    finished.value = true
  }

  if (created.value > 0) {
    /*
     * Read whole one last time, so that the rows just written are in it as well - the reading above the
     * assumptions happened before a single one of them existed.
     */
    try {
      await load(true)
    } catch (error) {
      reportError(error)
    }
    emit('restored')
  }

  notify(
    failures.value.length === 0
      ? t('import.doneClean', { created: created.value, total: total.value })
      : t('import.done', {
          created: created.value,
          total: total.value,
          failed: failures.value.length,
        }),
    failures.value.length === 0 ? 'success' : 'warning',
  )
}

const close = (open: boolean) => {
  if (running.value) {
    return
  }

  emit('update:modelValue', open)
}
</script>

<style scoped>
.import {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.import__note,
.import__muted {
  font-size: 0.8125rem;
  color: rgb(var(--v-theme-app-muted));
  line-height: 1.5;
}

.import__line {
  font-size: 0.875rem;
}

.import__failures {
  border: 0.0625rem solid rgba(var(--v-theme-error), 0.4);
  border-radius: 0.5rem;
  padding: 0.75rem;
  font-size: 0.8125rem;
  max-block-size: 12rem;
  overflow-y: auto;
}

.import__failures-title {
  font-weight: 600;
  padding-block-end: 0.25rem;
}

.import__failures ul {
  padding-inline-start: 1.25rem;
}
</style>
