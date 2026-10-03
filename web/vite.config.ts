import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev-only proxy: /api/* → Flask on 5055, with the /api prefix stripped.
// Prod builds don't use this — the SPA is served alongside the API by a
// reverse proxy (Hetzner Load Balancer, see docs/00-stack-and-architecture.md).
export default defineConfig({
  plugins: [react(), tailwindcss()],
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
