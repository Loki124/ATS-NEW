<template>
  <div class="err-page">
    <div class="glass-panel err-card">
      <div class="err-left">
        <h1 class="err-code">404</h1>
        <span class="err-tag">PAGE NOT FOUND</span>
      </div>
      <div class="err-right">
        <h2 class="err-title">你访问的页面不存在</h2>
        <p class="err-desc">页面可能已被移除、链接拼写错误，或临时无法访问。请检查 URL 或使用下方按钮回到主流程。</p>
        <div class="err-actions">
          <button class="btn btn-primary" @click="$router.replace('/dashboard')">返回工作台</button>
          <button class="btn btn-secondary" @click="$router.back()">返回上一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<!-- v2 bugfix P1-B: .err-* CSS 已统一抽到 styles/glass.css（DRY 修复），组件无 scoped 样式 -->