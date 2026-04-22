/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Preferred: full API origin including ``/api`` prefix, e.g. ``http://localhost:8000/api`` */
  readonly VITE_API_BASE_URL?: string
  /** @deprecated Use VITE_API_BASE_URL */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
