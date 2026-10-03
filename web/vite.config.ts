import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-only proxy: /api/* → Flask on 5055, with the /api prefix stripped.
// Tailwind runs via PostCSS (postcss.config.js), not a Vite plugin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5055',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
