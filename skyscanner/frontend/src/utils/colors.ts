/**
 * The mapping between the states of the inventory and the theme colour tokens their chips are painted with.
 *
 * What an industry is coloured is decided by the shared palette, because every product colours a vocabulary
 * the same way. What a status means is decided here, because only this product has these statuses.
 */

import { DEFAULT_TOKEN } from '@truth-platform/core-ui'

import type { EntityStatus, EventStatus, ExperimentResult } from '@/models/common'

const EVENT_STATUS_TOKENS: Record<EventStatus, string> = {
  draft: 'status-neutral',
  operational: 'status-positive'
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
const paletteToken = (value: string, palette: string | undefined): string =>
  palette === 'experiment' ? experimentResultToken(value) : statusToken(value)

export { experimentResultToken, paletteToken, statusToken }
