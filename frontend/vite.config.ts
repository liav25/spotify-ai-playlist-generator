import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    // Make environment variables available to the frontend
    __VITE_API_URL__: JSON.stringify(process.env.VITE_API_URL || 'http://127.0.0.1:8000')
  },
  server: {
    port: 3000,
    // Only use proxy in development
    proxy: process.env.NODE_ENV !== 'production' ? {
      '/api': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    } : {}
  }
})
