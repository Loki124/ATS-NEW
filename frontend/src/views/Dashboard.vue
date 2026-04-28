<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold mb-6">工作台</h1>
    
    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div class="stat bg-white shadow rounded-lg p-4">
        <div class="stat-title text-gray-500">待处理需求</div>
        <div class="stat-value text-primary text-3xl">{{ stats.pendingDemands }}</div>
        <div class="stat-desc">较上周 +12%</div>
      </div>
      <div class="stat bg-white shadow rounded-lg p-4">
        <div class="stat-title text-gray-500">进行中职位</div>
        <div class="stat-value text-success text-3xl">{{ stats.activePositions }}</div>
        <div class="stat-desc">较上周 +5%</div>
      </div>
      <div class="stat bg-white shadow rounded-lg p-4">
        <div class="stat-title text-gray-500">候选人</div>
        <div class="stat-value text-warning text-3xl">{{ stats.candidates }}</div>
        <div class="stat-desc">较上周 +8%</div>
      </div>
      <div class="stat bg-white shadow rounded-lg p-4">
        <div class="stat-title text-gray-500">面试安排</div>
        <div class="stat-value text-info text-3xl">{{ stats.interviews }}</div>
        <div class="stat-desc">本周已安排</div>
      </div>
    </div>

    <!-- 招聘漏斗 -->
    <div class="card bg-white shadow mb-6">
      <div class="card-body">
        <h2 class="card-title mb-4">招聘漏斗</h2>
        <div class="flex items-end gap-4">
          <div class="flex flex-col items-center">
            <div class="bg-blue-500 text-white px-4 py-8 rounded-t" style="width: 80px;">
              {{ funnel.applications }}
            </div>
            <span class="text-sm mt-2">投递</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="bg-cyan-500 text-white px-4 py-6 rounded-t" style="width: 80px;">
              {{ funnel.screenings }}
            </div>
            <span class="text-sm mt-2">筛选</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="bg-green-500 text-white px-4 py-4 rounded-t" style="width: 80px;">
              {{ funnel.interviews }}
            </div>
            <span class="text-sm mt-2">面试</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="bg-orange-500 text-white px-4 py-2 rounded-t" style="width: 80px;">
              {{ funnel.offers }}
            </div>
            <span class="text-sm mt-2">Offer</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="bg-purple-500 text-white px-4 py-1 rounded-t" style="width: 80px;">
              {{ funnel.hired }}
            </div>
            <span class="text-sm mt-2">入职</span>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 快捷操作 -->
      <div class="card bg-white shadow">
        <div class="card-body">
          <h2 class="card-title mb-4">快捷操作</h2>
          <div class="grid grid-cols-3 gap-4">
            <button class="btn btn-outline btn-primary" @click="$router.push('/demands')">
              创建需求
            </button>
            <button class="btn btn-outline btn-success" @click="$router.push('/candidates')">
              添加候选人
            </button>
            <button class="btn btn-outline btn-warning" @click="$router.push('/interviews')">
              安排面试
            </button>
          </div>
        </div>
      </div>

      <!-- 最近活动 -->
      <div class="card bg-white shadow">
        <div class="card-body">
          <h2 class="card-title mb-4">最近活动</h2>
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <div class="avatar placeholder">
                <div class="bg-primary text-white rounded-full w-8">
                  <span class="text-xs">张</span>
                </div>
              </div>
              <div class="flex-1">
                <p class="text-sm">张三 投递了 前端开发工程师</p>
                <p class="text-xs text-gray-400">2分钟前</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div class="avatar placeholder">
                <div class="bg-success text-white rounded-full w-8">
                  <span class="text-xs">李</span>
                </div>
              </div>
              <div class="flex-1">
                <p class="text-sm">李四 完成了面试评估</p>
                <p class="text-xs text-gray-400">15分钟前</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div class="avatar placeholder">
                <div class="bg-warning text-white rounded-full w-8">
                  <span class="text-xs">王</span>
                </div>
              </div>
              <div class="flex-1">
                <p class="text-sm">王五 发送了Offer</p>
                <p class="text-xs text-gray-400">1小时前</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const stats = ref({
  pendingDemands: 12,
  activePositions: 28,
  candidates: 156,
  interviews: 8,
})

const funnel = ref({
  applications: 500,
  screenings: 320,
  interviews: 120,
  offers: 35,
  hired: 12,
})
</script>
