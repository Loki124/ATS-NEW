/* 由 brand-tokens.mjs 生成，请勿手改 —— 运行 `npm run tokens` 重新生成。 */
/**
 * 品牌令牌（TS 侧）。
 * 与 brand-tokens.css 同源产出，供 Naive UI themeOverrides 使用：
 * Naive 的 parseColor 不解析 CSS 变量，只接受 hex 字面量。
 *
 * - brand-fg     : 品牌色作前景（强调文字/图标/链接），已按 R-210 逐模式选「刚好达标 4.5:1」的阶
 * - brand-button : 主按钮底色 + 其上的前景色（-on-）
 */
export const BRAND_TOKENS = {
  brand: '#6366F1',
  fg: {
    light: { step: 600, color: '#5050d1', ratio: 6.16 },
    dark:  { step: 200,  color: '#99a2e3',  ratio: 6.01 },
  },
  button: {
    light: { step: 600, bg: '#5050d1', on: '#ffffff', ratio: 6.16 },
    dark:  { step: 300,  bg: '#7f89cf',  on: '#111827', ratio: 5.39 },
  },
  buttonText: {
    light: '#ffffff',
    dark:  '#111827',
  },
} as const;
