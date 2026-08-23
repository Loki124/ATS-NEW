<template>
  <n-layout class="settings-layout" has-sider :sider-width="collapsed ? 64 : 220">
    <!-- 左侧子菜单 -->
    <n-layout-sider
      :width="220"
      :collapsed-width="64"
      :collapsed="collapsed"
      collapse-mode="width"
      :native-scrollbar="false"
      class="settings-sider"
    >
      <div class="sider-header" :class="{ collapsed: collapsed }">
        <h2 v-if="!collapsed" class="sider-title">设置</h2>
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

      <div class="settings-menu" :class="{ collapsed: collapsed }">
        <!-- 折叠态：扁平图标列表 + tooltip -->
        <template v-if="collapsed">
          <n-tooltip
            v-for="item in flatMenuItems"
            :key="item.key"
            placement="right"
            trigger="hover"
          >
            <template #trigger>
              <div
                class="menu-item menu-item--collapsed"
                :class="{ active: activeKey === item.key }"
                @click="handleMenuClick(item.key)"
              >
                <n-icon v-if="item.icon" class="menu-icon" :component="item.icon" />
              </div>
            </template>
            {{ item.label }}
          </n-tooltip>
        </template>

        <!-- 展开态：分组菜单（支持二级 + 三级嵌套） -->
        <template v-else>
          <div
            v-for="group in subMenuOptions"
            :key="group.key"
            class="menu-group"
          >
            <div
              class="group-header"
              :class="{ expanded: isGroupExpanded(group.key) }"
              @click="toggleGroup(group.key)"
            >
              <span class="group-title">{{ group.label }}</span>
              <n-icon
                class="group-arrow"
                :component="isGroupExpanded(group.key) ? ChevronUpOutline : ChevronDownOutline"
              />
            </div>

            <div v-show="isGroupExpanded(group.key)" class="group-body">
              <template v-for="item in group.children" :key="item.key">
                <!-- 叶子菜单项 -->
                <div
                  v-if="!item.children?.length"
                  class="menu-item"
                  :class="{ active: activeKey === item.key }"
                  @click="handleMenuClick(item.key)"
                >
                  <n-icon v-if="item.icon" class="menu-icon" :component="item.icon" />
                  <span class="menu-label">{{ item.label }}</span>
                </div>

                <!-- 可展开父菜单项 -->
                <div v-else class="menu-item-parent">
                  <div
                    class="menu-item has-children"
                    :class="{ active: isParentActive(item) }"
                    @click="toggleItem(item.key)"
                  >
                    <n-icon v-if="item.icon" class="menu-icon" :component="item.icon" />
                    <span class="menu-label">{{ item.label }}</span>
                    <n-icon
                      class="group-arrow item-arrow"
                      :component="isItemExpanded(item.key) ? ChevronUpOutline : ChevronDownOutline"
                    />
                  </div>

                  <div v-show="isItemExpanded(item.key)" class="sub-menu">
                    <div
                      v-for="sub in item.children"
                      :key="sub.key"
                      class="menu-item sub-menu-item"
                      :class="{ active: activeKey === sub.key }"
                      @click="handleMenuClick(sub.key)"
                    >
                      <n-icon v-if="sub.icon" class="menu-icon sub-menu-icon" :component="sub.icon" />
                      <span class="menu-label">{{ sub.label }}</span>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>
    </n-layout-sider>

    <!-- 右侧内容 -->
    <n-layout-content class="settings-content">
      <!-- 页面级极光（不随内容滚动，与校招管控 .cc-aurora 同源） -->
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
import { computed, ref, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { Component } from 'vue'
import {
  NIcon,
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NTooltip,
} from 'naive-ui'
import {
  PersonCircleOutline,
  BusinessOutline,
  PeopleOutline,
  BookOutline,
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
  ChevronBackOutline,
  ChevronForwardOutline,
  ColorPaletteOutline,
  LocationOutline,
  VideocamOutline,
  MailOutline,
  ShieldCheckmarkOutline,
  PeopleCircleOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

// 设置侧边栏折叠状态
const collapsed = ref(false)

interface MenuItem {
  key: string
  label: string
  icon?: Component
  children?: MenuItem[]
}

interface MenuGroup {
  key: string
  label: string
  children: MenuItem[]
}

// 子菜单：分组结构（按产品最新设置架构）
const subMenuOptions: MenuGroup[] = [
  {
    key: 'group-basic',
    label: '基本信息',
    children: [
      { key: '/settings/account', label: '个人信息管理', icon: PersonCircleOutline },
      {
        key: '/settings/company-mgmt',
        label: '公司信息管理',
        icon: BusinessOutline,
        children: [
          { key: '/settings/company', label: '公司信息', icon: BusinessOutline },
          { key: '/settings/company/address', label: '公司地址', icon: LocationOutline },
          { key: '/settings/company/meeting-rooms', label: '公司会议室', icon: VideocamOutline },
          { key: '/settings/company/resume-mailbox', label: '接收简历邮箱', icon: MailOutline },
          { key: '/settings/company/brand', label: '品牌信息管理', icon: ColorPaletteOutline },
        ],
      },
      {
        key: '/settings/org-mgmt',
        label: '组织信息管理',
        icon: PeopleOutline,
        children: [
          { key: '/settings/department', label: '组织职责管理', icon: BusinessOutline },
          { key: '/settings/permissions', label: '角色管理', icon: ShieldCheckmarkOutline },
          { key: '/settings/user-management', label: '团队成员管理', icon: PeopleOutline },
          { key: '/settings/user-groups', label: '用户组管理', icon: PeopleCircleOutline },
        ],
      },
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
      { key: '/settings/company-library', label: '公司库', icon: BusinessOutline },
      { key: '/settings/school-library', label: '院校库', icon: SchoolOutline },
      { key: '/settings/dynamic-fields', label: '动态字段', icon: ConstructOutline },
      { key: '/settings/scraped-resumes', label: '我找的简历', icon: SearchOutline },
      { key: '/settings/data-dashboard', label: '数据中心', icon: AnalyticsOutline },
      { key: '/settings/external', label: '对外接口', icon: ServerOutline },
      { key: '/settings/public', label: '公共设置', icon: CloudUploadOutline },
    ],
  },
]

// 扁平化所有叶子节点（折叠态用）
const flatMenuItems = computed<MenuItem[]>(() => {
  const result: MenuItem[] = []
  function walk(items: MenuItem[]) {
    for (const item of items) {
      if (item.children?.length) {
        walk(item.children)
      } else {
        result.push(item)
      }
    }
  }
  subMenuOptions.forEach(g => walk(g.children))
  return result
})

// 查找当前路由所在的 group / 父级 item，用于自动展开
function findLeafContext(path: string) {
  for (const group of subMenuOptions) {
    for (const item of group.children) {
      if (item.key === path) return { group, parent: undefined as MenuItem | undefined }
      if (item.children?.length) {
        for (const sub of item.children) {
          if (sub.key === path) return { group, parent: item }
        }
      }
    }
  }
  return null
}

// 顶级分组展开状态
const expandedKeys = ref<string[]>([])
function isGroupExpanded(key: string) {
  return expandedKeys.value.includes(key)
}
function toggleGroup(key: string) {
  if (isGroupExpanded(key)) {
    expandedKeys.value = expandedKeys.value.filter(k => k !== key)
  } else {
    expandedKeys.value = [...expandedKeys.value, key]
  }
}

// 二级可展开项状态
const expandedItemKeys = ref<string[]>([])
function isItemExpanded(key: string) {
  return expandedItemKeys.value.includes(key)
}
function toggleItem(key: string) {
  if (isItemExpanded(key)) {
    expandedItemKeys.value = expandedItemKeys.value.filter(k => k !== key)
  } else {
    expandedItemKeys.value = [...expandedItemKeys.value, key]
  }
}

function isParentActive(item: MenuItem) {
  return item.children?.some(sub => sub.key === activeKey.value) ?? false
}

// 进入页面或路由变化时，自动展开当前路由所在的分组与父级菜单
function expandCurrentContext() {
  const ctx = findLeafContext(route.path)
  if (!ctx) return
  if (ctx.group && !isGroupExpanded(ctx.group.key)) {
    expandedKeys.value = [...expandedKeys.value, ctx.group.key]
  }
  if (ctx.parent && !isItemExpanded(ctx.parent.key)) {
    expandedItemKeys.value = [...expandedItemKeys.value, ctx.parent.key]
  }
}

watch(() => route.path, expandCurrentContext, { immediate: true })

// 当前路由对应的菜单 key —— 优化：computed 兜底 + optimisticKey 覆盖
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
  height: 100%;
  background: transparent;
  overflow: hidden;
}

/* 左侧子菜单栏 —— 玻璃面板 */
.settings-sider {
  background: var(--glass-bg-panel) !important;
  backdrop-filter: blur(var(--glass-blur-panel)) !important;
  -webkit-backdrop-filter: blur(var(--glass-blur-panel)) !important;
  border-right: none !important;
}
.sider-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px 20px;
  border-bottom: 1px solid var(--border-hairline);
  background: var(--glass-bg-panel);
  backdrop-filter: blur(var(--glass-blur-panel));
  -webkit-backdrop-filter: blur(var(--glass-blur-panel));
}
.sider-header.collapsed {
  justify-content: center;
  padding: 16px 8px 12px;
}
.sider-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}
.collapse-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: transparent;
  border: 1px solid transparent;
  color: var(--ink-soft);
  cursor: pointer;
  font-size: 16px;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.collapse-btn:hover {
  background: var(--brand-tint);
  color: var(--brand);
  border-color: var(--glass-border);
}
.collapse-btn.collapsed {
  width: 32px;
  height: 32px;
}

.settings-menu {
  padding: 8px 0 16px;
}
.settings-menu.collapsed {
  padding: 8px 0;
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
  flex-shrink: 0;
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

/* 可展开父菜单项 */
.menu-item.has-children {
  padding-left: 20px;
  justify-content: flex-start;
}
.menu-item.has-children .menu-label {
  flex: 1;
}
.item-arrow {
  margin-left: auto;
}

/* 三级子菜单 */
.sub-menu {
  overflow: hidden;
}
.sub-menu-item {
  padding: 9px 20px 9px 56px;
  font-size: 13px;
}
.sub-menu-icon {
  font-size: 15px;
}

/* 折叠态：图标居中，无文字 */
.menu-item--collapsed {
  justify-content: center;
  padding: 12px 0;
}
.menu-item--collapsed .menu-icon {
  margin: 0;
}
.menu-item--collapsed.active::before {
  top: 6px;
  bottom: 6px;
}

/* 激活态：品牌浅底 + 品牌字 + 左侧 3px accent bar */
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

/* 右侧内容区 */
.settings-content {
  position: relative;
  padding: 0;
  margin-left: 16px;
  overflow: hidden; /* 外层不滚动，交给内部 .settings-scroll，极光才能固定 */
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: transparent;
}
/* 内部滚动容器：承载各设置页，极光在其下层固定不动 */
.settings-scroll {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 20px;
}
/* 设置子页根容器（.page-container / .cc-page 等）的 padding 已由本容器统一提供，
   避免与全局 .page-container 的 24px 叠加成双重间距 */
.settings-scroll :deep(.page-container),
.settings-scroll :deep(.cc-page) {
  padding: 0;
  min-height: 100%;
}
</style>
