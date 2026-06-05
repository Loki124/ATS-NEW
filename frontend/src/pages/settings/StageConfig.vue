<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">阶段配置</h1>
    </div>
    <n-card>
      <n-empty description="阶段配置功能开发中">
        <template #icon>
          <n-icon :component="GitNetworkOutline" :size="64" color="#FBCE5B" />
        </template>
      </n-empty>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { GitNetworkOutline } from '@vicons/ionicons5'
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
