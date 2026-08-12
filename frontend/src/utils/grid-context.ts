/**
 * The shared context every generated cell renderer reads, holding the callbacks the table needs from its page.
 */

import type { ICellRendererParams } from 'ag-grid-community'
import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'

import type { Artifact } from '@/models/common'
import type { GridRow } from '@/models/grid'
import type { Industry } from '@/models/industry'

interface GridContext {
  industries: Industry[]
  expandedIds: string[]
  toggleExpanded: (rowId: string) => void
  openEvent: (rowId: string) => void
  openArtifact: (artifact: Artifact) => void
  downloadArtifact: (artifact: Artifact) => void
  findRow: (rowId: string) => GridRow | undefined
  /*
   * A cell has no way of asking what the rows were searched for or which industry the table is narrowed to,
   * and both decide how it renders: the search term is what a cell paints its matches with, and the industry
   * is what an expanded panel is read against. They travel with the rest of the context so that no renderer
   * has to reach back into the page that owns the table.
   */
  search: string
  industryFilter: string | null
}

const EMPTY_CONTEXT: GridContext = {
  industries: [],
  expandedIds: [],
  toggleExpanded: () => undefined,
  openEvent: () => undefined,
  openArtifact: () => undefined,
  downloadArtifact: () => undefined,
  findRow: () => undefined,
  search: '',
  industryFilter: null,
}

/**
 * Read the shared context out of the parameters AG Grid hands to a cell renderer.
 */
const readContext = (params: ICellRendererParams<GridRow>): GridContext => {
  const candidate: GridContext | undefined = params.context

  return candidate ?? EMPTY_CONTEXT
}

/**
 * Read the identifier of the row a cell renderer is rendering.
 */
const readRowId = (params: ICellRendererParams<GridRow>): string =>
  params.data === undefined ? '' : String(params.data.id)

/**
 * The term the rows on screen were searched for, offered to whatever ends up rendering one of their values.
 *
 * An expanded row is a panel of tables of its own, and the cells at the far end of it are several components
 * away from the table that knows what was searched for - a detail panel, an entity table - none of which has
 * any business carrying a search term through itself. The row offers the term and whoever paints matches
 * takes it, which is also what makes the very same components render unpainted on the event page: nothing
 * there was searched for, so nothing there offers a term.
 */
const SEARCH_TERM: InjectionKey<Readonly<Ref<string>>> = Symbol('search-term')

/** What a surface that never searched anything answers with, so that its cells paint nothing. */
const NO_SEARCH_TERM: Readonly<Ref<string>> = ref('')

/**
 * Offer the term the rows underneath this component were searched for.
 */
const provideSearchTerm = (term: Readonly<Ref<string>>): void => {
  provide(SEARCH_TERM, term)
}

/**
 * Read the term the rows around this component were searched for, or nothing outside a searched table.
 */
const useSearchTerm = (): Readonly<Ref<string>> => inject(SEARCH_TERM, NO_SEARCH_TERM)

export type { GridContext }
export { EMPTY_CONTEXT, provideSearchTerm, readContext, readRowId, useSearchTerm }
