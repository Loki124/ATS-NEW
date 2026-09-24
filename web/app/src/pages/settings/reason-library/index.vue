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
          <!-- tags 子路由由 router-view 渲染; keep-alive 缓存避免切换 Tab 重拉接口(交互卡顿) -->
          <router-view v-if="activeTab === 'tags'" v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </n-tab-pane>
        <n-tab-pane name="rules" :tab="t('reasonLibrary.tabs.rules')">
          <router-view v-if="activeTab === 'rules'" v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
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
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

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
/* === 复用 settings-page 三件套 + 页面滚动契约 ===
 * 关键高度链（对齐 CampusControl 验证过的模型）:
 *   .settings-scroll(overflow:hidden,确定高度)
 *   └ .page-container(全局强制 display:flex!important flex列)
 *     └ .page-body(本页强制 flex列 + overflow:hidden,滚动下沉到 .table-wrap)
 *       ├ .page-header(flex-shrink:0 固定)
 *       └ .rl-tabs(flex:1 撑满) → .n-tabs-pane-wrapper → .n-tab-pane(flex:1)
 *         └ .rl-tags-page / .rl-rules-page(flex:1) → .table-wrap(flex:1 overflow:auto)
 * 注: 全局 .settings-scroll :deep(.page-body) 是 overflow-y:auto 的【块级】容器,
 *     会让其内的 flex:1 子项(.rl-tabs)失去 flex 父级而高度塌缩(数据表 body 高度=0)。
 *     故此处用 .rl-page.page-container :deep(.page-body) 提特异性 + !important 覆盖为 flex列。 */
.rl-page {
  padding: 0 var(--space-6);
}
.rl-page :deep(.page-header) {
  margin-bottom: var(--space-4);
}
/* 提特异性(0,3,0)压过全局 .settings-scroll :deep(.page-body)(0,2,0), 强制 flex 列 + 取消整页滚动 */
.rl-page.page-container :deep(.page-body) {
  display: flex !important;
  flex-direction: column !important;
  flex: 1 1 auto !important;
  min-height: 0 !important;
  overflow: hidden !important;   /* 滚动职责下放 .table-wrap, 仅数据列表区滚动 */
}
.rl-tabs {
  /* n-tabs 占据剩余高度, 内部 tab-pane 才能正确撑开 */
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.rl-tabs :deep(.n-tabs-nav) {
  background: transparent;
}
.rl-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
}
.rl-tabs :deep(.n-tab-pane) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding-top: var(--space-3);
}
</style>
