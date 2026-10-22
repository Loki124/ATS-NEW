<template>
  <!-- 轮岗资源：模块四（需求 4-1 / 4-2 / 4-3）的统一入口。
       三个页签分别承载：统计概览（BG/BU 多维测算表）、资源测算（直播/客服/其他/总数据）、
       轮岗资源台账（直播间 + 客服部门 + 其他 合一，2026-10-22 兵哥指令合并）。
       页面身份由顶部导航「校招生管理 → 轮岗资源」承载，与校招生管理其余列表页一致：不重复标题与提示条。 -->
  <div class="page-container">
    <div class="page-body">
      <n-tabs
        v-model:value="activeTab"
        type="line"
        display-directive="show:lazy"
        class="rr-tabs"
        @update:value="onTabChange"
      >
        <n-tab-pane name="stats" tab="统计概览">
          <ResourceStatsOverviewPanel />
        </n-tab-pane>
        <n-tab-pane name="bu" tab="资源测算">
          <ResourceSummaryPanel />
        </n-tab-pane>
        <!-- 2026-10-22 兵哥指令：直播间 + 客服部门整合为「轮岗资源」→
             原两个页签合并为一个，用「资源类型」列区分形态。 -->
        <n-tab-pane name="resource" tab="轮岗资源">
          <RotationResourcePanel />
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ResourceStatsOverviewPanel from './ResourceStatsOverview.vue'
import ResourceSummaryPanel from './ResourceSummary.vue'
import RotationResourcePanel from './RotationResourcePanel.vue'

/** 页签键：与 URL 查询参数 ?tab= 同值，旧路径重定向也用这套键。 */
type ResourceTab = 'stats' | 'bu' | 'resource'
const TAB_KEYS: ResourceTab[] = ['stats', 'bu', 'resource']

const route = useRoute()
const router = useRouter()

const activeTab = ref<ResourceTab>('stats')

/** 页签切换同步到 URL，便于刷新保持与旧深链落到对应页签。 */
function onTabChange(tab: ResourceTab) {
  if (route.query.tab === tab) return
  router.replace({ query: { ...route.query, tab } })
}

onMounted(() => {
  const q = route.query.tab
  if (typeof q === 'string' && (TAB_KEYS as string[]).includes(q)) {
    activeTab.value = q as ResourceTab
  }
})
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
  overflow-y: hidden;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
/* 页签栏固定在上方，内容区（面板）占满剩余高度并各自内部滚动（R-215 区域滚动） */
.rr-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.rr-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
}
.rr-tabs :deep(.n-tab-pane) {
  box-sizing: border-box;
  height: 100%;
  padding: var(--space-2) 0 0 0;
  display: flex;
  flex-direction: column;
}
</style>
