/**
 * The payloads of the entities nested inside an event, such as the telemetries and the log collections.
 */

import type { Artifact, EntityStatus, MetadataAttribute, ObjectTypeReference } from './common'

interface EntityType {
  id: string
  key: string
  name: string
  description: string
  icon: string | null
  /** The industries the type belongs to. An empty list means every industry may use it. */
  industries: string[]
}

type EntityResponse = {
  id: string
  object_id: number
  name: string
  event_id: string
  object_type: ObjectTypeReference
  object_type_key: string
  module: string | null
  code_version: string | null
  status: EntityStatus
  notes: string
  upload_source: string
  requested_at: string | null
  received_at: string | null
  raw_files: Artifact[]
  parsed_files: Artifact[]
  parsed_additional_files: Artifact[]
  metadata: MetadataAttribute[]
  created_at: string
  updated_at: string | null
  created_by: string | null
  updated_by: string | null
}

interface EntityCreateRequest {
  name: string
  entity_type_key: string
  module: string | null
  code_version: string | null
  status: EntityStatus
  notes: string
  upload_source: string
  requested_at: string | null
  received_at: string | null
  raw_files: Artifact[]
  parsed_files: Artifact[]
  parsed_additional_files: Artifact[]
  metadata: MetadataAttribute[]
}

interface EntityUpdateRequest {
  /** Why the change is being made. The service records it in the edit history and refuses an empty one. */
  reason: string
  name?: string
  module?: string | null
  code_version?: string | null
  status?: EntityStatus
  notes?: string
  raw_files?: Artifact[]
  parsed_files?: Artifact[]
  parsed_additional_files?: Artifact[]
  metadata?: MetadataAttribute[]
}

export type { EntityCreateRequest, EntityResponse, EntityType, EntityUpdateRequest }
