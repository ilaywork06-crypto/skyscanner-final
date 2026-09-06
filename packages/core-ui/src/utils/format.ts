/**
 * The formatting helpers shared by every surface of the system - dates, sizes, keys and labels.
 *
 * These live in the library rather than in the web client because they decide how a value reads, and the
 * same value has to read the same way in a table, in a dialog and in an edit history.
 */

/*
 * Every moment travels and is stored in UTC, and every moment is read in the time zone of the viewer.
 *
 * The client used to render moments in UTC so that two users far apart would quote the very same string to
 * each other. That is not how anybody reads a timestamp: a user compares it against the clock on their own
 * wall, so an event uploaded at 22:45 has to read 22:45 to the person who uploaded it rather than 19:45.
 * Leaving the zone out of the options is what asks the runtime for the zone of the viewer.
 */
const DATE_OPTIONS: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
}

const DATE_TIME_OPTIONS: Intl.DateTimeFormatOptions = {
  ...DATE_OPTIONS,
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}

/*
 * The same moment written as short as it can be and still be read: two digit year, no seconds. It is what the
 * bookkeeping columns of a table carry - created at, updated at - where the full form takes a hundred and
 * ninety pixels of a row for the least interesting thing on it.
 */
const COMPACT_DATE_TIME_OPTIONS: Intl.DateTimeFormatOptions = {
  year: '2-digit',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}

const SIZE_UNITS: string[] = ['B', 'KB', 'MB', 'GB', 'TB']
const SIZE_STEP = 1024
const EMPTY_PLACEHOLDER = '—'

/** How many digits the year and the month or the day take in the value of a date input. */
const YEAR_DIGITS = 4
const MONTH_DAY_DIGITS = 2

/**
 * Render a moment as a date in the time zone of the viewer.
 */
const formatDate = (value: string | null | undefined): string => {
  if (value === null || value === undefined || value.length === 0) {
    return EMPTY_PLACEHOLDER
  }

  const moment = new Date(value)

  return Number.isNaN(moment.getTime()) ? EMPTY_PLACEHOLDER : moment.toLocaleDateString('en-GB', DATE_OPTIONS)
}

/**
 * Render a moment as a date and a time in the time zone of the viewer.
 */
const formatDateTime = (value: string | null | undefined): string => {
  if (value === null || value === undefined || value.length === 0) {
    return EMPTY_PLACEHOLDER
  }

  const moment = new Date(value)

  return Number.isNaN(moment.getTime()) ? EMPTY_PLACEHOLDER : moment.toLocaleString('en-GB', DATE_TIME_OPTIONS)
}

/**
 * Render a moment as the shortest date and time that is still readable, in the time zone of the viewer.
 */
const formatCompactDateTime = (value: string | null | undefined): string => {
  if (value === null || value === undefined || value.length === 0) {
    return EMPTY_PLACEHOLDER
  }

  const moment = new Date(value)

  return Number.isNaN(moment.getTime())
    ? EMPTY_PLACEHOLDER
    : moment.toLocaleString('en-GB', COMPACT_DATE_TIME_OPTIONS)
}

/**
 * Render a byte count with the largest unit that keeps the number readable.
 */
const formatBytes = (value: number): string => {
  if (value <= 0) {
    return `0 ${SIZE_UNITS[0]}`
  }

  const exponent = Math.min(Math.floor(Math.log(value) / Math.log(SIZE_STEP)), SIZE_UNITS.length - 1)
  const scaled = value / SIZE_STEP ** exponent

  return `${scaled.toFixed(exponent === 0 ? 0 : 1)} ${SIZE_UNITS[exponent]}`
}

/**
 * Turn the value of a date input into the moment the API stores, or nothing when it was left empty.
 *
 * A day the user picks means midnight of that day where the user is rather than midnight in UTC, because the
 * picker is read against the same wall clock every displayed moment is. Omitting the offset from the string
 * is what asks the runtime for local midnight; the moment is still handed to the API in UTC, where a day
 * picked east of Greenwich lands on the evening before. `toDateInput` reads it back in the same zone, so the
 * day survives being saved and opened again unchanged - which is exactly what UTC midnight broke for
 * everybody west of Greenwich, where it read back as the day before.
 */
const toIsoDate = (value: string): string | null =>
  value.length === 0 ? null : new Date(`${value}T00:00:00`).toISOString()

/**
 * Turn a stored moment back into the value a date input shows.
 *
 * The calendar day is taken in the zone of the viewer instead of being sliced off the front of the ISO
 * string, which would hand back the UTC day: east of Greenwich an evening moment already belongs to the next
 * day in UTC, so slicing offered a day the event is not displayed under anywhere else.
 */
const toDateInput = (value: string | null | undefined): string => {
  if (value === null || value === undefined || value.length === 0) {
    return ''
  }

  const moment = new Date(value)
  if (Number.isNaN(moment.getTime())) {
    return ''
  }

  const year = String(moment.getFullYear()).padStart(YEAR_DIGITS, '0')
  /* The runtime counts months from zero while the input writes them from one. */
  const month = String(moment.getMonth() + 1).padStart(MONTH_DAY_DIGITS, '0')
  const day = String(moment.getDate()).padStart(MONTH_DAY_DIGITS, '0')

  return `${year}-${month}-${day}`
}

/**
 * Turn a machine key into the label a user reads.
 */
const humanizeKey = (key: string): string =>
  key
    .split(/[_.-]/)
    .filter((part) => part.length > 0)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')

/**
 * Shorten a long text so that it fits into one cell.
 */
const truncate = (value: string, limit: number): string =>
  value.length <= limit ? value : `${value.slice(0, limit - 1)}…`

/**
 * Turn a label the user typed into the machine key it is stored under.
 */
const slugify = (value: string): string =>
  value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')

export {
  EMPTY_PLACEHOLDER,
  formatBytes,
  formatCompactDateTime,
  formatDate,
  formatDateTime,
  humanizeKey,
  slugify,
  toDateInput,
  toIsoDate,
  truncate,
}
