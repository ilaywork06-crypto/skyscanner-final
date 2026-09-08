/**
 * The vocabulary of the inventory - the words this product uses, on top of the ones the platform shares.
 *
 * Everything that more than one product means the same thing by lives in the shared library and is re-stated
 * here, so that a page of the inventory imports its whole vocabulary from one place rather than having to
 * know which half of it happens to be shared.
 */

export type {
  Artifact,
  ArtifactKind,
  Coordinate,
  FieldType,
  JsonValue,
  MetadataAttribute,
  ObjectTypeReference,
  OperationResult,
  PageResponse,
} from '@truth-platform/core-ui'

type EventStatus = 'draft' | 'operational'

type EntityStatus = 'raw' | 'parsing' | 'partially_parsed' | 'parsed' | 'failed'

type ExperimentResult = 'successful' | 'partial' | 'failed'

type ParseState = 'all' | 'parsed' | 'not_parsed'

/** Which half of a document a declaration describes, narrowed to the two halves this product has. */
type FieldScope = 'event' | 'entity'

/** A built in event field that only the event types declaring it ask for. */
type OptionalEventField =  'event_date' | 'experiment_result' | 'notes'

export type { EntityStatus, EventStatus, ExperimentResult, FieldScope, OptionalEventField, ParseState }
