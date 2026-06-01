<template>
  <div class="dashboard-page">
    <a-card 
      :style="{ 
        borderRadius: '12px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.08)'
      }"
    >
      <div class="dashboard-content">
        <a-typography-title :level="2">🎉 ATS招聘管理系统</a-typography-title>
        <a-typography-text type="secondary" :style="{ fontSize: '16px' }">
          欢迎使用招聘管理系统
        </a-typography-text>
        
        <div class="dashboard-actions">
          <a-space size="large" wrap>
            <a-button 
              type="primary" 
              size="large"
              @click="goToDemands"
            >
              <template #icon><PlusOutlined /></template>
              创建需求
            </a-button>
            <a-button 
              size="large"
              @click="goToCandidates"
            >
              候选人管理
            </a-button>
            <a-button 
              size="large"
              @click="goToPositions"
            >
              职位管理
            </a-button>
          </a-space>
        </div>

        <div class="dashboard-stats">
          <a-typography-title :level="4">📊 招聘数据概览</a-typography-title>
          <a-row :gutter="[24, 24]" :style="{ marginTop: '20px' }">
            <a-col :xs="24" :sm="12" :md="6">
              <a-card size="small" :style="{ borderRadius: '8px' }">
                <a-typography-text type="secondary">招聘需求</a-typography-text>
                <div class="stat-value" style="color: #FBCE5B">28</div>
              </a-card>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-card size="small" :style="{ borderRadius: '8px' }">
                <a-typography-text type="secondary">进行中职位</a-typography-text>
                <div class="stat-value" style="color: #13c2c2">156</div>
              </a-card>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-card size="small" :style="{ borderRadius: '8px' }">
                <a-typography-text type="secondary">候选人</a-typography-text>
                <div class="stat-value" style="color: #faad14">892</div>
              </a-card>
            </a-col>
            <a-col :xs="24" :sm="12" :md="6">
              <a-card size="small" :style="{ borderRadius: '8px' }">
                <a-typography-text type="secondary">本周面试</a-typography-text>
                <div class="stat-value" style="color: #52c41a">45</div>
              </a-card>
            </a-col>
          </a-row>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { PlusOutlined } from '@ant-design/icons-vue'

const router = useRouter()

const goToDemands = () => {
  router.push('/demands')
}

const goToCandidates = () => {
  router.push('/candidates')
}

const goToPositions = () => {
  router.push('/positions')
}
</script>

<style scoped>
.dashboard-page {
  padding: 24px;
  min-height: 100%;
}

.dashboard-content {
  text-align: center;
  padding: 60px 20px;
}

.dashboard-actions {
  margin-top: 40px;
}

.dashboard-stats {
  margin-top: 60px;
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  margin-top: 8px;
}
</style>