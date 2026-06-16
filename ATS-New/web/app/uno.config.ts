import { defineConfig, presetUno, presetIcons, presetTypography, presetWebFonts } from 'unocss'

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
      // 品牌主色（金黄色系，保留旧 ant 主题的 #FBCE5B）
      primary: {
        DEFAULT: '#FBCE5B',
        dark: '#E5B82A',
        light: '#FCE5A6',
      },
      // Naive UI 风格的状态色
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      info: '#1890ff',
    },
    fontFamily: {
      sans: '"PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      mono: '"SF Mono", Menlo, Monaco, Consolas, "Courier New", monospace',
    },
  },
  shortcuts: {
    // 常用布局快捷类
    'flex-center': 'flex items-center justify-center',
    'flex-between': 'flex items-center justify-between',
    'page-container': 'p-6 min-h-screen',
    'card-base': 'bg-white rounded-xl shadow-sm',
    // 品牌色：金色渐变背景（用于 logo / 标题图标 / 强调徽标）
    // 改色只改 theme.colors.primary 即可全站联动
    'bg-primary-gradient': 'bg-gradient-to-br from-primary to-primary-dark',
  },
  safelist: [
    // 动态 className 保险
    'text-primary', 'bg-primary', 'border-primary',
    'text-success', 'text-warning', 'text-error', 'text-info',
  ],
})
