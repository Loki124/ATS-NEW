import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
// Plan O Task 8: 产物分析
import { visualizer } from 'rollup-plugin-visualizer'
import path from 'path'
import { fileURLToPath } from 'url'
// @ts-expect-error: config file is outside tsconfig.node.json file list used for Vite config
import config from './src/config'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig(({ mode }) => ({
  // 2026-06-29 花无缺: 生产环境 base='/static/' 让 chunk 走 /static/assets/xxx,
  //   跟 Django STATIC_URL='/static/' + whitenoise 对齐.
  // ⚠️ dev 模式必须用 '/', 否则 index.html 里所有 asset 路径都带 /static/ 前缀,
  //   Vite dev server 仍能 serve (它有 fallback), 但 SPA history 路由深链
  //   (如 /settings/mou 直访) 会让浏览器请求 /static/settings/mou, 触发 whitenoise 提示.
  base: mode === 'development' ? '/' : '/static/',
  plugins: [
    vue(),
    UnoCSS(),
    // Plan O Task 8: 产物分析 (默认不启用, 仅 ANALYZE=1 时)
    mode === 'production' && process.env.ANALYZE === '1'
      ? visualizer({
          filename: 'dist/stats.html',
          gzipSize: true,
          brotliSize: true,
          template: 'treemap',
        })
      : null,
  ].filter(Boolean),
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
  // 依赖预构建 — dev 启动 + build 前都会跑
  // naive-ui 2.x 是分模块 ESM,内部 cssr 库 (treemate/async-validator/seemly/...) 在
  // top-level 就有副作用(createApp 时立刻执行 setup),必须让 esbuild 预构建把它们
  // 锁成单一 .js 产物。否则 rollup 后续拆分 chunk 会重排求值顺序,触发 TDZ 白屏。
  // 2026-06-15: 增加 'naive-ui' 到 include,让 dev/prod 行为一致
  optimizeDeps: {
    include: ['naive-ui'],
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Plan O: 优化产物
    // 2026-06-29: target 升 es2022 — main.ts 用了 top-level await (await fetchMe() 在 mount 前),
    //            es2020 不支持 top-level await, build:nocheck 也会 esbuild 报错
    target: 'es2022',
    cssCodeSplit: true,
    chunkSizeWarningLimit: 1500,
    // 手动分块: 第三方库单独, 路由懒加载 chunk 由 router 控制
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            // Naive UI 生态 + 它全部间接依赖必须放同一 chunk
            // (treemate / async-validator / seemly / vueuc / vdirs / vooks / csstype /
            //  highlight.js / lodash(-es) / date-fns / date-fns-tz / @css-render 系
            //  — naive-ui 2.44.1 间接依赖约 10+ 个小库,被拆到 vendor-misc 后
            //  rollup 重排求值顺序,出现 TDZ 'Cannot access ma before initialization',
            //  Vue mount 失败 #app 空)
            // 2026-06-15: 把 naive-ui 全部间接依赖归到 vendor-naive-ui, 消除 vendor-misc
            if (
              id.includes('naive-ui') ||
              id.includes('@css-render') ||
              id.includes('css-render') ||
              id.includes('seemly') ||
              id.includes('evtd') ||
              id.includes('date-fns') ||
              id.includes('treemate') ||
              id.includes('vueuc') ||
              id.includes('vdirs') ||
              id.includes('vooks') ||
              id.includes('async-validator') ||
              id.includes('csstype') ||
              id.includes('highlight.js') ||
              id.includes('lodash')
            ) {
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
            // 其他 vendor (理论上不该再有,留 fallback)
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
}))
