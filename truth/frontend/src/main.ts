/**
 * The entry point of the web client, mounting the application with its file based router and its theme.
 */

import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { routes } from 'vue-router/auto-routes'

import App from '@/App.vue'
import vuetify from '@/plugins/vuetify'

const router = createRouter({
  history: createWebHistory(),
  routes,
})

createApp(App).use(router).use(vuetify).mount('#app')
