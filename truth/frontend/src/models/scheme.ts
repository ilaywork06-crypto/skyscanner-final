/**
 * The attributes a schema declares, and the shape the service stores them in.
 *
 * The API types a scheme's fields as `list[dict[str, JsonValue]]`, so the service will hand back whatever was
 * written into it and promises nothing about the keys. Everything read here goes through the descriptors
 * below, generously enough that a schema written by hand or by a script is still understood; everything
 * written goes out in exactly the shape the service expects, and nothing else.
 */

import type { JsonValue } from '@truth-platform/core-ui'

/**
 * The kinds of attribute the service accepts.
 *
 * These are the spellings that travel on the wire, not labels - a type is stored as this exact string.
 */
type SchemeFieldType =
  | 'string'
  | 'boolean'
  | 'confined_number'
  | 'confined_float'
  | 'enum'
  | 'date'

/** One attribute of an assumption, as a schema declares it. */
interface SchemeField {
  /** The key the value is stored under in the assumption's own values. */
  key: string
  /** What the attribute is called where a person reads it. */
  displayName: string
  type: SchemeFieldType
  required: boolean
  /** Whether the attribute holds several values rather than one. */
  array: boolean
  /** The vocabulary an enumerated attribute is drawn from. Empty for every other kind. */
  options: string[]
  /** The bounds and the increment of a confined number. Nothing at all for every other kind. */
  min: number | null
  max: number | null
  step: number | null
  /** Where the attribute sits among its siblings. Held for laying out a form, never written. */
  order: number
}

/** A whole scheme, as the client works with it once the stored dictionaries have been read. */
interface Scheme {
  fields: SchemeField[]
}

/**
 * A scheme in the shape the service stores it, which is the shape it travels in.
 *
 * The constraint list is sent empty because the service does not support constraints yet. Both spellings are
 * declared because the service reads one on the way in and answers with the other.
 */
interface StoredScheme {
  fields: Record<string, JsonValue>[]
  constraints?: Record<string, JsonValue>[]
  constrains?: Record<string, JsonValue>[]
}

export type { Scheme, SchemeField, SchemeFieldType, StoredScheme }
