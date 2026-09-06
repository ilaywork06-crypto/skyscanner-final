/**
 * Reading a whole collection out of an API that only offers a window onto it.
 *
 * Every listing of this service takes an offset and a limit and answers with a bare array, and none of them
 * says how many rows there are in total. A caller that wants the whole collection - which is every caller
 * here, because the table filters, sorts and pages in the browser - therefore has to ask repeatedly until a
 * page comes back short, which is the only signal the API gives that it has reached the end.
 */

/** How many rows one request asks for. Large enough that most collections arrive in one or two rounds. */
const PAGE_SIZE = 200

/**
 * A ceiling on the rounds, so that a service which keeps answering full pages cannot spin the client forever.
 *
 * At the page size above this is two hundred thousand rows, which is far past anything the table can render
 * and far past anything this register is expected to hold.
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
