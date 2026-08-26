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
   * How tall the panel of one expanded row turned out to be, once it has rendered and can be measured.
   *
   * A row of the grid is given its height before anything is drawn inside it, so the table can only guess
   * at the panel out of what it knows about the event - and a guess is either short, which cuts the panel
   * off, or generous, which leaves a band of empty table underneath it. The panel measures itself instead
   * and says so, and the row is given exactly that.
   */
  reportDetailHeight: (parentId: string, height: number) => void
  /*
   * A cell has no way of asking what the rows on screen were searched for, and that is what it paints its
   * matches with, so the term travels with the rest of the context rather than every renderer reaching back
   * into the page that owns the table.
   */
  search: string
}

const EMPTY_CONTEXT: GridContext = {
  industries: [],
  expandedIds: [],
  toggleExpanded: () => undefined,
  openEvent: () => undefined,
  openArtifact: () => undefined,
  downloadArtifact: () => undefined,
  findRow: () => undefined,
  reportDetailHeight: () => undefined,
  search: '',
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
