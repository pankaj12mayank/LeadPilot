import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/recharts')) return 'recharts'
          if (id.includes('node_modules/@tanstack/react-table')) return 'react-table'
          if (id.includes('node_modules/lucide-react')) return 'lucide'
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    // Same path as backend API_ROOT_PATH (default /api). No rewrite — FastAPI serves /api/... .
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/branding': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
