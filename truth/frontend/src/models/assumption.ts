/**
 * The payloads of the assumptions themselves - the rows of the table and the reading of a single one.
 */

import type { JsonValue } from '@truth-platform/core-ui'

import type { Industry } from './industry'
import type { SchemaDetail, SchemaSummary } from './schema'

/**
 * An assumption as the listing hands it over.
 *
 * The listing carries neither the values of the assumption nor the industries it belongs to, which is why
 * every row of the table is completed from its own reading before it can be filtered or coloured by either.
 */
interface AssumptionSummary {
  id: string
  name: string
  assumption_text: string
  proposing_party: string
  tags: string[]
  validation_responsible_parties: string[]
  revision: number
  creator: string
  created_at: string
  schemas: SchemaSummary[]
}

/** An assumption read on its own, which is the only shape carrying its values and its industries. */
interface AssumptionDetail extends Omit<AssumptionSummary, 'schemas'> {
  schemas: SchemaDetail[]
  values: Record<string, JsonValue>
  revision_reason: string
  /** The declarations of every schema of the assumption, merged by the service into one flat list. */
  aggregated_scheme: Record<string, string>[]
  archived: boolean
  deleted: boolean
  industries: Industry[]
}

/** What creating an assumption asks for. */
interface AssumptionDraft {
  name: string
  assumption_text: string
  proposing_party: string
  /** The schemas the assumption is declared by, each named by its uuid or by its name. */
  schemas: string[]
  values: Record<string, JsonValue>
  tags: string[]
  validation_responsible_parties: string[]
  creator: string
  /** The industries the assumption belongs to, each named by its uuid or by its name. */
  industries: string[]
  /** Reserved by the service and sent empty, because nothing in the API says what may go in it. */
  special_fields: Record<string, JsonValue>
}

/** What an assumption is called and where it came from, for the panel opened underneath its row. */
interface AssumptionRow extends AssumptionSummary {
  /** The reading of the assumption, once it has arrived. Rows are listed before they are completed. */
  detail: AssumptionDetail | null
}

export type { AssumptionDetail, AssumptionDraft, AssumptionRow, AssumptionSummary }
