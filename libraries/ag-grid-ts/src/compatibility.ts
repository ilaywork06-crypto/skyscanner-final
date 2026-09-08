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
 *
 * The same stylesheets carry a second thing an older browser cannot read. The grid writes a good sixty of
 * its rules *inside* other rules - `.ag-header-cell-resize { ...; &:after { ... } }` is the shape almost all
 * of them take - and native nesting reached Chrome in version 112, one version after the colour function.
 * Below that the nested rule is not a slightly different rule, it is a parse error: the browser throws it
 * away and every resize handle, checkbox tick, sort arrow, hovered row and focus ring written that way is
 * simply absent. Those rules are therefore hoisted out to stand on their own, with the nesting selector
 * replaced by whatever the rule around it selected.
 *
 * The two are asked about separately. A browser on Chrome 111 understands the colours and not the nesting,
 * so answering one question for both would either leave that browser broken or rewrite sheets that were
 * fine as they stood.
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
 * One piece of a block: either a run of declarations or a rule of its own.
 *
 * A block is read as the sequence it was written as rather than as two buckets, because the order the two
 * kinds appear in is what decides the cascade once the nesting is taken out.
 */
type StyleNode =
  | { kind: 'declarations'; text: string }
  | { kind: 'rule'; prelude: string; body: StyleNode[] }

/** The at rules whose contents are not selectors, so nothing inside one of them is ever flattened. */
const OPAQUE_AT_RULES: string[] = [
  '@keyframes',
  '@-webkit-keyframes',
  '@font-face',
  '@counter-style',
  '@property',
  '@page',
  '@font-feature-values',
]

/** The nesting selector, which stands for whatever the rule around it selects. */
const NESTING_SELECTOR = /&/g

/**
 * Decide whether the browser can read a rule written inside another rule.
 *
 * Native nesting reached Chrome in version 112 - one version later than the colour function above - so a
 * browser may well understand the palette and still drop every rule the grid nested inside another. The two
 * are therefore asked about separately rather than one standing in for the other.
 */
const supportsNesting = (): boolean =>
  typeof CSS !== 'undefined' && typeof CSS.supports === 'function' && CSS.supports('selector(&)')

/**
 * Find where a string that started at one index ends, so that its contents are never read as syntax.
 *
 * :param css: The stylesheet being read.
 * :param from: Index of the opening quote.
 * :return: Index just past the closing quote.
 */
const readString = (css: string, from: number): number => {
  const quote = css[from]
  let index = from + 1

  while (index < css.length) {
    if (css[index] === '\\') {
      index += 2

      continue
    }
    if (css[index] === quote) {
      return index + 1
    }
    index += 1
  }

  return index
}

/**
 * Split a selector list on the commas that separate its selectors rather than on those inside a bracket.
 *
 * `:is(.a, .b) .c` is one selector and not two, and a split that did not know that would turn the grid's
 * own `:where(...)` selectors into fragments that select nothing at all.
 *
 * :param selector: The selector list being split.
 * :return: The individual selectors, in the order they were written.
 */
const splitSelectorList = (selector: string): string[] => {
  const parts: string[] = []
  let depth = 0
  let current = ''
  let index = 0

  while (index < selector.length) {
    const character = selector[index]

    if (character === '"' || character === "'") {
      const end = readString(selector, index)
      current += selector.slice(index, end)
      index = end

      continue
    }

    if (character === '(' || character === '[') {
      depth += 1
    }
    if (character === ')' || character === ']') {
      depth -= 1
    }

    if (character === ',' && depth === 0) {
      parts.push(current)
      current = ''
      index += 1

      continue
    }

    current += character
    index += 1
  }
  parts.push(current)

  return parts.map((part) => part.trim()).filter((part) => part.length > 0)
}

/**
 * Find the last semicolon of a run of text that ends a declaration rather than sitting inside a bracket.
 *
 * What stands between that semicolon and the opening brace is the selector of a nested rule, and what
 * stands before it are the declarations of the rule around it. Reading the two apart is the whole of it:
 * `color:red;&:after` is one declaration and one nested selector, not a selector called `color:red;&:after`.
 *
 * :param text: The text gathered since the last brace, which holds no brace of its own.
 * :return: Index of the separating semicolon, or minus one when the whole run is a selector.
 */
const lastDeclarationEnd = (text: string): number => {
  let depth = 0
  let found = -1
  let index = 0

  while (index < text.length) {
    const character = text[index]

    if (character === '"' || character === "'") {
      index = readString(text, index)

      continue
    }

    if (character === '(' || character === '[') {
      depth += 1
    }
    if (character === ')' || character === ']') {
      depth -= 1
    }
    if (character === ';' && depth === 0) {
      found = index
    }
    index += 1
  }

  return found
}

/**
 * Read a stylesheet, or the inside of one block of it, into the rules and declarations it is made of.
 *
 * :param css: The stylesheet being read.
 * :param from: Index the reading starts at.
 * :return: The pieces of this block and the index of the brace that closed it.
 */
const parseNodes = (css: string, from: number): { nodes: StyleNode[]; index: number } => {
  const nodes: StyleNode[] = []
  let pending = ''
  let index = from

  while (index < css.length) {
    const character = css[index]

    /* A comment is not content, and one holding a brace would otherwise close a block that never opened. */
    if (character === '/' && css[index + 1] === '*') {
      const close = css.indexOf('*/', index + 2)
      index = close === -1 ? css.length : close + 2

      continue
    }

    if (character === '"' || character === "'") {
      const end = readString(css, index)
      pending += css.slice(index, end)
      index = end

      continue
    }

    if (character === '}') {
      break
    }

    if (character === '{') {
      const cut = lastDeclarationEnd(pending)
      const declarations = cut === -1 ? '' : pending.slice(0, cut + 1).trim()
      const prelude = (cut === -1 ? pending : pending.slice(cut + 1)).trim()
      if (declarations.length > 0) {
        nodes.push({ kind: 'declarations', text: declarations })
      }

      const inner = parseNodes(css, index + 1)
      nodes.push({ kind: 'rule', prelude, body: inner.nodes })
      pending = ''
      index = inner.index + 1

      continue
    }

    pending += character
    index += 1
  }

  const trailing = pending.trim()
  if (trailing.length > 0) {
    nodes.push({ kind: 'declarations', text: trailing })
  }

  return { nodes, index }
}

/**
 * Write a block back out exactly as it was read, which is what an at rule nothing may be hoisted out of gets.
 */
const serializeNodes = (nodes: StyleNode[]): string =>
  nodes
    .map((node) =>
      node.kind === 'declarations' ? node.text : `${node.prelude}{${serializeNodes(node.body)}}`,
    )
    .join('')

/** The name of an at rule, which is what decides whether its contents hold rules or something else. */
const atRuleName = (prelude: string): string => (/^@[\w-]+/.exec(prelude) ?? [''])[0].toLowerCase()

/**
 * Work out what a nested selector selects once it is written on its own.
 *
 * A selector that names the rule around it has that naming replaced, and one that does not is a descendant
 * of it - which is what the relaxed form of the syntax means and what a browser without nesting would never
 * work out for itself. A parent that is a list has to be wrapped before it is substituted, because
 * `.a, .b` put in front of `:hover` would otherwise read as `.a` and `.b:hover` rather than as both hovered.
 *
 * :param child: Selector of the nested rule, as it was written.
 * :param parent: Selector of the rule it was written inside, already resolved.
 * :return: The selector the nested rule has once it stands on its own.
 */
const resolveSelector = (child: string, parent: string): string => {
  const reference = splitSelectorList(parent).length > 1 ? `:is(${parent})` : parent

  return splitSelectorList(child)
    .map((one) => (one.includes('&') ? one.replace(NESTING_SELECTOR, reference) : `${reference} ${one}`))
    .join(',')
}

/**
 * Write out one block as rules that stand on their own, hoisting everything nested inside it.
 *
 * The declarations of a block are gathered as they are met and written out the moment a nested rule
 * interrupts them, so a declaration written after a nested rule stays after it. That ordering is not a
 * detail: two rules of equal weight are settled by which of them came last, and hoisting every declaration
 * of a block into one rule at the top would quietly reverse the answer wherever the grid overrides itself.
 *
 * :param nodes: The pieces of the block being written out.
 * :param parent: Selector the block belongs to, empty at the top level of a stylesheet.
 * :param out: The rules gathered so far, which this appends to.
 */
const flattenNodes = (nodes: StyleNode[], parent: string, out: string[]): void => {
  let declarations: string[] = []

  const flush = (): void => {
    if (declarations.length === 0) {
      return
    }

    const text = declarations.join('')
    out.push(parent.length > 0 ? `${parent}{${text}}` : text)
    declarations = []
  }

  nodes.forEach((node) => {
    if (node.kind === 'declarations') {
      declarations.push(node.text.endsWith(';') ? node.text : `${node.text};`)

      return
    }

    flush()

    if (node.prelude.startsWith('@')) {
      /* The frames of an animation are not selectors, so the block is kept exactly as the grid wrote it. */
      if (OPAQUE_AT_RULES.includes(atRuleName(node.prelude))) {
        out.push(`${node.prelude}{${serializeNodes(node.body)}}`)

        return
      }

      /*
       * A condition wrapped around rules keeps its wrapper and hands its contents the same selector it was
       * given, which is what turns a query written inside a rule into the same query written around it.
       */
      const inner: string[] = []
      flattenNodes(node.body, parent, inner)
      out.push(`${node.prelude}{${inner.join('')}}`)

      return
    }

    flattenNodes(node.body, parent.length > 0 ? resolveSelector(node.prelude, parent) : node.prelude, out)
  })

  flush()
}

/**
 * Decide whether a stylesheet actually writes anything inside a rule of its own.
 *
 * Asking this before rewriting is what leaves a sheet that never nested byte for byte as the grid wrote it,
 * and it cannot be answered by looking for the nesting selector: the relaxed form of the syntax lets a rule
 * be nested under nothing but a combinator, which is how `.ag-label-align-top { ...; > * { ... } }` is
 * written, and a search for `&` walks straight past it.
 *
 * :param nodes: The pieces of the block being examined.
 * :param insideRule: Whether that block is itself the body of a style rule.
 * :return: Whether anything here has to be hoisted out.
 */
const holdsNestedRules = (nodes: StyleNode[], insideRule: boolean): boolean =>
  nodes.some((node) => {
    if (node.kind === 'declarations') {
      return false
    }

    /* A rule of any kind written inside a style rule is exactly what an older browser cannot read. */
    if (insideRule) {
      return true
    }

    if (OPAQUE_AT_RULES.includes(atRuleName(node.prelude))) {
      return false
    }

    return holdsNestedRules(node.body, !node.prelude.startsWith('@'))
  })

/**
 * Rewrite a stylesheet so that nothing in it is written inside anything else.
 *
 * :param css: The stylesheet being rewritten.
 * :return: The same stylesheet with every nested rule standing on its own.
 */
const flattenNesting = (css: string): string => {
  const parsed = parseNodes(css, 0).nodes
  if (!holdsNestedRules(parsed, false)) {
    return css
  }

  const out: string[] = []
  flattenNodes(parsed, '', out)

  return out.join('')
}

/**
 * Decide whether the stylesheets the grid writes have to be rewritten for this browser at all.
 *
 * Two separate things are being asked about, one version of Chrome apart, and a browser may need either of
 * them without needing the other. Neither missing means every sheet is left exactly as the grid wrote it.
 */
const needsStyleCompatibility = (): boolean => !supportsColorMix() || !supportsNesting()

/**
 * Rewrite the stylesheets the grid injected into the two things an older browser can actually read.
 *
 * The colours the theme derives are worked out into plain ones, and the rules the grid writes inside other
 * rules are hoisted out to stand on their own. A browser that understands one of the two and not the other
 * gets only the half it is missing, and the sheets a browser can read as they stand are never touched.
 *
 * Only the sheets the grid wrote are read at all, and only in a browser that needs it, so on everything
 * modern this costs two feature tests and nothing else.
 */
const applyThemeCompatibility = (root: Document | ShadowRoot = document): void => {
  if (!needsStyleCompatibility()) {
    return
  }

  const sheets = Array.from(root.querySelectorAll<HTMLStyleElement>(INJECTED_STYLES))
  const mixesNeeded = !supportsColorMix()
  const nestingNeeded = !supportsNesting()

  /*
   * Every sheet is read for its properties before any of them is rewritten. The grid writes the palette into
   * one sheet and the rules that mix over it into another, so a rewriter working sheet by sheet would reach
   * the mixes before it had ever seen the colours they are written over.
   */
  const variables: Variables = new Map()
  if (mixesNeeded) {
    sheets.forEach((sheet) => readVariables(sheet.textContent ?? '', variables))
  }

  sheets.forEach((sheet) => {
    const css = sheet.textContent ?? ''

    /*
     * The mixes are worked out before the nesting is taken apart, because a mix is a value and the nesting
     * is the shape around it: resolving the values first means each of them is met exactly once, however
     * many rules the block it sits in is about to become.
     */
    const coloured = mixesNeeded && css.includes('color-mix') ? resolveColorMix(css, variables) : css
    const resolved = nestingNeeded ? flattenNesting(coloured) : coloured

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
  if (!needsStyleCompatibility() || typeof MutationObserver === 'undefined' || observed.has(root)) {
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
  flattenNesting,
  needsStyleCompatibility,
  observeThemeCompatibility,
  parseColor,
  resolveColorMix,
  supportsColorMix,
  supportsNesting,
}
