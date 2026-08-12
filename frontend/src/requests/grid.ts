/**
 * Every call that fetches a generated table - its column definitions, its blocks of rows and its filter options.
 */

import type { GeneratedGridConfiguration, GridRowsPage } from '@/models/grid'
import type { GridRowsRequest } from '@/models/query'
import { client } from '@/requests/client'

/**
 * Read the configuration of the inventory table for the global view or for a single industry.
 */
const readEventColumns = async (industry: string | null): Promise<GeneratedGridConfiguration> => {
  const response = await client.get<GeneratedGridConfiguration>('/grid/events/columns', {
    params: { industry: industry ?? undefined },
  })

  return response.data
}

/**
 * Read the configuration of the table that renders the entities of one event.
 */
const readEntityColumns = async (
  industry: string | null,
  entityType: string | null,
): Promise<GeneratedGridConfiguration> => {
  const response = await client.get<GeneratedGridConfiguration>('/grid/entities/columns', {
    params: { industry: industry ?? undefined, entity_type: entityType ?? undefined },
  })

  return response.data
}

/**
 * Read one block of inventory rows, already flattened into the shape the column definitions address.
 */
const readEventRows = async (request: GridRowsRequest): Promise<GridRowsPage> => {
  const response = await client.post<GridRowsPage>('/grid/events/rows', request)

  return response.data
}

/**
 * Read the values one column currently holds, so that the client can offer them as filter options.
 */
const readColumnValues = async (key: string): Promise<string[]> => {
  const response = await client.get<string[]>(`/grid/events/values/${key}`)

  return response.data
}

export { readColumnValues, readEntityColumns, readEventColumns, readEventRows }
