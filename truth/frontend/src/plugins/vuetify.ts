/**
 * The Vuetify setup of the web client - the single place that holds every colour of the light and the dark theme.
 *
 * Nothing anywhere else in this client names a colour. A component that needs one reads a token from here,
 * which is what lets the whole interface be re-lit by switching the theme rather than by being repainted.
 */

import '@mdi/font/css/materialdesignicons.css'
/*
 * The two families of the design are self hosted rather than pulled from a font CDN, so that the client keeps
 * rendering in its intended type behind a firewall and on the first paint. Inter carries the interface, Kufam
 * carries the wordmark and the headings.
 */
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/700.css'
import '@fontsource/kufam/400.css'
import '@fontsource/kufam/500.css'
import '@fontsource/kufam/600.css'
import '@fontsource/kufam/700.css'
import 'vuetify/styles'

import { configureThemes } from '@truth-platform/core-ui'
import { createVuetify, type ThemeDefinition } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import { en, he } from 'vuetify/locale'

const DARK_THEME_NAME = 'truthDark'
const LIGHT_THEME_NAME = 'truthLight'

/*
 * The dark theme is the one the design was drawn in: a deep navy page under a near black header, with the
 * table sitting on it as a slightly lighter sheet and one blue carrying every action.
 */
const darkTheme: ThemeDefinition = {
  dark: true,
  colors: {
    background: '#0A1330',
    'on-background': '#E6ECFF',
    surface: '#111C42',
    'on-surface': '#E6ECFF',
    'surface-bright': '#18244F',
    'surface-light': '#1D2A5C',
    'surface-variant': '#243363',
    'on-surface-variant': '#9AA6C8',
    'control-surface': '#1D2A5C',
    'control-surface-hover': '#26356E',
    'control-border': '#2F3F78',
    primary: '#2E90FA',
    'primary-darken-1': '#1570CD',
    secondary: '#7B68EE',
    accent: '#38BDF8',
    info: '#38BDF8',
    success: '#22C55E',
    warning: '#FACC15',
    error: '#F87171',
    'app-header-start': '#1C1C1E',
    'app-header-end': '#4A4A4F',
    'app-border': '#243363',
    'app-muted': '#9AA6C8',
    /* The tab in front of the others reads as a sheet of paper laid over the dark page. */
    'tab-active': '#FFFFFF',
    'on-tab-active': '#0A1330',
    'table-header': '#3A4772',
    'table-row': '#0E1738',
    'table-row-alt': '#0B1430',
    'table-hover': '#1A2757',
    'table-foreground': '#E6ECFF',
    'table-header-foreground': '#DCE4FF',
    'chip-industry-amber': '#C9A227',
    'chip-industry-blue': '#2E90FA',
    'chip-industry-violet': '#8B7BF0',
    'chip-industry-rose': '#ED7A9B',
    'chip-industry-coral': '#FF8A5B',
    'chip-industry-green': '#34D399',
    'chip-platform': '#2E90FA',
    'status-positive': '#22C55E',
    'status-negative': '#F87171',
    'status-neutral': '#7B68EE',
    'status-pending': '#FACC15',
    'status-partial': '#FF8A5B',
  },
}

/*
 * The light theme is the same design lit from the front: a pale blue page, white sheets, and every chip
 * painted in the darkest reading of its own hue so that white lettering stays legible on it.
 */
const lightTheme: ThemeDefinition = {
  dark: false,
  colors: {
    background: '#F1F4FE',
    'on-background': '#101B3D',
    surface: '#FFFFFF',
    'on-surface': '#101B3D',
    'surface-bright': '#FFFFFF',
    'surface-light': '#E8EEFC',
    'surface-variant': '#DCE4F7',
    'on-surface-variant': '#4A5680',
    'control-surface': '#E8EEFC',
    'control-surface-hover': '#DAE3F8',
    'control-border': '#B9C8EA',
    primary: '#1570CD',
    'primary-darken-1': '#0F58A3',
    secondary: '#6552D6',
    accent: '#0284C7',
    info: '#0284C7',
    success: '#15803D',
    warning: '#B45309',
    error: '#DC2626',
    'app-header-start': '#C7D2FE',
    'app-header-end': '#E0E7FF',
    'app-border': '#C6D2EE',
    'app-muted': '#4A5680',
    /* White would vanish into the pale header here, so the selected tab takes the blue of the palette. */
    'tab-active': '#1570CD',
    'on-tab-active': '#FFFFFF',
    'table-header': '#DCE4F7',
    'table-row': '#FFFFFF',
    'table-row-alt': '#F5F8FF',
    'table-hover': '#E5EDFF',
    'table-foreground': '#101B3D',
    'table-header-foreground': '#33406B',
    'chip-industry-amber': '#B07D1A',
    'chip-industry-blue': '#0071C4',
    'chip-industry-violet': '#6552D6',
    'chip-industry-rose': '#C75478',
    'chip-industry-coral': '#D95F35',
    'chip-industry-green': '#0F9D4A',
    'chip-platform': '#1570CD',
    'status-positive': '#15803D',
    'status-negative': '#DC2626',
    'status-neutral': '#6552D6',
    'status-pending': '#B45309',
    'status-partial': '#D95F35',
  },
}

/* The shared theme switch has no way of knowing what this product called its two themes, so it is told. */
configureThemes({ dark: DARK_THEME_NAME, light: LIGHT_THEME_NAME, storageKey: 'truth.theme' })


/*
 * Both languages are handed to Vuetify at build time, together with the map that says which of them runs
 * right to left. Vuetify draws a handful of words of its own - the empty state of a select, the labels of a
 * pager - and mirrors its own components off this locale rather than off the document, so a locale it was
 * never given is a locale it cannot be switched to. `useLanguage` moves `locale.current` between these two.
 */
const vuetify = createVuetify({
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  locale: { locale: 'en', fallback: 'en', messages: { en, he }, rtl: { he: true } },
  theme: {
    defaultTheme: DARK_THEME_NAME,
    themes: {
      [DARK_THEME_NAME]: darkTheme,
      [LIGHT_THEME_NAME]: lightTheme,
    },
  },
  defaults: {
    VCard: { rounded: 'lg', flat: true },
    VBtn: { rounded: 'lg', variant: 'flat' },
    VTextField: { variant: 'solo-filled', flat: true, density: 'comfortable', hideDetails: 'auto' },
    VTextarea: { variant: 'solo-filled', flat: true, hideDetails: 'auto' },
    VSelect: { variant: 'solo-filled', flat: true, density: 'comfortable', hideDetails: 'auto' },
    VAutocomplete: { variant: 'solo-filled', flat: true, density: 'comfortable', hideDetails: 'auto' },
    VCombobox: { variant: 'solo-filled', flat: true, density: 'comfortable', hideDetails: 'auto' },
    VChip: { size: 'small', label: true },
  },
})

export { DARK_THEME_NAME, LIGHT_THEME_NAME }
export default vuetify
