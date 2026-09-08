/**
 * The entry point of the web client, mounting the application with its file based router and its theme.
 */

import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { routes } from 'vue-router/auto-routes'

import App from '@/App.vue'
import vuetify from '@/plugins/vuetify'
import { installRuntimeShims } from '@truth-platform/core-ui'

/*
 * The methods an older browser is opened without, put in place before anything reaches for one. The two
 * clients are built on the same libraries and opened on the same workstations, so they hold the same floor.
 */
installRuntimeShims()

const router = createRouter({
  history: createWebHistory(),
  routes,
})

createApp(App).use(router).use(vuetify).mount('#app')
