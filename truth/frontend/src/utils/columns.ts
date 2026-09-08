/**
 * Building the table's columns out of the schemas, rather than writing any of them down here.
 *
 * The API has no endpoint that generates column definitions, so the generation that would run in the backend
 * runs here instead - but it runs off exactly the same source it would have run off there: the schemas held
 * in the database. Nothing below names an attribute of an assumption. The fixed columns are the fields the
 * API itself declares on every assumption, and every other column is read out of whichever schemas the
 * assumptions on screen happen to be declared by.
 */

import type { FieldType, GeneratedColumn, GeneratedGridConfiguration } from '@truth-platform/core-ui'
import { humanizeKey } from '@truth-platform/core-ui'

import type { SchemeField } from '@/models/scheme'
import { renderType } from '@/utils/scheme'

/** Where a schema declared value sits inside the flattened row. */
const VALUE_PREFIX = 'values'

/** Which renderer paints each kind of value. */
const TYPE_RENDERERS: Record<FieldType, string> = {
  string: 'TextCellRenderer',
  text: 'TextCellRenderer',
  number: 'TextCellRenderer',
  integer: 'TextCellRenderer',
  boolean: 'BooleanCellRenderer',
  date: 'DateCellRenderer',
  datetime: 'DateCellRenderer',
  enum: 'ChipCellRenderer',
  file: 'TextCellRenderer',
  json: 'JsonCellRenderer',
  coordinate: 'CoordinateCellRenderer',
}

/** Which filter each kind of value is narrowed with. */
const TYPE_FILTERS: Record<FieldType, string> = {
  string: 'agTextColumnFilter',
  text: 'agTextColumnFilter',
  number: 'agNumberColumnFilter',
  integer: 'agNumberColumnFilter',
  boolean: 'SetColumnFilter',
  date: 'agDateColumnFilter',
  datetime: 'agDateColumnFilter',
  enum: 'SetColumnFilter',
  file: 'agTextColumnFilter',
  json: 'agTextColumnFilter',
  coordinate: 'agTextColumnFilter',
}

/** What every column carries unless it says otherwise, so that each definition below states only its own part. */
const COLUMN_DEFAULTS = {
  sortable: true,
  floatingFilter: false,
  resizable: true,
  hide: false,
  editable: false,
  maxWidth: null,
  pinned: null,
  cellDataType: false as const,
  headerClass: null,
  cellClass: 'sky-cell',
  autoHeight: false,
  dynamic: false,
  discovered: false,
  industry: null,
  quickFilter: false,
}

/** How a column is described before the defaults are folded into it. */
interface ColumnInput {
  colId: string
  field: string
  headerName: string
  type: FieldType
  /** How the column shares the room left over, or nothing for one that keeps a width of its own. */
  flex?: number
  /** A fixed width, for the narrow columns that would otherwise be stretched by a share of the room. */
  width?: number
  minWidth: number
  renderer?: string
  filter?: string | false
  params?: Record<string, string | number | boolean | null>
  sortable?: boolean
  autoHeight?: boolean
  quickFilter?: boolean
  dynamic?: boolean
  cellClass?: string
}

/**
 * Fold the defaults into one described column.
 */
const toColumn = (input: ColumnInput): GeneratedColumn => ({
  ...COLUMN_DEFAULTS,
  colId: input.colId,
  field: input.field,
  headerName: input.headerName,
  sortable: input.sortable ?? COLUMN_DEFAULTS.sortable,
  filter: input.filter ?? TYPE_FILTERS[input.type],
  flex: input.flex ?? null,
  width: input.width ?? null,
  minWidth: input.minWidth,
  cellRenderer: input.renderer ?? TYPE_RENDERERS[input.type],
  cellRendererParams: input.params ?? {},
  autoHeight: input.autoHeight ?? COLUMN_DEFAULTS.autoHeight,
  fieldType: input.type,
  dynamic: input.dynamic ?? COLUMN_DEFAULTS.dynamic,
  quickFilter: input.quickFilter ?? COLUMN_DEFAULTS.quickFilter,
  cellClass: input.cellClass ?? COLUMN_DEFAULTS.cellClass,
  filterOptions: [],
})

/**
 * The columns that describe what the API declares on every assumption, whatever schema it was written under.
 *
 * These are not a choice about what an assumption is - they are the fields the endpoints themselves return,
 * so a register with no schemas at all still has a readable table.
 */
const fixedColumns = (): GeneratedColumn[] => [
  toColumn({
    colId: 'expand',
    field: 'id',
    headerName: '',
    type: 'string',
    width: 56,
    minWidth: 56,
    renderer: 'ExpandCellRenderer',
    filter: false,
    sortable: false,
    cellClass: 'sky-cell truth-cell--expand',
  }),
  toColumn({ colId: 'name', field: 'name', headerName: 'Name', type: 'string', flex: 2, minWidth: 180 }),
  toColumn({
    colId: 'assumption_text',
    field: 'assumption_text',
    headerName: 'Assumption',
    type: 'text',
    flex: 3,
    minWidth: 240,
  }),
  toColumn({
    colId: 'industries',
    field: 'industries',
    headerName: 'Industry',
    type: 'enum',
    flex: 2,
    minWidth: 160,
    renderer: 'ChipListCellRenderer',
    filter: 'SetColumnFilter',
    params: { palette: 'industry' },
    autoHeight: true,
  }),
  toColumn({
    colId: 'schemas',
    field: 'schemas',
    headerName: 'Schemas',
    type: 'enum',
    flex: 2,
    minWidth: 160,
    renderer: 'ChipListCellRenderer',
    filter: 'SetColumnFilter',
    /* Each schema keeps a colour of its own, so which one declares a row is legible at a glance. */
    params: { palette: 'industry' },
    autoHeight: true,
  }),
  toColumn({
    colId: 'proposing_party',
    field: 'proposing_party',
    headerName: 'Proposing party',
    type: 'string',
    flex: 1,
    minWidth: 150,
    renderer: 'ChipCellRenderer',
    filter: 'SetColumnFilter',
    quickFilter: true,
  }),
  toColumn({
    colId: 'validation_responsible_parties',
    field: 'validation_responsible_parties',
    headerName: 'Validation by',
    type: 'enum',
    flex: 2,
    minWidth: 170,
    renderer: 'ChipListCellRenderer',
    filter: 'SetColumnFilter',
    autoHeight: true,
  }),
  toColumn({
    colId: 'tags',
    field: 'tags',
    headerName: 'Tags',
    type: 'enum',
    flex: 2,
    minWidth: 150,
    renderer: 'ChipListCellRenderer',
    filter: 'SetColumnFilter',
    autoHeight: true,
    quickFilter: true,
  }),
  toColumn({
    colId: 'revision',
    field: 'revision',
    headerName: 'Rev',
    type: 'integer',
    width: 90,
    minWidth: 80,
  }),
  toColumn({
    colId: 'creator',
    field: 'creator',
    headerName: 'Creator',
    type: 'string',
    flex: 1,
    minWidth: 140,
    renderer: 'ChipCellRenderer',
    filter: 'SetColumnFilter',
    quickFilter: true,
  }),
  toColumn({
    colId: 'created_at',
    field: 'created_at',
    headerName: 'Created at',
    type: 'datetime',
    flex: 1,
    minWidth: 170,
    params: { withTime: true },
    cellClass: 'sky-cell sky-cell--stamp',
  }),
]

/**
 * Describe one schema declared attribute as the column that renders it.
 */
const fieldColumn = (field: SchemeField): GeneratedColumn => {
  const rendered = renderType(field.type)

  return toColumn({
    colId: field.key,
    field: `${VALUE_PREFIX}.${field.key}`,
    headerName: field.displayName.length > 0 ? field.displayName : humanizeKey(field.key),
    type: rendered,
    flex: 1,
    minWidth: 140,
    renderer: field.array ? 'ChipListCellRenderer' : TYPE_RENDERERS[rendered],
    filter: field.array || rendered === 'enum' ? 'SetColumnFilter' : TYPE_FILTERS[rendered],
    autoHeight: field.array,
    quickFilter: rendered === 'enum' && !field.array,
    dynamic: true,
  })
}

/**
 * Build the whole configuration of the register's table out of the attributes the schemas declare.
 */
const buildConfiguration = (fields: SchemeField[]): GeneratedGridConfiguration => ({
  scope: 'assumption',
  industry: null,
  columns: [...fixedColumns(), ...fields.map((field) => fieldColumn(field))],
  defaultSort: [{ key: 'created_at', direction: 'desc' }],
  quickFilterKeys: ['proposing_party', 'creator', 'tags'],
  rowHeight: 48,
  headerHeight: 44,
  /*
   * The version changes whenever the declared attributes change, which is what tells a table already on
   * screen that its columns have to be rebuilt rather than merely refilled.
   */
  version: `assumption:${fields.map((field) => `${field.key}:${field.type}`).join(',')}`,
})

export { TYPE_FILTERS, TYPE_RENDERERS, VALUE_PREFIX, buildConfiguration, fieldColumn, fixedColumns }
