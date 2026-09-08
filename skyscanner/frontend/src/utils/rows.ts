/**
 * The helper that flattens one entity into the row shape the generated entity columns address.
 */

import { toValueMap } from '@truth-platform/core-ui'

import type { EntityResponse } from '@/models/entity'
import type { EventSummary } from '@/models/event'
import type { GridRow } from '@/models/grid'

/**
 * Flatten one entity into the row shape the generated entity columns address.
 */
const entityToRow = (entity: EntityResponse): GridRow => {
  /*
   * The entity table reads its files out of two columns - what came in raw, and everything the parsing
   * produced - so the products of the parsing are rolled in with the parsed files here exactly as the
   * events service rolls them in on its own side. The single list of every file is kept beside them,
   * because a saved view or a script may still be addressing it.
   */
  const parsed = [...entity.parsed_files, ...entity.parsed_additional_files]

  return {
    ...entity,
    object_type_name: entity.object_type.name,
    object_type_key: entity.object_type_key,
    parsed_all_files: parsed,
    files: [...entity.raw_files, ...parsed],
    data: toValueMap(entity.metadata),
  }
}

/**
 * Flatten one event into the row shape the generated event columns address.
 *
 * The inventory is handed rows the backend already flattened, so nothing needed this until the page of a
 * single event came to show the same attributes the expanded row of the inventory does. What it reads back
 * is one event rather than a page of them, so the flattening the backend would have done is done here, and
 * the two surfaces render the identical value through the identical column.
 */
const eventToRow = (event: EventSummary): GridRow => ({
  ...event,
  event_type_names: event.event_type.map((type) => type.name).join(', '),
  data: toValueMap(event.metadata),
})

export { entityToRow, eventToRow }
