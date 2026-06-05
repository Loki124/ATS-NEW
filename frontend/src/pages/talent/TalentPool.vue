<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">人才库</h1>
    </div>
    <n-card>
      <n-empty description="人才库功能开发中">
        <template #icon>
          <n-icon :component="PeopleCircleOutline" :size="64" color="#FBCE5B" />
        </template>
      </n-empty>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { PeopleCircleOutline } from '@vicons/ionicons5'
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
</style>
