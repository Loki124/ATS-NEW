// ESLint v9 flat config
// 2026-06-29 花无缺: 项目刚装 ESLint 9, 写 flat config.
// 范围: src/**/*.{vue,ts,js} + tests/**. 排除 dist / node_modules.
import js from '@eslint/js';
import vue from 'eslint-plugin-vue';
import tseslint from 'typescript-eslint';
import globals from 'globals';

export default [
  // 全局规则
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // 2026-06-29: TODO 队列 - 这些规则首次跑会刷大量 issue, 不一次性全开
      // 'no-unused-vars': 'warn',  // 暂时不开, 项目里很多未用导入
      // 'no-console': 'warn',
      '@typescript-eslint/no-unused-vars': 'off',     // 跟 TS 推荐集一致
      '@typescript-eslint/no-explicit-any': 'off',    // 项目用了大量 any (mock 数据 / 后端类型不全)
      'vue/multi-word-component-names': 'off',         // 一些单字组件名 (Login, Layout) 不强制多字
      // Fix 3 XSS: 重新启用 v-html 规则. OfferList.vue 已改用 sandbox iframe.
      // 如有特殊场景需 v-html, 必须 // eslint-disable-next-line vue/no-v-html + 安全审计.
      'vue/no-v-html': 'error',
      'vue/html-self-closing': 'off',                  // 风格问题
      'vue/max-attributes-per-line': 'off',           // 风格问题
      'vue/singleline-html-element-content-newline': 'off',  // 风格
      'vue/html-indent': 'off',                        // 风格
      'vue/html-closing-bracket-newline': 'off',       // 风格
      'vue/first-attribute-linebreak': 'off',          // 风格
      'no-undef': 'off',                               // TS 关心
    },
  },
  // .vue 文件额外规则
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 2022,
        sourceType: 'module',
      },
    },
  },
  // 忽略 dist / node_modules / 静态文件 / 构建与测试产物
  //
  // 2026-10-15: 补 coverage/**。此前 vitest 覆盖率门禁因缺 @vitest/coverage-v8
  //   从未真正跑通过，coverage/ 目录不会生成，问题被掩盖。门禁修好后
  //   `npm test -- --coverage` 会产出 coverage/（内含 sorter.js 等报告资产），
  //   未忽略时 eslint 会把这些生成物当源码扫出 2 个 warning，
  //   而 CI 顺序是「先 coverage 后 lint:ci（--max-warnings=0）」→ 直接红。
  {
    ignores: [
      'dist*/**',
      'node_modules/**',
      '**/*.min.js',
      'public/**',
      '*.cjs',
      'coverage/**',
      'playwright-report/**',
      'test-results/**',
    ],
  },
];
