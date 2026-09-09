/**
 * The shared context every generated cell renderer reads, holding the callbacks the table needs from its page.
 *
 * A renderer is handed to AG Grid by name and is mounted by the grid rather than by the page around it, so
 * there is no component above it to take its callbacks from. The page puts them here instead, and every
 * renderer - however deep in a panel of panels it ends up - reads the same object.
 */

import type { ICellRendererParams } from 'ag-grid-community'
import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'

import type { Artifact, TaxonomyItem } from '../models/common'
import type { GridRow } from '../models/grid'
import { hashedToken } from './palette'

interface GridContext {
  /** The vocabulary the rows are grouped by, which is what a chip of one of its members is coloured from. */
  taxonomy: TaxonomyItem[]
  expandedIds: string[]
  toggleExpanded: (rowId: string) => void
  /** Open the row itself - its own page, wherever the product keeps one. */
  openRow: (rowId: string) => void
  /*
   * Narrow the table to a set of values of one column, from inside a panel opened underneath a row.
   *
   * A panel is where a reader finally sees what a row is filed under, and "show me the others like this" is
   * the question they ask next. Without this they would have to remember the value, close the panel, find
   * the column and type it back in - so the panel offers it, and it is written into the column's own filter
   * rather than alongside it, which is what makes the chip above the table and the header agree about it.
   */
  filterBy: (colId: string, values: string[]) => void
  openArtifact: (artifact: Artifact) => void
  downloadArtifact: (artifact: Artifact) => void
  findRow: (rowId: string) => GridRow | undefined
  /*
   * Which colour a value of a coloured column is painted in.
   *
   * What a status means is the product's own business - one product's "partial" is an amber half success and
   * another's is a state of parsing - so the mapping is handed in rather than held here, and a product that
   * has nothing to say falls back to colouring the value by its own name.
   */
  tokenFor: (value: string, palette: string | undefined) => string
  /*
   * How tall the panel of one expanded row turned out to be, once it has rendered and can be measured.
   *
   * A row of the grid is given its height before anything is drawn inside it, so the table can only guess
   * at the panel out of what it knows about the row - and a guess is either short, which cuts the panel
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
  taxonomy: [],
  expandedIds: [],
  toggleExpanded: () => undefined,
  openRow: () => undefined,
  filterBy: () => undefined,
  openArtifact: () => undefined,
  downloadArtifact: () => undefined,
  findRow: () => undefined,
  tokenFor: (value) => hashedToken(value),
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
 * away from the table that knows what was searched for - a detail panel, a nested table - none of which has
 * any business carrying a search term through itself. The row offers the term and whoever paints matches
 * takes it, which is also what makes the very same components render unpainted on a detail page: nothing
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
