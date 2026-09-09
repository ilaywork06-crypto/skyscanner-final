/**
 * The payloads of the industries, which are the top of the navigation and the vocabulary assumptions belong to.
 */

/**
 * An industry as every endpoint of the API hands it over - an identifier and a name, and nothing else.
 *
 * The service holds a description and a creator as well, but never gives either of them back, so nothing in
 * the client may be written as though it had them.
 */
interface Industry {
  id: string
  name: string
}

/** What creating an industry asks for. */
interface IndustryDraft {
  name: string
  description: string
  creator: string
}

export type { Industry, IndustryDraft }
