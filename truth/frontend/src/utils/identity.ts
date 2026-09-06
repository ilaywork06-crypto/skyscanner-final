/**
 * Who the client says it is when it creates something.
 *
 * Every write of this API takes a creator and the service authenticates nobody, so the name has to come from
 * the client. It is remembered in the browser so that a person states it once rather than on every dialog,
 * and it is deliberately a single place: when the service starts reading an identity off its own headers,
 * this is the one function that stops being needed.
 */

const STORAGE_KEY = 'truth.creator'

/** What a creator is called before anybody has said who they are. */
const ANONYMOUS = 'unknown'

/**
 * Read who the client is creating things as.
 *
 * A browser that refuses to hand its storage over - a private window, or one told to block site data - throws
 * rather than answering, and the deployment's own default is a better answer than a failure to render.
 */
const readCreator = (): string => {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored !== null && stored.trim().length > 0) {
      return stored.trim()
    }
  } catch {
    /* Nothing was remembered, so the default below stands. */
  }

  const configured = import.meta.env.VITE_DEFAULT_CREATOR

  return configured !== undefined && configured.length > 0 ? configured : ANONYMOUS
}

/**
 * Remember who the client is creating things as, and carry on without remembering it if the browser refuses.
 */
const writeCreator = (creator: string): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, creator.trim())
  } catch {
    /* The name still holds for this session, which is the part that matters. */
  }
}

export { ANONYMOUS, readCreator, writeCreator }
