/**
 * Every call that reads or changes the events of the inventory.
 */

import type { PageResponse } from '@/models/common'
import type { EventCreateRequest, EventDetail, EventSummary, EventUpdateRequest } from '@/models/event'
import type { SearchQuery } from '@/models/query'
import { client } from '@/requests/client'

const EVENTS_PATH = '/events'

/**
 * Read one page of the inventory the way the toolbar and the table asked for it.
 */
const searchEvents = async (query: SearchQuery): Promise<PageResponse<EventSummary>> => {
  const response = await client.post<PageResponse<EventSummary>>(`${EVENTS_PATH}/search`, query)

  return response.data
}

/**
 * Read a single event together with every entity nested inside it.
 */
const readEvent = async (eventId: string): Promise<EventDetail> => {
  const response = await client.get<EventDetail>(`${EVENTS_PATH}/${eventId}`)

  return response.data
}

/**
 * Store a new event with the files, the dynamic values and the entities the wizard collected.
 */
const createEvent = async (request: EventCreateRequest): Promise<EventDetail> => {
  const response = await client.post<EventDetail>(EVENTS_PATH, request)

  return response.data
}

/**
 * Change an event so that data revealed after the upload can be filled in later on.
 */
const updateEvent = async (eventId: string, request: EventUpdateRequest): Promise<EventDetail> => {
  const response = await client.patch<EventDetail>(`${EVENTS_PATH}/${eventId}`, request)

  return response.data
}

/**
 * Remove an event together with the entities nested inside it.
 */
const deleteEvent = async (eventId: string): Promise<void> => {
  await client.delete(`${EVENTS_PATH}/${eventId}`)
}

export { createEvent, deleteEvent, readEvent, searchEvents, updateEvent }
