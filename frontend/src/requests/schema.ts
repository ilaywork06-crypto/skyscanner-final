/**
 * Every call around the dynamic schema - the declared fields, the event types, the entity types and the industries.
 */

import type { FieldScope, FieldType, JsonValue, OptionalEventField } from '@/models/common'
import type { EntityType } from '@/models/entity'
import type { EventType } from '@/models/event'
import type { FieldConstraint, FieldDefinition, FieldDependency, FieldMetadata } from '@/models/field'
import type { Industry, IndustryUpdateRequest } from '@/models/industry'
import type { Platform, PlatformDraft } from '@/models/platform'
import { client } from '@/requests/client'

interface FieldQuery {
  scope: FieldScope
  industry?: string | null
  entityType?: string | null
  includeShared?: boolean
  /** Which half of the form is read - the object's own fields, its additional data, or both. */
  additional?: boolean | null
}

interface TypeDraft {
  key: string
  name: string
  description: string
  industries: string[]
  order: number
}

interface EventTypeDraft extends TypeDraft {
  fields: OptionalEventField[]
  /** The keys of the declared event fields the type asks for on top of the built in ones. */
  custom_fields: string[]
}

interface EntityTypeDraft extends TypeDraft {
  icon: string | null
}

/**
 * A declaration as the client sends it, which is the stored shape minus everything the service fills in.
 */
interface FieldDraft {
  name: string
  key: string
  type: FieldType
  array: boolean
  default: JsonValue
  required: boolean
  scope: FieldScope
  industry: string | null
  entity_type: string | null
  additional: boolean
  metadata: FieldMetadata
  constraints: FieldConstraint[]
  depends_on: FieldDependency[]
  filterable: boolean
  sortable: boolean
  editable: boolean
  visible: boolean
  order: number
}

interface IndustryDraft {
  key: string
  name: string
  description: string
  color: string
  modules: string[]
}

/**
 * Read the declarations that apply to a scope, so that the client can render the matching schema.
 */
const listFields = async (query: FieldQuery): Promise<FieldDefinition[]> => {
  const response = await client.get<FieldDefinition[]>('/fields', {
    params: {
      scope: query.scope,
      industry: query.industry ?? undefined,
      entity_type: query.entityType ?? undefined,
      include_shared: query.includeShared ?? true,
      additional: query.additional ?? undefined,
    },
  })

  return response.data
}

/**
 * Read the event types an industry may choose from.
 */
const listEventTypes = async (industry?: string | null): Promise<EventType[]> => {
  const response = await client.get<EventType[]>('/types/events', { params: { industry: industry ?? undefined } })

  return response.data
}

/**
 * Read the entity types an industry may choose from.
 */
const listEntityTypes = async (industry?: string | null): Promise<EntityType[]> => {
  const response = await client.get<EntityType[]>('/types/entities', { params: { industry: industry ?? undefined } })

  return response.data
}

/**
 * Read the platforms an industry may name on its events.
 */
const listPlatforms = async (industry?: string | null): Promise<Platform[]> => {
  const response = await client.get<Platform[]>('/types/platforms', {
    params: { industry: industry ?? undefined },
  })

  return response.data
}

/**
 * Declare a new platform the create wizard offers for the industries it belongs to.
 */
const createPlatform = async (draft: PlatformDraft): Promise<Platform> => {
  const response = await client.post<Platform>('/types/platforms', draft)

  return response.data
}

/**
 * Declare a new event type the create wizard offers.
 */
const createEventType = async (draft: EventTypeDraft): Promise<EventType> => {
  const response = await client.post<EventType>('/types/events', draft)

  return response.data
}

/**
 * Declare a new entity type the event page groups its entities by.
 */
const createEntityType = async (draft: EntityTypeDraft): Promise<EntityType> => {
  const response = await client.post<EntityType>('/types/entities', draft)

  return response.data
}

/**
 * Remove a declared type, which hides it from the selectors without touching the documents that use it.
 */
const deleteType = async (typeId: string): Promise<void> => {
  await client.delete(`/types/${typeId}`)
}

/**
 * Declare a new dynamic field, which is what turns a key somebody invented into a question the forms ask.
 */
const createField = async (draft: FieldDraft): Promise<FieldDefinition> => {
  const response = await client.post<FieldDefinition>('/fields', draft)

  return response.data
}

/**
 * Remove a declared field, which hides its column and stops the forms asking for it.
 */
const deleteField = async (fieldId: string): Promise<void> => {
  await client.delete(`/fields/${fieldId}`)
}

/**
 * Read every registered industry together with the amount of events it holds.
 */
const listIndustries = async (): Promise<Industry[]> => {
  const response = await client.get<Industry[]>('/industries')

  return response.data
}

/**
 * Read a single industry addressed by its machine key.
 */
const createIndustry = async (draft: IndustryDraft): Promise<Industry> => {
  const response = await client.post<Industry>('/industries', draft)

  return response.data
}

/**
 * Change a registered industry, which is how the vocabulary of the entity origins is maintained.
 */
const updateIndustry = async (key: string, changes: IndustryUpdateRequest): Promise<Industry> => {
  const response = await client.patch<Industry>(`/industries/${key}`, changes)

  return response.data
}

/**
 * Read a single industry addressed by its machine key.
 */
const readIndustry = async (key: string): Promise<Industry> => {
  const response = await client.get<Industry>(`/industries/${key}`)

  return response.data
}

export type { EntityTypeDraft, EventTypeDraft, FieldDraft, FieldQuery, IndustryDraft, TypeDraft }
export {
  createEntityType,
  createEventType,
  createField,
  createIndustry,
  createPlatform,
  deleteField,
  deleteType,
  listEntityTypes,
  listEventTypes,
  listFields,
  listIndustries,
  listPlatforms,
  readIndustry,
  updateIndustry,
}
