/**
 * The language the interface is written in, and the switch between English and Hebrew.
 *
 * Two things change when the language does, and they are easy to confuse. One is the words - every label,
 * every heading, every message - and that is a lookup. The other is the direction, and that is not a lookup
 * at all: Hebrew runs right to left, so the whole page has to be mirrored, and a page is mirrored in three
 * separate places that do not know about one another. This is the one thing that knows about all three:
 *
 *   1. the document, whose `dir` is what makes the browser lay text out the other way and what every CSS
 *      logical property in this library is already written against;
 *   2. Vuetify, which mirrors its own components off its locale rather than off the document, so the locale
 *      is moved with it;
 *   3. AG Grid, which takes its direction once when it builds itself and never looks again - which is why
 *      the tables are keyed on the language and rebuilt rather than told.
 *
 * The words themselves are held in dictionaries a product registers. What this library ships is the
 * vocabulary of the table, because the table is what this library draws; the words a product uses for its
 * own subject are that product's to register, and both halves are looked up through the same `t`.
 */

import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
import { useLocale } from 'vuetify'

/** The languages the interface is offered in. */
type Language = 'en' | 'he'

/** One dictionary: the phrases of one language, addressed by the key the interface asks for them under. */
type Dictionary = Record<string, string>

/** The same phrases in both languages, which is what a product registers. */
type Translations = Record<Language, Dictionary>

interface LanguageState {
  language: Ref<Language>
  /** Whether the interface is currently written right to left, which is what a layout asks rather than the name. */
  isRtl: ComputedRef<boolean>
  /** The direction, ready to be bound to a `dir` attribute. */
  direction: ComputedRef<'rtl' | 'ltr'>
  t: (key: string, values?: Record<string, string | number>) => string
  setLanguage: (next: Language) => void
  toggle: () => void
}

/** The two languages, in the order a picker offers them. */
const LANGUAGES: Language[] = ['en', 'he']

/** What each language is called in itself, because a language picker nobody can read is not a picker. */
const LANGUAGE_NAMES: Record<Language, string> = { en: 'English', he: 'עברית' }

/** Where the chosen language is remembered between sessions. */
const STORAGE_KEY = 'ui.language'

/** The language a browser that has never been asked is served, and the fallback of every lookup. */
const DEFAULT_LANGUAGE: Language = 'en'

/** The Vuetify locales the two languages map onto, which is what mirrors Vuetify's own components. */
const VUETIFY_LOCALES: Record<Language, string> = { en: 'en', he: 'he' }

/** A placeholder inside a phrase, written `{name}` and filled from the values a caller passes. */
const PLACEHOLDER_PATTERN = /\{(\w+)\}/g

/**
 * Read the language the user last chose.
 *
 * A browser that refuses to hand its storage over - a private window, or one told to block site data -
 * throws rather than answering, and a language is not worth failing to render the application for.
 */
const readStoredLanguage = (): Language => {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)

    return stored === 'he' || stored === 'en' ? stored : DEFAULT_LANGUAGE
  } catch {
    return DEFAULT_LANGUAGE
  }
}

/**
 * Remember the language the user just chose, and carry on without remembering it if the browser refuses.
 */
const storeLanguage = (value: Language): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, value)
  } catch {
    /* The switch still works for this session, which is the part that matters. */
  }
}

/*
 * The language is held here rather than inside the composable, so that every component of the application
 * reads the very same one. A ref created per caller would give each of them a language of its own, and the
 * header would switch while the table it sits above stayed where it was.
 */
const language = ref<Language>(readStoredLanguage())

/*
 * Every phrase the application knows, in both languages. A product adds its own to these rather than
 * replacing them, because the words this library ships - the furniture of the table - are drawn by this
 * library and are needed whatever the product around them is.
 */
const dictionaries: Translations = { en: {}, he: {} }

/**
 * Add a set of phrases to the vocabulary of the interface.
 *
 * Registered rather than passed in, because the components that read a phrase are several layers below
 * whoever owns the dictionary and threading it through all of them would put a translation prop on
 * components that have nothing else to do with the language.
 *
 * A key that is registered twice keeps the phrase registered last, which is what lets a product reword
 * something this library ships - an inventory counts events and a register counts assumptions, and both
 * are the same pagination bar.
 */
const registerTranslations = (translations: Partial<Translations>): void => {
  LANGUAGES.forEach((name) => {
    Object.assign(dictionaries[name], translations[name] ?? {})
  })
}

/**
 * Fill the placeholders of a phrase with the values a caller passed for them.
 *
 * A placeholder nobody passed a value for is left as it is rather than blanked, because a phrase that reads
 * `{count} rows` is a phrase somebody forgot to pass a count to, and saying so is more use than hiding it.
 */
const fill = (phrase: string, values: Record<string, string | number> | undefined): string => {
  if (values === undefined) {
    return phrase
  }

  return phrase.replace(PLACEHOLDER_PATTERN, (whole, name: string) =>
    name in values ? String(values[name]) : whole,
  )
}

/**
 * Look one phrase up in the language the interface is currently written in.
 *
 * A phrase that has no Hebrew falls back to its English rather than to nothing, so a dictionary that is
 * behind leaves a few English words on a Hebrew page instead of leaving holes in it. A key that is in
 * neither reads as itself, which is what makes a missing phrase obvious while it is being written rather
 * than at the moment somebody switches the language.
 */
const translate = (key: string, values?: Record<string, string | number>): string => {
  const phrase = dictionaries[language.value][key] ?? dictionaries[DEFAULT_LANGUAGE][key] ?? key

  return fill(phrase, values)
}

/**
 * Write the language and its direction onto the document itself.
 *
 * This is what actually mirrors the page. Every layout in this library and in the products around it is
 * written in logical properties - `padding-inline-start` rather than `padding-left`, `inline-size` rather
 * than `width` - and a logical property means nothing until the document says which way the text runs.
 * Setting `dir` here therefore mirrors every one of them at once, without a single stylesheet knowing
 * that a second direction exists.
 */
const applyToDocument = (value: Language): void => {
  const root = document.documentElement
  root.setAttribute('lang', value)
  root.setAttribute('dir', value === 'he' ? 'rtl' : 'ltr')
}

applyToDocument(language.value)

/**
 * Keep Vuetify's own locale on the language the rest of the interface is written in.
 *
 * Vuetify mirrors its components off its locale rather than off the document, so moving the locale is what
 * turns a menu, a dialog and a select around. The locale lives on the Vuetify instance and is reached by
 * injection, which is the whole reason this is attempted rather than done: AG Grid mounts a cell renderer
 * outside the tree the application was mounted in, and a renderer that insisted on reaching the instance
 * would throw rather than draw a cell. It does not need to reach it either - something inside the tree has
 * already moved the locale, and there is only one of them to move.
 */
const bridgeVuetifyLocale = (): void => {
  let locale: ReturnType<typeof useLocale>
  try {
    locale = useLocale()
  } catch {
    return
  }

  const sync = (value: Language) => {
    const wanted = VUETIFY_LOCALES[value]
    if (locale.current.value !== wanted) {
      locale.current.value = wanted
    }
  }

  sync(language.value)
  watch(language, sync)
}

/**
 * Expose the language of the interface, the direction it runs in and the lookup every label goes through.
 */
const useLanguage = (): LanguageState => {
  bridgeVuetifyLocale()

  const isRtl = computed<boolean>(() => language.value === 'he')
  const direction = computed<'rtl' | 'ltr'>(() => (isRtl.value ? 'rtl' : 'ltr'))

  const setLanguage = (next: Language) => {
    if (next === language.value) {
      return
    }

    language.value = next
    storeLanguage(next)
    applyToDocument(next)
  }

  const toggle = () => {
    setLanguage(language.value === 'en' ? 'he' : 'en')
  }

  return {
    language,
    isRtl,
    direction,
    t: translate,
    setLanguage,
    toggle,
  }
}

export type { Dictionary, Language, LanguageState, Translations }
export { LANGUAGES, LANGUAGE_NAMES, language, registerTranslations, translate, useLanguage }
