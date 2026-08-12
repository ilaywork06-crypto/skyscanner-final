/**
 * The composable that binds the generated inventory table to the API and to the actions of the toolbar.
 */

import { createGridController, type GridController, type RowsQuery } from '@skyscanner/ag-grid-ts'

import type { ParseState } from '@/models/common'
import type { GeneratedGridConfiguration, GridRow, GridRowsPage } from '@/models/grid'
import type { EventExportRequest, GridRowsRequest } from '@/models/query'
import { readEventColumns, readEventRows } from '@/requests/grid'

const DEFAULT_PAGE_SIZE = 25
const EXPORT_PAGE_SIZE = 500

/**
 * Turn the query of the grid controller into the request payload the backend expects.
 */
const toRowsRequest = (query: RowsQuery): GridRowsRequest => ({
  search: query.search,
  industry: query.industry,
  parse_state: query.parseState as ParseState,
  filters: query.filters,
  sort: query.sort,
  page: query.page,
  page_size: query.pageSize,
  columns: [],
})

/**
 * Build the controller of the inventory table, already wired to the endpoints of the events service.
 */
const useEventsGrid = (industry: string | null): GridController => {
  const controller = createGridController({
    loadConfiguration: (currentIndustry): Promise<GeneratedGridConfiguration> => readEventColumns(currentIndustry),
    loadRows: (query): Promise<GridRowsPage> => readEventRows(toRowsRequest(query)),
    pageSize: DEFAULT_PAGE_SIZE,
  })
  controller.industry.value = industry

  return controller
}

/**
 * Build the request payload of the current view, used by the export action of the toolbar.
 *
 * The export follows the table as it stands on screen, so it carries the very filters and ordering the grid
 * is showing. Handing it a list of identifiers narrows it further, down to the rows the user ticked.
 */
const buildExportRequest = (
  controller: GridController,
  columns: string[],
  eventIds: string[] = [],
): EventExportRequest => ({
  search: controller.search.value.length > 0 ? controller.search.value : null,
  industry: controller.industry.value,
  parse_state: controller.parseState.value as ParseState,
  filters: controller.filterConditions.value,
  sort: controller.sortSpecifications.value,
  page: 1,
  page_size: EXPORT_PAGE_SIZE,
  columns,
  event_ids: eventIds,
})

/**
 * Find one row of the current block by its identifier.
 */
const findRowById = (rows: GridRow[], rowId: string): GridRow | undefined =>
  rows.find((row) => String(row.id) === rowId)

export { DEFAULT_PAGE_SIZE, buildExportRequest, findRowById, toRowsRequest, useEventsGrid }
