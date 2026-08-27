/**
 * The helpers that read values out of the flattened grid rows, where dynamic values live under a nested key.
 */

import type { Artifact, FieldType, JsonValue, MetadataAttribute } from '@/models/common'
import type { EntityResponse } from '@/models/entity'
import type { GridRow } from '@/models/grid'

const PATH_SEPARATOR = '.'

/**
 * Read a value out of a row by the path a generated column addresses.
 */
const readPath = (row: GridRow, path: string): JsonValue => {
  const parts = path.split(PATH_SEPARATOR)
  let current: JsonValue = row as JsonValue

  for (const part of parts) {
    if (current === null || typeof current !== 'object' || Array.isArray(current)) {
      return null
    }
    current = current[part] ?? null
  }

  return current
}

/**
 * Read a value out of a row and render it as the text a cell shows.
 */
const readText = (row: GridRow, path: string): string => {
  const value = readPath(row, path)
  if (value === null || value === undefined) {
    return ''
  }

  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(', ')
  }

  if (typeof value === 'object') {
    return JSON.stringify(value)
  }

  return String(value)
}

/**
 * Read the artifacts a file shaped cell renders.
 */
const readArtifacts = (value: JsonValue): Artifact[] => {
  if (!Array.isArray(value)) {
    return []
  }

  return value.filter((item): item is Artifact => item !== null && typeof item === 'object' && !Array.isArray(item))
}

/**
 * Turn the dynamic values of a form into the attributes the API expects.
 *
 * A value that follows a declared field is typed by that declaration, and one the user invented on the spot
 * is typed by what they picked beside it. Saying so here is what lets a number stay a number and a date stay
 * a date once the value is read back, rather than everything coming home as text.
 */
const toMetadataAttributes = (
  values: Record<string, JsonValue>,
  types: Record<string, FieldType> = {},
): MetadataAttribute[] =>
  Object.entries(values)
    .filter(([, value]) => value !== null && value !== '' && !(Array.isArray(value) && value.length === 0))
    .map(([key, value]) => ({ key, value, type: types[key] ?? 'string' }))

/**
 * Turn the attributes of a stored document back into the flat mapping the generated columns address.
 */
const toValueMap = (attributes: MetadataAttribute[]): Record<string, JsonValue> => {
  const values: Record<string, JsonValue> = {}
  attributes.forEach((attribute) => {
    values[attribute.key] = attribute.value
  })

  return values
}

/**
 * Read back the type every stored value was written with, so that reopening a form offers the same input.
 */
const toValueTypeMap = (attributes: MetadataAttribute[]): Record<string, FieldType> => {
  const types: Record<string, FieldType> = {}
  attributes.forEach((attribute) => {
    types[attribute.key] = attribute.type
  })

  return types
}

/**
 * Flatten one entity into the row shape the generated entity columns address.
 */
const entityToRow = (entity: EntityResponse): GridRow => {
  /*
   * The entity table reads its files out of two columns - what came in raw, and everything the parsing
   * produced - so the products of the parsing are rolled in with the parsed files here exactly as the
   * events service rolls them in on its own side. The single list of every file is kept beside them,
   * because a saved view or a script may still be addressing it.
   */
  const parsed = [...entity.parsed_files, ...entity.parsed_additional_files]

  return {
    ...entity,
    object_type_name: entity.object_type.name,
    object_type_key: entity.object_type_key,
    parsed_all_files: parsed,
    files: [...entity.raw_files, ...parsed],
    data: toValueMap(entity.metadata),
  }
}

export { entityToRow, readArtifacts, readPath, readText, toMetadataAttributes, toValueMap, toValueTypeMap }
