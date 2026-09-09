/**
 * Handing AG Grid the language the rest of the interface is written in.
 *
 * AG Grid draws a handful of words of its own - the overlay of an empty table, the entries of a column menu,
 * the sorting commands - and it draws them out of a flat map it is given once. It is given that map here,
 * built out of the very same dictionary every other label in the application is looked up in, so that a
 * table cannot end up half translated because a second list of words was kept somewhere else.
 *
 * Direction is the other half and is not a word at all. `enableRtl` is read when the grid builds itself and
 * never again, so a table cannot be switched from one direction to the other - which is why `gridLanguageKey`
 * exists: bound to the `key` of the grid component, it makes a change of language destroy the table and
 * build a new one, which is the only way AG Grid changes direction at all.
 */

import { language, translate } from '../composables/useLanguage'
import type { GeneratedColumn, GeneratedGridConfiguration } from '../models/grid'

/**
 * Build the words AG Grid draws with, in whichever language the interface is currently written in.
 *
 * Only the keys the two products can actually reach are listed. AG Grid's map holds several hundred, most of
 * them belonging to the enterprise features and to the filters this library replaces with its own - and a
 * translation of a phrase that is never rendered is a phrase that goes stale without anybody noticing.
 */
const gridLocaleText = (): Record<string, string> => ({
  noRowsToShow: translate('grid.noRowsToShow'),
  loadingOoo: translate('grid.loading'),
  pinColumn: translate('grid.pinColumn'),
  pinLeft: translate('grid.pinLeft'),
  pinRight: translate('grid.pinRight'),
  noPin: translate('grid.noPin'),
  autosizeThisColumn: translate('grid.autosizeThisColumn'),
  autosizeAllColumns: translate('grid.autosizeAllColumns'),
  resetColumns: translate('grid.resetColumns'),
  sortAscending: translate('grid.sortAscending'),
  sortDescending: translate('grid.sortDescending'),
  sortUnSort: translate('grid.sortUnSort'),
  columns: translate('grid.columns'),
  chooseColumns: translate('grid.chooseColumns'),
})

/**
 * Whether the table itself is laid out right to left, which is one of the options it is built with.
 */
const gridIsRtl = (): boolean => language.value === 'he'

/**
 * Head every column of a table in the language the interface is currently written in.
 *
 * This is done once, where the configuration lands, rather than by each of the dozen places that read a
 * header. A header is read by the grid itself, by the chips above the table, by the quick filter pills, by
 * the column picker, by the search box inside a set filter, by the viewer a long value opens and by the
 * spreadsheet export - and every one of them reads `headerName`. Swapping the name here means all of them
 * are right without knowing that a second language exists.
 *
 * A column with no Hebrew name keeps the one it has rather than falling back to its key. The built in
 * columns are named by whoever generated them and carry both; a declared one carries whatever the person
 * who declared it wrote down, which for most of them is one name in one language, and that name is their
 * vocabulary rather than a word to be invented a translation for.
 */
const localiseColumns = (
  configuration: GeneratedGridConfiguration,
): GeneratedGridConfiguration => {
  if (language.value !== 'he') {
    return configuration
  }

  return {
    ...configuration,
    columns: configuration.columns.map((column: GeneratedColumn) =>
      column.headerNameHebrew.length > 0 ? { ...column, headerName: column.headerNameHebrew } : column,
    ),
  }
}

/**
 * The value a table is keyed on, so that changing the language rebuilds it instead of leaving it mirrored
 * the way it was built.
 *
 * Everything else about a language change is reactive - the labels above the table, the words in its cells,
 * the direction of the page around it - and this is the one thing that is not, because the direction of an
 * AG Grid is fixed at construction. Keying the component on the language turns a change that AG Grid cannot
 * make into one Vue makes for it, by throwing the table away and building a second one the other way round.
 */
const gridLanguageKey = (): string => language.value

export { gridIsRtl, gridLanguageKey, gridLocaleText, localiseColumns }
