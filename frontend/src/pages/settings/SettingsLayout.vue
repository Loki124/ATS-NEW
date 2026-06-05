<template>
  <div class="settings-layout">
    <!-- 左侧子菜单 -->
    <aside class="settings-sider">
      <div class="sider-header">
        <h2 class="sider-title">设置</h2>
      </div>
      <n-menu
        :value="activeKey"
        :options="subMenuOptions"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :indent="18"
        @update:value="handleMenuClick"
        class="settings-menu"
      />
    </aside>

    <!-- 右侧内容 -->
    <main class="settings-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, h, ref, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NIcon,
} from 'naive-ui'
import {
  PersonCircleOutline,
  PersonAddOutline,
  CheckmarkDoneOutline,
  BusinessOutline,
  PeopleOutline,
  KeyOutline,
  LockClosedOutline,
  SettingsOutline,
  BookmarkOutline,
  ClipboardOutline,
  StarOutline,
  GitNetworkOutline,
  GitBranchOutline,
  StopwatchOutline,
  ConstructOutline,
  LayersOutline,
  InformationCircleOutline,
  CloudUploadOutline,
  ServerOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// 子菜单：分组结构（与原 Layout.vue 的 系统管理 子树对齐）
const subMenuOptions = [
  {
    key: 'group-hr',
    type: 'group',
    label: '人事设置',
    children: [
      { key: '/settings/account', label: '员工信息设置', icon: renderIcon(PersonCircleOutline) },
      { key: '/settings/onboarding', label: '入职设置', icon: renderIcon(PersonAddOutline) },
      { key: '/settings/approval', label: '审批设置', icon: renderIcon(CheckmarkDoneOutline) },
    ],
  },
  {
    key: 'group-org',
    type: 'group',
    label: '组织设置',
    children: [
      { key: '/settings/department', label: '部门管理', icon: renderIcon(BusinessOutline) },
      { key: '/settings/user-management', label: '用户管理', icon: renderIcon(PeopleOutline) },
      { key: '/settings/permission', label: '权限管理', icon: renderIcon(KeyOutline) },
      { key: '/settings/mou', label: 'MOU权限管理', icon: renderIcon(LockClosedOutline) },
    ],
  },
  {
    key: 'group-process',
    type: 'group',
    label: '过程管理',
    children: [
      { key: '/settings/demand-config', label: '招聘需求设置', icon: renderIcon(ClipboardOutline) },
      { key: '/settings/dictionary', label: '数据字典', icon: renderIcon(BookmarkOutline) },
      { key: '/settings/scoring', label: '评分规则', icon: renderIcon(StarOutline) },
    ],
  },
  {
    key: 'group-speedup',
    type: 'group',
    label: '招聘提速',
    children: [
      { key: '/settings/recruitment-stage', label: '阶段模板库', icon: renderIcon(LayersOutline) },
      { key: '/settings/recruitment-process', label: '招聘流程', icon: renderIcon(GitNetworkOutline) },
      { key: '/settings/recruitment-round', label: '面试轮次', icon: renderIcon(StopwatchOutline) },
      { key: '/settings/process-management', label: '招聘流程配置 (旧)', icon: renderIcon(ConstructOutline) },
      { key: '/settings/stage', label: '招聘阶段配置 (旧)', icon: renderIcon(LayersOutline) },
    ],
  },
  {
    key: 'group-misc',
    type: 'group',
    label: '其他',
    children: [
      { key: '/settings/company', label: '公司信息', icon: renderIcon(InformationCircleOutline) },
      { key: '/settings/external', label: '对外接口', icon: renderIcon(ServerOutline) },
      { key: '/settings/public', label: '公共设置', icon: renderIcon(CloudUploadOutline) },
    ],
  },
]

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
  display: flex;
  min-height: calc(100vh - 64px); /* 减掉主 Layout 头部高度 */
  background: #fff;
}

/* 左侧子菜单栏 */
.settings-sider {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid #e5e7eb;
  background: #fafafa;
  padding: 16px 0;
  overflow-y: auto;
}
.sider-header {
  padding: 0 20px 12px;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 8px;
}
.sider-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}
.settings-menu {
  background: transparent;
}
.settings-menu :deep(.n-menu-item-content) {
  font-size: 14px;
}
.settings-menu :deep(.n-menu-item-content--selected) {
  font-weight: 600;
}

/* 关闭所有 transition —— 避免切换菜单时 active 态叠加 ~300ms 造成闪烁 */
.settings-menu :deep(.n-menu-item-content),
.settings-menu :deep(.n-menu-item-content::before),
.settings-menu :deep(.n-menu-item-content .n-icon),
.settings-menu :deep(.n-menu-item-content-arrow) {
  transition: none !important;
  animation: none !important;
}

/* 右侧内容区 */
.settings-content {
  flex: 1;
  min-width: 0; /* 防止 flex 子元素内容溢出 */
  padding: 0;
  overflow-x: auto;
}
</style>
