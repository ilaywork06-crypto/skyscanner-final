/**
 * Binding the register's table to the service that answers it.
 *
 * The grid controller of the library asks for two functions - one that builds the columns and one that reads
 * a page of rows - and neither of them cares where the answer comes from. Here both go to the service: the
 * columns are still generated from the declarations the client holds, but every question about the rows -
 * the search, the restrictions, the ordering, the window and the count - is answered by the register itself.
 *
 * That is the whole difference between a table that works at thirty assumptions and one that works at a
 * hundred thousand. What crosses the network is one screen of rows, whatever the register holds.
 */

import { createGridController, type GridController } from '@truth-platform/ag-grid-ts'
import type { GeneratedGridConfiguration, GridRowsPage } from '@truth-platform/core-ui'
import { watch, type ComputedRef } from 'vue'

import type { SchemeField } from '@/models/scheme'
import { queryAssumptions, readFacet } from '@/requests/assumptions'
import { buildConfiguration } from '@/utils/columns'
import { assumptionToRow } from '@/utils/rows'

const DEFAULT_PAGE_SIZE = 25

/** What the table is being shown out of, and what it is currently narrowed to. */
interface AssumptionsGridInput {
  fields: ComputedRef<SchemeField[]>
  /** The industry the register is being read under, or nothing for the whole of it. */
  industry: ComputedRef<string | null>
}

interface AssumptionsGrid {
  controller: GridController
}

/**
 * Build the controller of the register's table, wired to the service that answers it.
 */
const useAssumptionsGrid = (input: AssumptionsGridInput): AssumptionsGrid => {
  /**
   * Build the columns out of the declared attributes, and fill each filter with the values actually present.
   *
   * The vocabulary of a filter is asked of the register rather than read off the rows on screen, which is the
   * only way it can be right: the rows on screen are one page of an answer, and a filter offering only what
   * that page happens to hold would narrow the register by the page it is already showing.
   */
  const loadConfiguration = async (): Promise<GeneratedGridConfiguration> => {
    const configuration = buildConfiguration(input.fields.value)
    const industry = input.industry.value

    const columns = await Promise.all(
      configuration.columns.map(async (column) => {
        if (column.filter !== 'SetColumnFilter') {
          return column
        }

        try {
          const facet = await readFacet(column.colId, industry)

          return { ...column, filterOptions: facet.values.map((value) => ({ value, label: value })) }
        } catch {
          /* A vocabulary that could not be gathered costs that column its list of choices and nothing else. */
          return column
        }
      }),
    )

    return { ...configuration, columns }
  }

  const controller = createGridController({
    loadConfiguration,
    loadRows: async (query): Promise<GridRowsPage> => {
      const answer = await queryAssumptions({
        search: query.search,
        industry: input.industry.value,
        filters: query.filters,
        sort: query.sort,
        offset: Math.max(0, (query.page - 1) * query.pageSize),
        limit: query.pageSize,
      })

      return {
        rows: answer.rows.map((row) => assumptionToRow(row)),
        total: answer.total,
        page: query.page,
        pageSize: query.pageSize,
        pages: Math.max(1, Math.ceil(answer.total / query.pageSize)),
      }
    },
    pageSize: DEFAULT_PAGE_SIZE,
  })

  /*
   * The columns are rebuilt when the declarations themselves changed, and only then, because rebuilding them
   * resets the arrangement the reader may have made of them.
   */
  watch(
    () => input.fields.value.map((field) => `${field.key}:${field.type}`).join(','),
    () => {
      void controller.refreshConfiguration()
    },
  )

  /*
   * Narrowing to an industry changes both halves at once: the rows are a different answer, and the filters
   * offer a different vocabulary, because the vocabulary is gathered within whatever the table is showing.
   */
  watch(
    () => input.industry.value,
    () => {
      void controller.refreshConfiguration()
      void controller.goToPage(1)
    },
  )

  return { controller }
}

export type { AssumptionsGrid, AssumptionsGridInput }
export { DEFAULT_PAGE_SIZE, useAssumptionsGrid }
