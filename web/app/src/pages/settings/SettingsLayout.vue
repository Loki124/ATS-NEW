<template>
  <n-layout class="settings-layout" has-sider :sider-width="collapsed ? 64 : 220" style="height: 100%">
    <!-- 左侧子菜单：n-menu 取代自写 menu-group（阶段 D 决策 2 配套） -->
    <n-layout-sider
      :width="220"
      :collapsed-width="64"
      :collapsed="collapsed"
      collapse-mode="width"
      :native-scrollbar="false"
      class="settings-sider glass-sidebar"
    >
      <div class="sider-header" :class="{ collapsed: collapsed }">
        <h2 v-if="!collapsed" class="sider-title gradient-title">设置</h2>
        <button
          class="collapse-btn"
          :class="{ collapsed: collapsed }"
          type="button"
          aria-label="折叠设置菜单"
          @click="collapsed = !collapsed"
        >
          <n-icon :component="collapsed ? ChevronForwardOutline : ChevronBackOutline" />
        </button>
      </div>

      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="subMenuOptions"
        :value="activeKey"
        :expanded-keys="expandedKeys"
        :theme-overrides="settingsMenuThemeOverrides"
        class="settings-menu"
        @update:value="handleMenuClick"
        @update:expanded-keys="onExpandedKeysChange"
      />
    </n-layout-sider>

    <!-- 右侧内容 -->
    <n-layout-content class="settings-content">
      <div class="settings-aurora" aria-hidden="true">
        <span class="blob blob-a"></span>
        <span class="blob blob-b"></span>
        <span class="blob blob-c"></span>
      </div>
      <div class="settings-scroll">
        <router-view />
      </div>
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
// ★ v1.1 补全 imports（文档 §8.2 P0-3）
import { ref, computed, watch, nextTick, h, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon, NLayout, NLayoutSider, NLayoutContent, NMenu } from 'naive-ui'
import {
  ChevronForwardOutline, ChevronBackOutline,
  PersonCircleOutline, BusinessOutline, PeopleOutline, BookOutline, BookmarkOutline,
  ClipboardOutline, StarOutline, SchoolOutline, GitNetworkOutline, GitBranchOutline,
  StopwatchOutline, ConstructOutline, LayersOutline, InformationCircleOutline,
  CloudUploadOutline, ServerOutline, SearchOutline, AnalyticsOutline,
  ColorPaletteOutline, LocationOutline, VideocamOutline, MailOutline,
  ShieldCheckmarkOutline, PeopleCircleOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

// 设置侧边栏折叠状态
const collapsed = ref(false)

// ★ v1.1 修复：subMenuOptions 用 Naive UI 官方 MenuOption 类型
//   group 项：type: 'group' + 必填 children
//   叶子项：可选 icon render 函数
import type { MenuOption } from 'naive-ui'
type MenuItem = MenuOption

// ★ v1.1 修复：subMenuOptions 列全 5 个分组（基本信息/过程管理/招聘提速/内容管理/其他）
//   + 每组 children 完整迁移（22 项菜单）
//   icon 渲染：保持 render 函数形式（与 Layout.vue 一致）
const subMenuOptions: MenuItem[] = [
  {
    key: 'g-basic',
    type: 'group',
    label: '基本信息',
    children: [
      { key: '/settings/account', label: '个人信息管理', icon: () => h(NIcon, null, { default: () => h(PersonCircleOutline) }) },
      {
        key: 'g-company',
        label: '公司信息管理',
        icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }),
        children: [
          { key: '/settings/company', label: '公司信息', icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }) },
          { key: '/settings/company/address', label: '公司地址', icon: () => h(NIcon, null, { default: () => h(LocationOutline) }) },
          { key: '/settings/company/meeting-rooms', label: '公司会议室', icon: () => h(NIcon, null, { default: () => h(VideocamOutline) }) },
          { key: '/settings/company/resume-mailbox', label: '接收简历邮箱', icon: () => h(NIcon, null, { default: () => h(MailOutline) }) },
          { key: '/settings/company/brand', label: '品牌信息管理', icon: () => h(NIcon, null, { default: () => h(ColorPaletteOutline) }) },
        ],
      },
      {
        key: 'g-org',
        label: '组织信息管理',
        icon: () => h(NIcon, null, { default: () => h(PeopleOutline) }),
        children: [
          { key: '/settings/department', label: '组织职责管理', icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }) },
          { key: '/settings/permissions', label: '角色管理', icon: () => h(NIcon, null, { default: () => h(ShieldCheckmarkOutline) }) },
          { key: '/settings/user-management', label: '团队成员管理', icon: () => h(NIcon, null, { default: () => h(PeopleOutline) }) },
          { key: '/settings/user-groups', label: '用户组管理', icon: () => h(NIcon, null, { default: () => h(PeopleCircleOutline) }) },
        ],
      },
    ],
  },
  {
    key: 'g-process',
    type: 'group',
    label: '过程管理',
    children: [
      { key: '/settings/demand-config', label: '招聘需求设置', icon: () => h(NIcon, null, { default: () => h(ClipboardOutline) }) },
      { key: '/settings/dictionary', label: '数据字典', icon: () => h(NIcon, null, { default: () => h(BookmarkOutline) }) },
      { key: '/settings/campus-control', label: '校招管控', icon: () => h(NIcon, null, { default: () => h(SchoolOutline) }) },
      { key: '/settings/scoring', label: '评分规则', icon: () => h(NIcon, null, { default: () => h(StarOutline) }) },
    ],
  },
  {
    key: 'g-speedup',
    type: 'group',
    label: '招聘提速',
    children: [
      { key: '/settings/recruitment-stage', label: '招聘阶段配置', icon: () => h(NIcon, null, { default: () => h(LayersOutline) }) },
      { key: '/settings/recruitment-process', label: '招聘流程', icon: () => h(NIcon, null, { default: () => h(GitNetworkOutline) }) },
      { key: '/settings/recruitment-round', label: '面试轮次', icon: () => h(NIcon, null, { default: () => h(StopwatchOutline) }) },
    ],
  },
  {
    key: 'g-content',
    type: 'group',
    label: '内容管理',
    children: [
      { key: '/settings/announcements', label: '制度公告', icon: () => h(NIcon, null, { default: () => h(BookOutline) }) },
    ],
  },
  {
    key: 'g-misc',
    type: 'group',
    label: '其他',
    children: [
      { key: '/settings/theme', label: '主题外观', icon: () => h(NIcon, null, { default: () => h(ColorPaletteOutline) }) },
      { key: '/settings/company-library', label: '公司库', icon: () => h(NIcon, null, { default: () => h(BusinessOutline) }) },
      { key: '/settings/school-library', label: '院校库', icon: () => h(NIcon, null, { default: () => h(SchoolOutline) }) },
      { key: '/settings/dynamic-fields', label: '动态字段', icon: () => h(NIcon, null, { default: () => h(ConstructOutline) }) },
      { key: '/settings/scraped-resumes', label: '我找的简历', icon: () => h(NIcon, null, { default: () => h(SearchOutline) }) },
      { key: '/settings/data-dashboard', label: '数据中心', icon: () => h(NIcon, null, { default: () => h(AnalyticsOutline) }) },
      { key: '/settings/external', label: '对外接口', icon: () => h(NIcon, null, { default: () => h(ServerOutline) }) },
      { key: '/settings/public', label: '公共设置', icon: () => h(NIcon, null, { default: () => h(CloudUploadOutline) }) },
    ],
  },
]

// n-menu themeOverrides（让 Naive n-menu 字色走 CSS 变量，单一来源）
const settingsMenuThemeOverrides = {
  itemTextColor: 'var(--ink-soft)',
  itemTextColorHover: 'var(--ink)',
  itemTextColorActive: 'var(--brand)',
  itemTextColorActiveHover: 'var(--brand)',
  itemIconColor: 'var(--ink-soft)',
  itemIconColorHover: 'var(--ink)',
  itemIconColorActive: 'var(--brand)',
  itemColorActive: 'var(--brand-soft)',
  itemColorActiveHover: 'var(--brand-soft)',
  borderRadius: '6px',
  groupTextColor: 'var(--ink-faint)',
}

// ★ v1.1 修复：expandCurrent 改为累计 ancestor 链（3 嵌套必须展开中间层 + 最外层 group）
function findPathToKey(items: MenuItem[], target: string, currentPath: Array<string | number> = []): Array<string | number> | null {
  for (const item of items) {
    const newPath = [...currentPath, item.key]
    if (item.key === target) return newPath
    if (item.children?.length) {
      const found = findPathToKey(item.children, target, newPath)
      if (found) return found
    }
  }
  return null
}

function expandCurrentTo(path: string) {
  const chain = findPathToKey(subMenuOptions, path)
  if (!chain) return
  // chain 是从最外层 group 到目标 key 的完整路径，剔除目标本身
  const ancestors = chain.slice(0, -1)
  const merged: Array<string | number> = [...expandedKeys.value, ...ancestors]
  expandedKeys.value = merged
}

const expandedKeys = ref<Array<string | number>>([])
function onExpandedKeysChange(keys: Array<string | number>) {
  expandedKeys.value = keys
}

// 当前路由对应的菜单 key —— 优化：computed 兜底 + optimisticKey 覆盖
const optimisticKey = ref('')
const optimisticTimer = ref<number>()

const activeKey = computed(() => {
  if (optimisticKey.value) return optimisticKey.value
  return route.path
})

watch(() => route.path, () => expandCurrentTo(route.path), { immediate: true })

function handleMenuClick(key: string) {
  if (typeof key === 'string' && key.startsWith('/')) {
    nextTick(() => { optimisticKey.value = key })
    if (optimisticTimer.value) window.clearTimeout(optimisticTimer.value)
    optimisticTimer.value = window.setTimeout(() => { optimisticKey.value = '' }, 1000)
    router.push(key)
  }
}

// 路由 commit 后清掉 optimisticKey
watch(() => route.path, () => {
  if (optimisticTimer.value) { window.clearTimeout(optimisticTimer.value); optimisticTimer.value = undefined }
  optimisticKey.value = ''
})
</script>

<style scoped>
/* 阶段 D 保留旧 CSS 兜底（下一轮删）—— 玻璃激活态覆盖：利用 settings-sider 已有 class="glass-sidebar"（glass.css 全局接管）*/
.settings-layout { height: 100%; background: transparent; overflow: hidden; }
.settings-layout { height: 100% !important; }
.sider-header {
  position: sticky; top: 0; z-index: 10;
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 16px 12px 20px;
  /* ⚠️ 22:35 兵哥反馈"设置主标题作为固定头部展示，仅让标题下方列表支持滚动"：
     - position: sticky + top: 0 已实现（实测滚 367px 后 y 仍 64），但背景半透明
       rgba(255,255,255,.55) 让用户视觉上感觉'跟着滚'
     - 改用 var(--glass-bg-elevated) (.72) 更不透明，明确'固定头部'的视觉边界 */
  border-bottom: 1px solid var(--border-hairline);
  background: var(--glass-bg-elevated);
  backdrop-filter: blur(var(--glass-blur-panel));
  -webkit-backdrop-filter: blur(var(--glass-blur-panel));
}
.sider-header.collapsed { justify-content: center; padding: 16px 8px 12px; }
.sider-title { margin: 0; font-size: 16px; font-weight: 600; color: var(--ink); }
.collapse-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px;
  border-radius: var(--radius-md);
  background: transparent; border: 1px solid transparent;
  color: var(--ink-soft); cursor: pointer; font-size: 16px;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.collapse-btn:hover { background: var(--brand-tint); color: var(--brand); border-color: var(--glass-border); }
.collapse-btn.collapsed { width: 32px; height: 32px; }

/* 右侧内容区 */
.settings-content {
  position: relative; padding: 0;
  overflow: hidden;
  display: flex; flex-direction: column;
  min-height: 0; height: 100%;
  background: transparent;
}
.settings-scroll {
  position: relative; z-index: 1;
  flex: 1; min-height: 0; height: 100%;
  overflow: auto; padding: 20px;
}
.settings-scroll :deep(.page-container) { padding: 0; min-height: 100%; }

/* === 阶段 D 第 2 轮：旧自写 menu CSS 已删除（DOM 已被 n-menu 取代）
   仅保留 n-menu wrapper 微调（settings-menu 是 n-menu 的 class 容器）=== */
.settings-menu { padding: 8px 0 16px; }
.settings-menu.collapsed { padding: 8px 0; }
</style>