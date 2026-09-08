/**
 * The compatibility shims the grid needs to render the same way across the browser versions it is opened in.
 *
 * The theming API of AG Grid derives most of its palette at run time: a border, a hover, a disabled label
 * and a header separator are all written as `color-mix(in srgb, ...)` over the few colours the theme names.
 * That function reached Chrome in version 111, and in anything older every derived declaration is dropped as
 * invalid - which is not a slightly different table, it is a table with no borders, no hover and unreadable
 * headers. The stylesheet the grid injects is therefore rewritten, with the mixes worked out here.
 *
 * Almost none of those mixes name a colour outright. The grid writes them over its own custom properties -
 * `color-mix(in srgb, transparent, var(--ag-active-color) 12%)` is the shape nearly all of them take - and a
 * rewriter that could only read literal colours would resolve a handful of them and leave the rest exactly as
 * invalid as it found them. So the properties are read out of the same stylesheets first, and an operand
 * naming one is expanded before the mix over it is worked out.
 *
 * The one thing that cannot be done here is the cascade. A custom property means whatever the last rule that
 * set it says, and this reads the sheets in order and lets the last definition win - which is what the
 * cascade does for rules of equal weight, and what the grid writes.
 */

/** Every custom property the injected stylesheets set, by name. */
type Variables = Map<string, string>

/** A colour as the three channels and the alpha every supported notation is read into. */
interface Rgba {
  r: number
  g: number
  b: number
  a: number
}

/**
 * One `color-mix(in srgb, ...)` call, allowing its arguments to hold a call of their own.
 *
 * The nesting matters twice over: an operand may be written as `rgba(...)`, and a mix may be given another
 * mix to blend. The second case is resolved from the inside out, which is what the pass loop below does.
 */
const MIX_PATTERN = /color-mix\(\s*in\s+srgb\s*,\s*((?:[^()]|\([^()]*\))*)\)/i

/** The style elements AG Grid writes its generated theme into, which are the only ones ever rewritten. */
const INJECTED_STYLES = 'style[data-ag-global-css]'

/** One custom property being set, which is where the colours the mixes are written over actually live. */
const VARIABLE_PATTERN = /(--[\w-]+)\s*:\s*([^;}]+)/g

/** One custom property being read, with the fallback it may carry for when nothing set it. */
const VARIABLE_REFERENCE = /var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)/

/** How many times a property naming another property is followed before the chain is given up on. */
const MAX_VARIABLE_DEPTH = 8

/** The roots a watch is already installed on, so every table on a page shares the one it finds there. */
const observed = new WeakSet<Document | ShadowRoot>()

/** How deeply one mix may be nested inside another, which is far past anything a theme actually writes. */
const MAX_NESTING = 16

/** The named colours the grid actually writes, which is the shortest list that answers every mix it makes. */
const NAMED_COLORS: Record<string, string> = {
  transparent: 'rgba(0, 0, 0, 0)',
  black: '#000000',
  white: '#ffffff',
}

const FULL_PERCENT = 100
const HEX_RADIX = 16
const SHORT_HEX_LENGTH = 4

/**
 * Decide whether the browser understands the colour function the generated theme is written in.
 */
const supportsColorMix = (): boolean =>
  typeof CSS !== 'undefined' &&
  typeof CSS.supports === 'function' &&
  CSS.supports('color', 'color-mix(in srgb, red 50%, blue)')

/**
 * Read every custom property one stylesheet sets, letting a later definition replace an earlier one.
 *
 * :param css: The stylesheet being read.
 * :param into: The properties gathered so far, which this adds to.
 */
const readVariables = (css: string, into: Variables): void => {
  for (const match of css.matchAll(VARIABLE_PATTERN)) {
    into.set(match[1], match[2].trim())
  }
}

/**
 * Put the value of every custom property a piece of text reads in place of the reading.
 *
 * A property may be written in terms of another one, so this follows the chain rather than expanding once.
 * The chain is bounded, because a property that names itself is a stylesheet nobody has to be rescued from
 * and an unbounded follow would hang the page rather than fail to colour a border.
 *
 * :param value: The text being expanded, which is one operand of a mix.
 * :param variables: The properties the stylesheets set.
 * :param depth: How many readings have already been followed.
 * :return: The same text with every property it reads replaced by what that property holds.
 */
const expandVariables = (value: string, variables: Variables, depth: number = 0): string => {
  if (depth >= MAX_VARIABLE_DEPTH) {
    return value
  }

  const match = VARIABLE_REFERENCE.exec(value)
  if (match === null) {
    return value
  }

  /* A property nothing set falls back to what the reading itself named, which is what the browser would do. */
  const replacement = (variables.get(match[1]) ?? match[2] ?? '').trim()
  const expanded = value.slice(0, match.index) + replacement + value.slice(match.index + match[0].length)

  return expandVariables(expanded, variables, depth + 1)
}

/**
 * Read one operand of a mix into its channels, following whatever it was written in terms of.
 *
 * An operand is rarely a colour as written. It is a custom property, and the property may hold another
 * property or a mix of its own, so it is expanded and then settled before there is anything to read.
 *
 * :param raw: The operand exactly as the stylesheet wrote it.
 * :param variables: The properties the stylesheets set.
 * :return: The colour it stands for, or nothing when it does not stand for one.
 */
const readOperandColor = (raw: string, variables: Variables): Rgba | null => {
  const expanded = expandVariables(raw, variables)
  const settled = expanded.toLowerCase().includes('color-mix') ? resolveColorMix(expanded, variables) : expanded

  return parseColor(settled)
}

/**
 * Read one colour into its channels, accepting the notations the generated theme writes.
 */
const parseColor = (value: string): Rgba | null => {
  const text = (NAMED_COLORS[value.trim().toLowerCase()] ?? value).trim()

  if (text.startsWith('#')) {
    return parseHex(text)
  }

  const channels = /^rgba?\(([^)]+)\)$/i.exec(text)
  if (channels === null) {
    return null
  }

  const parts = channels[1]
    .split(/[\s,/]+/)
    .filter((part) => part.length > 0)
    .map((part) => (part.endsWith('%') ? (Number.parseFloat(part) / FULL_PERCENT) * 255 : Number.parseFloat(part)))

  const [r, g, b, a] = parts
  if (![r, g, b].every((channel) => Number.isFinite(channel))) {
    return null
  }

  /* The alpha of a four part notation is a fraction rather than a channel, so it is read back off the scale. */
  return { r, g, b, a: a === undefined ? 1 : a / 255 }
}

/**
 * Read a hexadecimal colour, in both the short and the long form and with or without an alpha.
 */
const parseHex = (text: string): Rgba | null => {
  const digits = text.slice(1)
  const expanded =
    digits.length < SHORT_HEX_LENGTH + 1
      ? digits
          .split('')
          .map((digit) => `${digit}${digit}`)
          .join('')
      : digits

  if (!/^[0-9a-f]{6}([0-9a-f]{2})?$/i.test(expanded)) {
    return null
  }

  const channel = (index: number): number => Number.parseInt(expanded.slice(index, index + 2), HEX_RADIX)
  const alpha = expanded.length > 6 ? channel(6) / 255 : 1

  return { r: channel(0), g: channel(2), b: channel(4), a: alpha }
}

/**
 * Split the arguments of one mix into the two colours and the weight the second of them carries.
 */
const readOperands = (body: string): { first: string; second: string; weight: number } | null => {
  const parts = splitArguments(body)
  if (parts.length !== 2) {
    return null
  }

  const [first, second] = parts.map((part) => readOperand(part))

  /*
   * A mix may state either weight or neither, and stating one is the same as stating the other, so whichever
   * side named a percentage decides how much of the second colour ends up in the answer.
   */
  const weight =
    second.percent !== null
      ? second.percent
      : first.percent !== null
        ? FULL_PERCENT - first.percent
        : FULL_PERCENT / 2

  return { first: first.color, second: second.color, weight: weight / FULL_PERCENT }
}

/**
 * Split one argument into the colour it names and the share it was given, if it was given one.
 */
const readOperand = (part: string): { color: string; percent: number | null } => {
  const trimmed = part.trim()
  const percent = /\s([\d.]+)%$/.exec(trimmed)
  if (percent === null) {
    return { color: trimmed, percent: null }
  }

  return { color: trimmed.slice(0, percent.index).trim(), percent: Number.parseFloat(percent[1]) }
}

/**
 * Split the arguments of a call on the commas that belong to it rather than to a call nested inside it.
 */
const splitArguments = (body: string): string[] => {
  const parts: string[] = []
  let depth = 0
  let current = ''

  for (const character of body) {
    if (character === '(') {
      depth += 1
    }
    if (character === ')') {
      depth -= 1
    }
    if (character === ',' && depth === 0) {
      parts.push(current)
      current = ''

      continue
    }
    current += character
  }
  parts.push(current)

  return parts
}

/**
 * Work out the colour one mix stands for, or nothing when either side is not a colour this can read.
 *
 * :param body: The arguments of the mix, as the stylesheet wrote them.
 * :param variables: The properties the stylesheets set, which the operands are usually written in terms of.
 * :return: The colour the mix stands for, or nothing when either side could not be read.
 */
const resolveMix = (body: string, variables: Variables): string | null => {
  const operands = readOperands(body)
  if (operands === null) {
    return null
  }

  const first = readOperandColor(operands.first, variables)
  const second = readOperandColor(operands.second, variables)
  if (first === null || second === null) {
    return null
  }

  /*
   * The channels are weighted by their own alpha before being mixed and divided back out afterwards, which
   * is how the function being replaced is defined and not a detail that can be skipped. Mixing the channels
   * as they stand makes a half transparent red over `transparent` come out a dark red at half alpha, because
   * the invisible black that `transparent` actually is gets a full half of the answer. Premultiplied, it
   * comes out the red it should be, and the transparency lands in the alpha where it belongs - which matters
   * here more than anywhere, because a hover and a border are exactly the mixes written over `transparent`.
   */
  const weight = operands.weight
  const alpha = first.a * (1 - weight) + second.a * weight
  const blend = (from: number, to: number): number =>
    alpha === 0 ? 0 : Math.round((from * first.a * (1 - weight) + to * second.a * weight) / alpha)

  /*
   * The answer is written as hexadecimal rather than as `rgba(...)` because it may itself be an operand of
   * the mix around it, and a replacement that brought brackets with it would change what that outer call
   * looks like. Eight digit hexadecimal has been understood far longer than the function being replaced.
   */
  return `#${[blend(first.r, second.r), blend(first.g, second.g), blend(first.b, second.b), Math.round(alpha * 255)]
    .map((channel) => Math.min(Math.max(channel, 0), 255).toString(HEX_RADIX).padStart(2, '0'))
    .join('')}`
}

/**
 * Replace every mix of a string that can be resolved without looking inside another one.
 *
 * One sweep therefore settles the innermost level of nesting wherever it appears. A mix that still holds a
 * mix is stepped over rather than guessed at, and a mix over something only the browser can resolve - a
 * custom property read at paint time - is carried through untouched.
 *
 * :param css: The stylesheet as it currently stands.
 * :param variables: The properties the stylesheets set.
 * :return: The same stylesheet with one level of mixes worked out.
 */
const resolveInnermost = (css: string, variables: Variables): string => {
  let head = ''
  let tail = css

  for (;;) {
    const match = MIX_PATTERN.exec(tail)
    if (match === null) {
      return head + tail
    }

    const end = match.index + match[0].length

    /*
     * A mix whose own arguments hold another mix is not this sweep's to resolve. Stepping past its opening
     * bracket alone leaves the inner call in front of the reader, so it is the one that gets found next and
     * the outer one becomes readable on the sweep after this.
     */
    if (match[1].toLowerCase().includes('color-mix')) {
      const opening = match.index + match[0].indexOf('(') + 1
      head += tail.slice(0, opening)
      tail = tail.slice(opening)

      continue
    }

    const replacement = resolveMix(match[1], variables)
    if (replacement === null) {
      head += tail.slice(0, end)
      tail = tail.slice(end)

      continue
    }

    head += tail.slice(0, match.index) + replacement
    tail = tail.slice(end)
  }
}

/**
 * Rewrite every mix of a stylesheet into the plain colour it stands for.
 *
 * The innermost calls are settled first and the whole string is then swept again, so a mix whose operand was
 * itself a mix becomes readable on the pass after that one. Sweeping stops as soon as nothing moved, which
 * is what leaves the calls this cannot read exactly as they were: that one declaration keeps behaving as it
 * does today rather than everything around it breaking.
 *
 * :param css: The stylesheet being rewritten.
 * :param variables: The properties the stylesheets set, without which almost nothing here can be resolved.
 * :return: The same stylesheet with every mix it could read worked out.
 */
const resolveColorMix = (css: string, variables: Variables = new Map()): string => {
  let resolved = css

  for (let pass = 0; pass < MAX_NESTING; pass += 1) {
    const swept = resolveInnermost(resolved, variables)
    if (swept === resolved) {
      return resolved
    }
    resolved = swept
  }

  return resolved
}

/**
 * Rewrite the stylesheets the grid injected so that a browser without the colour function still gets colours.
 *
 * Only the sheets the grid wrote are touched, and only in a browser that needs it, so on everything modern
 * this costs one feature test and nothing else.
 */
const applyThemeCompatibility = (root: Document | ShadowRoot = document): void => {
  if (supportsColorMix()) {
    return
  }

  const sheets = Array.from(root.querySelectorAll<HTMLStyleElement>(INJECTED_STYLES))

  /*
   * Every sheet is read for its properties before any of them is rewritten. The grid writes the palette into
   * one sheet and the rules that mix over it into another, so a rewriter working sheet by sheet would reach
   * the mixes before it had ever seen the colours they are written over.
   */
  const variables: Variables = new Map()
  sheets.forEach((sheet) => readVariables(sheet.textContent ?? '', variables))

  sheets.forEach((sheet) => {
    const css = sheet.textContent ?? ''
    if (!css.includes('color-mix')) {
      return
    }

    const resolved = resolveColorMix(css, variables)
    if (resolved !== css) {
      sheet.textContent = resolved
    }
  })
}

/**
 * Keep the rewritten palette in place for as long as the page is open.
 *
 * One sweep when a table is built holds only until the grid writes its stylesheet again, which it does every
 * time the theme it is handed changes. That regenerated sheet arrives with its mixes unresolved, so on a
 * browser without the colour function a table that had borders and a hover a moment earlier loses both in
 * the middle of a session, and only a reload brings them back. The sheets are therefore watched rather than
 * swept once: every rewrite the grid makes is answered with a rewrite of ours.
 *
 * :param root: The document or shadow root the grid injected its stylesheets into.
 */
const observeThemeCompatibility = (root: Document | ShadowRoot = document): void => {
  if (supportsColorMix() || typeof MutationObserver === 'undefined' || observed.has(root)) {
    return
  }

  observed.add(root)
  applyThemeCompatibility(root)

  const observer = new MutationObserver(() => {
    applyThemeCompatibility(root)

    /*
     * The rewrite just made is a mutation like any other, and reading it back would leave the watch
     * answering itself for as long as the page is open. Dropping the records it left is what ends that.
     */
    observer.takeRecords()
  })

  /*
   * Only the head is watched, and only for a stylesheet appearing or being written over. The rows of the
   * table are mutations too, and a watch that saw them would be answering every redraw of a table on the
   * very machines this exists for.
   */
  observer.observe('head' in root ? root.head : root, {
    childList: true,
    subtree: true,
    characterData: true,
  })
}

export type { Rgba, Variables }
export {
  applyThemeCompatibility,
  observeThemeCompatibility,
  parseColor,
  resolveColorMix,
  supportsColorMix,
}
