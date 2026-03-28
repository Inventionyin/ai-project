import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log(`[Vite Proxy] ${req.method} ${req.url} -> ${options.target}${req.url}`);
          });
          proxy.on('error', (err: any, req, res) => {
            const code = typeof err?.code === 'string' ? err.code : ''
            const base = code ? `${code} ${String(err?.message || '')}`.trim() : String(err?.message || err)
            const hint = code === 'ECONNREFUSED' ? ` (backend not reachable at ${options.target})` : ''
            console.error(`[Vite Proxy Error] ${base}${hint}`);
          });
        }
      }
    }
  }
})
