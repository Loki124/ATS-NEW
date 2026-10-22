/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/**/*.{test,spec}.ts'],
    exclude: ['node_modules', 'dist', 'e2e'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      // 统计范围限定「有单测覆盖的逻辑层」。全量统计会把 176 个从未被测试 import
      //   的 .vue 页面全计为 0%，把整体稀释到 16.84%，门禁失去灵敏度。
      //   收窄后新增逻辑层文件（utils/api/... 下的 .ts）不带测试仍会被计入并稀释，
      //   因此约束力保留；.vue 组件测试另行推进，不混入本门禁基数。
      include: ['src/{utils,api,composables,stores,router,services,styles}/**/*.ts'],
      // 2026-10-08 (#25): 覆盖率门禁。低于阈值 → CI 失败, 防止"测试越写越少还判绿"。
      //   2026-10-15 修正: 原 70/55/65/70 是拍脑袋值, 从未真正跑通过（缺
      //   @vitest/coverage-v8, 门禁一直静默失败）。现按实测基线锁定:
      //   25.37/79.4/43.61/25.37 向下取整 → 25/79/43/25。
      //   2026-10-21 (整改卡 E8 第一步): 实测基线已升到 35.38/83.1/49.12/35.38,
      //   再次向下取整 → 35/82/48/35。分支与函数两项比实测低约 1 个点作缓冲
      //   (这两项最易随新增文件波动, statements/lines 相对稳定)。
      //   这是「防恶化」基线而非目标值, 后续只许上调不许下调;
      //   补完一批 .vue 组件测试后应重新实测并再抬一次。
      thresholds: {
        statements: 35,
        branches: 82,
        functions: 48,
        lines: 35,
      },
    },
  },
})
