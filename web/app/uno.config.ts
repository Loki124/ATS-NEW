import { defineConfig, presetUno, presetIcons, presetTypography, presetWebFonts } from 'unocss'

/**
 * UnoCSS 配置 — 液态玻璃设计系统 v2（2026-08-21）
 *
 * 单一事实来源：DESIGN.md + src/styles/tokens.css
 *
 * 关键改动（v1 → v2）：
 *   - 品牌主色 primary：硬编码 #FBCE5B（金色）→ var(--brand) 驱动
 *     → 改 tokens.css 的 --brand 即可全站换肤（按钮、激活态、链接、Logo、玻璃辉光联动）
 *   - card-base：扁平白卡 `bg-white rounded-xl shadow-sm` → 玻璃面板快捷类
 *     → 替换为 .glass-panel / .glass-card（DESIGN.md §4）
 *   - bg-primary-gradient：用 --brand + --brand-grad-a 派生
 *
 * 迁移注意：
 *   - UnoCSS 的 `colors.primary.DEFAULT` 支持 var() 语法；工具类 `bg-primary/text-primary/border-primary`
 *     会编译为 `background-color: var(--brand)`。
 *   - 旧 `card-base` 暂时保留为 `glass-card` 别名（向后兼容），后续 T3.x 迁移时统一替换。
 */
export default defineConfig({
  presets: [
    presetUno(),         // 兼容 Tailwind 写法（默认）
    presetTypography(),  // typography 工具
    presetIcons({       // 图标（按需）—— 当前未启用，icons 走 @vicons/ionicons5
      scale: 1.2,
      warn: false,
    }),
    presetWebFonts({
      provider: 'none', // 不下载 Google Fonts（避免外网依赖）；如需可改 google
    }),
  ],
  theme: {
    colors: {
      // === 品牌主色（v2：var(--brand) 驱动）===
      // 改 src/styles/tokens.css 的 --brand 即全站联动。
      // 腾讯 CI 备选：--brand: #0052D9。
      primary: {
        DEFAULT: 'var(--brand)',            // 主色（靛紫 #6366F1）
        dark:    'var(--brand-dark)',       // 渐变深端（自动派生）
        light:   'var(--brand-hover)',      // hover 态（自动派生）
        pressed: 'var(--brand-pressed)',    // active 态（自动派生）
        soft:    'var(--brand-soft)',       // 12% 浅底（激活底、tag 底）
        tint:    'var(--brand-tint)',       // 6% 极浅底（hover 行）
      },
      // === Naive UI 风格的状态色（v2：从 tokens 派生，保持单一事实来源）===
      success: 'var(--c-success)',
      warning: 'var(--c-warning)',
      error:   'var(--c-error)',
      info:    'var(--c-info)',
    },
    fontFamily: {
      sans: 'var(--font-sans)',
      mono: 'var(--font-mono)',
    },
  },
  shortcuts: {
    // === 常用布局快捷类 ===
    'flex-center': 'flex items-center justify-center',
    'flex-between': 'flex items-center justify-between',
    'page-container': 'p-6 min-h-screen',

    // === 品牌色渐变背景（v2：用 --brand + --brand-grad-a 派生）===
    // 用于 Logo / 标题图标 / 强调徽标。改色只改 tokens.css 的 --brand 即全站联动。
    'bg-primary-gradient':
      'bg-gradient-to-br from-primary to-primary-dark',

    // === 玻璃态快捷类不再用 self-referencing shortcut ===
    // glass-card / glass-panel / glass-input / glass-tag / btn-* / .app-aurora / .gradient-title
    // 等玻璃原子类全部由 src/styles/glass.css 提供真实样式。
    // UnoCSS 看到不认识的类名会原样保留到 CSS，再由外部 .css 提供样式。
    // safelist 同步列出（防止被 purge）。
  },
  safelist: [
    // === 动态 className 保险 ===
    'text-primary', 'bg-primary', 'border-primary',
    'text-success', 'text-warning', 'text-error', 'text-info',
    // === 玻璃态快捷类（防止动态绑定被 purge）===
    'glass-card', 'glass-panel',
  ],
})
