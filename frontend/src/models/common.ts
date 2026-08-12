/**
 * The building blocks reused by most payloads of the API - stored files, dynamic values and the caller identity.
 */

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }

type ArtifactKind = 'raw' | 'parsed' | 'parsed_additional' | 'additional'

type FieldType =
  | 'string'
  | 'text'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'enum'
  | 'file'
  | 'json'

type EventStatus = 'draft' | 'raw' | 'parsed' | 'partial' | 'failed' | 'archived'

type EntityStatus = 'raw' | 'parsing' | 'parsed' | 'failed'

type ExperimentResult = 'successful' | 'partial' | 'failed'

type ParseState = 'all' | 'parsed' | 'not_parsed'

type FieldScope = 'event' | 'entity'

type ObjectTypeReference = {
  id: string
  name: string
}

type Artifact = {
  id: string
  name: string
  path: string
  descriptor: string
  kind: ArtifactKind
  suffix: string
  folder: string | null
  source: string | null
  size_bytes: number
  content_type: string
  checksum: string | null
  /** Who put the file into the bucket. Files stored before the field existed carry nothing. */
  uploaded_by: string | null
  created_at: string | null
  updated_at: string | null
}

type MetadataAttribute = {
  key: string
  value: JsonValue
  type: FieldType
}

interface OperationResult {
  success: boolean
  message: string
  affected: number
}

interface PageResponse<ItemT> {
  items: ItemT[]
  total: number
  page: number
  page_size: number
  pages: number
}

export type {
  Artifact,
  ArtifactKind,
  EntityStatus,
  EventStatus,
  ExperimentResult,
  FieldScope,
  FieldType,
  JsonValue,
  MetadataAttribute,
  ObjectTypeReference,
  OperationResult,
  PageResponse,
  ParseState,
}
