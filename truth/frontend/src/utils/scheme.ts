/**
 * Reading and writing the free form dictionaries a schema declares its attributes as.
 *
 * The API types a scheme's fields and constraints as `list[dict[str, JsonValue]]`, so the service will store
 * whatever it is handed and hand back whatever was stored. Nothing may therefore be assumed about the keys of
 * a stored field beyond what can be recognised. Reading is deliberately generous - a field written as `name`,
 * as `key` or as `field` is the same field - while writing is strict, so that a schema built in this client
 * reads back exactly as it was declared.
 */

import type { FieldType, JsonValue } from '@truth-platform/core-ui'
import { humanizeKey } from '@truth-platform/core-ui'

import type { ConstraintRule, Scheme, SchemeConstraint, SchemeField, StoredScheme } from '@/models/scheme'

/** The keys a stored field may name its own key with, in the order they are believed. */
const KEY_ALIASES: string[] = ['key', 'name', 'field', 'field_name', 'id']

/** The keys a stored field may name its label with. A field with none of these is labelled from its key. */
const LABEL_ALIASES: string[] = ['label', 'title', 'display_name', 'display', 'caption']

/** The keys a stored field may name its type with. */
const TYPE_ALIASES: string[] = ['type', 'field_type', 'data_type', 'kind', 'format']

/** The keys a stored field may offer its vocabulary under. */
const OPTION_ALIASES: string[] = ['options', 'choices', 'enum', 'values', 'allowed', 'allowed_values']

/** The keys a stored field may mark itself required with. */
const REQUIRED_ALIASES: string[] = ['required', 'mandatory', 'is_required']

/** The keys a stored field may mark itself as holding several values with. */
const ARRAY_ALIASES: string[] = ['array', 'multiple', 'is_list', 'many', 'repeated']

/** The keys a stored field may carry its description under. */
const DESCRIPTION_ALIASES: string[] = ['description', 'help', 'hint', 'doc', 'comment']

/** What each spelling of a type read off a stored field is understood as. */
const TYPE_BY_NAME: Record<string, FieldType> = {
  str: 'string',
  string: 'string',
  text: 'text',
  textarea: 'text',
  longtext: 'text',
  int: 'integer',
  integer: 'integer',
  number: 'number',
  float: 'number',
  double: 'number',
  decimal: 'number',
  bool: 'boolean',
  boolean: 'boolean',
  checkbox: 'boolean',
  date: 'date',
  datetime: 'datetime',
  timestamp: 'datetime',
  enum: 'enum',
  select: 'enum',
  choice: 'enum',
  json: 'json',
  object: 'json',
  dict: 'json',
  map: 'json',
  coordinate: 'coordinate',
  geo: 'coordinate',
  location: 'coordinate',
}

/** What a field whose type is unreadable is treated as, which is the type that renders anything. */
const FALLBACK_TYPE: FieldType = 'string'

/** The spellings of a list type, which say how many values a field holds rather than what kind they are. */
const ARRAY_TYPE_NAMES: string[] = ['list', 'array', 'set', 'tuple', 'sequence']

/**
 * Read one string out of a stored dictionary, trying each alias in turn.
 */
const readString = (raw: Record<string, JsonValue>, aliases: string[]): string | null => {
  for (const alias of aliases) {
    const value = raw[alias]
    if (typeof value === 'string' && value.trim().length > 0) {
      return value.trim()
    }
  }

  return null
}

/**
 * Read one flag out of a stored dictionary, accepting the several ways a flag gets written down.
 */
const readFlag = (raw: Record<string, JsonValue>, aliases: string[]): boolean => {
  for (const alias of aliases) {
    const value = raw[alias]
    if (typeof value === 'boolean') {
      return value
    }
    if (typeof value === 'string') {
      return ['true', 'yes', '1'].includes(value.trim().toLowerCase())
    }
    if (typeof value === 'number') {
      return value !== 0
    }
  }

  return false
}

/**
 * Read the vocabulary of an enumerated field, whichever key it was offered under.
 */
const readOptions = (raw: Record<string, JsonValue>): string[] => {
  for (const alias of OPTION_ALIASES) {
    const value = raw[alias]
    if (Array.isArray(value)) {
      return value.filter((item) => item !== null && typeof item !== 'object').map((item) => String(item))
    }
  }

  return []
}

/**
 * Work out what kind of value a field holds and whether it holds one of them or several.
 *
 * A type is often written as a list of something - `list[str]`, `string[]`, `array of number` - which says
 * two separate things at once, so both are read out of it rather than the whole spelling being given up on.
 */
const readType = (raw: Record<string, JsonValue>): { type: FieldType; array: boolean } => {
  const written = readString(raw, TYPE_ALIASES)
  const declaredArray = readFlag(raw, ARRAY_ALIASES)

  if (written === null) {
    /* A field with a vocabulary and no stated type is an enumeration, whatever else it forgot to say. */
    const type: FieldType = readOptions(raw).length > 0 ? 'enum' : FALLBACK_TYPE

    return { type, array: declaredArray }
  }

  const lowered = written.toLowerCase().trim()
  const inner = /^(?:list|array|set|tuple|sequence)\s*(?:\[|<|\bof\b)\s*([a-z_]+)/.exec(lowered)
  if (inner !== null) {
    return { type: TYPE_BY_NAME[inner[1]] ?? FALLBACK_TYPE, array: true }
  }

  const suffixed = /^([a-z_]+)\s*\[\s*\]$/.exec(lowered)
  if (suffixed !== null) {
    return { type: TYPE_BY_NAME[suffixed[1]] ?? FALLBACK_TYPE, array: true }
  }

  if (ARRAY_TYPE_NAMES.includes(lowered)) {
    return { type: FALLBACK_TYPE, array: true }
  }

  return { type: TYPE_BY_NAME[lowered] ?? FALLBACK_TYPE, array: declaredArray }
}

/**
 * Read one stored field, or nothing at all when there is no key to be found in it.
 *
 * A dictionary of exactly one entry is read as that entry - a schema written as `{"speed": "number"}` names
 * a field and its type in the shortest way anybody would think to write it, and refusing to understand that
 * would leave the whole schema unreadable over a spelling nobody promised to follow.
 */
const readField = (raw: Record<string, JsonValue>, order: number): SchemeField | null => {
  const entries = Object.entries(raw)
  const named = readString(raw, KEY_ALIASES)

  if (named === null && entries.length === 1 && typeof entries[0][1] === 'string') {
    const [key, written] = entries[0]

    return buildField({ key, label: humanizeKey(key), raw: { type: written }, order })
  }

  if (named === null) {
    return null
  }

  return buildField({ key: named, label: readString(raw, LABEL_ALIASES) ?? humanizeKey(named), raw, order })
}

/**
 * Assemble one field descriptor out of what was recognised in the dictionary it was stored as.
 */
const buildField = (input: {
  key: string
  label: string
  raw: Record<string, JsonValue>
  order: number
}): SchemeField => {
  const { type, array } = readType(input.raw)

  return {
    key: input.key,
    label: input.label,
    type,
    array,
    required: readFlag(input.raw, REQUIRED_ALIASES),
    default: input.raw.default ?? null,
    options: readOptions(input.raw),
    description: readString(input.raw, DESCRIPTION_ALIASES),
    unit: readString(input.raw, ['unit', 'units', 'measure']),
    placeholder: readString(input.raw, ['placeholder', 'example']),
    group: readString(input.raw, ['group', 'section', 'category']),
    order: input.order,
  }
}

/** What each spelling of a restriction is understood as. */
const RULE_BY_NAME: Record<string, ConstraintRule> = {
  required: 'required',
  mandatory: 'required',
  min: 'min',
  minimum: 'min',
  gte: 'min',
  max: 'max',
  maximum: 'max',
  lte: 'max',
  min_length: 'min_length',
  minlength: 'min_length',
  max_length: 'max_length',
  maxlength: 'max_length',
  pattern: 'pattern',
  regex: 'pattern',
  matches: 'pattern',
  one_of: 'one_of',
  oneof: 'one_of',
  in: 'one_of',
  enum: 'one_of',
}

/**
 * Read one stored restriction.
 *
 * A restriction is written either as a dictionary naming its rule - `{"field": "speed", "rule": "min",
 * "value": 0}` - or as the rule itself keyed by the field, which is the shorter way anybody writes one by
 * hand. Both are read; anything else is kept whole and enforced by the service rather than here.
 */
const readConstraint = (raw: Record<string, JsonValue>): SchemeConstraint => {
  const field = readString(raw, ['field', 'key', 'name', 'target']) ?? ''
  const written = readString(raw, ['rule', 'constraint', 'type', 'operator', 'kind'])
  const message = readString(raw, ['message', 'error', 'detail'])

  if (written !== null) {
    return {
      field,
      rule: RULE_BY_NAME[written.toLowerCase()] ?? 'unknown',
      value: raw.value ?? raw.values ?? null,
      message,
      raw,
    }
  }

  /* Nothing named a rule, so the rule is whichever recognised word the dictionary is keyed by. */
  for (const [key, value] of Object.entries(raw)) {
    const rule = RULE_BY_NAME[key.toLowerCase()]
    if (rule !== undefined) {
      return { field, rule, value, message, raw }
    }
  }

  return { field, rule: 'unknown', value: null, message, raw }
}

/**
 * Read a whole stored scheme into the descriptors the forms and the columns are built from.
 *
 * Both spellings of the constraint list are accepted, because the service takes one on the way in and gives
 * the other back on the way out.
 */
const readScheme = (stored: StoredScheme | null | undefined): Scheme => {
  const fields = (stored?.fields ?? [])
    .filter((raw): raw is Record<string, JsonValue> => raw !== null && typeof raw === 'object' && !Array.isArray(raw))
    .map((raw, index) => readField(raw, index))
    .filter((field): field is SchemeField => field !== null)

  const constraints = (stored?.constraints ?? stored?.constrains ?? [])
    .filter((raw): raw is Record<string, JsonValue> => raw !== null && typeof raw === 'object' && !Array.isArray(raw))
    .map((raw) => readConstraint(raw))

  return { fields, constraints }
}

/**
 * Write a scheme back into the shape the service stores it in.
 *
 * Only what a field actually says is written, so a schema of three plain attributes does not read back as
 * three dictionaries of a dozen nulls. The constraint list is written under the spelling the service reads on
 * the way in, which is not the spelling it answers with.
 */
const writeScheme = (scheme: Scheme): StoredScheme => ({
  fields: scheme.fields.map((field) => {
    const raw: Record<string, JsonValue> = {
      key: field.key,
      label: field.label,
      type: field.type,
    }
    if (field.array) {
      raw.array = true
    }
    if (field.required) {
      raw.required = true
    }
    if (field.options.length > 0) {
      raw.options = field.options
    }
    if (field.default !== null) {
      raw.default = field.default
    }
    if (field.description !== null) {
      raw.description = field.description
    }
    if (field.unit !== null) {
      raw.unit = field.unit
    }
    if (field.placeholder !== null) {
      raw.placeholder = field.placeholder
    }
    if (field.group !== null) {
      raw.group = field.group
    }

    return raw
  }),
  constrains: scheme.constraints.map((constraint) => constraint.raw),
})

/**
 * Merge the fields of several schemas into the one list an assumption declared by all of them carries.
 *
 * Two schemas may well declare the same key, and an assumption carries one value under it whichever schema
 * asked for it, so the first declaration wins and the rest are dropped rather than shown twice.
 */
const mergeFields = (schemes: Scheme[]): SchemeField[] => {
  const merged: SchemeField[] = []
  const seen = new Set<string>()

  schemes.forEach((scheme) => {
    scheme.fields.forEach((field) => {
      if (!seen.has(field.key)) {
        seen.add(field.key)
        merged.push({ ...field, order: merged.length })
      }
    })
  })

  return merged
}

export { mergeFields, readConstraint, readField, readScheme, readType, writeScheme }
