/**
 * The mapping between the values of the inventory and the theme colour tokens their chips are painted with.
 */

import type { EntityStatus, EventStatus, ExperimentResult } from '@/models/common'
import type { Industry } from '@/models/industry'

const INDUSTRY_PALETTE: string[] = [
  'chip-industry-amber',
  'chip-industry-blue',
  'chip-industry-violet',
  'chip-industry-rose',
  'chip-industry-coral',
  'chip-industry-green',
]

/** What each industry colour is called where one is picked, in the order the picker offers them. */
const INDUSTRY_COLOUR_NAMES: Record<string, string> = {
  'chip-industry-amber': 'Amber',
  'chip-industry-blue': 'Blue',
  'chip-industry-violet': 'Violet',
  'chip-industry-rose': 'Rose',
  'chip-industry-coral': 'Coral',
  'chip-industry-green': 'Green',
}

const EVENT_STATUS_TOKENS: Record<EventStatus, string> = {
  draft: 'status-neutral',
  raw: 'status-pending',
  parsed: 'status-positive',
  partial: 'status-pending',
  failed: 'status-negative',
  archived: 'app-muted',
}

const ENTITY_STATUS_TOKENS: Record<EntityStatus, string> = {
  raw: 'status-pending',
  parsing: 'status-neutral',
  /* Some of the data came through and some did not, which is the same half success the events call partial. */
  partially_parsed: 'status-partial',
  parsed: 'status-positive',
  failed: 'status-negative',
}

/*
 * The outcome of an activity needs its own mapping rather than sharing the status one: "partial" means an
 * amber half success here, while as a parsing status it means something else entirely.
 */
const EXPERIMENT_RESULT_TOKENS: Record<ExperimentResult, string> = {
  successful: 'status-positive',
  partial: 'status-partial',
  failed: 'status-negative',
}

const DEFAULT_TOKEN = 'app-muted'

/**
 * Pick the colour token of a status chip, whichever kind of status it carries.
 */
const statusToken = (status: string): string => {
  const eventToken = EVENT_STATUS_TOKENS[status as EventStatus]
  if (eventToken !== undefined) {
    return eventToken
  }

  return ENTITY_STATUS_TOKENS[status as EntityStatus] ?? DEFAULT_TOKEN
}

/**
 * Pick the colour token of an experiment result chip - green when it worked, orange when it half worked.
 */
const experimentResultToken = (result: string): string =>
  EXPERIMENT_RESULT_TOKENS[result as ExperimentResult] ?? DEFAULT_TOKEN

/**
 * Pick the colour token of a chip that a generated column asked for by palette name.
 */
const paletteToken = (palette: string | undefined, value: string): string =>
  palette === 'experiment' ? experimentResultToken(value) : statusToken(value)

/**
 * Pick the colour token of an industry chip, preferring the colour the industry was registered with.
 */
const industryToken = (industryKey: string, industries: Industry[]): string => {
  const industry = industries.find((candidate) => candidate.key === industryKey)
  if (industry !== undefined && industry.color.length > 0) {
    if (industry.color.startsWith('chip-')) {
      return industry.color
    }

    return `chip-industry-${industry.color.replace('industry', '').toLowerCase()}`
  }

  const index = Math.abs(hashText(industryKey)) % INDUSTRY_PALETTE.length

  return INDUSTRY_PALETTE[index]
}

/**
 * Turn a piece of text into a stable number, so that the same value always gets the same colour.
 */
const hashText = (value: string): number => {
  let hash = 0
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(index)
    hash |= 0
  }

  return hash
}

export {
  INDUSTRY_COLOUR_NAMES,
  INDUSTRY_PALETTE,
  experimentResultToken,
  hashText,
  paletteToken,
  statusToken,
  industryToken,
}
