/**
 * Every call around the schemas - the declarations that decide what attributes an assumption carries.
 */

import type { SchemaDetail, SchemaDraft, SchemaRevisionDraft, SchemaSummary } from '@/models/schema'
import { client } from '@/requests/client'
import { readAll } from '@/requests/paging'

const SCHEMAS_PATH = '/schema'

/**
 * Read one window of the schemas.
 */
const listSchemas = async (offset: number, limit: number): Promise<SchemaSummary[]> => {
  const response = await client.get<SchemaSummary[]>(SCHEMAS_PATH, { params: { offset, limit } })

  return response.data
}

/**
 * Read every declared schema, as the listing hands them over.
 */
const readAllSchemas = async (onProgress?: (loaded: number) => void): Promise<SchemaSummary[]> =>
  readAll(listSchemas, onProgress)

/**
 * Read one schema whole, at the revision it is currently at.
 */
const readSchema = async (schemaId: string): Promise<SchemaDetail> => {
  const response = await client.get<SchemaDetail>(`${SCHEMAS_PATH}/${schemaId}`)

  return response.data
}

/**
 * Read the latest revision of one schema, which is what a form is built from.
 */
const readLatestSchema = async (schemaId: string): Promise<SchemaDetail> => {
  const response = await client.get<SchemaDetail>(`${SCHEMAS_PATH}/${schemaId}/latest`)

  return response.data
}

/**
 * Read one schema addressed by its name rather than by its identifier.
 */
const readSchemaByName = async (name: string): Promise<SchemaDetail> => {
  const response = await client.get<SchemaDetail>(`${SCHEMAS_PATH}/name/${encodeURIComponent(name)}`)

  return response.data
}

/**
 * Declare a new schema and hand back the identifier it was given.
 */
const createSchema = async (draft: SchemaDraft): Promise<string> => {
  const response = await client.post<{ id: string }>(SCHEMAS_PATH, draft)

  return response.data.id
}

/**
 * Revise a schema addressed by its identifier, which is the only way a declaration is ever changed.
 */
const createSchemaRevision = async (schemaId: string, draft: SchemaRevisionDraft): Promise<string> => {
  const response = await client.post<{ id: string }>(`${SCHEMAS_PATH}/${schemaId}/revisions`, draft)

  return response.data.id
}

/**
 * Revise a schema addressed by its name.
 */
const createSchemaRevisionByName = async (name: string, draft: SchemaRevisionDraft): Promise<string> => {
  const response = await client.post<{ id: string }>(
    `${SCHEMAS_PATH}/name/${encodeURIComponent(name)}/revisions`,
    draft,
  )

  return response.data.id
}

export {
  createSchema,
  createSchemaRevision,
  createSchemaRevisionByName,
  listSchemas,
  readAllSchemas,
  readLatestSchema,
  readSchema,
  readSchemaByName,
}
