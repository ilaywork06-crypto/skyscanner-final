/**
 * The bridge between the Vuetify palette and the AG Grid theming parameters, so the table follows the app theme.
 */

import { themeQuartz, type Theme } from 'ag-grid-community'

type ThemeColors = Record<string, string>

const FALLBACK_COLOR = '#8C9AC4'

/**
 * Read one colour token out of the current Vuetify palette.
 */
const readColor = (colors: ThemeColors, token: string): string => colors[token] ?? FALLBACK_COLOR

/**
 * Build the AG Grid theme of the inventory table out of the palette of the active Vuetify theme.
 */
const buildGridTheme = (colors: ThemeColors, isDark: boolean): Theme =>
  themeQuartz.withParams({
    accentColor: readColor(colors, 'primary'),
    backgroundColor: readColor(colors, 'table-row'),
    foregroundColor: readColor(colors, 'table-foreground'),
    borderColor: readColor(colors, 'app-border'),
    browserColorScheme: isDark ? 'dark' : 'light',
    chromeBackgroundColor: readColor(colors, 'table-header'),
    headerBackgroundColor: readColor(colors, 'table-header'),
    headerTextColor: readColor(colors, 'table-header-foreground'),
    headerFontWeight: 700,
    headerFontSize: 12,
    oddRowBackgroundColor: readColor(colors, 'table-row-alt'),
    rowHoverColor: readColor(colors, 'table-hover'),
    selectedRowBackgroundColor: readColor(colors, 'table-hover'),
    rowBorder: { style: 'solid', width: 1, color: readColor(colors, 'app-border') },
    wrapperBorder: false,
    wrapperBorderRadius: 12,
    /*
     * A table of many columns spends this on every one of them, on every row on screen. Sixteen either side
     * of a value is a quarter of a narrow column given to nothing, which is what turned a wide register into
     * a page of gaps; the cells set their own padding on top of this, so this is the floor rather than the
     * whole of it.
     */
    cellHorizontalPadding: 8,
    fontFamily: 'inherit',
    fontSize: 14,
  })

export type { ThemeColors }
export { buildGridTheme }
