/**
 * The vocabulary every surface built on this library shares - stored files, typed values and paged answers.
 *
 * What belongs here is what more than one product means the same thing by. A status an inventory happens to
 * put on its events, or a state a parser happens to leave a file in, is that product's own word and stays in
 * that product's own models.
 */

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }

type ArtifactKind = 'raw' | 'parsed' | 'parsed_additional' | 'additional'

type FieldType =
  | 'string'
  | 'text'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'enum'
  | 'file'
  | 'json'
  | 'coordinate'

/**
 * Which half of a document a declaration describes.
 *
 * A product names its own halves - an inventory has events and the entities under them, an assumption
 * register has assumptions and the schemas over them - so the scope is left as free text rather than as a
 * closed list that every product would have to be added to.
 */
type FieldScope = string

/** A point on the globe, held as the three numbers the map picker hands back. */
type Coordinate = {
  lon: number
  lat: number
  alt: number | null
}

type ObjectTypeReference = {
  id: string
  name: string
}

type Artifact = {
  id: string
  name: string
  path: string
  descriptor: string
  kind: ArtifactKind
  suffix: string
  folder: string | null
  source: string | null
  size_bytes: number
  content_type: string
  checksum: string | null
  /** Who put the file into the bucket. Files stored before the field existed carry nothing. */
  uploaded_by: string | null
  created_at: string | null
  updated_at: string | null
}

type MetadataAttribute = {
  key: string
  value: JsonValue
  type: FieldType
}

interface OperationResult {
  success: boolean
  message: string
  affected: number
}

interface PageResponse<ItemT> {
  items: ItemT[]
  total: number
  page: number
  page_size: number
  pages: number
}

/**
 * One member of a vocabulary the interface navigates by and paints chips from.
 *
 * An inventory calls these its industries and an assumption register calls them the same, but the library
 * only needs the three things it draws them with, so it asks for exactly those.
 */
interface TaxonomyItem {
  key: string
  name: string
  color: string
}

export type {
  Artifact,
  ArtifactKind,
  Coordinate,
  FieldScope,
  FieldType,
  JsonValue,
  MetadataAttribute,
  ObjectTypeReference,
  OperationResult,
  PageResponse,
  TaxonomyItem,
}
