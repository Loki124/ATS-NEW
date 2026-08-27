<template>
  <n-layout class="settings-layout" has-sider :sider-width="64" style="height: 100%">
    <!-- 左侧子菜单：n-menu 取代自写 menu-group（阶段 D 决策 2 配套）
         ⚠️ 不再用 n-layout-sider：它会自动把 header + menu 一起包进内部 .n-layout-scroll-container，
         导致 Naive 的 scrollbar 竖向跨整个容器、覆盖在 header 上方（用户反馈"滚动条覆盖header"）。
         改为自定义 .settings-sider（flex column），header 固定、menu 单独 overflow-y:auto，
         scrollbar 只出现在菜单区，不接触 header。 -->
    <div
      class="settings-sider glass-sidebar"
      :class="{ 'settings-sider--floating': effectiveExpanded }"
      @mouseenter="hoverExpanded = true"
      @mouseleave="hoverExpanded = false"
    >
      <div class="sider-header" :class="{ collapsed: !effectiveExpanded }">
        <h2 v-if="effectiveExpanded" class="sider-title gradient-title">设置</h2>
        <n-icon v-else class="sider-logo" :component="SettingsOutline" />
      </div>

      <div class="settings-sider-menu">
        <n-menu
          :collapsed="!effectiveExpanded"
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
      </div>
    </div>

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
import { NIcon, NLayout, NLayoutContent, NMenu } from 'naive-ui'
import {
  SettingsOutline,
  PersonCircleOutline, BusinessOutline, PeopleOutline, BookOutline, BookmarkOutline,
  ClipboardOutline, StarOutline, SchoolOutline, GitNetworkOutline, GitBranchOutline,
  StopwatchOutline, ConstructOutline, LayersOutline, InformationCircleOutline,
  CloudUploadOutline, ServerOutline, SearchOutline, AnalyticsOutline,
  ColorPaletteOutline, LocationOutline, VideocamOutline, MailOutline,
  ShieldCheckmarkOutline, PeopleCircleOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

// 设置侧边栏：默认折叠 64px 常驻，hover 浮层展开（仿顶层 Layout.vue 范式）
// - collapsed 作为永久基础态固定 true（sider 始终占 grid 第 1 列 64px）
// - hoverExpanded 由 mouseenter/leave 驱动，effectiveExpanded 控制浮层展开
const collapsed = ref(true)
const hoverExpanded = ref(false)
const effectiveExpanded = computed(() => hoverExpanded.value)

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
/* 仿顶层 Layout.vue 范式：grid 两列 64px + 1fr，浮层 sider 脱离后仍保留第 1 列 64px 占位 */
.settings-layout { height: 100% !important; background: transparent; overflow: hidden; display: grid !important; grid-template-columns: 64px 1fr !important; grid-template-rows: 100% !important; }

/* ⚠️ 自定义 .settings-sider（取代 n-layout-sider）：
   - flex column 让 header / menu 上下分区
   - position:relative 给之后可能的 footer absolute 定位预留
   - border-right 视觉边界（与右内容分隔），圆角顶部对齐 panel */
.settings-sider {
  grid-column: 1;
  grid-row: 1;
  display: flex;
  flex-direction: column;
  width: 64px !important;          /* 始终占 grid 第 1 列 64px（基础折叠态常驻） */
  height: 100%;
  min-height: 0;
  overflow: visible !important;    /* 浮层展开时菜单文字不被 sider 容器裁剪 */
  position: relative;
  border-right: 1px solid var(--border-hairline);
  transition: none !important;     /* 关闭 width 过渡，hover 瞬切避免抖动 */
}
/* hover 浮层展开：脱离 grid 流、叠在内容上方，不挤压 content（content 仍占第 2 列） */
.settings-sider.settings-sider--floating {
  position: fixed !important;
  left: 0 !important;
  top: 0 !important;
  width: 220px !important;
  max-width: 220px !important;
  height: 100dvh !important;
  z-index: 1000;
  background: var(--glass-bg-elevated);
  -webkit-backdrop-filter: blur(var(--glass-blur-panel));
  backdrop-filter: blur(var(--glass-blur-panel));
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.20);   /* 浮层投影，与右侧内容区分（非品牌色中性阴影） */
  border-right: 1px solid var(--border-hairline);
}
/* 滚动区：占据 header 之外剩余高度，scrollbar 只在这里出现 */
.settings-sider-menu {
  flex: 1;
  min-height: 0;            /* flex 子项 min-height 默认 auto 会撑爆，必须 0 */
  overflow-y: auto;         /* 原生滚动，glass.css 全局 ::-webkit-scrollbar 已美化 */
  overflow-x: hidden;
  /* iOS 弹性滚动 + 桌面端丝滑 */
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;

  /* === 该元素自身的 scrollbar 显隐规则（兵哥反馈 global ::- 不够稳）===
     - 默认 thumb 完全透明（看不到滚动条，但仍在 DOM 里可滚）
     - 自身被 hover 时，thumb 呈 brand 紫（与项目其它滚条统一）
     - 直接选择器（.settings-sider-menu:hover::-webkit-scrollbar-thumb）可靠，
       不依赖 parent :hover 传递（webkit 不支持 parent:hover → 伪元素传递）
     - 颜色统一用 glass.css 的 --scrollbar-color-* 系列 token，单源 */
  scrollbar-color: transparent transparent;             /* Firefox 默认透明 */
  scrollbar-width: thin;
  transition: scrollbar-color 0.2s var(--ease-out);
}
.settings-sider-menu::-webkit-scrollbar {
  width: 5px;
  height: 5px;
  background: transparent;
  /* 关键：scrollbar 自身不接收点击。
     真实 Chromium classic scrollbar 的 rail(5px) 紧贴 n-menu 子菜单箭头，
     点击箭头时若略微偏移到 rail，浏览器触发 "jump to here" 滚动
     → 菜单内容移动几像素 → 鼠标按下/抬起落到不同元素 → n-menu click 被吞，
     表现为"折叠/展开要点好几次"。
     headless Chromium 无此 hit-test 行为，所以自动化不重现、但用户每次都遇到。
     thumb 单独恢复 pointer-events: auto 以保留拖动。 */
  pointer-events: none;
}
.settings-sider-menu::-webkit-scrollbar-thumb {
  background: transparent;                              /* webkit 默认透明 */
  border-radius: 3px;
  transition: background 0.2s var(--ease-out);
  pointer-events: auto;          /* thumb 仍可拖动（hover 显色后） */
}
.settings-sider-menu:hover {
  scrollbar-color: var(--scrollbar-color-hover) transparent;   /* Firefox 显色（统一 token） */
}
.settings-sider-menu:hover::-webkit-scrollbar-thumb {
  background: var(--scrollbar-color-hover);           /* webkit 显色（统一 token） */
}
.settings-sider-menu:hover::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-color-drag);            /* 自身 thumb hover 更深 */
}
.sider-header {
  position: sticky; top: 0; z-index: 10;
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 16px 12px 20px;
  flex-shrink: 0;            /* header 不让位，永远在顶部 */
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
.sider-logo { font-size: 22px; color: var(--ink-soft); margin: 0 auto; display: block; }

/* 右侧内容区 */
.settings-content {
  grid-column: 2;
  grid-row: 1;
  position: relative; padding: 0;
  overflow: hidden;
  display: flex; flex-direction: column;
  min-height: 0; height: 100%;
  background: transparent;
}
.settings-scroll {
  position: relative; z-index: 1;
  flex: 1; min-height: 0; height: 100%;
  /* ⚠️ 22:50 兵哥反馈"页面整体滚动 + 标题区滚动"双重滚动：
     - 原 overflow: auto 让 .settings-scroll 自身成滚动容器
     - 与各页 .page-body (overflow-y: auto) 同时存在 → 内容超长时双重滚动
     - 桌面端改为 overflow: hidden，由各页 .page-body 内部滚（单一滚动职责）
     - 移动端（≤ 767px）保留 overflow: auto（移动端布局单列，更适合整体滚） */
  overflow: hidden;
  padding: 20px;
}
@media (max-width: 767px) {
  .settings-scroll { overflow: auto; }
}
.settings-scroll :deep(.page-container) { padding: 0; min-height: 100%; }

/* === 阶段 D 第 2 轮：旧自写 menu CSS 已删除（DOM 已被 n-menu 取代）
   仅保留 n-menu wrapper 微调（settings-menu 是 n-menu 的 class 容器）=== */
.settings-menu { padding: 8px 0 16px; }
.settings-menu.collapsed { padding: 8px 0; }

/* === 折叠态 CSS 补丁：Naive UI 自身 .menu-item-group-title 在 :collapsed=true 下未做隐藏 ===
   现象：折叠 64px 时 group label "基本信息/过程管理/招聘提速/内容管理" 被 CSS 强竖排成「基/本/信/息」单字一行
   根因：MenuOptionGroup.mjs 第 47-53 行无条件渲染 group title；cssr.mjs 第 102 行只把 .n-menu-item-content-header 设 opacity:0
   方案：display:none 强制藏 group title + children label，children 之间用 hairline 隔开，icon 居中 === */
.settings-sider :deep(.settings-menu.n-menu--collapsed .n-menu-item-group-title),
.settings-sider :deep(.settings-menu.n-menu--collapsed .n-menu-item-content-header),
.settings-sider :deep(.settings-menu.n-menu--collapsed .n-menu-item-content__arrow) {
  display: none !important;
}
.settings-sider :deep(.settings-menu.n-menu--collapsed .n-menu-item-content__icon) {
  margin: 0 auto !important;
}
.settings-sider :deep(.settings-menu.n-menu--collapsed .n-menu-item-group + .n-menu-item-group) {
  border-top: 1px solid var(--border-hairline);
  margin-top: 8px;
  padding-top: 8px;
}
.settings-sider :deep(.settings-menu.n-menu--collapsed .n-menu-item) {
  margin-top: 4px !important;
}

</style>