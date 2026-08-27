/**
 * The preview of the brief the events service writes for an event whose uploader did not write one.
 *
 * The convention itself lives in the events service, which is what actually names the event; this renders the
 * same parts in the same order so that the wizard can show what is about to be written rather than leaving
 * the user to press Create and find out. The one part it cannot know is the running number, which the service
 * mints when the event is stored.
 */

/** How the parts of a brief are joined, matching the convention of the events service exactly. */
const PART_SEPARATOR = ' · '
const PLATFORM_SEPARATOR = ' + '
const TYPE_SEPARATOR = ' / '

/** Past this the platforms are counted rather than named, so a brief stays a line somebody can read. */
const MAX_NAMED_PLATFORMS = 3

/** What an event whose type has not been picked yet is called while the preview is still incomplete. */
const UNTYPED_LABEL = 'Event'

/** How the running number the service mints is stood in for while the event does not have one yet. */
const PENDING_NUMBER = '#…'

/** The day spelled out rather than written in digits, so it cannot be mistaken for a reference number. */
const DATE_OPTIONS: Intl.DateTimeFormatOptions = { day: '2-digit', month: 'short', year: 'numeric' }

interface BriefParts {
  /** Names of the event types the event is filed under. */
  typeNames: string[]
  /** Keys of the platforms the event ran on. */
  platforms: string[]
  /** Key of the industry the event belongs to. */
  industry: string | null
  /** The day of the activity as the date input holds it, empty when the type does not ask for one. */
  eventDate: string
}

/**
 * Name the platforms an event ran on, counting them once there are more of them than a brief can carry.
 */
const platformLabel = (platforms: string[]): string => {
  const named = platforms.filter((platform) => platform.length > 0)
  if (named.length === 0) {
    return ''
  }

  if (named.length <= MAX_NAMED_PLATFORMS) {
    return named.join(PLATFORM_SEPARATOR)
  }

  const shown = named.slice(0, MAX_NAMED_PLATFORMS).join(PLATFORM_SEPARATOR)

  return `${shown} +${named.length - MAX_NAMED_PLATFORMS}`
}

/**
 * Read the day a brief is dated by, which is the day of the activity or, without one, today.
 */
const briefDate = (eventDate: string): string => {
  const moment = eventDate.length > 0 ? new Date(`${eventDate}T00:00:00`) : new Date()

  return Number.isNaN(moment.getTime())
    ? new Date().toLocaleDateString('en-GB', DATE_OPTIONS)
    : moment.toLocaleDateString('en-GB', DATE_OPTIONS)
}

/**
 * Render the brief the events service is about to write, as far as the wizard can know it.
 */
const buildEventBriefPreview = (parts: BriefParts): string => {
  const collected: string[] = [
    parts.typeNames.length > 0 ? parts.typeNames.join(TYPE_SEPARATOR) : UNTYPED_LABEL,
  ]

  const platforms = platformLabel(parts.platforms)
  if (platforms.length > 0) {
    collected.push(platforms)
  }

  if (parts.industry !== null && parts.industry.length > 0) {
    collected.push(parts.industry)
  }

  collected.push(briefDate(parts.eventDate))
  collected.push(PENDING_NUMBER)

  return collected.join(PART_SEPARATOR)
}

export type { BriefParts }
export { buildEventBriefPreview }
