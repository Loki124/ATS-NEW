<template>
  <div class="page-container rl-page">
    <div class="page-body">
      <!-- 顶部标题 (沿用 settings/page-header 契约) -->
      <div class="page-header">
        <div>
          <h1 class="page-title">{{ t('reasonLibrary.title') }}</h1>
          <p class="page-subtitle">{{ t('reasonLibrary.subtitle') }}</p>
        </div>
      </div>

      <!-- Tabs: 二级导航 — 复用 n-tabs type=line 与 page 风格一致 -->
      <n-tabs
        :value="activeTab"
        type="line"
        animated
        class="rl-tabs"
        @update:value="onTabChange"
      >
        <n-tab-pane name="tags" :tab="t('reasonLibrary.tabs.tags')">
          <!-- tags 子路由由 router-view 渲染; 仅当命中 tags 时挂载 (router 自动) -->
          <router-view v-if="activeTab === 'tags'" v-slot="{ Component }">
            <component :is="Component" />
          </router-view>
        </n-tab-pane>
        <n-tab-pane name="rules" :tab="t('reasonLibrary.tabs.rules')">
          <router-view v-if="activeTab === 'rules'" v-slot="{ Component }">
            <component :is="Component" />
          </router-view>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 原因库 父布局 (T-15)
 * - 渲染两个 Tab: tags + rules
 * - 通过 query.tab 同步状态 (刷新页面保持当前 tab)
 * - children 路由由 router-view 挂载; 子路由文件仅在命中对应 tab 时渲染
 *   (避免两个页面同时 mount 抢 API 锁)
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NTabs, NTabPane } from 'naive-ui'
import { t } from '../../../locales/zh-CN'

const route = useRoute()
const router = useRouter()

const activeTab = computed<string>(() => {
  const q = (route.query.tab as string) || (route.path.endsWith('/rules') ? 'rules' : 'tags')
  return q === 'rules' ? 'rules' : 'tags'
})

function onTabChange(name: string) {
  if (name === activeTab.value) return
  // 切换 tab: 跳转对应子路由 (保持嵌套结构 + URL 可分享)
  router.push({ path: `/settings/reason-library/${name}` })
}
</script>

<style scoped>
/* === 复用 settings-page 三件套 + page-body 滚动契约 === */
.rl-page {
  padding: 0 var(--space-6);
}
.rl-page :deep(.page-header) {
  margin-bottom: var(--space-4);
}
.rl-tabs {
  /* 让 n-tabs 占据剩余高度, 子页面 .page-body 才能正确滚动 */
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.rl-tabs :deep(.n-tab-pane) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  /* 子页面自带 .page-container → 此处不重复叠加 */
  padding-top: var(--space-3);
}
</style>
