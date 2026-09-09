/**
 * The bundle: a register written out whole, and read back in whole somewhere else.
 *
 * The spreadsheet export beside this one is for a person - it carries the columns that were on screen, in the
 * order they were on screen, with every value flattened into the one cell a sheet holds it in. That is
 * exactly what makes it useless for putting the register back: a flattened value has lost whether it was a
 * number or the word for one, a hidden column has lost its values entirely, and a renamed header no longer
 * says which key it came from.
 *
 * A bundle is the other thing. It carries the register in the shapes the API itself creates things in, so
 * restoring one is a sequence of the very same writes a person would have made by hand - and it carries the
 * three collections rather than only the rows, because an assumption names the schemas that declare it and
 * the industries it is filed under, and neither of those is worth anything on a register that never heard
 * of them.
 *
 * The order those three are written in is not a preference. An assumption names its schemas and its
 * industries by name, so both have to exist before it does; that is the whole reason a bundle is restored in
 * three passes rather than in one.
 *
 * Everything inside is named rather than identified. The identifiers of one register mean nothing in
 * another, and the API accepts a name wherever it accepts an identifier, so a bundle taken from one register
 * restores into a second one that has never seen a single one of its uuids.
 */

import type { JsonValue } from '@truth-platform/core-ui'

import type { AssumptionDetail, AssumptionDraft } from '@/models/assumption'
import type { Industry } from '@/models/industry'
import type { SchemaDetail } from '@/models/schema'
import type { StoredScheme } from '@/models/scheme'

/** What marks a file as one of these rather than as any other JSON somebody dropped on the dialog. */
const BUNDLE_FORMAT = 'truth.register.bundle'

/** The revision of the shape below, so that a bundle written today is still recognisable when it changes. */
const BUNDLE_VERSION = 1

/** The stem a bundle is saved under, before the moment it was taken. */
const FILE_PREFIX = 'truth-bundle'

/** One industry as a bundle carries it, which is what creating one asks for. */
interface BundledIndustry {
  name: string
  description: string
  creator: string
}

/** One schema as a bundle carries it, declaration and all. */
interface BundledSchema {
  name: string
  description: string
  type: number
  scheme: StoredScheme
  creator: string
}

/**
 * One assumption as a bundle carries it.
 *
 * The revision and the moment it was created are carried but are not written back: the API stamps both
 * itself and offers no way to say otherwise, so they are here for a reader of the file rather than for the
 * restore. Saying so in the file is better than dropping them and leaving a reader to wonder.
 */
interface BundledAssumption {
  name: string
  assumption_text: string
  proposing_party: string
  schemas: string[]
  industries: string[]
  values: Record<string, JsonValue>
  tags: string[]
  validation_responsible_parties: string[]
  creator: string
  special_fields: Record<string, JsonValue>
  revision: number
  created_at: string
}

/** A whole register, written out. */
interface Bundle {
  format: string
  version: number
  /** When the bundle was taken, so two of them can be told apart by something other than their file name. */
  created_at: string
  /** The industry the register was being read under when it was taken, or nothing for a whole register. */
  industry: string | null
  industries: BundledIndustry[]
  schemas: BundledSchema[]
  assumptions: BundledAssumption[]
}

/**
 * Describe one industry the way a bundle carries it.
 *
 * The API never hands back a description or a creator of an industry - it stores both and returns neither -
 * so neither can be carried, and a restored industry is created with the empty description the reader of the
 * bundle is given. There is nothing to be done about that from here; it is a property of the API.
 */
const bundleIndustry = (industry: Industry, creator: string): BundledIndustry => ({
  name: industry.name,
  description: '',
  creator,
})

/**
 * Describe one schema the way a bundle carries it.
 *
 * The declaration travels exactly as the service stored it rather than as this client read it. A scheme is a
 * free form list of dictionaries, and the reader of one is deliberately generous - it understands a field
 * that named itself `field` rather than `key`, and a type written as `list[str]`. Writing back what was read
 * would quietly rewrite every such schema into this client's own spelling, which is a change nobody asked
 * for to data nobody said this client owns.
 */
const bundleSchema = (schema: SchemaDetail): BundledSchema => ({
  name: schema.name,
  description: schema.description,
  /* The API holds a kind as a number and offers no vocabulary for it, so the one every schema is created under. */
  type: 0,
  scheme: schema.scheme,
  creator: schema.creator,
})

/**
 * Describe one assumption the way a bundle carries it.
 */
const bundleAssumption = (assumption: AssumptionDetail): BundledAssumption => ({
  name: assumption.name,
  assumption_text: assumption.assumption_text,
  proposing_party: assumption.proposing_party,
  schemas: assumption.schemas.map((schema) => schema.name),
  industries: assumption.industries.map((industry) => industry.name),
  values: assumption.values,
  tags: [...assumption.tags],
  validation_responsible_parties: [...assumption.validation_responsible_parties],
  creator: assumption.creator,
  special_fields: {},
  revision: assumption.revision,
  created_at: assumption.created_at,
})

/**
 * Build a bundle out of the pieces of the register that were read for it.
 */
const buildBundle = (input: {
  industry: string | null
  industries: Industry[]
  schemas: SchemaDetail[]
  assumptions: AssumptionDetail[]
  creator: string
}): Bundle => ({
  format: BUNDLE_FORMAT,
  version: BUNDLE_VERSION,
  created_at: new Date().toISOString(),
  industry: input.industry,
  industries: input.industries.map((industry) => bundleIndustry(industry, input.creator)),
  schemas: input.schemas.map((schema) => bundleSchema(schema)),
  assumptions: input.assumptions.map((assumption) => bundleAssumption(assumption)),
})

/**
 * Build the name a bundle is saved under, stamped so that two of them never overwrite one another.
 */
const bundleFileName = (industry: string | null): string => {
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z')
  const scope = industry === null ? '' : `-${industry.replace(/[^\w-]+/g, '-').toLowerCase()}`

  return `${FILE_PREFIX}${scope}-${stamp}.json`
}

/**
 * Render a bundle as the text of the file it is saved as.
 */
const writeBundle = (bundle: Bundle): string => JSON.stringify(bundle, null, 2)

/**
 * Whether a value read out of a file is a dictionary rather than a list or a scalar.
 */
const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value)

/**
 * Read a list of strings out of whatever was actually in the file.
 *
 * A bundle is a file that was on a disk, so it may have been edited by hand between the two ends of this,
 * and everything below is written on that basis: what is not there reads as empty rather than as a failure.
 */
const readStrings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []

/**
 * Read one string out of a dictionary, or the empty string where none was written.
 */
const readText = (raw: Record<string, unknown>, key: string): string =>
  typeof raw[key] === 'string' ? (raw[key] as string) : ''

/**
 * Read a dictionary of values out of a dictionary, or an empty one.
 */
const readValues = (raw: Record<string, unknown>, key: string): Record<string, JsonValue> =>
  isRecord(raw[key]) ? (raw[key] as Record<string, JsonValue>) : {}

/**
 * Read the declaration of a schema out of a bundle, in the shape the service stores it in.
 *
 * Both spellings of the constraint list are kept if they were there, because the service reads one and
 * answers with the other, and a bundle that travelled between the two should not lose whichever it carried.
 */
const readScheme = (value: unknown): StoredScheme => {
  if (!isRecord(value)) {
    return { fields: [] }
  }

  const fields = Array.isArray(value.fields)
    ? value.fields.filter((field): field is Record<string, JsonValue> => isRecord(field))
    : []

  return { fields }
}

/**
 * Read a file back into a bundle, or nothing at all when it is not one.
 *
 * The format marker is checked rather than assumed, because the alternative is a dialog that accepts any
 * JSON at all, reports that it holds nothing, and leaves the reader to work out that they picked the wrong
 * file. A bundle from a later version is still read: the shape below only ever grows, and refusing a file
 * over a number is worse than restoring the part of it this client understands.
 */
const readBundle = (text: string): Bundle | null => {
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch {
    return null
  }

  if (!isRecord(parsed) || parsed.format !== BUNDLE_FORMAT) {
    return null
  }

  const industries = Array.isArray(parsed.industries) ? parsed.industries : []
  const schemas = Array.isArray(parsed.schemas) ? parsed.schemas : []
  const assumptions = Array.isArray(parsed.assumptions) ? parsed.assumptions : []

  return {
    format: BUNDLE_FORMAT,
    version: typeof parsed.version === 'number' ? parsed.version : BUNDLE_VERSION,
    created_at: readText(parsed, 'created_at'),
    industry: typeof parsed.industry === 'string' ? parsed.industry : null,
    industries: industries.filter(isRecord).map((raw) => ({
      name: readText(raw, 'name'),
      description: readText(raw, 'description'),
      creator: readText(raw, 'creator'),
    })),
    schemas: schemas.filter(isRecord).map((raw) => ({
      name: readText(raw, 'name'),
      description: readText(raw, 'description'),
      type: typeof raw.type === 'number' ? raw.type : 0,
      scheme: readScheme(raw.scheme),
      creator: readText(raw, 'creator'),
    })),
    assumptions: assumptions.filter(isRecord).map((raw) => ({
      name: readText(raw, 'name'),
      assumption_text: readText(raw, 'assumption_text'),
      proposing_party: readText(raw, 'proposing_party'),
      schemas: readStrings(raw.schemas),
      industries: readStrings(raw.industries),
      values: readValues(raw, 'values'),
      tags: readStrings(raw.tags),
      validation_responsible_parties: readStrings(raw.validation_responsible_parties),
      creator: readText(raw, 'creator'),
      special_fields: {},
      revision: typeof raw.revision === 'number' ? raw.revision : 1,
      created_at: readText(raw, 'created_at'),
    })),
  }
}

/**
 * What a bundle names something by, translated into what this register calls the same thing.
 *
 * A bundle names everything rather than identifying it, because the identifiers of one register mean
 * nothing in another. The API documents a name as being accepted wherever an identifier is - but a name is
 * the road that is least likely to be paved: the reference implementation resolves an industry by either
 * and a schema by identifier alone, and an assumption created against a name it would not resolve is
 * created with no schema at all and says nothing about it.
 *
 * So the names are turned back into identifiers here, out of what this client is already holding, and only
 * the ones it cannot place are sent as names. That is right whichever way the service resolves them.
 */
type Resolver = (name: string) => string

/**
 * Build a resolver over a collection this register holds, which answers with the identifier of a name.
 */
const nameResolver = (held: { id: string; name: string }[]): Resolver => {
  const byName = new Map(held.map((item) => [item.name, item.id]))

  return (name: string) => byName.get(name) ?? name
}

/**
 * Turn one bundled assumption into the draft that creates it.
 *
 * The creator is taken from the bundle when it carries one, so a restored register still says who wrote
 * each assumption rather than attributing the whole of it to whoever pressed the button.
 */
const assumptionDraft = (
  bundled: BundledAssumption,
  fallbackCreator: string,
  resolve: { schema: Resolver; industry: Resolver },
): AssumptionDraft => ({
  name: bundled.name,
  assumption_text: bundled.assumption_text,
  proposing_party: bundled.proposing_party,
  schemas: bundled.schemas.map((name) => resolve.schema(name)),
  values: bundled.values,
  tags: [...bundled.tags],
  validation_responsible_parties: [...bundled.validation_responsible_parties],
  creator: bundled.creator.length > 0 ? bundled.creator : fallbackCreator,
  industries: bundled.industries.map((name) => resolve.industry(name)),
  special_fields: {},
})

/**
 * What tells two assumptions apart for the purpose of not writing the same one twice.
 *
 * The API has no uniqueness of its own and no way to ask whether something is already there, so restoring
 * the same bundle twice would otherwise double the register. An assumption is taken to be the one already
 * held when its name and its text match, which is what makes a restore that was interrupted safe to run
 * again - and is deliberately not the whole assumption, because a bundle carries the values of a revision
 * that the register may since have moved past.
 */
const assumptionKey = (name: string, text: string): string => `${name.trim()} ${text.trim()}`

export type { Bundle, BundledAssumption, BundledIndustry, BundledSchema, Resolver }
export {
  BUNDLE_FORMAT,
  BUNDLE_VERSION,
  assumptionDraft,
  assumptionKey,
  buildBundle,
  bundleFileName,
  nameResolver,
  readBundle,
  writeBundle,
}
