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
      // 2026-10-08 (#25): 覆盖率门禁。低于阈值 → CI 失败, 防止"测试越写越少还判绿"。
      //   门槛保守: 现状未知, 先锁 70/55/65/70, 后续随覆盖补齐再上调。
      thresholds: {
        statements: 70,
        branches: 55,
        functions: 65,
        lines: 70,
      },
    },
  },
})
