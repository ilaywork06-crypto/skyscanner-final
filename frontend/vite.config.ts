/**
 * The build configuration of the web client, wiring the file based router, Vuetify and the API proxy.
 */

import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import VueRouter from 'unplugin-vue-router/vite'
import { defineConfig } from 'vite'
import vuetify from 'vite-plugin-vuetify'

const EVENTS_SERVICE_TARGET = process.env.EVENTS_SERVICE_URL ?? 'http://localhost:8000'
const STORAGE_SERVICE_TARGET = process.env.STORAGE_SERVICE_URL ?? 'http://localhost:8001'
const NOTIFICATION_SERVICE_TARGET = process.env.NOTIFICATION_SERVICE_URL ?? 'http://localhost:8002'

export default defineConfig({
  plugins: [
    VueRouter({ routesFolder: 'src/pages', dts: 'src/typed-router.d.ts' }),
    vue(),
    vuetify({ autoImport: true }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@skyscanner/ag-grid-ts': fileURLToPath(new URL('../packages/ag-grid-ts/src/index.ts', import.meta.url)),
      '@skyscanner/sky-ui': fileURLToPath(new URL('../packages/sky-ui/src/index.ts', import.meta.url)),
    },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api/storage': { target: STORAGE_SERVICE_TARGET, changeOrigin: true },
      '/api/notifications': { target: NOTIFICATION_SERVICE_TARGET, changeOrigin: true },
      '/api': { target: EVENTS_SERVICE_TARGET, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1600,
  },
})
