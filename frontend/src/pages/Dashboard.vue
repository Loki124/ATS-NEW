<template>
  <div class="dashboard-page">
    <n-card :bordered="false" class="card-base">
      <div class="dashboard-content">
        <n-h2>🎉 ATS招聘管理系统</n-h2>
        <n-text :depth="3" class="text-base">欢迎使用招聘管理系统</n-text>

        <div class="dashboard-actions mt-6">
          <n-space size="large" wrap>
            <n-button type="primary" size="large" @click="goToDemands">
              <template #icon>
                <n-icon :component="AddOutline" />
              </template>
              创建需求
            </n-button>
            <n-button size="large" @click="goToCandidates">候选人管理</n-button>
            <n-button size="large" @click="goToPositions">职位管理</n-button>
          </n-space>
        </div>

        <div class="dashboard-stats mt-8">
          <n-h4>📊 招聘数据概览</n-h4>
          <n-grid :cols="4" :x-gap="24" :y-gap="24" responsive="screen" :item-responsive="true" class="mt-5">
            <n-grid-item span="4 m:2 l:1">
              <n-card size="small" :bordered="false" class="rounded-lg text-center">
                <n-text :depth="3">招聘需求</n-text>
                <div class="stat-value" style="color: #FBCE5B">28</div>
              </n-card>
            </n-grid-item>
            <n-grid-item span="4 m:2 l:1">
              <n-card size="small" :bordered="false" class="rounded-lg text-center">
                <n-text :depth="3">进行中职位</n-text>
                <div class="stat-value" style="color: #13c2c2">156</div>
              </n-card>
            </n-grid-item>
            <n-grid-item span="4 m:2 l:1">
              <n-card size="small" :bordered="false" class="rounded-lg text-center">
                <n-text :depth="3">候选人</n-text>
                <div class="stat-value" style="color: #faad14">892</div>
              </n-card>
            </n-grid-item>
            <n-grid-item span="4 m:2 l:1">
              <n-card size="small" :bordered="false" class="rounded-lg text-center">
                <n-text :depth="3">本周面试</n-text>
                <div class="stat-value" style="color: #52c41a">45</div>
              </n-card>
            </n-grid-item>
          </n-grid>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { AddOutline } from '@vicons/ionicons5'

const router = useRouter()

const goToDemands = () => router.push('/demands')
const goToCandidates = () => router.push('/candidates')
const goToPositions = () => router.push('/positions')
</script>

<style scoped>
.dashboard-page {
  padding: 0;
}
.dashboard-actions :deep(.n-button) {
  min-width: 140px;
}
.stat-value {
  font-size: 32px;
  font-weight: 700;
  margin-top: 8px;
}
</style>
