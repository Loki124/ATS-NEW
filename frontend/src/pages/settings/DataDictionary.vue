<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">数据字典</h1>
    </div>
    <n-card>
      <n-empty description="数据字典功能开发中">
        <template #icon>
          <n-icon :component="BookOutline" :size="64" color="#FBCE5B" />
        </template>
      </n-empty>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { BookOutline } from '@vicons/ionicons5'
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
