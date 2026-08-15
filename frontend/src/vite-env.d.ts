/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string;
  readonly VITE_APP_ENV: string;
  readonly VITE_BACKEND_URL: string;
  readonly VITE_COSINE_SIMILARITY_THRESHOLD: string;
  readonly VITE_SLA_RESPONSE_HOURS: string;
  readonly VITE_ENABLE_AI_ASSISTANT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}