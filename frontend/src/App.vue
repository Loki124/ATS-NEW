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
import { onMounted } from 'vue'
import { zhCN, dateZhCN, darkTheme, type GlobalThemeOverrides } from 'naive-ui'
import { useUserStore } from './stores/user'

const userStore = useUserStore()

// 品牌主色：#FBCE5B（金黄色）
const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#FBCE5B',
    primaryColorHover: '#FCD97D',
    primaryColorPressed: '#E5B82A',
    primaryColorSuppl: '#FBCE5B',
    successColor: '#52c41a',
    warningColor: '#faad14',
    errorColor: '#ff4d4f',
    infoColor: '#1890ff',
    borderRadius: '8px',
  },
  Card: {
    borderRadius: '12px',
  },
  Button: {
    borderRadiusMedium: '8px',
    // 修复：主色按钮文字色（避免金底白字看不清）
    textColorPrimary: '#1f2937',
    textColorHoverPrimary: '#1f2937',
    textColorPressedPrimary: '#1f2937',
    textColorFocusPrimary: '#1f2937',
  },
}

onMounted(() => {
  // 恢复登录状态
  const token = localStorage.getItem('token')
  if (token) {
    const userData = localStorage.getItem('user')
    if (userData) {
      userStore.setUser(JSON.parse(userData))
    }
  }
})
</script>

<style>
/* 全局样式已在 index.css 中定义 */
</style>
