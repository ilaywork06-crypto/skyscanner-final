/**
 * The payloads of the industries, rendered as the tabs above the inventory table and as the industry overview page.
 */

interface Industry {
  id: string
  key: string
  name: string
  description: string
  color: string
  /** The modules an entity of this industry may name. Empty means any text is accepted. */
  modules: string[]
  event_count: number
  created_at: string
}

interface IndustryCreateRequest {
  key: string
  name: string
  description: string
  color: string
  modules: string[]
}

interface IndustryUpdateRequest {
  name?: string
  description?: string
  color?: string
  modules?: string[]
}

export type { Industry, IndustryCreateRequest, IndustryUpdateRequest }
