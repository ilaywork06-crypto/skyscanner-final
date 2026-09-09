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
  | 'ultra_enum'
  | 'date'
  | 'multi_field'

/** One attribute of an assumption, as a schema declares it. */
interface SchemeField {
  /** The key the value is stored under in the assumption's own values. */
  key: string
  /** What the attribute is called where a person reads it. */
  displayName: string
  /**
   * What the attribute is called on a Hebrew page, when whoever declared the schema said.
   *
   * The fixed columns of the table are this product's own words and are translated from its dictionary. The
   * declared ones are not: a schema is written by the people using the register, under names this client has
   * never seen, so the only place a Hebrew name for one of them could come from is the declaration itself.
   * A schema that carries none keeps its declared name in both languages, which is the honest answer -
   * inventing a translation of somebody's own vocabulary would be worse than leaving it alone.
   */
  displayNameHebrew: string
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
  /**
   * Everything else the stored field carried, kept exactly as it was found.
   *
   * A schema is stored as a free form dictionary and is written by people and scripts this client never
   * meets, so a field may carry keys it has no idea about - the parts of a kind of field this client does
   * not draw a form for yet, or something added to the schema after this was written. Writing only the keys
   * it recognises would quietly delete all of that the first time somebody revised the schema through this
   * client, which is the sort of loss nobody notices until the thing that needed the key stops working.
   *
   * So they are carried through untouched, and the keys this client does own are written over the top of
   * them. Held for the round trip, never edited here.
   */
  extras: Record<string, JsonValue>
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
