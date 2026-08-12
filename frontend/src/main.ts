/**
 * The entry point of the web client, mounting the application with its file based router and its theme.
 */

import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { routes } from 'vue-router/auto-routes'

import App from '@/App.vue'
import { SUBSCRIPTIONS_ENABLED } from '@/features'
import vuetify from '@/plugins/vuetify'

/** The address of the subscriptions page, and the page a visitor is sent to while it is switched off. */
const SUBSCRIPTIONS_PATH = '/subscriptions'
const FALLBACK_PATH = '/events'

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/*
 * The router builds its routes from the files under `src/pages`, so a page keeps its route for as long as its
 * file exists - hiding the links that lead to it would still leave the address reachable to anybody who typed
 * it. A feature that is switched off is enforced here instead, on the one road into every page.
 */
router.beforeEach((to) => {
  if (!SUBSCRIPTIONS_ENABLED && to.path.startsWith(SUBSCRIPTIONS_PATH)) {
    return FALLBACK_PATH
  }

  return true
})

createApp(App).use(router).use(vuetify).mount('#app')
