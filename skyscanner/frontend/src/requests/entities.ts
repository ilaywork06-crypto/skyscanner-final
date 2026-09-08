/**
 * Every call that reads or changes the entities nested inside an event.
 */

import type { EntityCreateRequest, EntityResponse, EntityUpdateRequest } from '@/models/entity'
import { client } from '@/requests/client'

/**
 * Build the address of the entity collection of one event.
 */
const entitiesPath = (eventId: string): string => `/events/${eventId}/entities`

/**
 * Read the entities of one event, optionally narrowed to a single entity type.
 */
const listEntities = async (eventId: string, entityType?: string): Promise<EntityResponse[]> => {
  const response = await client.get<EntityResponse[]>(entitiesPath(eventId), {
    params: entityType === undefined ? {} : { entity_type: entityType },
  })

  return response.data
}

/**
 * Attach a new entity to an event that already exists.
 */
const addEntity = async (eventId: string, request: EntityCreateRequest): Promise<EntityResponse> => {
  const response = await client.post<EntityResponse>(entitiesPath(eventId), request)

  return response.data
}

/**
 * Change an entity, which is how the parsed products of a telemetry reach the system after the raw upload.
 */
const updateEntity = async (
  eventId: string,
  entityId: string,
  request: EntityUpdateRequest,
): Promise<EntityResponse> => {
  const response = await client.patch<EntityResponse>(`${entitiesPath(eventId)}/${entityId}`, request)

  return response.data
}

/**
 * Remove an entity from an event.
 */
const deleteEntity = async (eventId: string, entityId: string): Promise<void> => {
  await client.delete(`${entitiesPath(eventId)}/${entityId}`)
}

export { addEntity, deleteEntity, listEntities, updateEntity }
