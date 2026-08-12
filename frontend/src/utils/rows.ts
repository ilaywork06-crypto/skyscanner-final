/**
 * The helpers that read values out of the flattened grid rows, where dynamic values live under a nested key.
 */

import type { Artifact, JsonValue, MetadataAttribute } from '@/models/common'
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
 */
const toMetadataAttributes = (values: Record<string, JsonValue>): MetadataAttribute[] =>
  Object.entries(values)
    .filter(([, value]) => value !== null && value !== '' && !(Array.isArray(value) && value.length === 0))
    .map(([key, value]) => ({ key, value, type: 'string' }))

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
 * Flatten one entity into the row shape the generated entity columns address.
 */
const entityToRow = (entity: EntityResponse): GridRow => ({
  ...entity,
  object_type_name: entity.object_type.name,
  object_type_key: entity.object_type_key,
  files: [...entity.raw_files, ...entity.parsed_files, ...entity.parsed_additional_files],
  data: toValueMap(entity.metadata),
})

export { entityToRow, readArtifacts, readPath, readText, toMetadataAttributes, toValueMap }
