<template>
  <n-config-provider
    :theme="isDark ? darkTheme : undefined"
    :theme-overrides="themeOverrides"
    :locale="zhCN"
    :date-locale="dateZhCN"
  >
    <n-loading-bar-provider>
      <n-message-provider>
        <n-dialog-provider>
          <n-notification-provider>
            <router-view />
          </n-notification-provider>
        </n-dialog-provider>
      </n-message-provider>
    </n-loading-bar-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { darkTheme, zhCN, dateZhCN, type GlobalThemeOverrides } from 'naive-ui'
import { useThemeStore } from './stores/theme'

// 启动期 user 重水化 + 服务端重调已统一在 main.ts 处理.
// 此前 App.vue onMounted 里的 localStorage('token') 兼容分支已删除 —
// 因为 main.ts step 1 已经覆盖了 'token' / 'accessToken' 双 key fallback,
// 这里再做一次会产生与 main.ts 顺序竞争, 是 dead code.

// === v2 液态玻璃：Naive UI themeOverrides（DESIGN.md §2）===
// 单一输入：stores/theme.ts 的 brandHex（来自 --brand / 设置页）。
// 改 brandHex 即可全站联动（按钮、激活态、链接、玻璃辉光、极光主光斑）。
//
// ⚠️ 已知限制：Naive UI 内部用 parseColor 把 primaryColor 转成 RGB 计算
//    hover/pressed 等派生色，传 CSS 变量字符串 `var(--brand)` 会导致
//    颜色工具函数失败（Naive 不解析 var()）。
//    妥协方案：themeOverrides 用 hex 字面量（由 store.deriveHover/derivePressed
//    派生，业务层玻璃类通过 var(--brand) 直接驱动）。
//
// ★ 2026-08-23 暗色修复：darkTheme 从 naive-ui 直接 import，
//    通过 computed 切 :theme prop 让 n-data-table / n-tabs / n-alert
//    等原生组件走深色调色板。配合 body.dark（CSS 变量）联动 glass/aurora。
const themeStore = useThemeStore()
const { brandHex, brandHoverHex, brandPressedHex, isDark } = storeToRefs(themeStore)

const themeOverrides = computed<GlobalThemeOverrides>(() => ({
  common: {
    primaryColor:        brandHex.value,
    primaryColorHover:   brandHoverHex.value,
    primaryColorPressed: brandPressedHex.value,
    primaryColorSuppl:   brandHex.value,
    // === 语义色（与 tokens.css §4 语义色同步，改令牌需同步此处 hex 字面量：Naive parseColor 不解析 var()）===
    successColor: '#16A34A',
    warningColor: '#F59E0B',
    errorColor:   '#EF4444',
    infoColor:    '#3B82F6',
    // === 圆角（DESIGN.md §11：主圆角 16px）===
    borderRadius: '16px',
    // === 暗色模式下的字色 / 表面色（让 Naive 原生组件走暗色变量不「浅色实底」）
    // 透明让 glass.css 接管；body.dark 联动 glass.css 切换深色透明 ===
    bodyColor: isDark.value ? 'transparent' : 'transparent',
    cardColor: isDark.value ? 'transparent' : '#ffffff',
    modalColor: isDark.value ? 'transparent' : '#ffffff',
    popoverColor: isDark.value ? 'transparent' : '#ffffff',
    tableColor: isDark.value ? 'transparent' : '#ffffff',      // ★ 解决「白卡漂浮」核心
    tableHeaderColor: isDark.value ? 'rgba(255, 255, 255, 0.04)' : 'rgba(255, 255, 255, 0.65)',
    tableColorHover: isDark.value ? 'rgba(255, 255, 255, 0.06)' : 'rgba(99, 102, 241, 0.06)',
    tableColorStriped: isDark.value ? 'transparent' : 'transparent',
    inputColor: isDark.value ? 'rgba(255, 255, 255, 0.06)' : 'rgba(255, 255, 255, 0.5)',
    inputColorDisabled: isDark.value ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.02)',
    buttonColor2: isDark.value ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.06)',
    buttonColor2Hover: isDark.value ? 'rgba(255, 255, 255, 0.18)' : 'rgba(0, 0, 0, 0.09)',
    buttonColor2Pressed: isDark.value ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)',
    actionColor:        isDark.value ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.04)',          // ★ v1.1 补充
    tabColor:           isDark.value ? 'rgba(255, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.7)',        // ★ v1.1 补充
    closeColorHover:    isDark.value ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.09)',            // ★ v1.1 补充
    textColor1: isDark.value ? 'rgba(232, 236, 246, 1)' : 'rgba(15, 23, 42, 1)',         // 主要文字
    textColor2: isDark.value ? 'rgba(174, 184, 204, 1)' : 'rgba(71, 85, 105, 1)',         // 次要文字
    textColor3: isDark.value ? 'rgba(124, 135, 155, 1)' : 'rgba(148, 163, 184, 1)',       // 占位符
    dividerColor: isDark.value ? 'rgba(255, 255, 255, 0.08)' : 'rgba(15, 23, 42, 0.08)',
    borderColor: isDark.value ? 'rgba(255, 255, 255, 0.12)' : 'rgba(15, 23, 42, 0.12)',
  },
  Card: {
    borderRadius: '16px',
  },
  Button: {
    borderRadiusMedium: '16px',
    // 玻璃按钮：白字（DESIGN.md §4 btn-primary：品牌渐变背景 → 白字最稳）
    textColorPrimary:          '#ffffff',
    textColorHoverPrimary:     '#ffffff',
    textColorPressedPrimary:   '#ffffff',
    textColorFocusPrimary:     '#ffffff',
    textColorDisabledPrimary:  '#ffffff',
  },
  // ★ v1.1 评审 P1-3：n-alert 暗色背景走 themeOverrides 不走 !important
  // 4 个 colorInfo/Success/Warning/Error 字段控制 n-alert 的色调
  Alert: {
    colorInfo:    isDark.value ? 'rgba(59, 130, 246, 0.18)' : 'rgba(59, 130, 246, 0.12)',
    colorSuccess: isDark.value ? 'rgba(22, 163, 74, 0.20)' : 'rgba(22, 163, 74, 0.12)',
    colorWarning: isDark.value ? 'rgba(245, 158, 11, 0.22)' : 'rgba(245, 158, 11, 0.14)',
    colorError:   isDark.value ? 'rgba(239, 68, 68, 0.20)' : 'rgba(239, 68, 68, 0.12)',
  },
}))
</script>

<style>
/* 全局样式已在 index.css 中定义 */
</style>