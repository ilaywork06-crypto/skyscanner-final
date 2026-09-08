/**
 * Every call around the industries - the vocabulary the navigation and the assumption chips are built from.
 */

import type { Industry, IndustryDraft } from '@/models/industry'
import { client } from '@/requests/client'
import { readAll } from '@/requests/paging'

const INDUSTRIES_PATH = '/industry'

/**
 * Read one window of the industries.
 */
const listIndustries = async (offset: number, limit: number): Promise<Industry[]> => {
  const response = await client.get<Industry[]>(INDUSTRIES_PATH, { params: { offset, limit } })

  return response.data
}

/**
 * Read every registered industry.
 */
const readAllIndustries = async (onProgress?: (loaded: number) => void): Promise<Industry[]> =>
  readAll(listIndustries, onProgress)

/**
 * Read every industry together with how many assumptions name it.
 *
 * The counting is one pass over the register inside the service. It used to be done here, by walking every
 * assumption the client had read - which meant the count was wrong until the last of them had arrived, and
 * impossible once there were more of them than a browser could hold.
 */
const readIndustriesWithCounts = async (): Promise<Industry[]> =>
  readAll(async (offset, limit) => {
    const response = await client.get<Industry[]>(INDUSTRIES_PATH, {
      params: { offset, limit, with_counts: true },
    })

    return response.data
  })

/**
 * Read a single industry addressed by its identifier.
 */
const readIndustry = async (industryId: string): Promise<Industry> => {
  const response = await client.get<Industry>(`${INDUSTRIES_PATH}/${industryId}`)

  return response.data
}

/**
 * Read a single industry addressed by its name.
 */
const readIndustryByName = async (name: string): Promise<Industry> => {
  const response = await client.get<Industry>(`${INDUSTRIES_PATH}/name/${encodeURIComponent(name)}`)

  return response.data
}

/**
 * Register a new industry and hand back the identifier it was given.
 */
const createIndustry = async (draft: IndustryDraft): Promise<string> => {
  const response = await client.post<{ id: string }>(INDUSTRIES_PATH, draft)

  return response.data.id
}

export {
  createIndustry,
  listIndustries,
  readAllIndustries,
  readIndustriesWithCounts,
  readIndustry,
  readIndustryByName,
}
