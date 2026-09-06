/**
 * The payloads of the saved table templates, which restore the columns, filters and ordering of a view.
 */

import type { FieldScope } from './common'
import type { FilterCondition, SortSpecification } from './query'

interface TemplateColumn {
  key: string
  visible: boolean
  order: number
  width: number | null
  pinned: string | null
}

interface TableTemplate {
  id: string
  name: string
  description: string
  scope: FieldScope
  industry: string | null
  owner: string
  shared: boolean
  columns: TemplateColumn[]
  filters: FilterCondition[]
  sort: SortSpecification[]
  created_at: string
  updated_at: string | null
}

interface TemplateCreateRequest {
  name: string
  description: string
  scope: FieldScope
  industry: string | null
  shared: boolean
  columns: TemplateColumn[]
  filters: FilterCondition[]
  sort: SortSpecification[]
}

export type { TableTemplate, TemplateColumn, TemplateCreateRequest }
