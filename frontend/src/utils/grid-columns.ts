/**
 * The column definitions the client builds for values that reached a document without a declaration.
 *
 * Everything the schema declares arrives as a generated column from the backend. A value written under a key
 * nobody declared arrives as nothing at all, so this is where one is described well enough to be rendered -
 * with the renderer its own stored type asks for, which is the same mapping the backend applies.
 */

import { humanizeKey } from '@skyscanner/sky-ui'

import type { FieldType, MetadataAttribute } from '@/models/common'
import type { GeneratedColumn, GridRow } from '@/models/grid'

/** Where a dynamic value sits inside the flattened row, matching the prefix the backend generates. */
const DYNAMIC_FIELD_PREFIX = 'data'

/** Which renderer paints each kind of value, mirroring the mapping the generated columns are built with. */
const TYPE_RENDERERS: Record<FieldType, string> = {
  string: 'TextCellRenderer',
  text: 'TextCellRenderer',
  number: 'TextCellRenderer',
  integer: 'TextCellRenderer',
  boolean: 'BooleanCellRenderer',
  date: 'DateCellRenderer',
  datetime: 'DateCellRenderer',
  enum: 'ChipCellRenderer',
  file: 'FilesCellRenderer',
  json: 'JsonCellRenderer',
  coordinate: 'CoordinateCellRenderer',
}

const DEFAULT_RENDERER = 'TextCellRenderer'

/**
 * Describe one undeclared value as the column that renders it.
 */
const undeclaredColumn = (attribute: MetadataAttribute): GeneratedColumn => ({
  colId: attribute.key,
  field: `${DYNAMIC_FIELD_PREFIX}.${attribute.key}`,
  headerName: humanizeKey(attribute.key),
  sortable: false,
  filter: false,
  floatingFilter: false,
  resizable: true,
  hide: false,
  editable: false,
  flex: 1,
  minWidth: 120,
  maxWidth: null,
  width: null,
  pinned: null,
  cellRenderer: TYPE_RENDERERS[attribute.type] ?? DEFAULT_RENDERER,
  cellRendererParams: { withTime: attribute.type === 'datetime' },
  cellDataType: false,
  headerClass: null,
  cellClass: null,
  autoHeight: attribute.type === 'file',
  fieldType: attribute.type,
  dynamic: true,
  /* Nothing declared this key either - it is read straight off the value the row was written with. */
  discovered: true,
  industry: null,
  /*
   * Nothing declared the key, so nothing declared what it is allowed to hold either: a value read off a
   * stored document has no vocabulary behind it and is therefore never offered as one to pick from.
   */
  filterOptions: [],
  quickFilter: false,
})

/**
 * Read the values a row carries under keys the generated columns never declared.
 *
 * A value written by a script, or typed into the additional data of a form before anybody standardised the
 * key, is stored with the type it was written as and nothing generates a column for it. Reading them out
 * here is what keeps them from being stored and then shown nowhere at all.
 */
const undeclaredAttributes = (columns: GeneratedColumn[], row: GridRow): MetadataAttribute[] => {
  const declared = new Set(columns.filter((column) => column.dynamic).map((column) => column.colId))
  const stored = row.metadata

  if (!Array.isArray(stored)) {
    return []
  }

  return stored
    .filter((item): item is MetadataAttribute => item !== null && typeof item === 'object' && !Array.isArray(item))
    .filter((attribute) => !declared.has(attribute.key))
}

/**
 * Build the columns that describe everything a row holds beyond its built in ones.
 *
 * The declared dynamic fields come first, in the order the schema gave them, and whatever else the row was
 * written with follows behind - so a table of them reads as the schema first and the improvisation after it.
 */
const attributeColumns = (columns: GeneratedColumn[], row: GridRow): GeneratedColumn[] => [
  ...columns.filter((column) => column.dynamic),
  ...undeclaredAttributes(columns, row).map((attribute) => undeclaredColumn(attribute)),
]

export { DYNAMIC_FIELD_PREFIX, TYPE_RENDERERS, attributeColumns, undeclaredAttributes, undeclaredColumn }
