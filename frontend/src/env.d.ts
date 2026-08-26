/**
 * The typing of the build time environment variables and of the single file components.
 */

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  /** The tile server the coordinate field draws its map from, named by the deployment. */
  readonly VITE_MAP_TILE_URL: string
  /** What that tile server is credited with underneath the map. */
  readonly VITE_MAP_ATTRIBUTION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'

  const component: DefineComponent<Record<string, never>, Record<string, never>, unknown>
  export default component
}
