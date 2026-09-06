/**
 * The typing of the build time environment variables and of the single file components.
 */

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  /** Who the client says it is when it creates something, until the service authenticates callers itself. */
  readonly VITE_DEFAULT_CREATOR: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'

  const component: DefineComponent<Record<string, never>, Record<string, never>, unknown>
  export default component
}
