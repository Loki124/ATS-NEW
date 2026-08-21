<template>
  <n-layout class="settings-layout" has-sider :sider-width="220">
    <!-- 左侧子菜单 -->
    <n-layout-sider
      bordered
      :width="220"
      :native-scrollbar="false"
      content-style="padding: 16px 0;"
      class="settings-sider"
    >
      <div class="sider-header">
        <h2 class="sider-title">设置</h2>
      </div>

      <div class="settings-menu">
        <div
          v-for="group in subMenuOptions"
          :key="group.key"
          class="menu-group"
        >
          <div
            class="group-header"
            :class="{ expanded: isExpanded(group.key) }"
            @click="toggleGroup(group.key)"
          >
            <span class="group-title">{{ group.label }}</span>
            <n-icon
              class="group-arrow"
              :component="isExpanded(group.key) ? ChevronUpOutline : ChevronDownOutline"
            />
          </div>

          <div v-show="isExpanded(group.key)" class="group-body">
            <div
              v-for="item in group.children"
              :key="item.key"
              class="menu-item"
              :class="{ active: activeKey === item.key }"
              @click="handleMenuClick(item.key)"
            >
              <n-icon v-if="item.icon" class="menu-icon" :component="item.icon" />
              <span class="menu-label">{{ item.label }}</span>
            </div>
          </div>
        </div>
      </div>
    </n-layout-sider>

    <!-- 右侧内容 -->
    <n-layout-content class="settings-content">
      <router-view />
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, ref, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NIcon,
  NLayout,
  NLayoutSider,
  NLayoutContent,
} from 'naive-ui'
import {
  PersonCircleOutline,
  PersonAddOutline,
  CheckmarkDoneOutline,
  BusinessOutline,
  BookOutline,
  PeopleOutline,
  KeyOutline,
  LockClosedOutline,
  SettingsOutline,
  BookmarkOutline,
  ClipboardOutline,
  StarOutline,
  SchoolOutline,
  GitNetworkOutline,
  GitBranchOutline,
  StopwatchOutline,
  ConstructOutline,
  LayersOutline,
  InformationCircleOutline,
  CloudUploadOutline,
  ServerOutline,
  SearchOutline,
  AnalyticsOutline,
  ChevronDownOutline,
  ChevronUpOutline,
  ColorPaletteOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

// 子菜单：分组结构（与原 Layout.vue 的 系统管理 子树对齐）
const subMenuOptions = [
  {
    key: 'group-hr',
    label: '人事设置',
    children: [
      { key: '/settings/account', label: '员工信息设置', icon: PersonCircleOutline },
      { key: '/settings/onboarding', label: '入职设置', icon: PersonAddOutline },
      { key: '/settings/approval', label: '审批设置', icon: CheckmarkDoneOutline },
    ],
  },
  {
    key: 'group-org',
    label: '组织设置',
    children: [
      { key: '/settings/department', label: '部门管理', icon: BusinessOutline },
      { key: '/settings/user-management', label: '用户管理', icon: PeopleOutline },
      { key: '/settings/mou', label: 'MOU权限管理', icon: LockClosedOutline },
      { key: '/settings/field-acl', label: '字段权限', icon: KeyOutline },
      { key: '/settings/permissions', label: '权限管理', icon: LockClosedOutline },
    ],
  },
  {
    key: 'group-process',
    label: '过程管理',
    children: [
      { key: '/settings/demand-config', label: '招聘需求设置', icon: ClipboardOutline },
      { key: '/settings/dictionary', label: '数据字典', icon: BookmarkOutline },
      { key: '/settings/campus-control', label: '校招管控', icon: SchoolOutline },
      { key: '/settings/scoring', label: '评分规则', icon: StarOutline },
    ],
  },
  {
    key: 'group-speedup',
    label: '招聘提速',
    children: [
      { key: '/settings/recruitment-stage', label: '招聘阶段配置', icon: LayersOutline },
      { key: '/settings/recruitment-process', label: '招聘流程', icon: GitNetworkOutline },
      { key: '/settings/recruitment-round', label: '面试轮次', icon: StopwatchOutline },
    ],
  },
  {
    key: 'group-content',
    label: '内容管理',
    children: [
      { key: '/settings/announcements', label: '制度公告', icon: BookOutline },
    ],
  },
  {
    key: 'group-misc',
    label: '其他',
    children: [
      { key: '/settings/theme', label: '主题外观', icon: ColorPaletteOutline },
      { key: '/settings/company', label: '公司信息', icon: InformationCircleOutline },
      { key: '/settings/external', label: '对外接口', icon: ServerOutline },
      { key: '/settings/public', label: '公共设置', icon: CloudUploadOutline },
      { key: '/settings/school-library', label: '院校库', icon: SchoolOutline },
      { key: '/settings/company-library', label: '公司库', icon: BusinessOutline },
      { key: '/settings/dynamic-fields', label: '动态字段', icon: ConstructOutline },
      { key: '/settings/scraped-resumes', label: '我找的简历', icon: SearchOutline },
      { key: '/settings/data-dashboard', label: '数据中心', icon: AnalyticsOutline },
    ],
  },
]

// 默认全部折叠
const expandedKeys = ref<string[]>([])

function isExpanded(key: string) {
  return expandedKeys.value.includes(key)
}

function toggleGroup(key: string) {
  if (isExpanded(key)) {
    expandedKeys.value = expandedKeys.value.filter(k => k !== key)
  } else {
    expandedKeys.value = [...expandedKeys.value, key]
  }
}

// 进入页面或路由变化时，自动展开当前路由所在的分组
function expandCurrentGroup() {
  const group = subMenuOptions.find(g => g.children.some(c => c.key === route.path))
  if (group && !isExpanded(group.key)) {
    expandedKeys.value = [...expandedKeys.value, group.key]
  }
}

watch(() => route.path, expandCurrentGroup, { immediate: true })

// 当前路由对应的菜单 key —— 优化：computed 兜底 + optimisticKey 覆盖
// 路由异步 commit 期间，optimisticKey 立即接管，消除"原菜单闪一下"
const optimisticKey = ref('')
const optimisticTimer = ref<number>()

const activeKey = computed(() => {
  if (optimisticKey.value) return optimisticKey.value
  return route.path
})

function handleMenuClick(key: string) {
  if (typeof key === 'string' && key.startsWith('/')) {
    // nextTick 延迟避免 Naive UI slot 警告
    nextTick(() => {
      optimisticKey.value = key
    })
    if (optimisticTimer.value) window.clearTimeout(optimisticTimer.value)
    optimisticTimer.value = window.setTimeout(() => {
      optimisticKey.value = ''
    }, 1000)
    router.push(key)
  }
}

// 路由 commit 后清掉 optimisticKey
watch(
  () => route.path,
  () => {
    if (optimisticTimer.value) {
      window.clearTimeout(optimisticTimer.value)
      optimisticTimer.value = undefined
    }
    optimisticKey.value = ''
  }
)
</script>

<style scoped>
.settings-layout {
  height: 100%; /* 填满父级 content-wrapper 的内容盒, 避免与 padding 叠加产生双滚动 */
  background: transparent; /* 透出 Layout 的全局极光底 */
  /* 关键: 让内部 n-layout-sider 和 n-layout-content 都按比例填满, 内容溢出时 .settings-content 内部滚 */
  overflow: hidden;
}
.settings-layout :deep(.n-layout-scroll-container) {
  height: 100%;
  overflow: hidden;
}

/* 左侧子菜单栏 —— 玻璃面板（DESIGN.md §4 glass-panel） */
.settings-sider {
  background: var(--glass-bg-panel) !important;
  backdrop-filter: blur(var(--glass-blur-panel)) !important;
  -webkit-backdrop-filter: blur(var(--glass-blur-panel)) !important;
  border-right: 1px solid var(--glass-border) !important;
}
.sider-header {
  padding: 0 20px 12px;
  border-bottom: 1px solid var(--border-hairline);
  margin-bottom: 8px;
}
.sider-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

.settings-menu {
  padding: 0 0 16px;
}

.menu-group {
  user-select: none;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.group-header:hover {
  background: var(--brand-tint);
}
.group-title {
  font-size: 13px;
  color: var(--ink-faint);
  font-weight: 500;
}
.group-arrow {
  font-size: 14px;
  color: var(--ink-faint);
  transition: transform var(--duration-base) var(--ease-out);
}

.group-body {
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px 10px 44px;
  cursor: pointer;
  color: var(--ink-soft);
  font-size: 14px;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
  position: relative;
}
.menu-item:hover {
  background: var(--brand-tint);
}
/* 激活态：品牌浅底 + 品牌字 + 左侧 3px accent bar（DESIGN.md §4 导航激活态） */
.menu-item.active {
  color: var(--brand);
  background: var(--brand-soft);
  font-weight: 600;
}
.menu-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: var(--brand);
  border-radius: 0 2px 2px 0;
}
.menu-icon {
  font-size: 18px;
  flex-shrink: 0;
}

/* 右侧内容区 —— flex 列布局, 子页面可填满高度 */
.settings-content {
  padding: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 关键: flex 子元素需要 min-height:0 才能正确收缩 */
  background: transparent; /* 透出极光底 */
}

/* 让所有 Settings 子页面的根 wrapper 撑满父高度 (不依赖具体 class)
   用 :deep 穿透 scoped CSS 边界 (子页面是另一个组件实例) */
.settings-content :deep(> *) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  box-sizing: border-box;
  padding: 16px 24px;
  gap: 12px;
  overflow: hidden;
}
/* page-header (h1 + buttons) 不压缩 */
.settings-content :deep(.page-header) {
  flex-shrink: 0;
}
/* stats-row + filter-row 也不压缩 (保持原高) */
.settings-content :deep(.stats-row),
.settings-content :deep(.filter-row) {
  flex-shrink: 0;
}
/* 主内容卡片 (n-card) 撑开 + 内部滚 + 玻璃材质（DESIGN.md §4 glass-card） */
.settings-content :deep(.n-card) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  /* 玻璃：半透明白 + blur + 描边（不透明兜底由 --glass-bg-card 的 rgba 保证） */
  background: var(--glass-bg-card) !important;
  backdrop-filter: blur(var(--glass-blur-card)) !important;
  -webkit-backdrop-filter: blur(var(--glass-blur-card)) !important;
  border: 1px solid var(--glass-border) !important;
}
.settings-content :deep(.n-card__content) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
}
/* n-data-table 撑开卡片内容 + 内部滚 */
.settings-content :deep(.n-data-table) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.settings-content :deep(.n-data-table-wrapper) {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.settings-content :deep(.n-data-table-base-table) {
  width: 100%;
}

/* =============================================================
 * 校招管控视觉锚点全局注入（DESIGN.md §4 · 阶段 5）
 * 父级 :deep 一次性覆盖所有 25+ 设置子页面,
 * 子页面零侵入,逻辑完全不动,只换视觉层。
 * 锚点：渐变标题 + 卡片头玻璃 + 透明 tab + 玻璃 filter row + kpi 行玻璃
 * ============================================================= */

/* ① page-title 渐变文字（= cc-title · 一次性替换所有子页面 H1） */
.settings-content :deep(.page-title),
.settings-content :deep(.page-header h2),
.settings-content :deep(.policy-admin__title) {
  font-size: var(--text-h1) !important;
  font-weight: 700 !important;
  margin: 0 !important;
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-grad-a) 55%, var(--brand-grad-b) 100%) !important;
  -webkit-background-clip: text !important;
  background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  color: transparent !important;
  letter-spacing: -0.01em;
  line-height: 1.25;
}
/* 标题容器为 flex 让 h1 + 按钮同行（部分子页面用 .page-header） */
.settings-content :deep(.page-header) {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding: var(--space-3) 0;
}
/* 子页面常见的副标题描述行 */
.settings-content :deep(.page-subtitle),
.settings-content :deep(.page-desc) {
  color: var(--ink-soft);
  font-size: var(--text-body);
  margin: 4px 0 0;
}

/* ② n-card 卡片头玻璃化（= cc-glass-panel 局部版） */
.settings-content :deep(.n-card-header) {
  background: rgba(255, 255, 255, .5) !important;
  border-bottom: 1px solid var(--border-hairline) !important;
}
body.dark .settings-content :deep(.n-card-header) {
  background: rgba(30, 41, 59, .5) !important;
}
.settings-content :deep(.n-card-header__main) {
  font-weight: 600 !important;
  color: var(--ink) !important;
  font-size: var(--text-h4) !important;
}

/* ③ n-tabs 透明导航（= cc-tabs 透明 nav） */
.settings-content :deep(.n-tabs-nav) {
  background: transparent !important;
}
.settings-content :deep(.n-tabs-tab) {
  font-weight: 500;
}

/* ④ filter-row / stats-row 玻璃面板（filter toolbar 容器） */
.settings-content :deep(.filter-row),
.settings-content :deep(.stats-row) {
  flex-shrink: 0;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-3);
}

/* ⑤ n-button type="primary" 升级为渐变按钮（= cc-gradient-btn） */
.settings-content :deep(.n-button--primary-type:not(.n-button--disabled):not([disabled])) {
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a)) !important;
  border-color: transparent !important;
  color: #fff !important;
  box-shadow: 0 4px 14px var(--glow-brand) !important;
  transition: all var(--duration-base) var(--ease-out) !important;
}
.settings-content :deep(.n-button--primary-type:not(.n-button--disabled):not([disabled]):hover) {
  box-shadow: 0 6px 20px var(--glow-brand) !important;
  transform: translateY(-1px);
}

/* ⑥ 配置容器 .config-container / .container 类如果是浅灰底,改透出极光 */
.settings-content :deep(.config-container),
.settings-content :deep(.container),
.settings-content :deep(.settings-page-body) {
  background: transparent;
}

/* ⑦ n-card 内部 form/table 默认 padding 微调 */
.settings-content :deep(.n-card__content) {
  padding: var(--space-4) var(--space-4);
}
.settings-content :deep(.n-data-table-th) {
  background: rgba(255, 255, 255, .5) !important;
  font-weight: 600 !important;
  color: var(--ink) !important;
}
body.dark .settings-content :deep(.n-data-table-th) {
  background: rgba(30, 41, 59, .5) !important;
}
.settings-content :deep(.n-data-table-tr:hover .n-data-table-td) {
  background: var(--brand-tint) !important;
}
</style>
