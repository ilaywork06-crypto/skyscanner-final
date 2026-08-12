/**
 * The composable behind the theme switch of the header, keeping the chosen mode across sessions.
 */

import { computed, type ComputedRef } from 'vue'
import { useTheme } from 'vuetify'

import { DARK_THEME_NAME, LIGHT_THEME_NAME } from '@/plugins/vuetify'

interface AppTheme {
  isDark: ComputedRef<boolean>
  colors: ComputedRef<Record<string, string>>
  toggle: () => void
}

const STORAGE_KEY = 'skyscanner.theme'

/**
 * Read the theme the user last chose, falling back to the dark one of the design.
 */
const readStoredTheme = (): string => window.localStorage.getItem(STORAGE_KEY) ?? DARK_THEME_NAME

/**
 * Expose the active theme, its palette and the switch between the dark and the light mode.
 */
const useAppTheme = (): AppTheme => {
  const theme = useTheme()
  const stored = readStoredTheme()
  if (theme.global.name.value !== stored) {
    theme.change(stored)
  }

  const isDark = computed<boolean>(() => theme.global.name.value === DARK_THEME_NAME)
  const colors = computed<Record<string, string>>(() => theme.current.value.colors)

  const toggle = () => {
    const next = isDark.value ? LIGHT_THEME_NAME : DARK_THEME_NAME
    theme.change(next)
    window.localStorage.setItem(STORAGE_KEY, next)
  }

  return { isDark, colors, toggle }
}

export type { AppTheme }
export { useAppTheme }
