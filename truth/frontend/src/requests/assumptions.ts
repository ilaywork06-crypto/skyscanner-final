/**
 * Every call around the assumptions - the window of the register a table is showing, and one assumption whole.
 *
 * Nothing here reads the register. The table asks a question and is handed the one window it is showing,
 * which is what lets a register of any size be worked with through a browser that could never hold it.
 */

import type { AssumptionDetail, AssumptionDraft, AssumptionRow } from '@/models/assumption'
import type { AssumptionPage, AssumptionQuery, Facet } from '@/models/query'
import { client } from '@/requests/client'

const ASSUMPTIONS_PATH = '/assumption'

/**
 * Ask the register the whole question the table is asking, and take back the one window it is showing.
 *
 * This is a POST because the question is a structure rather than a word. A filter model written into a query
 * string is a filter model waiting to be cut short by whichever proxy in the way has the shortest opinion
 * about how long an address may be.
 */
const queryAssumptions = async (query: AssumptionQuery): Promise<AssumptionPage> => {
  const response = await client.post<AssumptionPage>(`${ASSUMPTIONS_PATH}/query`, query)

  return response.data
}

/**
 * Read one window of the register as it stands, newest first and narrowed by nothing.
 */
const listAssumptions = async (offset: number, limit: number): Promise<AssumptionRow[]> => {
  const response = await client.get<AssumptionRow[]>(ASSUMPTIONS_PATH, { params: { offset, limit } })

  return response.data
}

/**
 * Read every value one column is known to hold, which is what its filter offers to pick from.
 *
 * The vocabulary is gathered off the register rather than off the declarations, so a column offers what is
 * actually there - including the values somebody wrote before a schema was revised to name them.
 */
const readFacet = async (key: string, industry: string | null): Promise<Facet> => {
  const response = await client.get<Facet>(`${ASSUMPTIONS_PATH}/facets/${encodeURIComponent(key)}`, {
    params: industry === null ? {} : { industry },
  })

  return response.data
}

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
 * Store a new assumption and hand back the identifier it was given.
 */
const createAssumption = async (draft: AssumptionDraft): Promise<string> => {
  const response = await client.post<{ id: string }>(ASSUMPTIONS_PATH, draft)

  return response.data.id
}

export { createAssumption, listAssumptions, queryAssumptions, readAssumption, readFacet, readLatestAssumption }
