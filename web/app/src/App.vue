<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
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
import { zhCN, dateZhCN, type GlobalThemeOverrides } from 'naive-ui'
import { useThemeStore } from './stores/theme'

// 启动期 user 重水化 + 服务端重调已统一在 main.ts 处理.
// 此前 App.vue onMounted 里的 localStorage('token') 兼容分支已删除 ——
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
const themeStore = useThemeStore()
const { brandHex, brandHoverHex, brandPressedHex } = storeToRefs(themeStore)

const themeOverrides = computed<GlobalThemeOverrides>(() => ({
  common: {
    primaryColor:        brandHex.value,
    primaryColorHover:   brandHoverHex.value,
    primaryColorPressed: brandPressedHex.value,
    primaryColorSuppl:   brandHex.value,
    // === 语义色（与 tokens.css 的 --c-* 默认值同步）===
    successColor: '#16A34A',
    warningColor: '#F59E0B',
    errorColor:   '#EF4444',
    infoColor:    '#3B82F6',
    // === 圆角（DESIGN.md §11：主圆角 16px）===
    borderRadius: '16px',
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
}))
</script>

<style>
/* 全局样式已在 index.css 中定义 */
</style>
