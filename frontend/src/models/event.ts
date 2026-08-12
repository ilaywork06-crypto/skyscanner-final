/**
 * The payloads of the events themselves - the rows of the inventory and the detail view of a single event.
 */

import type {
  Artifact,
  EventStatus,
  ExperimentResult,
  MetadataAttribute,
  ObjectTypeReference,
} from './common'
import type { EntityCreateRequest, EntityResponse } from './entity'

interface EventType {
  id: string
  key: string
  name: string
  description: string
  industry: string | null
}

interface EventSummary {
  id: string
  event_id: number
  reference_id: string
  name: string
  event_type: ObjectTypeReference[]
  industry: string
  platform: string
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
  platform: string
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
  platform?: string
  status?: EventStatus
  experiment_result?: ExperimentResult | null
  event_date?: string | null
  notes?: string
  additional_files?: Artifact[]
  metadata?: MetadataAttribute[]
}

export type { EventCreateRequest, EventDetail, EventSummary, EventType, EventUpdateRequest }
