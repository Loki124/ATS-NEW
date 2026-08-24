<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">评分规则</h1>
      <p class="page-subtitle">定义候选人评分维度与权重，支撑面试评价标准化</p>
    </div>
    <n-card>
      <n-empty description="评分规则功能开发中">
        <template #icon>
          <n-icon :component="StarOutline" :size="64" color="var(--brand)" />
        </template>
      </n-empty>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { StarOutline } from '@vicons/ionicons5'
</script>

<style scoped>
/* 删除 scoped .page-header/.page-title 覆盖（规范：复用全局 glass.css 渐变规格与通栏分隔线） */
</style>
