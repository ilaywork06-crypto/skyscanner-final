/**
 * Every call around the dynamic schema - the declared fields, the event types, the entity types and the industries.
 */

import type { FieldScope } from '@/models/common'
import type { EntityType } from '@/models/entity'
import type { EventType } from '@/models/event'
import type { FieldDefinition } from '@/models/field'
import type { Industry, IndustryUpdateRequest } from '@/models/industry'
import { client } from '@/requests/client'

interface FieldQuery {
  scope: FieldScope
  industry?: string | null
  entityType?: string | null
  includeShared?: boolean
}

interface EventTypeDraft {
  key: string
  name: string
  description: string
  industry: string | null
  order: number
}

interface EntityTypeDraft extends EventTypeDraft {
  icon: string | null
}

interface IndustryDraft {
  key: string
  name: string
  description: string
  color: string
  entity_origins: string[]
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

export type { EntityTypeDraft, EventTypeDraft, FieldQuery, IndustryDraft }
export {
  createEntityType,
  createEventType,
  createIndustry,
  deleteType,
  listEntityTypes,
  listEventTypes,
  listFields,
  listIndustries,
  readIndustry,
  updateIndustry,
}
