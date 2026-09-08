/**
 * The vocabulary of the register - every industry and every schema, read once and shared by every page.
 *
 * The assumptions are deliberately not here. They are read one window at a time, by whichever table is
 * showing them, and are never held whole: the register is expected to grow past anything a browser could be
 * handed, and a client that held it all would stop working at exactly the size the register becomes worth
 * having. What is held here is the two collections that are bounded by how many people write into them -
 * the industries and the declarations - because the columns of the table are built out of the declarations
 * and reading them again for every question would be a round trip nobody asked for.
 */

import { computed, ref, shallowRef, type ComputedRef, type Ref, type ShallowRef } from 'vue'

import type { Industry } from '@/models/industry'
import type { SchemaDetail, SchemaSummary } from '@/models/schema'
import type { Scheme, SchemeField } from '@/models/scheme'
import { readAllIndustries } from '@/requests/industries'
import { readAllSchemas, readLatestSchema } from '@/requests/schemas'
import { mergeFields, readScheme } from '@/utils/scheme'

interface RegisterState {
  industries: Ref<Industry[]>
  schemas: Ref<SchemaSummary[]>
  /** The declarations of every schema, read once and keyed by identifier. */
  schemaDetails: ShallowRef<Map<string, SchemaDetail>>
  loading: Ref<boolean>
  errorMessage: Ref<string>
  /** Every attribute any schema of the register declares, which is what the dynamic columns are built from. */
  fields: ComputedRef<SchemeField[]>
  load: (force?: boolean) => Promise<void>
  readSchemaDetail: (schemaId: string) => Promise<SchemaDetail>
  findIndustry: (identifier: string) => Industry | undefined
  schemeOf: (schemaId: string) => Scheme
}

const industries = ref<Industry[]>([])
const schemas = ref<SchemaSummary[]>([])
const schemaDetails = shallowRef<Map<string, SchemaDetail>>(new Map())
const loading = ref<boolean>(false)
const errorMessage = ref<string>('')

let loaded = false
let loadingPromise: Promise<void> | null = null

/**
 * Read every declaration once, so that a schema named by several assumptions is fetched a single time.
 */
const loadSchemaDetails = async (summaries: SchemaSummary[]): Promise<void> => {
  /*
   * The declarations are read at the same time but stored in the order they were listed in, not the order
   * they happened to answer in. The columns of the table are built by walking this, so storing them as they
   * landed gave the table a different arrangement on every load - which is not something a reader should
   * have to notice.
   */
  const read = await Promise.all(
    summaries.map(async (summary): Promise<[string, SchemaDetail] | null> => {
      try {
        return [summary.id, await readLatestSchema(summary.id)]
      } catch {
        /* A declaration that cannot be read costs its own columns and nothing else, so the rest still loads. */
        return null
      }
    }),
  )

  schemaDetails.value = new Map(read.filter((entry): entry is [string, SchemaDetail] => entry !== null))
}

/**
 * Read the vocabulary the register is described by.
 */
const runLoad = async (): Promise<void> => {
  loading.value = true
  errorMessage.value = ''

  try {
    const [readIndustries, readSchemas] = await Promise.all([readAllIndustries(), readAllSchemas()])

    industries.value = readIndustries
    schemas.value = readSchemas
    loaded = true

    await loadSchemaDetails(readSchemas)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'The register could not be read'
    throw error
  } finally {
    loading.value = false
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

  /** An industry is addressed by its identifier in the routes and by its name in the payloads, so both work. */
  const findIndustry = (identifier: string): Industry | undefined =>
    industries.value.find((industry) => industry.id === identifier || industry.name === identifier)

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
    schemaDetails,
    loading,
    errorMessage,
    fields,
    load,
    readSchemaDetail,
    findIndustry,
    schemeOf,
  }
}

export type { RegisterState }
export { useRegister }
