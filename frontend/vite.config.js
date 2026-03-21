import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Serves /landing as a clean URL for the static landing page
 * (public/landing.html). Rewrites /landing → /landing.html so
 * Vite serves the static file from public/.
 */
function landingCleanUrl() {
  return {
    name: 'landing-clean-url',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url || ''

        // /landing → serve /landing.html internally (clean URL support)
        if (url === '/landing' || url.startsWith('/landing?')) {
          req.url = url.replace('/landing', '/landing.html')
        }

        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), landingCleanUrl()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
        target: 'http://api:8000',
        changeOrigin: true,
      },
      '/l/': {
        target: 'http://api:8000',
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },
})
