/**
 * Flattening an assumption into the row shape the generated columns address.
 */

import type { GridRow, JsonValue } from '@truth-platform/core-ui'

import type { AssumptionRow } from '@/models/assumption'

/**
 * Flatten one assumption into a row.
 *
 * A row is built from the listing whether or not the reading of the assumption has arrived, so the table can
 * be shown as soon as the register has been listed. The values and the industries appear on the row the
 * moment its reading lands, because those two are carried by nothing but the reading.
 */
const assumptionToRow = (assumption: AssumptionRow): GridRow => {
  const detail = assumption.detail

  return {
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
    industries: detail === null ? [] : detail.industries.map((industry) => industry.name),
    industry_ids: detail === null ? [] : detail.industries.map((industry) => industry.id),
    revision_reason: detail?.revision_reason ?? '',
    archived: detail?.archived ?? false,
    deleted: detail?.deleted ?? false,
    /** Whether the reading has landed, which is what tells a panel to wait rather than to show nothing. */
    complete: detail !== null,
    values: (detail?.values ?? {}) as JsonValue,
  }
}

export { assumptionToRow }
