/**
 * The payloads of the dynamic field declarations that shape the create wizard and the generated columns.
 */

import type { FieldScope, FieldType, JsonValue } from './common'

interface FieldConstraint {
  name: string
  value: JsonValue
  message: string | null
}

type DependencyOperator = 'has_value' | 'is_empty' | 'equals' | 'one_of' | 'not_equals'

/**
 * A condition on another field that decides whether this one is asked for at all.
 *
 * The field it points at belongs to the same form, or, for a field of an entity, to the event that entity
 * hangs under - the only other form whose values are known while the entity is filled in.
 */
interface FieldDependency {
  field: string
  operator: DependencyOperator
  values: JsonValue[]
}

interface FieldMetadata {
  allowed_file_types: string[]
  options: string[]
  unit: string | null
  description: string | null
  placeholder: string | null
  group: string | null
}

interface FieldDefinition {
  id: string
  name: string
  key: string
  type: FieldType
  array: boolean
  default: JsonValue
  required: boolean
  scope: FieldScope
  industry: string | null
  entity_type: string | null
  metadata: FieldMetadata
  constraints: FieldConstraint[]
  depends_on: FieldDependency[]
  filterable: boolean
  sortable: boolean
  editable: boolean
  visible: boolean
  order: number
  created_at: string
  updated_at: string | null
  created_by: string | null
}

interface FieldValue {
  key: string
  value: JsonValue
}

export type {
  DependencyOperator,
  FieldConstraint,
  FieldDefinition,
  FieldDependency,
  FieldMetadata,
  FieldValue,
}
