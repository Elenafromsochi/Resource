import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// Два клиента из общего кода: сайт (web.html) и Telegram Mini App (miniapp.html).
// Механизм один, отличается только точка входа и адаптер авторизации.
export default defineConfig({
  plugins: [vue()],
  server: { host: true, port: 5173 },
  build: {
    rollupOptions: {
      input: {
        web: resolve(__dirname, 'web.html'),
        miniapp: resolve(__dirname, 'miniapp.html'),
      },
    },
  },
})
