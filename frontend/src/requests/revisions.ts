/**
 * Every call that reads the edit history of an event or of one of its entities.
 */

import type { Revision } from '@/models/revision'
import { client } from '@/requests/client'

/**
 * Read the recorded edits of one event, newest first.
 */
const listEventRevisions = async (eventId: string, includeEntities = true): Promise<Revision[]> => {
  const response = await client.get<Revision[]>(`/events/${eventId}/revisions`, {
    params: { include_entities: includeEntities },
  })

  return response.data
}

/**
 * Read the recorded edits of one entity, newest first.
 */
const listEntityRevisions = async (eventId: string, entityId: string): Promise<Revision[]> => {
  const response = await client.get<Revision[]>(`/events/${eventId}/entities/${entityId}/revisions`)

  return response.data
}

export { listEntityRevisions, listEventRevisions }
