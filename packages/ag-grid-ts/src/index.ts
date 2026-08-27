/**
 * The public surface of the AG Grid client library - configuration parsing, grid setup and reactive rendering.
 */

import { applyThemeCompatibility, supportsColorMix } from './compatibility'
import { createGridController } from './controller'
import { SET_FILTER_TYPE, buildFilterConditions, buildFilterModel, buildSortSpecifications } from './datasource'
import { DETAIL_ROW_KEY, buildGridOptions, isDetailRow, registerGridModules } from './grid'
import { parseColumnDefinitions } from './parse'

import type { GridController, GridControllerInput, RowsQuery } from './controller'
import type { AgFilterType } from './datasource'
import type { GridOptionsInput } from './grid'
import type { CellRendererRegistry, FilterComponentRegistry, ParseOptions } from './parse'
import type {
  FilterCondition,
  FilterOperator,
  FilterOption,
  GeneratedColumn,
  GeneratedGridConfiguration,
  GridRow,
  GridRowsPage,
  JsonValue,
  SortDirection,
  SortSpecification,
} from './types'

export type {
  AgFilterType,
  CellRendererRegistry,
  FilterComponentRegistry,
  FilterCondition,
  FilterOperator,
  FilterOption,
  GeneratedColumn,
  GeneratedGridConfiguration,
  GridController,
  GridControllerInput,
  GridOptionsInput,
  GridRow,
  GridRowsPage,
  JsonValue,
  ParseOptions,
  RowsQuery,
  SortDirection,
  SortSpecification,
}
export {
  DETAIL_ROW_KEY,
  SET_FILTER_TYPE,
  applyThemeCompatibility,
  buildFilterConditions,
  buildFilterModel,
  buildGridOptions,
  buildSortSpecifications,
  createGridController,
  isDetailRow,
  parseColumnDefinitions,
  registerGridModules,
  supportsColorMix,
}
