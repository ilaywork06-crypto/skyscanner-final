/**
 * How a value of a vocabulary is turned into the theme colour token its chip is painted with.
 *
 * A product registers its own colours where it can - an industry is created with one - and everything else
 * is coloured by its own name, so that the same word always arrives in the same colour without anybody
 * having to choose one for it.
 */

import type { TaxonomyItem } from '../models/common'

/** The chip colours of the palette, in the order a picker offers them. */
const CHIP_PALETTE: string[] = [
  'chip-industry-amber',
  'chip-industry-blue',
  'chip-industry-violet',
  'chip-industry-rose',
  'chip-industry-coral',
  'chip-industry-green',
]

/** What each of those colours is called where one is picked by hand. */
const CHIP_COLOUR_NAMES: Record<string, string> = {
  'chip-industry-amber': 'Amber',
  'chip-industry-blue': 'Blue',
  'chip-industry-violet': 'Violet',
  'chip-industry-rose': 'Rose',
  'chip-industry-coral': 'Coral',
  'chip-industry-green': 'Green',
}

/** What a value with nothing else to say about it is painted in. */
const DEFAULT_TOKEN = 'app-muted'

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

/**
 * Pick the colour of a value out of the palette, by its own name and nothing else.
 */
const hashedToken = (value: string): string => CHIP_PALETTE[Math.abs(hashText(value)) % CHIP_PALETTE.length]

/**
 * Pick the colour token of a chip, preferring the colour the member was registered with.
 */
const taxonomyToken = (key: string, items: TaxonomyItem[]): string => {
  const item = items.find((candidate) => candidate.key === key)
  if (item !== undefined && item.color.length > 0) {
    if (item.color.startsWith('chip-')) {
      return item.color
    }

    return `chip-industry-${item.color.replace('industry', '').toLowerCase()}`
  }

  return hashedToken(key)
}

export { CHIP_COLOUR_NAMES, CHIP_PALETTE, DEFAULT_TOKEN, hashText, hashedToken, taxonomyToken }
