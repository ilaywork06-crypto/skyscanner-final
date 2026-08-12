/**
 * The Vuetify setup of the web client - the single place that holds every colour of the light and the dark theme.
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

import { createVuetify, type ThemeDefinition } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

const DARK_THEME_NAME = 'skyscannerDark'
const LIGHT_THEME_NAME = 'skyscannerLight'

const darkTheme: ThemeDefinition = {
  dark: true,
  colors: {
    background: '#060C21',
    'on-background': '#E6ECFF',
    surface: '#101A3E',
    'on-surface': '#E6ECFF',
    'surface-bright': '#16224C',
    'surface-light': '#1B2856',
    'surface-variant': '#22315F',
    'on-surface-variant': '#9AA6C8',
    'control-surface': '#1B2856',
    'control-surface-hover': '#243367',
    'control-border': '#2E3E73',
    primary: '#1F75FE',
    'primary-darken-1': '#0F5BD1',
    secondary: '#7B68EE',
    accent: '#0087EB',
    info: '#0087EB',
    success: '#0BDA51',
    warning: '#FFDB58',
    error: '#FF6347',
    'app-header-start': '#050A1C',
    'app-header-end': '#2A3A94',
    'app-border': '#22315F',
    'app-muted': '#9AA6C8',
    /* The industry tab in front of the others reads as a sheet of paper laid over the dark header. */
    'tab-active': '#FFFFFF',
    'on-tab-active': '#10193A',
    'table-header': '#3A4772',
    'table-row': '#101A3E',
    'table-row-alt': '#0D1637',
    'table-hover': '#1A2757',
    'table-foreground': '#E6ECFF',
    'table-header-foreground': '#DCE4FF',
    'chip-industry-amber': '#FFDB58',
    'chip-industry-blue': '#0087EB',
    'chip-industry-violet': '#7B68EE',
    'chip-industry-rose': '#ED7A9B',
    'chip-industry-coral': '#FF7F50',
    'chip-platform': '#1F75FE',
    'status-positive': '#0BDA51',
    'status-negative': '#FF6347',
    'status-neutral': '#7B68EE',
    'status-pending': '#FFDB58',
    'status-partial': '#FF7F50',
  },
}

const lightTheme: ThemeDefinition = {
  dark: false,
  colors: {
    background: '#F4F6FE',
    'on-background': '#10193A',
    surface: '#FFFFFF',
    'on-surface': '#10193A',
    'surface-bright': '#FFFFFF',
    'surface-light': '#E8EEFC',
    'surface-variant': '#DCE4F7',
    'on-surface-variant': '#4A5680',
    'control-surface': '#E8EEFC',
    'control-surface-hover': '#DAE3F8',
    'control-border': '#B9C8EA',
    primary: '#1F75FE',
    'primary-darken-1': '#0F5BD1',
    secondary: '#7B68EE',
    accent: '#0087EB',
    info: '#0087EB',
    success: '#0BDA51',
    warning: '#FFDB58',
    error: '#FF6347',
    'app-header-start': '#EDF1FF',
    'app-header-end': '#C4D2FF',
    'app-border': '#C6D2EE',
    'app-muted': '#4A5680',
    /* White would vanish into the pale header here, so the selected tab takes the sky blue of the palette. */
    'tab-active': '#0087EB',
    'on-tab-active': '#FFFFFF',
    'table-header': '#DCE4F7',
    'table-row': '#FFFFFF',
    'table-row-alt': '#F4F7FE',
    'table-hover': '#E5EDFF',
    'table-foreground': '#10193A',
    'table-header-foreground': '#33406B',
    'chip-industry-amber': '#FF7F50',
    'chip-industry-blue': '#0087EB',
    'chip-industry-violet': '#7B68EE',
    'chip-industry-rose': '#ED7A9B',
    'chip-industry-coral': '#FF6347',
    'chip-platform': '#1F75FE',
    'status-positive': '#0BDA51',
    'status-negative': '#FF6347',
    'status-neutral': '#7B68EE',
    'status-pending': '#FFDB58',
    'status-partial': '#FF7F50',
  },
}

const vuetify = createVuetify({
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
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
    VFileInput: { variant: 'solo-filled', flat: true, density: 'comfortable', hideDetails: 'auto' },
    VChip: { size: 'small', label: true },
  },
})

export { DARK_THEME_NAME, LIGHT_THEME_NAME }
export default vuetify
