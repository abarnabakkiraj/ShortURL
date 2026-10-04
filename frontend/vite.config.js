import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true, // the backend's CORS setting expects exactly http://localhost:5173
    host: true, // also listen outside the container when running in Docker
  },
})
