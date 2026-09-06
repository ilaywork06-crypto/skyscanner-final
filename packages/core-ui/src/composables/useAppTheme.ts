/**
 * The composable behind the theme switch of the header, keeping the chosen mode across sessions.
 *
 * The two themes are named by the product that installs them rather than here, because each one registers
 * its own palette with Vuetify; what is shared is the switching, the remembering and the reading back.
 */

import { computed, type ComputedRef } from 'vue'
import { useTheme } from 'vuetify'

interface AppTheme {
  isDark: ComputedRef<boolean>
  colors: ComputedRef<Record<string, string>>
  toggle: () => void
}

/** What the two themes of a product are called and where the choice between them is remembered. */
interface ThemeNames {
  dark: string
  light: string
  storageKey: string
}

let names: ThemeNames = { dark: 'dark', light: 'light', storageKey: 'ui.theme' }

/**
 * Name the two themes this product registered, which the switch moves between.
 *
 * Called once while the application starts, before anything renders the switch.
 */
const configureThemes = (configuration: ThemeNames): void => {
  names = configuration
}

/**
 * Read the theme the user last chose, falling back to the dark one of the design.
 *
 * A browser that refuses to hand its storage over - a private window, or one told to block site data -
 * throws rather than answering, and a theme is not worth failing to render the application for.
 */
const readStoredTheme = (): string => {
  try {
    return window.localStorage.getItem(names.storageKey) ?? names.dark
  } catch {
    return names.dark
  }
}

/**
 * Remember the theme the user just chose, and carry on without remembering it if the browser refuses.
 */
const storeTheme = (value: string): void => {
  try {
    window.localStorage.setItem(names.storageKey, value)
  } catch {
    /* The switch still works for this session, which is the part that matters. */
  }
}

/**
 * Expose the active theme, its palette and the switch between the dark and the light mode.
 */
const useAppTheme = (): AppTheme => {
  const theme = useTheme()
  const stored = readStoredTheme()
  if (theme.global.name.value !== stored) {
    theme.change(stored)
  }

  const isDark = computed<boolean>(() => theme.global.name.value === names.dark)
  const colors = computed<Record<string, string>>(() => theme.current.value.colors)

  const toggle = () => {
    const next = isDark.value ? names.light : names.dark
    theme.change(next)
    storeTheme(next)
  }

  return { isDark, colors, toggle }
}

export type { AppTheme, ThemeNames }
export { configureThemes, useAppTheme }
