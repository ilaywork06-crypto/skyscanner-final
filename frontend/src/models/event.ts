/**
 * The payloads of the events themselves - the rows of the inventory and the detail view of a single event.
 */

import type {
  Artifact,
  EventStatus,
  ExperimentResult,
  MetadataAttribute,
  ObjectTypeReference,
  OptionalEventField,
} from './common'
import type { EntityCreateRequest, EntityResponse } from './entity'

interface EventType {
  id: string
  key: string
  name: string
  description: string
  /** The industries the type belongs to. An empty list means every industry may use it. */
  industries: string[]
  /** The built in event fields this type asks for on top of the ones every event carries. */
  fields: OptionalEventField[]
  /** The keys of the declared event fields this type asks for on top of the built in ones. */
  custom_fields: string[]
}

interface EventSummary {
  id: string
  event_id: number
  reference_id: string
  name: string
  event_type: ObjectTypeReference[]
  industry: string
  platforms: string[]
  status: EventStatus
  experiment_result: ExperimentResult | null
  event_date: string | null
  created_at: string
  updated_at: string | null
  notes: string
  additional_files: Artifact[]
  metadata: MetadataAttribute[]
  entity_counts: Record<string, number>
  created_by: string | null
  updated_by: string | null
}

interface EventDetail extends EventSummary {
  objects: EntityResponse[]
  upload_source: string
}

interface EventCreateRequest {
  name: string | null
  reference_id: string
  event_type_keys: string[]
  industry: string
  platforms: string[]
  status: EventStatus
  experiment_result: ExperimentResult | null
  event_date: string | null
  notes: string
  upload_source: string
  additional_files: Artifact[]
  metadata: MetadataAttribute[]
  entities: EntityCreateRequest[]
}

interface EventUpdateRequest {
  /** Why the change is being made. The service records it in the edit history and refuses an empty one. */
  reason: string
  name?: string
  reference_id?: string
  event_type_keys?: string[]
  industry?: string
  platforms?: string[]
  status?: EventStatus
  experiment_result?: ExperimentResult | null
  event_date?: string | null
  notes?: string
  additional_files?: Artifact[]
  metadata?: MetadataAttribute[]
}

export type { EventCreateRequest, EventDetail, EventSummary, EventType, EventUpdateRequest }
