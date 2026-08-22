<template>
  <n-layout class="settings-layout" has-sider :sider-width="collapsed ? 64 : 220">
    <!-- 左侧子菜单 -->
    <n-layout-sider
      :width="220"
      :collapsed-width="64"
      :collapsed="collapsed"
      collapse-mode="width"
      :native-scrollbar="false"
      content-style="padding: 16px 0;"
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

        <!-- 展开态：分组菜单 -->
        <template v-else>
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
        </template>
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
  NTooltip,
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
  ChevronBackOutline,
  ChevronForwardOutline,
  ColorPaletteOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

// 设置侧边栏折叠状态
const collapsed = ref(false)

// 折叠态使用的扁平菜单项（保留原分组顺序）
const flatMenuItems = computed(() => subMenuOptions.flatMap(g => g.children))

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
  /* n-layout-scroll-container 规则已迁移到 styles/glass.css（v2 bugfix P1-A 删 :deep） */
}

/* 左侧子菜单栏 —— 玻璃面板（DESIGN.md §4 glass-panel） */
.settings-sider {
  background: var(--glass-bg-panel) !important;
  backdrop-filter: blur(var(--glass-blur-panel)) !important;
  -webkit-backdrop-filter: blur(var(--glass-blur-panel)) !important;
  border-right: none !important;
}
.sider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px 12px 20px;
  border-bottom: 1px solid var(--border-hairline);
  margin-bottom: 8px;
}
.sider-header.collapsed {
  justify-content: center;
  padding: 0 8px 12px;
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

.settings-menu.collapsed {
  padding: 0;
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

/* v2.7: 删 :deep 300 行注入 · 依赖 glass.css 全局 .n-card.n-card / .gradient-title / .n-button--primary-type 规则
   v2 bugfix P1-A：n-layout-scroll-container 子选择器已迁到 glass.css（直接子元素 > 关系，无需穿透） */
</style>
