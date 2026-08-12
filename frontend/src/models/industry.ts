/**
 * The payloads of the industries, rendered as the tabs above the inventory table and as the industry overview page.
 */

interface Industry {
  id: string
  key: string
  name: string
  description: string
  color: string
  /** The values an entity of this industry may name as its origin. Empty means any text is accepted. */
  entity_origins: string[]
  event_count: number
  created_at: string
}

interface IndustryCreateRequest {
  key: string
  name: string
  description: string
  color: string
  entity_origins: string[]
}

interface IndustryUpdateRequest {
  name?: string
  description?: string
  color?: string
  entity_origins?: string[]
}

export type { Industry, IndustryCreateRequest, IndustryUpdateRequest }
