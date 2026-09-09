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
import { language, translate } from '@truth-platform/core-ui'

import type { SchemeField } from '@/models/scheme'
import { fieldLabel, renderType } from '@/utils/scheme'

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
  /*
   * The columns of this table are already built in whichever language the interface is written in - the
   * fixed ones out of the dictionary, the declared ones out of the declaration - so there is no second
   * name to fall back to and the shared header swap has nothing to do here.
   */
  headerNameHebrew: '',
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
  wrapText: false,
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
  /**
   * The side of the table the column is held against while the rest of it scrolls, or nothing to scroll.
   *
   * Written as `left` in both directions, which is what AG Grid calls the side a reader starts from: a
   * right to left table pins it to the right, because that is where reading begins there.
   */
  pinned?: string
  minWidth: number
  renderer?: string
  filter?: string | false
  params?: Record<string, string | number | boolean | null>
  sortable?: boolean
  autoHeight?: boolean
  /** Whether a value too long for one line is wrapped onto several rather than cut short with an ellipsis. */
  wrapText?: boolean
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
  pinned: input.pinned ?? COLUMN_DEFAULTS.pinned,
  minWidth: input.minWidth,
  cellRenderer: input.renderer ?? TYPE_RENDERERS[input.type],
  cellRendererParams: input.params ?? {},
  autoHeight: input.autoHeight ?? COLUMN_DEFAULTS.autoHeight,
  /* Wrapping without a row free to grow writes the extra lines behind the row below, so the two travel together. */
  wrapText: input.wrapText ?? COLUMN_DEFAULTS.wrapText,
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
    pinned: 'left',
    cellClass: 'sky-cell truth-cell--expand',
  }),
  /*
   * The three columns that say which row this is are held against the side of the table while the rest of it
   * scrolls underneath them. A register grows a column per declared attribute, so a wide one is scrolled
   * sideways as a matter of course - and a value read halfway along it means nothing without the assumption
   * it belongs to still being on screen.
   *
   * They are pinned as a block rather than the assumption alone, because a pinned column is moved to the
   * side of the table whether it was there or not: pinning only the assumption would reorder the head of
   * every row. A pinned column also takes no share of the leftover room, so these three carry widths of
   * their own rather than the flex the scrolling columns share.
   */
  toColumn({
    colId: 'name',
    field: 'name',
    headerName: translate('column.name'),
    type: 'string',
    width: 200,
    minWidth: 140,
    pinned: 'left',
    autoHeight: true,
    wrapText: true,
  }),
  /*
   * The assumption itself is a sentence rather than a label, so it is the one column that is read rather
   * than scanned - it wraps onto as many lines as it takes and the row grows with it. Cutting it short with
   * an ellipsis meant the one column somebody opened the register for was the one they could not read.
   */
  toColumn({
    colId: 'assumption_text',
    field: 'assumption_text',
    headerName: translate('column.assumptionText'),
    type: 'text',
    width: 340,
    minWidth: 220,
    pinned: 'left',
    autoHeight: true,
    wrapText: true,
  }),
  toColumn({
    colId: 'industries',
    field: 'industries',
    headerName: translate('column.industry'),
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
    headerName: translate('column.schemas'),
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
    headerName: translate('column.proposingParty'),
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
    headerName: translate('column.validationBy'),
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
    headerName: translate('column.tags'),
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
    headerName: translate('column.revision'),
    type: 'integer',
    width: 90,
    minWidth: 80,
  }),
  toColumn({
    colId: 'creator',
    field: 'creator',
    headerName: translate('column.creator'),
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
    headerName: translate('column.createdAt'),
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
    headerName: fieldLabel(field),
    type: rendered,
    flex: 1,
    minWidth: 140,
    renderer: field.array ? 'ChipListCellRenderer' : TYPE_RENDERERS[rendered],
    filter: field.array || rendered === 'enum' ? 'SetColumnFilter' : TYPE_FILTERS[rendered],
    /*
     * A declared attribute that holds text is read rather than scanned, exactly as the assumption is, so it
     * wraps as well. The numbers, the dates and the flags are short by construction and gain nothing from a
     * second line, so they stay on one and the row is not made taller for them.
     */
    autoHeight: field.array || rendered === 'string',
    wrapText: !field.array && rendered === 'string',
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
  /*
   * The floor a row of one line short values falls back to. It is no longer what every row is: the table
   * sizes each of them from the tallest cell in it, so a wrapped assumption is as tall as it needs and a
   * row of labels is this.
   */
  rowHeight: 40,
  headerHeight: 38,
  /*
   * The version changes whenever the declared attributes change, which is what tells a table already on
   * screen that its columns have to be rebuilt rather than merely refilled.
   */
  version: `assumption:${language.value}:${fields.map((field) => `${field.key}:${field.type}`).join(',')}`,
})

export { TYPE_FILTERS, TYPE_RENDERERS, VALUE_PREFIX, buildConfiguration, fieldColumn, fixedColumns }
