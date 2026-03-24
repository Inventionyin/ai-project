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
          proxy.on('error', (err, req, res) => {
            console.error(`[Vite Proxy Error] ${err.message}`);
          });
        }
      }
    }
  }
})
