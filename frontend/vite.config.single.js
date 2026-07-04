// Сборка приложения в один автономный файл БЕЗ ES-модулей (формат IIFE),
// чтобы HTML открывался прямо из файла и с любого статического хостинга.
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // В IIFE-сборке Vite не подставляет NODE_ENV автоматически — делаем это сами,
  // иначе Vue падает с "process is not defined".
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    outDir: 'dist-single',
    cssCodeSplit: false,
    lib: {
      entry: 'src/main.js',
      formats: ['iife'],
      name: 'FitApp',
      fileName: () => 'app.js',
    },
    rollupOptions: {
      output: { inlineDynamicImports: true, assetFileNames: 'app.[ext]' },
    },
  },
})
