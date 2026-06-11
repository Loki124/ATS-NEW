import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import path from 'path'
import { fileURLToPath } from 'url'
import config from './src/config'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig({
  plugins: [
    vue(),
    UnoCSS(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: config.frontend.port,
    proxy: {
      [config.api.baseUrl]: {
        target: config.backend.url,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Plan O: 优化产物
    target: 'es2020',
    cssCodeSplit: true,
    chunkSizeWarningLimit: 1500,
    // 手动分块: 第三方库单独, 路由懒加载 chunk 由 router 控制
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            // Naive UI 单独 chunk
            if (id.includes('naive-ui') || id.includes('@css-render') || id.includes('evtd')) {
              return 'vendor-naive-ui'
            }
            // Vue 核心
            if (id.includes('@vue') || id.includes('vue-router') || id.includes('pinia') || id.includes('@vueuse')) {
              return 'vendor-vue'
            }
            // Icons
            if (id.includes('@vicons') || id.includes('@iconify')) {
              return 'vendor-icons'
            }
            // UnoCSS
            if (id.includes('unocss') || id.includes('@unocss')) {
              return 'vendor-unocss'
            }
            // 其他 vendor
            return 'vendor-misc'
          }
          // src 内的工具库
          if (id.includes('/src/utils/') || id.includes('/src/api/')) {
            return 'app-utils'
          }
        },
        // 启用 chunk 文件名模板 (含 hash)
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
      },
    },
  },
})
