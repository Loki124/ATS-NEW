<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">轮岗资源</h1>
          <p class="page-subtitle">直播间资源（平台 / 地点 / 容量）管理</p>
        </div>
      </div>
      <n-empty description="轮岗资源页面建设中" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { NEmpty } from 'naive-ui'
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.page-header {
  flex-shrink: 0;
}
</style>
