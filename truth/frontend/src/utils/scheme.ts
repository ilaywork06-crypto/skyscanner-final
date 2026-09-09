/**
 * Reading and writing the free form dictionaries a schema declares its attributes as.
 *
 * Reading is deliberately generous - a field named `key`, `name` or `field` is the same field, and a display
 * name written as `label` or `title` is still a display name - because the service stores whatever it is
 * handed and a schema may have been written by a script or by hand. Writing is strict: a field goes out
 * carrying the five keys every field must have and the extra ones its own type calls for, and nothing else.
 */

import type { FieldType, JsonValue } from '@truth-platform/core-ui'
import { humanizeKey, language } from '@truth-platform/core-ui'

import type { Scheme, SchemeField, SchemeFieldType, StoredScheme } from '@/models/scheme'

/** The keys a stored field may name its own key with, in the order they are believed. */
const KEY_ALIASES: string[] = ['key', 'name', 'field', 'field_name', 'id']

/** The keys a stored field may carry its display name under. */
const NAME_ALIASES: string[] = ['display_name', 'displayName', 'label', 'title', 'display', 'caption']

/**
 * The keys a stored field may carry its Hebrew display name under.
 *
 * Read as generously as every other alias, and for the same reason: a schema is written by hand or by a
 * script somewhere else, so the client recognises the spellings somebody would plausibly have used rather
 * than insisting on one nobody was told about.
 */
const HEBREW_NAME_ALIASES: string[] = [
  'display_name_he',
  'displayNameHe',
  'display_name_hebrew',
  'label_he',
  'title_he',
  'name_he',
  'he',
  'hebrew',
]

/** The keys a stored field may name its type with. */
const TYPE_ALIASES: string[] = ['type', 'field_type', 'data_type', 'kind']

/** The keys a stored field may offer its vocabulary under. */
const OPTION_ALIASES: string[] = ['options', 'choices', 'enum', 'values', 'allowed', 'allowed_values']

/** The keys a stored field may mark itself required with. */
const REQUIRED_ALIASES: string[] = ['required', 'mandatory', 'is_required']

/** The keys a stored field may mark itself as holding several values with. */
const ARRAY_ALIASES: string[] = ['array', 'multiple', 'is_list', 'many', 'repeated']

/** What each spelling of a type read off a stored field is understood as. */
const TYPE_BY_NAME: Record<string, SchemeFieldType> = {
  string: 'string',
  str: 'string',
  text: 'string',
  boolean: 'boolean',
  bool: 'boolean',
  confined_number: 'confined_number',
  'confined number': 'confined_number',
  number: 'confined_number',
  int: 'confined_number',
  integer: 'confined_number',
  confined_float: 'confined_float',
  'confined float': 'confined_float',
  float: 'confined_float',
  double: 'confined_float',
  decimal: 'confined_float',
  enum: 'enum',
  select: 'enum',
  choice: 'enum',
  ultra_enum: 'ultra_enum',
  'ultra enum': 'ultra_enum',
  ultraenum: 'ultra_enum',
  date: 'date',
  datetime: 'date',
  multi_field: 'multi_field',
  'multi field': 'multi_field',
  multifield: 'multi_field',
}

/**
 * The keys this client owns on a stored field, which are the ones it writes and therefore may overwrite.
 *
 * Everything else a field carries is somebody else's and is carried back out untouched. The list is the
 * spellings this client would ever write, plus the aliases it reads them under - a field read through the
 * alias `label` and written back under `display_name` would otherwise go out carrying both, one of them
 * stale.
 */
const OWNED_KEYS: Set<string> = new Set([
  ...KEY_ALIASES,
  ...NAME_ALIASES,
  ...HEBREW_NAME_ALIASES,
  ...TYPE_ALIASES,
  ...OPTION_ALIASES,
  ...REQUIRED_ALIASES,
  ...ARRAY_ALIASES,
  'min',
  'max',
  'step',
])

/** What a field whose type cannot be read is treated as, which is the type that holds anything. */
const FALLBACK_TYPE: SchemeFieldType = 'string'

/** The spellings of a list type, which say how many values a field holds rather than what kind they are. */
const ARRAY_TYPE_NAMES: string[] = ['list', 'array', 'set', 'tuple', 'sequence']

/** How each kind of attribute is rendered, which is the vocabulary the table and the forms are built in. */
const RENDER_TYPES: Record<SchemeFieldType, FieldType> = {
  string: 'string',
  boolean: 'boolean',
  confined_number: 'integer',
  confined_float: 'number',
  enum: 'enum',
  /* An ultra enum is an enumeration, so it is picked from a list and painted as a chip like any other. */
  ultra_enum: 'enum',
  date: 'date',
  /*
   * A multi field holds a value made of several, and nothing here knows what those are. It is therefore
   * painted as the structure it is - readable, openable, and whole - rather than flattened into a word that
   * would claim to be the value. That is the honest rendering until the shape of one is written down.
   */
  multi_field: 'json',
}

/** Which kinds carry bounds and an increment, and are typed as numbers wherever one is entered. */
const NUMERIC_TYPES: SchemeFieldType[] = ['confined_number', 'confined_float']

/**
 * Which kinds are declared with a vocabulary of their own.
 *
 * An ultra enum is an enumeration, so it is offered and stored with the list of values every enumeration
 * carries. Everything else it may hold beyond that is carried through as it was found rather than guessed
 * at, which is what `extras` is for.
 */
const OPTION_TYPES: SchemeFieldType[] = ['enum', 'ultra_enum']

/**
 * How one kind of attribute is rendered - the type the columns and the form inputs are chosen by.
 */
const renderType = (type: SchemeFieldType): FieldType => RENDER_TYPES[type] ?? 'string'

/**
 * Whether a kind of attribute is entered as a number, which decides how a typed value is stored.
 */
const isNumeric = (type: SchemeFieldType): boolean => NUMERIC_TYPES.includes(type)

/**
 * Whether a kind of attribute is drawn from a vocabulary declared with it.
 */
const hasOptions = (type: SchemeFieldType): boolean => OPTION_TYPES.includes(type)

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
 * Read one number out of a stored dictionary, or nothing where none was written.
 */
const readNumber = (raw: Record<string, JsonValue>, key: string): number | null => {
  const value = raw[key]
  if (typeof value === 'number') {
    return value
  }

  if (typeof value === 'string' && value.trim().length > 0) {
    const parsed = Number(value)

    return Number.isNaN(parsed) ? null : parsed
  }

  return null
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
 * A type is often written as a list of something - `list[str]`, `string[]` - which says two separate things
 * at once, so both are read out of it rather than the whole spelling being given up on.
 */
const readType = (raw: Record<string, JsonValue>): { type: SchemeFieldType; array: boolean } => {
  const written = readString(raw, TYPE_ALIASES)
  const declaredArray = readFlag(raw, ARRAY_ALIASES)

  if (written === null) {
    /* A field with a vocabulary and no stated type is an enumeration, whatever else it forgot to say. */
    return { type: readOptions(raw).length > 0 ? 'enum' : FALLBACK_TYPE, array: declaredArray }
  }

  const lowered = written.toLowerCase().trim()
  const inner = /^(?:list|array|set|tuple|sequence)\s*(?:\[|<|\bof\b)\s*([a-z_ ]+)/.exec(lowered)
  if (inner !== null) {
    return { type: TYPE_BY_NAME[inner[1].trim()] ?? FALLBACK_TYPE, array: true }
  }

  const suffixed = /^([a-z_ ]+?)\s*\[\s*\]$/.exec(lowered)
  if (suffixed !== null) {
    return { type: TYPE_BY_NAME[suffixed[1].trim()] ?? FALLBACK_TYPE, array: true }
  }

  if (ARRAY_TYPE_NAMES.includes(lowered)) {
    return { type: FALLBACK_TYPE, array: true }
  }

  return { type: TYPE_BY_NAME[lowered] ?? FALLBACK_TYPE, array: declaredArray }
}

/**
 * Assemble one field descriptor out of what was recognised in the dictionary it was stored as.
 */
const buildField = (input: {
  key: string
  displayName: string
  raw: Record<string, JsonValue>
  order: number
}): SchemeField => {
  const { type, array } = readType(input.raw)

  return {
    key: input.key,
    displayName: input.displayName,
    displayNameHebrew: readString(input.raw, HEBREW_NAME_ALIASES) ?? '',
    type,
    array,
    required: readFlag(input.raw, REQUIRED_ALIASES),
    options: hasOptions(type) ? readOptions(input.raw) : [],
    min: isNumeric(type) ? readNumber(input.raw, 'min') : null,
    max: isNumeric(type) ? readNumber(input.raw, 'max') : null,
    step: isNumeric(type) ? readNumber(input.raw, 'step') : null,
    order: input.order,
    extras: Object.fromEntries(
      Object.entries(input.raw).filter(([key]) => !OWNED_KEYS.has(key)),
    ),
  }
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

    return buildField({ key, displayName: humanizeKey(key), raw: { type: written }, order })
  }

  if (named === null) {
    return null
  }

  return buildField({ key: named, displayName: readString(raw, NAME_ALIASES) ?? humanizeKey(named), raw, order })
}

/**
 * Read a whole stored scheme into the descriptors the forms and the columns are built from.
 */
const readScheme = (stored: StoredScheme | null | undefined): Scheme => ({
  fields: (stored?.fields ?? [])
    .filter((raw): raw is Record<string, JsonValue> => raw !== null && typeof raw === 'object' && !Array.isArray(raw))
    .map((raw, index) => readField(raw, index))
    .filter((field): field is SchemeField => field !== null),
})

/**
 * Write one field into the dictionary the service stores it as.
 *
 * The five keys every field must carry are always written, the flags included: a field the user left
 * unticked is `false` rather than absent, because a missing flag is not the same thing as a false one and
 * the service reads it as neither. Past those, a field carries only what its own type calls for.
 */
const writeField = (field: SchemeField): Record<string, JsonValue> => {
  const raw: Record<string, JsonValue> = {
    /*
     * Whatever the field carried that this client does not own goes out first, so that the keys it does own
     * are written over the top of it and can never be shadowed by a stale copy of themselves.
     */
    ...field.extras,
    key: field.key.trim(),
    display_name: field.displayName.trim(),
    type: field.type,
    required: field.required,
    array: field.array,
  }

  /* A Hebrew name is written only when there is one, so a schema declared without one stays as it was. */
  if (field.displayNameHebrew.trim().length > 0) {
    raw.display_name_he = field.displayNameHebrew.trim()
  }

  if (hasOptions(field.type)) {
    raw.options = [...field.options]
  }

  if (isNumeric(field.type)) {
    /* The bounds and the increment are each optional, so only the ones actually set are written. */
    if (field.min !== null) {
      raw.min = field.min
    }
    if (field.max !== null) {
      raw.max = field.max
    }
    if (field.step !== null) {
      raw.step = field.step
    }
  }

  return raw
}

/**
 * Write a scheme back into the shape the service stores it in.
 *
 * The constraint list goes out empty under the spelling the service reads on the way in - which is not the
 * spelling it answers with - because the service does not support constraints yet.
 */
const writeScheme = (scheme: Scheme): StoredScheme => ({
  fields: scheme.fields.map((field) => writeField(field)),
  constrains: [],
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

/**
 * What one declared attribute is called in the language the interface is currently written in.
 *
 * A schema that declared a Hebrew name is read in Hebrew; one that did not keeps the name it was declared
 * under, in both languages, because that name is the register's own vocabulary rather than this client's.
 */
const fieldLabel = (field: SchemeField): string => {
  if (language.value === 'he' && field.displayNameHebrew.trim().length > 0) {
    return field.displayNameHebrew.trim()
  }

  return field.displayName.length > 0 ? field.displayName : humanizeKey(field.key)
}

export {
  HEBREW_NAME_ALIASES,
  OPTION_TYPES,
  fieldLabel,
  hasOptions,
  isNumeric,
  mergeFields,
  readField,
  readScheme,
  readType,
  renderType,
  writeField,
  writeScheme,
}
