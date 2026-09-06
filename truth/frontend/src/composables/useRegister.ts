/**
 * The register itself - every industry, every schema and every assumption, read once and shared by every page.
 *
 * The API answers one window of one collection at a time and offers no search, no filter and no ordering, so
 * the client holds the whole register and answers those questions itself. Reading it happens in two stages,
 * because the listing of the assumptions carries neither their values nor the industries they belong to:
 *
 *   1. the industries, the schemas and the listed assumptions arrive, and the table can be shown;
 *   2. every assumption is read on its own, several at a time, and the rows gain their values, their
 *      industries and the columns those values are shown in.
 *
 * The table is usable throughout the second stage rather than after it, which matters because that stage is
 * one request per assumption and there is no endpoint that would make it fewer.
 */

import { computed, ref, shallowRef, type ComputedRef, type Ref, type ShallowRef } from 'vue'

import type { AssumptionDetail, AssumptionRow, AssumptionSummary } from '@/models/assumption'
import type { Industry } from '@/models/industry'
import type { SchemaDetail, SchemaSummary } from '@/models/schema'
import type { Scheme, SchemeField } from '@/models/scheme'
import { readAllAssumptions, readAssumptionDetails, readLatestAssumption } from '@/requests/assumptions'
import { readAllIndustries } from '@/requests/industries'
import { readAllSchemas, readLatestSchema } from '@/requests/schemas'
import { mergeFields, readScheme } from '@/utils/scheme'

/** How far the reading of the register has got, so that the page can say so rather than spin in silence. */
interface LoadProgress {
  /** How many assumptions have been read on their own so far. */
  completed: number
  /** How many there are to read. */
  total: number
}

interface RegisterState {
  industries: Ref<Industry[]>
  schemas: Ref<SchemaSummary[]>
  assumptions: ShallowRef<AssumptionRow[]>
  /** The declarations of every schema, read once and keyed by identifier. */
  schemaDetails: ShallowRef<Map<string, SchemaDetail>>
  loading: Ref<boolean>
  completing: Ref<boolean>
  progress: Ref<LoadProgress>
  errorMessage: Ref<string>
  /** Every attribute any schema of the register declares, which is what the dynamic columns are built from. */
  fields: ComputedRef<SchemeField[]>
  load: (force?: boolean) => Promise<void>
  readSchemaDetail: (schemaId: string) => Promise<SchemaDetail>
  refreshAssumption: (assumptionId: string) => Promise<AssumptionDetail>
  findIndustry: (identifier: string) => Industry | undefined
  findAssumption: (assumptionId: string) => AssumptionRow | undefined
  schemeOf: (schemaId: string) => Scheme
}

const industries = ref<Industry[]>([])
const schemas = ref<SchemaSummary[]>([])
const assumptions = shallowRef<AssumptionRow[]>([])
const schemaDetails = shallowRef<Map<string, SchemaDetail>>(new Map())
const loading = ref<boolean>(false)
const completing = ref<boolean>(false)
const progress = ref<LoadProgress>({ completed: 0, total: 0 })
const errorMessage = ref<string>('')

let loaded = false
let loadingPromise: Promise<void> | null = null

/**
 * Replace one row of the register, keeping the array itself a fresh one so that the table notices.
 */
const replaceRow = (assumptionId: string, change: (row: AssumptionRow) => AssumptionRow): void => {
  assumptions.value = assumptions.value.map((row) => (row.id === assumptionId ? change(row) : row))
}

/**
 * Read every declaration once, so that a schema named by several assumptions is fetched a single time.
 */
const loadSchemaDetails = async (summaries: SchemaSummary[]): Promise<void> => {
  const details = new Map<string, SchemaDetail>()

  await Promise.all(
    summaries.map(async (summary) => {
      try {
        details.set(summary.id, await readLatestSchema(summary.id))
      } catch {
        /* A declaration that cannot be read costs its own columns and nothing else, so the rest still loads. */
      }
    }),
  )

  schemaDetails.value = details
}

/**
 * Read the whole register, then complete every assumption in the background.
 */
const runLoad = async (): Promise<void> => {
  loading.value = true
  errorMessage.value = ''

  try {
    const [readIndustries, readSchemas, listed] = await Promise.all([
      readAllIndustries(),
      readAllSchemas(),
      readAllAssumptions(),
    ])

    industries.value = readIndustries
    schemas.value = readSchemas
    assumptions.value = listed.map((summary: AssumptionSummary) => ({ ...summary, detail: null }))
    progress.value = { completed: 0, total: listed.length }
    loaded = true

    await loadSchemaDetails(readSchemas)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'The register could not be read'
    throw error
  } finally {
    loading.value = false
  }

  void completeAssumptions()
}

/**
 * Read every listed assumption on its own, so that the rows gain their values and their industries.
 *
 * This is deliberately not awaited by the loader: the table is rendered from the listing and fills in as the
 * readings land, rather than the page being held blank for one request per assumption.
 */
const completeAssumptions = async (): Promise<void> => {
  const pending = assumptions.value.filter((row) => row.detail === null).map((row) => row.id)
  if (pending.length === 0) {
    return
  }

  completing.value = true
  try {
    await readAssumptionDetails(pending, (detail) => {
      replaceRow(detail.id, (row) => ({ ...row, detail }))
      progress.value = { ...progress.value, completed: progress.value.completed + 1 }
    })
  } finally {
    completing.value = false
  }
}

/**
 * Expose the register, loading it the first time somebody asks for it.
 */
const useRegister = (): RegisterState => {
  /**
   * Read the register, and hand every caller during a load the very same one rather than starting another.
   */
  const load = async (force = false): Promise<void> => {
    if (loaded && !force) {
      return
    }

    if (loadingPromise !== null) {
      return loadingPromise
    }

    loadingPromise = runLoad().finally(() => {
      loadingPromise = null
    })

    return loadingPromise
  }

  /**
   * Read the declaration of one schema, from what is already held wherever possible.
   */
  const readSchemaDetail = async (schemaId: string): Promise<SchemaDetail> => {
    const held = schemaDetails.value.get(schemaId)
    if (held !== undefined) {
      return held
    }

    const detail = await readLatestSchema(schemaId)
    schemaDetails.value = new Map(schemaDetails.value).set(schemaId, detail)

    return detail
  }

  /**
   * Read one assumption again and put what came back on its row, after it was created or changed elsewhere.
   */
  const refreshAssumption = async (assumptionId: string): Promise<AssumptionDetail> => {
    const detail = await readLatestAssumption(assumptionId)
    replaceRow(assumptionId, (row) => ({ ...row, detail }))

    return detail
  }

  /** An industry is addressed by its identifier in the routes and by its name in the payloads, so both work. */
  const findIndustry = (identifier: string): Industry | undefined =>
    industries.value.find((industry) => industry.id === identifier || industry.name === identifier)

  const findAssumption = (assumptionId: string): AssumptionRow | undefined =>
    assumptions.value.find((row) => row.id === assumptionId)

  const schemeOf = (schemaId: string): Scheme => readScheme(schemaDetails.value.get(schemaId)?.scheme)

  /*
   * Every attribute the register knows about, which is the union of what its schemas declare. A key declared
   * by two schemas is one column, because an assumption carries one value under it either way.
   */
  const fields = computed<SchemeField[]>(() =>
    mergeFields([...schemaDetails.value.values()].map((detail) => readScheme(detail.scheme))),
  )

  return {
    industries,
    schemas,
    assumptions,
    schemaDetails,
    loading,
    completing,
    progress,
    errorMessage,
    fields,
    load,
    readSchemaDetail,
    refreshAssumption,
    findIndustry,
    findAssumption,
    schemeOf,
  }
}

export type { LoadProgress, RegisterState }
export { useRegister }
