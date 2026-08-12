/**
 * The payloads of the edit history - who changed an event or an entity, when, why and what moved.
 */

import type { JsonValue } from './common'

type RevisionTarget = 'event' | 'entity'

interface FieldChange {
  key: string
  label: string
  before: JsonValue
  after: JsonValue
}

interface Revision {
  id: string
  target: RevisionTarget
  event_id: string
  entity_id: string | null
  entity_name: string
  version: number
  reason: string
  changed_by: string
  changed_at: string
  changes: FieldChange[]
}

export type { FieldChange, Revision, RevisionTarget }
