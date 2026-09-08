/**
 * The build configuration of the web client, wiring the file based router, Vuetify and the API proxy.
 */

import { hostname } from 'node:os'
import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import VueRouter from 'unplugin-vue-router/vite'
import { defineConfig } from 'vite'
import vuetify from 'vite-plugin-vuetify'

/** Where the assumptions API is reached while the client is being developed against it. */
const API_TARGET = process.env.TRUTH_API_URL ?? 'http://localhost:8000'

/*
 * The oldest browsers the client is built for. Chrome 90 covers every workstation the register is opened on
 * today and several generations behind them, and the table library needs a hand of its own below Chrome 111 -
 * `packages/ag-grid-ts/src/compatibility.ts` is where the colours it derives are worked out for those.
 */
const BROWSER_TARGETS: string[] = ['chrome90', 'edge90', 'firefox90', 'safari15']

/*
 * Which names a browser may ask for this server by.
 *
 * The dev server refuses a request whose Host header is a name it was not told about, which is what stops a
 * page on the internet from resolving its own domain to this machine and reading the source through the
 * visitor's browser. An address is never a name, so reaching the server by IP has always worked; it is
 * opening it as `http://<machine>:5174` from another desk that gets turned away.
 *
 * The machine's own name is therefore allowed by default, which covers everybody on the network who reaches
 * it the obvious way. TRUTH_ALLOWED_HOSTS names any others - a short name, a domain, or `.example.com` for every name
 * under one - and `all` gives up the protection entirely, which is only sensible on a network you trust.
 */
const readAllowedHosts = (): string[] | true => {
  const named = (process.env.TRUTH_ALLOWED_HOSTS ?? '')
    .split(',')
    .map((host) => host.trim())
    .filter((host) => host.length > 0)

  if (named.includes('all')) {
    return true
  }

  const own = hostname()

  return [...new Set([...named, own, `${own}.local`, 'localhost'])]
}

export default defineConfig({
  plugins: [
    VueRouter({ routesFolder: 'src/pages', dts: 'src/typed-router.d.ts' }),
    vue(),
    vuetify({ autoImport: true }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@truth-platform/ag-grid-ts': fileURLToPath(
        new URL('../../packages/ag-grid-ts/src/index.ts', import.meta.url),
      ),
      '@truth-platform/core-ui': fileURLToPath(new URL('../../packages/core-ui/src/index.ts', import.meta.url)),
    },
  },
  server: {
    host: true,
    /* A port of its own, so that this client and the inventory can be run side by side. */
    port: 5174,
    allowedHosts: readAllowedHosts(),
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, '') },
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
