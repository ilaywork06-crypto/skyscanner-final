/**
 * Binding the register's table to the register held in memory.
 *
 * The grid controller of the library asks for two functions - one that builds the columns and one that reads
 * a page of rows - and neither of them cares whether the answer came from a service or from an array. That is
 * what lets this product keep the whole generated table without having a single endpoint behind it: the
 * columns are generated from the schemas and the pages are cut out of the rows already read.
 */

import { createGridController, type GridController } from '@truth-platform/ag-grid-ts'
import type { GeneratedGridConfiguration, GridRow, GridRowsPage } from '@truth-platform/core-ui'
import { computed, onScopeDispose, watch, type ComputedRef, type Ref } from 'vue'

import type { AssumptionRow } from '@/models/assumption'
import type { SchemeField } from '@/models/scheme'
import { buildConfiguration } from '@/utils/columns'
import { collectOptions, runQuery } from '@/utils/query'
import { assumptionToRow } from '@/utils/rows'

const DEFAULT_PAGE_SIZE = 25

/**
 * How long the table waits after the register moves before it reads its rows again.
 *
 * Completing the register is one request per assumption, and each answer that lands changes the rows. Reacting
 * to every one of them would re-run the whole query - and re-render the table - a few hundred times during the
 * first load, for a table nobody can read while it flickers. Waiting a moment collapses a burst of arrivals
 * into a single refresh, and a lone change still lands well inside a blink.
 */
const REFRESH_DELAY_MS = 150

/** What the table is being shown out of, and what it is currently narrowed to. */
interface AssumptionsGridInput {
  assumptions: Ref<AssumptionRow[]>
  fields: ComputedRef<SchemeField[]>
  /** The industry the register is being read under, or nothing for the whole of it. */
  industry: ComputedRef<string | null>
}

interface AssumptionsGrid {
  controller: GridController
  /** Every row of the register as the table addresses it, before any narrowing. */
  rows: ComputedRef<GridRow[]>
}

/**
 * Build the controller of the register's table, wired to the rows held in memory.
 */
const useAssumptionsGrid = (input: AssumptionsGridInput): AssumptionsGrid => {
  const rows = computed<GridRow[]>(() => input.assumptions.value.map((row) => assumptionToRow(row)))

  /* The rows of the industry being read, which is what both the columns and the pages are drawn from. */
  const scoped = computed<GridRow[]>(() => {
    const industry = input.industry.value
    if (industry === null) {
      return rows.value
    }

    return rows.value.filter((row) => {
      const names = row.industries
      const ids = row.industry_ids

      return (
        (Array.isArray(names) && names.includes(industry)) || (Array.isArray(ids) && ids.includes(industry))
      )
    })
  })

  /**
   * Build the columns out of the declared attributes, and fill each filter with the values actually present.
   *
   * A filter that offers a vocabulary reads it off the rows rather than off the declaration, so a column
   * offers what the register holds - including the values somebody wrote before the schema was revised to
   * name them.
   */
  const loadConfiguration = (): Promise<GeneratedGridConfiguration> => {
    const configuration = buildConfiguration(input.fields.value)

    return Promise.resolve({
      ...configuration,
      columns: configuration.columns.map((column) =>
        column.filter === 'SetColumnFilter'
          ? {
              ...column,
              filterOptions: collectOptions(scoped.value, column.colId).map((value) => ({ value, label: value })),
            }
          : column,
      ),
    })
  }

  const controller = createGridController({
    loadConfiguration,
    loadRows: (query): Promise<GridRowsPage> => {
      const answer = runQuery(scoped.value, {
        search: query.search ?? '',
        filters: query.filters,
        sort: query.sort,
        page: query.page,
        pageSize: query.pageSize,
      })

      return Promise.resolve({
        rows: answer.rows,
        total: answer.total,
        page: query.page,
        pageSize: query.pageSize,
        pages: Math.max(1, Math.ceil(answer.total / query.pageSize)),
      })
    },
    pageSize: DEFAULT_PAGE_SIZE,
  })

  /*
   * The register grows while it is being read - every assumption that is completed adds its values, and
   * every schema that lands adds its columns - so the table is rebuilt as that happens rather than showing
   * whatever it happened to be built from first. The columns are only rebuilt when the declarations
   * themselves changed, because rebuilding them resets the arrangement the reader may have made of them.
   */
  watch(
    () => input.fields.value.map((field) => `${field.key}:${field.type}`).join(','),
    () => {
      void controller.refreshConfiguration()
    },
  )

  /*
   * The rows are read again whenever the register moves underneath the table - an assumption completed, one
   * created, an industry left - collapsed into one refresh per burst rather than one per arrival.
   */
  let pending: ReturnType<typeof setTimeout> | null = null

  watch(scoped, () => {
    if (pending !== null) {
      clearTimeout(pending)
    }

    pending = setTimeout(() => {
      pending = null
      void controller.refreshRows()
    }, REFRESH_DELAY_MS)
  })

  onScopeDispose(() => {
    if (pending !== null) {
      clearTimeout(pending)
    }
  })

  return { controller, rows }
}

export type { AssumptionsGrid, AssumptionsGridInput }
export { DEFAULT_PAGE_SIZE, useAssumptionsGrid }
