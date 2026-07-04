import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Относительные пути к ассетам — сайт одинаково работает и в корне,
  // и в подпапке (например, на GitHub Pages: /Resource/).
  base: './',
  server: { host: true, port: 5173 },
})
