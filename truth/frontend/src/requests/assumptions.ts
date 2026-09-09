/**
 * Every call around the assumptions - the rows of the register and the reading of a single one.
 */

import type { AssumptionDetail, AssumptionDraft, AssumptionSummary } from '@/models/assumption'
import { client } from '@/requests/client'
import { readAll } from '@/requests/paging'

const ASSUMPTIONS_PATH = '/assumption'

/**
 * How many readings are in the air at once while the listed assumptions are being completed.
 *
 * The listing carries neither the values of an assumption nor the industries it belongs to, so every row has
 * to be read on its own before the table can filter or colour by either. Doing that one at a time makes a
 * register of two hundred assumptions two hundred round trips end to end; doing it without a ceiling opens
 * two hundred sockets at once and several browsers refuse past six.
 */
const DETAIL_CONCURRENCY = 6

/**
 * Read one window of the assumptions.
 */
const listAssumptions = async (offset: number, limit: number): Promise<AssumptionSummary[]> => {
  const response = await client.get<AssumptionSummary[]>(ASSUMPTIONS_PATH, { params: { offset, limit } })

  return response.data
}

/**
 * Read every assumption, as the listing hands them over.
 */
const readAllAssumptions = async (onProgress?: (loaded: number) => void): Promise<AssumptionSummary[]> =>
  readAll(listAssumptions, onProgress)

/**
 * Read one assumption whole, at the revision it is currently at.
 */
const readAssumption = async (assumptionId: string): Promise<AssumptionDetail> => {
  const response = await client.get<AssumptionDetail>(`${ASSUMPTIONS_PATH}/${assumptionId}`)

  return response.data
}

/**
 * Read the latest revision of one assumption, which is what its page and its panel are built from.
 */
const readLatestAssumption = async (assumptionId: string): Promise<AssumptionDetail> => {
  const response = await client.get<AssumptionDetail>(`${ASSUMPTIONS_PATH}/${assumptionId}/latest`)

  return response.data
}

/**
 * Complete a batch of listed assumptions by reading each of them, several at a time.
 *
 * One reading that fails does not take the batch down with it: the row it belongs to is simply left as the
 * listing gave it, which is a row that shows everything but its values and its industries. A register where
 * one assumption is unreadable is still a register the other rows can be worked with.
 */
const readAssumptionDetails = async (
  assumptionIds: string[],
  onLoaded: (detail: AssumptionDetail) => void,
  onFailed?: (assumptionId: string, error: Error) => void,
): Promise<void> => {
  let next = 0

  const worker = async (): Promise<void> => {
    while (next < assumptionIds.length) {
      const index = next
      next += 1
      const assumptionId = assumptionIds[index]
      try {
        onLoaded(await readLatestAssumption(assumptionId))
      } catch (error) {
        onFailed?.(assumptionId, error instanceof Error ? error : new Error('The assumption could not be read'))
      }
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(DETAIL_CONCURRENCY, assumptionIds.length) }, () => worker()),
  )
}

/**
 * Store a new assumption and hand back the identifier it was given.
 */
const createAssumption = async (draft: AssumptionDraft): Promise<string> => {
  const response = await client.post<{ id: string }>(ASSUMPTIONS_PATH, draft)

  return response.data.id
}

export {
  DETAIL_CONCURRENCY,
  createAssumption,
  listAssumptions,
  readAllAssumptions,
  readAssumption,
  readAssumptionDetails,
  readLatestAssumption,
}
