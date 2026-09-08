/**
 * Reading a whole collection out of an API that only offers a window onto it.
 *
 * The industries and the schemas are listed with an offset and a limit and answered with a bare array, and
 * neither listing says how many there are in total, so reading one whole means asking repeatedly until a page
 * comes back short - the only signal those listings give that they have reached the end.
 *
 * The assumptions are not read this way and must not be. They are asked for one window at a time, through
 * the query endpoint, because there is no size of register at which reading all of them is the right thing
 * to do. What this reads whole are the two collections bounded by how many people write into them.
 */

/** How many rows one request asks for. Large enough that most collections arrive in one or two rounds. */
const PAGE_SIZE = 200

/**
 * A ceiling on the rounds, so that a service which keeps answering full pages cannot spin the client forever.
 *
 * At the page size above this is two hundred thousand rows, which is far past any number of industries or
 * declarations a register acquires - and those are the only two things read this way.
 */
const MAX_PAGES = 1000

/**
 * Read every row of a listing, a page at a time, and hand back the whole collection.
 *
 * The reader is told how far it has got after each page, because a first load of several rounds is otherwise
 * a spinner that says nothing for as long as it takes.
 */
const readAll = async <ItemT>(
  readPage: (offset: number, limit: number) => Promise<ItemT[]>,
  onProgress?: (loaded: number) => void,
): Promise<ItemT[]> => {
  const collected: ItemT[] = []

  for (let round = 0; round < MAX_PAGES; round += 1) {
    const page = await readPage(collected.length, PAGE_SIZE)
    collected.push(...page)
    onProgress?.(collected.length)

    /* A page that came back short is the last one: there was nothing left to fill it with. */
    if (page.length < PAGE_SIZE) {
      break
    }
  }

  return collected
}

export { MAX_PAGES, PAGE_SIZE, readAll }
