<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">班级管理</h1>
          <p class="page-subtitle">校招生班级（班主任 / 班长 / HRBP）管理</p>
        </div>
      </div>
      <n-empty description="班级管理页面建设中" />
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
