<template>
  <v-app>
    <v-main class="app-shell">
      <RouterView />
      <AppSnackbar />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { AppSnackbar, useSnackbar } from '@truth-platform/core-ui'
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'

import { useRegister } from '@/composables/useRegister'

const { load } = useRegister()
const { reportError } = useSnackbar()

/*
 * The whole register is read once, here, rather than by each page that needs a piece of it: the API offers no
 * way to ask a narrower question, so every page would otherwise read the same collections over again.
 */
onMounted(async () => {
  try {
    await load()
  } catch (error) {
    reportError(error)
  }
})
</script>

<style>
/*
 * The two families of the design. Inter is the interface type and carries everything the user reads inside
 * the application: controls, labels, headings and table cells alike. Kufam is the display type, and in the
 * mockups it appears in one single place - the wordmark - so it is scoped to exactly that.
 */
:root {
  --truth-font-body: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
  --truth-font-display: 'Kufam', 'Inter', 'Segoe UI', system-ui, sans-serif;
}

html,
body,
#app {
  block-size: 100%;
}

/*
 * Vuetify names its own family on the application root and on several of its components, so the interface
 * type has to be restated at least as specifically to win. Menus and dialogs are teleported out of the
 * application root into the overlay container, which is why that is listed as well.
 */
.v-application,
.v-application .v-btn,
.v-application .v-field__input,
.v-application .v-list-item-title,
.v-overlay-container,
.v-overlay-container .v-btn,
.v-overlay-container .v-list-item-title {
  font-family: var(--truth-font-body);
}

.app-shell {
  min-block-size: 100vh;
  background-color: rgb(var(--v-theme-background));
}

/* Every page grows with its content and lets the browser scroll it, rather than pinning to the viewport. */
.sky-page {
  display: flex;
  flex-direction: column;
  min-block-size: 100vh;
}

.sky-page__content {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  gap: 1rem;
  padding-inline: 2rem;
  padding-block: 1rem;
  min-inline-size: 0;
}

/*
 * A cell of the table has to keep what it holds inside its own column. The grid only clips the cells whose
 * height is fixed, so a cell that grows to fit its content would otherwise let a long value run straight
 * across the columns beside it.
 */
.sky-cell {
  display: flex;
  align-items: center;
  min-inline-size: 0;
  overflow: hidden;
}

.sky-cell > * {
  min-inline-size: 0;
  max-inline-size: 100%;
}

/* A column of bookkeeping stamps reads at the end of its column rather than at the start of it. */
.sky-cell--stamp {
  justify-content: flex-end;
}

.sky-header--stamp .ag-header-cell-label {
  justify-content: flex-end;
}

/* The chevron that opens a row sits centred in a column of its own, with no padding to push it off centre. */
.truth-cell--expand {
  justify-content: center;
  padding-inline: 0 !important;
}

@media (max-width: 48rem) {
  .sky-page__content {
    padding-inline: 1rem;
  }
}
</style>
