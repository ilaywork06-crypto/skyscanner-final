/**
 * The helper that flattens one entity into the row shape the generated entity columns address.
 */

import { toValueMap } from '@truth-platform/core-ui'

import type { EntityResponse } from '@/models/entity'
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

export { entityToRow }
