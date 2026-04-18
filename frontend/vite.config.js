import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import packageJson from './package.json' with { type: 'json' }

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    define: {
      'import.meta.env.VITE_APP_VERSION': JSON.stringify(packageJson.version),
    },
    server: {
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
    preview: {
      host: '0.0.0.0',
    },
    test: {
      environment: 'jsdom',
      globals: true,
    },
  }
})
