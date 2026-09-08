/**
 * The payloads of the assumptions themselves - the rows of the register and the reading of a single one.
 */

import type { JsonValue } from '@truth-platform/core-ui'

import type { Industry } from './industry'
import type { SchemaDetail, SchemaSummary } from './schema'

/**
 * An assumption as the register lists it, which is everything a row is drawn out of.
 *
 * The listing carries the values and the industries. It did not always: the register used to hand over rows
 * without either, and the client answered that by reading every listed assumption again on its own - one
 * request per row, which is a register that stops loading long before it stops growing.
 */
interface AssumptionRow {
  id: string
  name: string
  assumption_text: string
  proposing_party: string
  tags: string[]
  validation_responsible_parties: string[]
  revision: number
  revision_reason: string
  creator: string
  created_at: string
  schemas: SchemaSummary[]
  industries: Industry[]
  values: Record<string, JsonValue>
  archived: boolean
  deleted: boolean
}

/**
 * An assumption read on its own, which is the only shape carrying the declarations whole.
 */
interface AssumptionDetail extends Omit<AssumptionRow, 'schemas'> {
  schemas: SchemaDetail[]
  /** The declarations of every schema of the assumption, merged by the service into one flat list. */
  aggregated_scheme: Record<string, JsonValue>[]
  special_fields: Record<string, JsonValue>
}

/** What creating an assumption asks for. */
interface AssumptionDraft {
  name: string
  assumption_text: string
  proposing_party: string
  /** The schemas the assumption is declared by, each named by its identifier or by its name. */
  schemas: string[]
  values: Record<string, JsonValue>
  tags: string[]
  validation_responsible_parties: string[]
  creator: string
  /** The industries the assumption belongs to, each named by its identifier or by its name. */
  industries: string[]
  /** Reserved by the service and sent empty, because nothing in the API says what may go in it. */
  special_fields: Record<string, JsonValue>
}

export type { AssumptionDetail, AssumptionDraft, AssumptionRow }
