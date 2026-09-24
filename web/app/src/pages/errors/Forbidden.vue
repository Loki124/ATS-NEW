<template>
  <div class="err-page">
    <div class="glass-panel err-card">
      <div class="err-left">
        <h1 class="err-code">403</h1>
        <span class="err-tag">访问被拒绝</span>
      </div>
      <div class="err-right">
        <h2 class="err-title">你没有访问该页面的权限</h2>
        <p class="err-desc">该页面仅限特定角色（如 SUPER_ADMIN / HRBP）访问。如需权限，请联系系统管理员。</p>
        <div class="err-actions">
          <button class="btn btn-primary" @click="$router.replace('/dashboard')">返回工作台</button>
          <button class="btn btn-secondary" @click="$router.back()">返回上一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts"></script>

<!-- v2 bugfix P1-B: .err-* CSS 已统一抽到 styles/glass.css（DRY 修复），组件无 scoped 样式 -->