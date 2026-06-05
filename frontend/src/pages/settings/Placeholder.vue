<template>
  <div class="placeholder-page">
    <n-card :bordered="false" class="rounded-xl" style="box-shadow: 0 2px 12px rgba(0,0,0,0.08)">
      <n-empty :description="descriptionText">
        <template #icon>
          <n-icon :component="icon" :size="64" color="#FBCE5B" />
        </template>
      </n-empty>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  TrendingUpOutline,
  TimeOutline,
} from '@vicons/ionicons5'

const route = useRoute()

// 路由名 → 友好的占位文案
const placeholderMap: Record<string, { icon: any; text: string }> = {
  Report: { icon: TrendingUpOutline, text: '数据中心 - 即将上线' },
}

const icon = computed(() => placeholderMap[route.name as string]?.icon ?? TimeOutline)
const descriptionText = computed(() => placeholderMap[route.name as string]?.text ?? '该功能开发中，敬请期待')
</script>

<style scoped>
.placeholder-page {
  padding: 24px;
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
