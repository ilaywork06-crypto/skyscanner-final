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

/*
 * The oldest browsers the client is built for. Chrome 90 covers every workstation the inventory is opened on
 * today and several generations behind them, and the table library needs a hand of its own below Chrome 111 -
 * `packages/ag-grid-ts/src/compatibility.ts` is where the colours it derives are worked out for those.
 */
const BROWSER_TARGETS: string[] = ['chrome90', 'edge90', 'firefox90', 'safari15']

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
    /*
     * The client is opened in whatever browser a given workstation happens to carry, which is not always a
     * current one. The default target of the bundler assumes a fairly recent baseline and emits syntax an
     * older Chrome refuses outright, so the floor is stated here instead of being inherited.
     */
    target: BROWSER_TARGETS,
  },
  optimizeDeps: {
    /* The dependencies are prebundled for the same floor, so development matches what is shipped. */
    esbuildOptions: { target: BROWSER_TARGETS },
  },
})
