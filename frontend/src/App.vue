<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useUserStore } from './stores/user'

const userStore = useUserStore()

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