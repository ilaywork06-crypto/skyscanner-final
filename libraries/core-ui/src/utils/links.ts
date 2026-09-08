/**
 * Finding the addresses inside a piece of text, so that a value somebody typed as a link reads as one.
 *
 * Nothing in the system ever asked for a field to hold a link, and people put them in anyway - a ticket, a
 * dashboard, a folder on a share, a wiki page describing what a run was for. Stored as a string they were
 * shown as a string: the one thing a reader wanted to do with the value was the one thing the value would
 * not do. These are the rules for reading the addresses back out of it.
 *
 * The reading is deliberately careful about two things. A value is text a user typed, so what is painted on
 * the page is always the characters they wrote and never markup built out of them; and an address is only
 * ever offered when it is one of the three schemes a browser should follow from here, so a value carrying
 * `javascript:` is text like any other rather than something a click can run.
 */

/** One run of a value: plain text, or text that is also an address. */
interface LinkSegment {
  text: string
  /** Where the run leads, or nothing when it is ordinary text. */
  href: string | null
}

/**
 * What is taken to be an address: a written scheme, a bare host that announces itself, or a mail address.
 *
 * The run is ended by whitespace and by the few characters that cannot appear in an address unescaped, which
 * is what stops a link from swallowing the sentence it was written in the middle of.
 */
const LINK_PATTERN =
  /(?:https?:\/\/|mailto:|www\.)[^\s<>"'` ]+|[\w.!#$%&'*+/=?^-]+@[\w-]+(?:\.[\w-]+)+/gi

/** The schemes a click here may follow. Everything else is text, whatever it looks like. */
const ALLOWED_SCHEMES: string[] = ['http:', 'https:', 'mailto:']

/** Whether a run already says which scheme it is to be followed under. */
const HAS_SCHEME = /^[a-z][\w+.-]*:/i

/** Punctuation that ends the sentence rather than the address, and is given back to the text around it. */
const TRAILING_PUNCTUATION = /[.,;:!?'"’”]+$/

/** The closing brackets an address may end with, each paired with what has to open it for it to count. */
const CLOSING_BRACKETS: Record<string, string> = { ')': '(', ']': '[', '}': '{' }

/**
 * Take back the punctuation at the end of a match that belongs to the sentence rather than to the address.
 *
 * `see http://wiki/run.` ends in a full stop that is not part of the page, and `(see http://wiki/run)` ends
 * in a bracket that closed the aside rather than the address - while `http://wiki/Run_(2026)` ends in one
 * that the address opened itself. The brackets are therefore counted rather than simply trimmed.
 *
 * :param match: The run as the pattern found it.
 * :return: The run with everything that belongs to the surrounding text taken off the end.
 */
const trimTrailing = (match: string): string => {
  let text = match

  for (;;) {
    const trimmed = text.replace(TRAILING_PUNCTUATION, '')
    const last = trimmed.slice(-1)
    const opening = CLOSING_BRACKETS[last]

    if (opening === undefined) {
      return trimmed
    }

    const opened = trimmed.split(opening).length - 1
    const closed = trimmed.split(last).length - 1
    if (opened >= closed) {
      return trimmed
    }

    text = trimmed.slice(0, -1)
  }
}

/**
 * Work out where a run leads, or nothing when it leads somewhere a click here should not follow.
 *
 * The address is read by the browser's own parser rather than by a pattern, which is what decides the
 * question being asked: not whether the text looks like a link, but what a browser would actually do with
 * it. Anything that is not one of the three schemes above comes back as nothing and stays text.
 *
 * :param text: The run, with the punctuation of the sentence already taken off.
 * :return: The address the run leads to, or nothing when it is not one that may be followed.
 */
const hrefFor = (text: string): string | null => {
  /*
   * A run that already names a scheme is left as it is - prefixing one that says `mailto:` would produce an
   * address naming the scheme twice. A bare mail address gets the scheme it implies, and anything else
   * announced itself with `www.` and gets the secure one.
   */
  const written = HAS_SCHEME.test(text) ? text : text.includes('@') ? `mailto:${text}` : `https://${text}`

  try {
    const url = new URL(written)

    return ALLOWED_SCHEMES.includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

/**
 * Split a value into its plain runs and its addresses, in the order they were written.
 *
 * A value holding no address at all comes back as a single run, so a caller can tell the common case apart
 * without scanning the answer.
 *
 * :param value: The text being read.
 * :return: The runs the value is made of.
 */
const splitLinks = (value: string): LinkSegment[] => {
  if (value.length === 0) {
    return []
  }

  const segments: LinkSegment[] = []
  let read = 0

  LINK_PATTERN.lastIndex = 0
  for (;;) {
    const match = LINK_PATTERN.exec(value)
    if (match === null) {
      break
    }

    const candidate = trimTrailing(match[0])
    const href = candidate.length === 0 ? null : hrefFor(candidate)
    if (href === null) {
      /* Not an address after all, so the reading carries on from just past what was rejected. */
      LINK_PATTERN.lastIndex = match.index + Math.max(candidate.length, 1)

      continue
    }

    if (match.index > read) {
      segments.push({ text: value.slice(read, match.index), href: null })
    }
    segments.push({ text: candidate, href })
    read = match.index + candidate.length
    LINK_PATTERN.lastIndex = read
  }

  if (segments.length === 0) {
    return [{ text: value, href: null }]
  }

  if (read < value.length) {
    segments.push({ text: value.slice(read), href: null })
  }

  return segments
}

/**
 * Say whether a value holds an address at all, which is the cheap question a renderer asks first.
 */
const holdsLink = (value: string): boolean => splitLinks(value).some((segment) => segment.href !== null)

export type { LinkSegment }
export { holdsLink, splitLinks }
