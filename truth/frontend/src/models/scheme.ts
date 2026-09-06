/**
 * The attributes a schema declares, read out of the free form dictionaries the service stores them as.
 *
 * The API types a scheme as `list[dict[str, JsonValue]]` for both its fields and its constraints, which means
 * the service will hand back whatever was written into it and promises nothing about the shape. Everything
 * this client reads is therefore read through the descriptors below, and everything it writes is written in
 * the canonical shape of those descriptors - so a schema built here reads back exactly, while one written by
 * hand or by a script is still understood as far as its keys can be recognised.
 */

import type { FieldType, JsonValue } from '@truth-platform/core-ui'

/** One attribute of an assumption, as a schema declares it. */
interface SchemeField {
  /** The key the value is stored under in the assumption's own values. */
  key: string
  /** What the attribute is called where a person reads it. */
  label: string
  type: FieldType
  /** Whether the attribute holds several values rather than one. */
  array: boolean
  required: boolean
  default: JsonValue
  /** The vocabulary an enumerated attribute is drawn from, empty when it is not enumerated. */
  options: string[]
  description: string | null
  unit: string | null
  placeholder: string | null
  /** What the attribute is filed under in a form of many attributes, or nothing to leave it ungrouped. */
  group: string | null
  order: number
}

/** What kinds of restriction this client understands well enough to enforce before an assumption is sent. */
type ConstraintRule =
  | 'required'
  | 'min'
  | 'max'
  | 'min_length'
  | 'max_length'
  | 'pattern'
  | 'one_of'
  | 'unknown'

/**
 * One restriction a schema puts on one of its fields.
 *
 * A restriction this client does not recognise is kept rather than dropped - it is still shown wherever the
 * schema is read - and simply never fails anything, because the service is what enforces it in the end.
 */
interface SchemeConstraint {
  /** The field the restriction applies to, or nothing when it was written without naming one. */
  field: string
  rule: ConstraintRule
  value: JsonValue
  message: string | null
  /** What was written, kept whole so that a restriction nobody here understands can still be displayed. */
  raw: Record<string, JsonValue>
}

/** A whole scheme, as the client works with it once the stored dictionaries have been read. */
interface Scheme {
  fields: SchemeField[]
  constraints: SchemeConstraint[]
}

/** A scheme in the shape the service stores it, which is the shape it travels in. */
interface StoredScheme {
  fields: Record<string, JsonValue>[]
  /*
   * The service spells this "constrains" on the way in and "constraints" on the way out, so both are
   * declared and the reader accepts either. Neither is corrected here, because correcting one would mean
   * sending the service a key it does not read.
   */
  constraints?: Record<string, JsonValue>[]
  constrains?: Record<string, JsonValue>[]
}

export type { ConstraintRule, Scheme, SchemeConstraint, SchemeField, StoredScheme }
