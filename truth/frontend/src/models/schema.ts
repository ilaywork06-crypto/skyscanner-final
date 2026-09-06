/**
 * The payloads of the schemas, which declare what attributes an assumption carries.
 */

import type { Industry } from './industry'
import type { StoredScheme } from './scheme'

/** A schema as the listing hands it over, which is everything but the declaration itself. */
interface SchemaSummary {
  id: string
  name: string
  revision: number
  creator: string
  created_at: string
}

/** A schema read on its own, which carries the declaration and everything around it. */
interface SchemaDetail extends SchemaSummary {
  description: string
  revision_reason: string
  latest_revision: boolean
  scheme: StoredScheme
  archived: boolean
  deleted: boolean
  industries: Industry[]
}

/** What creating a schema asks for. */
interface SchemaDraft {
  name: string
  description: string
  /** The kind of schema, which the service holds as a number and offers no vocabulary for. */
  type: number
  scheme: StoredScheme
  creator: string
  /*
   * Which industries the schema belongs to, as the numeric identifiers the service wants here.
   *
   * Nothing in the API hands those numbers out - an industry is only ever read back with its uuid - so this
   * is sent empty, which is what leaves a schema reaching across every industry.
   */
  industries: number[]
}

/** What revising a schema asks for, which is a new declaration and the reason it was changed. */
interface SchemaRevisionDraft {
  creator: string
  revision_reason: string
  scheme: StoredScheme
}

export type { SchemaDetail, SchemaDraft, SchemaRevisionDraft, SchemaSummary }
