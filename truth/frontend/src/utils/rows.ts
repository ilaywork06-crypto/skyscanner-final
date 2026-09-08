/**
 * Flattening an assumption into the row shape the generated columns address.
 */

import type { GridRow, JsonValue } from '@truth-platform/core-ui'

import type { AssumptionRow } from '@/models/assumption'

/**
 * Flatten one listed assumption into a row.
 *
 * The listing carries everything a row needs, so a row is complete the moment it arrives. It was not always
 * so: the rows used to be shown from a listing that carried neither the values nor the industries, and each
 * one filled itself in from a reading of its own afterwards.
 */
const assumptionToRow = (assumption: AssumptionRow): GridRow => ({
  id: assumption.id,
  name: assumption.name,
  assumption_text: assumption.assumption_text,
  proposing_party: assumption.proposing_party,
  tags: assumption.tags,
  validation_responsible_parties: assumption.validation_responsible_parties,
  revision: assumption.revision,
  creator: assumption.creator,
  created_at: assumption.created_at,
  schemas: assumption.schemas.map((schema) => schema.name),
  schema_ids: assumption.schemas.map((schema) => schema.id),
  industries: assumption.industries.map((industry) => industry.name),
  industry_ids: assumption.industries.map((industry) => industry.id),
  revision_reason: assumption.revision_reason,
  archived: assumption.archived,
  deleted: assumption.deleted,
  values: assumption.values as JsonValue,
})

export { assumptionToRow }
