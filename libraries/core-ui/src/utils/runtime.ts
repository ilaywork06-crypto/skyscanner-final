/**
 * The handful of built in methods the client is opened without, installed only where they are missing.
 *
 * The bundler is told the oldest browser this is built for, and it answers that by rewriting *syntax*: an
 * arrow function, optional chaining, a class field. It does nothing at all about *methods*, because a method
 * that does not exist is not a compile time fact - so `Array.prototype.findLast`, which arrived in Chrome 97,
 * is emitted exactly as it was written and throws on anything older the moment the code path runs.
 *
 * That code path is rarely ours. It belongs to the component libraries, which are built against a far more
 * recent baseline than this client is opened on, and it fails in the place a user is least able to explain -
 * a ripple that kills a click, a table that stops redrawing. The floor is therefore held here rather than
 * hoped for: each method is installed only when the browser lacks it, so on everything current this file
 * costs a few property lookups at start up and changes nothing.
 *
 * Every one of these is written to the specification of the method it stands in for, including the parts
 * that are easy to skip: the callback takes the value, the index and the array, `thisArg` is honoured, and a
 * method that copies returns a new array rather than touching the one it was called on.
 */

/** The methods below are installed onto prototypes, which is exactly what a shim is. */
/* eslint-disable no-extend-native */

/** What a comparison of two values reports, and what a sort is given when it is given nothing. */
type Comparator<ItemT> = (left: ItemT, right: ItemT) => number

/**
 * Install one method onto a prototype, leaving a browser that already has it exactly as it was.
 *
 * :param target: The prototype the method belongs on.
 * :param name: What the method is called.
 * :param value: The implementation used where the browser offers none.
 */
const define = (target: object, name: string, value: unknown): void => {
  if (name in target) {
    return
  }

  Object.defineProperty(target, name, {
    value,
    writable: true,
    configurable: true,
    enumerable: false,
  })
}

/**
 * Install everything the client may be opened without.
 *
 * Called once, from the entry point, before anything else has had the chance to reach for one of them.
 */
const installRuntimeShims = (): void => {
  /* Chrome 97. Vuetify reaches for it while it is taking a ripple back off an element that was clicked. */
  define(Array.prototype, 'findLast', function findLast<ItemT>(
    this: ItemT[],
    predicate: (value: ItemT, index: number, array: ItemT[]) => unknown,
    thisArg?: unknown,
  ): ItemT | undefined {
    for (let index = this.length - 1; index >= 0; index -= 1) {
      if (predicate.call(thisArg, this[index], index, this)) {
        return this[index]
      }
    }

    return undefined
  })

  /* Chrome 97, and the pair of the one above. */
  define(Array.prototype, 'findLastIndex', function findLastIndex<ItemT>(
    this: ItemT[],
    predicate: (value: ItemT, index: number, array: ItemT[]) => unknown,
    thisArg?: unknown,
  ): number {
    for (let index = this.length - 1; index >= 0; index -= 1) {
      if (predicate.call(thisArg, this[index], index, this)) {
        return index
      }
    }

    return -1
  })

  /* Chrome 92. Counting from the end of a list is the whole of it. */
  define(Array.prototype, 'at', function at<ItemT>(this: ItemT[], index: number): ItemT | undefined {
    const from = Math.trunc(index) || 0

    return this[from < 0 ? this.length + from : from]
  })

  /* Chrome 92, and the same method on a string. */
  define(String.prototype, 'at', function at(this: string, index: number): string | undefined {
    const from = Math.trunc(index) || 0
    const at_ = from < 0 ? this.length + from : from

    return at_ >= 0 && at_ < this.length ? this.charAt(at_) : undefined
  })

  /*
   * Chrome 110. Vue writes these onto the arrays it makes reactive, which means they exist as properties on
   * every reactive array whether the browser has them or not - and the moment one is called, Vue calls
   * straight through to the native method underneath and finds nothing there.
   */
  define(Array.prototype, 'toSorted', function toSorted<ItemT>(
    this: ItemT[],
    compare?: Comparator<ItemT>,
  ): ItemT[] {
    return [...this].sort(compare)
  })

  define(Array.prototype, 'toReversed', function toReversed<ItemT>(this: ItemT[]): ItemT[] {
    return [...this].reverse()
  })

  define(Array.prototype, 'toSpliced', function toSpliced<ItemT>(
    this: ItemT[],
    start: number,
    deleteCount?: number,
    ...items: ItemT[]
  ): ItemT[] {
    const copy = [...this]
    if (deleteCount === undefined) {
      copy.splice(start)
    } else {
      copy.splice(start, deleteCount, ...items)
    }

    return copy
  })

  define(Array.prototype, 'with', function withAt<ItemT>(this: ItemT[], index: number, value: ItemT): ItemT[] {
    const copy = [...this]
    copy[index < 0 ? this.length + index : index] = value

    return copy
  })

  /* Chrome 93. The readable way of asking what `hasOwnProperty` asks. */
  define(Object, 'hasOwn', function hasOwn(target: object, key: PropertyKey): boolean {
    return Object.prototype.hasOwnProperty.call(target, key)
  })
}

export { installRuntimeShims }
