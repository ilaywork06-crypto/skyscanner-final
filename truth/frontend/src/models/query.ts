/**
 * The question the table asks the register, and the answer it gets back.
 *
 * Every part of this is answered by the service rather than in the browser. The register is expected to hold
 * far more assumptions than a browser can be handed, so what arrives is one window of an answer and the size
 * of the whole of it - never the register itself.
 */

import type { FilterCondition, SortSpecification } from '@truth-platform/core-ui'

import type { AssumptionRow } from './assumption'

/** Everything the table is asking at once. */
interface AssumptionQuery {
  search: string | null
  /** The industry the answer is narrowed to, by identifier or by name, or nothing for the whole register. */
  industry: string | null
  filters: FilterCondition[]
  sort: SortSpecification[]
  offset: number
  limit: number
  /**
   * Whether the answer counts the whole match as well as returning the window.
   *
   * A table needs the count to draw its pager. Anything walking the answer in blocks - an export, say - knows
   * it has reached the end when a block comes back short, and counting again for every block doubles the work
   * of the whole walk for something already known.
   */
  include_total?: boolean
}

/** One window of an answer, and how many assumptions the whole of it holds. */
interface AssumptionPage {
  rows: AssumptionRow[]
  total: number
  offset: number
  limit: number
}

/** Every value one column is known to hold, which is what its filter offers to pick from. */
interface Facet {
  key: string
  values: string[]
  /** Whether the register holds more values than were gathered, so the filter says what it is offering. */
  truncated: boolean
}

export type { AssumptionPage, AssumptionQuery, Facet }
