import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './frontend/src'),
    },
  },
  root: './frontend',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // Backend API server (see `python3 -m src.web.server --port 8003`)
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
      },
    },
  },
})


