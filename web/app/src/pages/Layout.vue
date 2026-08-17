<template>
  <div class="app-layout">
    <!-- 侧边栏（左侧竖排模式） -->
    <n-layout-sider
      v-if="menuLayout === 'side'"
      bordered
      :width="240"
      :collapsed-width="64"
      show-trigger
      collapse-mode="width"
      :collapsed="collapsed"
      :native-scrollbar="false"
      class="bg-gray-900 app-sider"
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div class="logo-container">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.48 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
            </svg>
          </div>
          <span v-if="!collapsed" class="logo-text text-white text-lg font-semibold whitespace-nowrap">ATS招聘系统</span>
        </div>
      </div>

      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="selectedKey"
        :expanded-keys="expandedKeys"
        :inverted="true"
        :theme-overrides="menuThemeOverrides"
        class="bg-gray-900"
        @update:value="handleMenuClick"
        @update:expanded-keys="onExpandedKeysChange"
      />
    </n-layout-sider>

    <!-- 主体 -->
    <div class="main-area">
      <!-- 头部 -->
      <n-layout-header bordered class="bg-white px-6 flex items-center justify-between h-16">
        <!-- 左集群 -->
        <div class="flex items-center gap-4 min-w-0" :class="menuLayout === 'top' ? 'flex-1' : ''">
          <!-- 顶部横排：Logo -->
          <div v-if="menuLayout === 'top'" class="top-logo flex items-center gap-2 shrink-0">
            <div class="logo-icon">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.48 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
              </svg>
            </div>
            <span class="text-base font-semibold text-gray-800 whitespace-nowrap">ATS招聘系统</span>
          </div>

          <!-- 顶部横排：水平菜单 -->
          <n-menu
            v-if="menuLayout === 'top'"
            mode="horizontal"
            :options="menuOptions"
            :value="selectedKey"
            :theme-overrides="topMenuThemeOverrides"
            class="top-menu flex-1 min-w-0"
            @update:value="handleMenuClick"
          />

          <!-- 左侧竖排：搜索框在左 -->
          <n-button v-if="menuLayout === 'side'" text class="layout-header__search-trigger shrink-0" aria-label="全局搜索" @click="onSearchClick">
            <div class="search-box flex items-center gap-2 px-3 py-1.5 rounded-md bg-gray-100 w-80 cursor-pointer">
              <n-icon :component="SearchOutline" />
              <span class="flex-1 text-sm text-gray-500 text-left">搜索候选人、职位、需求...</span>
              <span class="text-xs text-gray-400 kbd-hint">⌘K</span>
            </div>
          </n-button>
        </div>

        <!-- 右集群 -->
        <div class="flex items-center gap-4 shrink-0">
          <!-- 顶部横排：搜索框在右 -->
          <n-button v-if="menuLayout === 'top'" text class="layout-header__search-trigger" aria-label="全局搜索" @click="onSearchClick">
            <div class="search-box flex items-center gap-2 px-3 py-1.5 rounded-md bg-gray-100 w-72 cursor-pointer">
              <n-icon :component="SearchOutline" />
              <span class="flex-1 text-sm text-gray-500 text-left">搜索候选人、职位、需求...</span>
              <span class="text-xs text-gray-400 kbd-hint">⌘K</span>
            </div>
          </n-button>

          <n-badge :value="5" :max="99">
            <n-button text aria-label="通知" @click="goToNotifications">
              <n-icon :component="NotificationsOutline" :size="20" />
            </n-button>
          </n-badge>

          <n-dropdown :options="userMenuOptions" trigger="click" @select="handleUserMenu">
            <div class="flex items-center gap-2 cursor-pointer">
              <n-avatar :size="36" round class="bg-primary text-gray-900 font-semibold">
                {{ userStore.user?.realName?.[0] || 'A' }}
              </n-avatar>
              <div class="flex flex-col leading-tight">
                <span class="text-sm font-medium text-gray-800">{{ userStore.user?.realName || '管理员' }}</span>
                <span class="text-xs text-gray-500">{{ userStore.user?.roleType === 'SUPER_ADMIN' ? '超级管理员' : '用户' }}</span>
              </div>
            </div>
          </n-dropdown>
        </div>
      </n-layout-header>

      <!-- 内容区 -->
      <div class="bg-gray-50 layout-content">
        <div class="content-wrapper p-6">
          <router-view />
        </div>
      </div>

      <!-- ⌘K 全局搜索 Modal -->
      <n-modal
        v-model:show="globalSearchOpen"
        preset="card"
        :bordered="false"
        :mask-closable="true"
        :show-icon="false"
        class="global-search-modal"
        style="width: 600px; max-width: 90vw;"
      >
        <GlobalSearch />
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, h, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, NIcon, NModal } from 'naive-ui'
import {
  SpeedometerOutline,
  DocumentTextOutline,
  PeopleOutline,
  PersonAddOutline,
  CalendarOutline,
  GiftOutline,
  TrendingUpOutline,
  NotificationsOutline,
  CogOutline,
  LogOutOutline,
  SearchOutline,
  ShareSocialOutline,
  PersonOutline,
  SettingsOutline,
} from '@vicons/ionicons5'
import GlobalSearch from '../components/common/GlobalSearch.vue'
import { useUserStore } from '../stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const message = useMessage()

const collapsed = ref(false)

// === 全局搜索 Modal（⌘K / Ctrl+K 打开，Esc 关闭） ===
const globalSearchOpen = ref(false)

function onSearchClick() {
  globalSearchOpen.value = true
}

function onKeydown(e: KeyboardEvent) {
  // ⌘K (mac) / Ctrl+K (其他平台) — 打开全局搜索
  if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault()
    globalSearchOpen.value = !globalSearchOpen.value
    return
  }
  // Esc 关闭已打开的搜索
  if (e.key === 'Escape' && globalSearchOpen.value) {
    globalSearchOpen.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})

// 菜单主题覆盖 —— 适配深色侧边栏（配合 :inverted="true"）
// Naive UI inverted 模式用 *Inverted 后缀的变量，否则覆盖无效
const menuThemeOverrides = {
  // 未选中：白色透明
  itemTextColorInverted: 'rgba(255, 255, 255, 0.88)',
  itemTextColorHoverInverted: '#ffffff',
  itemIconColorInverted: 'rgba(255, 255, 255, 0.88)',
  itemIconColorHoverInverted: '#ffffff',

  // 选中态：品牌金文字 + 30% 金色背景（更高对比度）
  itemTextColorActiveInverted: '#FBCE5B',
  itemTextColorActiveHoverInverted: '#FBCE5B',
  itemIconColorActiveInverted: '#FBCE5B',
  itemIconColorActiveHoverInverted: '#FBCE5B',
  itemColorActiveInverted: 'rgba(251, 206, 91, 0.18)',
  itemColorActiveHoverInverted: 'rgba(251, 206, 91, 0.28)',
  itemColorActiveCollapsedInverted: 'rgba(251, 206, 91, 0.18)',

  // 子项激活：金色
  itemTextColorChildActiveInverted: '#FBCE5B',
  itemTextColorChildActiveHoverInverted: '#FBCE5B',
  itemIconColorChildActiveInverted: '#FBCE5B',
  itemIconColorChildActiveHoverInverted: '#FBCE5B',

  // 箭头 / 分组
  arrowColorInverted: 'rgba(255, 255, 255, 0.6)',
  arrowColorHoverInverted: '#ffffff',
  arrowColorActiveInverted: '#FBCE5B',
  arrowColorChildActiveInverted: '#FBCE5B',
  groupTextColorInverted: 'rgba(255, 255, 255, 0.5)',

  borderRadius: '6px',
}

// 顶部横排菜单：浅色主题（header 为白底，用深色文字 + 金色激活）
const topMenuThemeOverrides = {
  itemTextColor: '#374151',
  itemTextColorHover: '#111827',
  itemTextColorActive: '#C8961A',
  itemTextColorActiveHover: '#C8961A',
  itemIconColor: '#6b7280',
  itemIconColorHover: '#374151',
  itemIconColorActive: '#C8961A',
  itemColorActive: 'rgba(251, 206, 91, 0.18)',
  itemColorActiveHover: 'rgba(251, 206, 91, 0.28)',
  itemColorActiveCollapsed: 'rgba(251, 206, 91, 0.18)',
  itemTextColorChildActive: '#C8961A',
  itemTextColorChildActiveHover: '#C8961A',
  itemIconColorChildActive: '#C8961A',
  itemColorActiveTop: 'rgba(251, 206, 91, 0.18)',
  itemColorActiveHoverTop: 'rgba(251, 206, 91, 0.28)',
  borderRadius: '6px',
}

const menuLayout = computed<'side' | 'top'>(() =>
  userStore.uiSettings?.menuLayout === 'top' ? 'top' : 'side',
)

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = [
  { key: '/dashboard', label: '工作台', icon: renderIcon(SpeedometerOutline) },
  { key: '/demands', label: '需求管理', icon: renderIcon(DocumentTextOutline) },
  { key: '/positions', label: '职位管理', icon: renderIcon(PeopleOutline) },
  {
    key: 'candidate',
    label: '候选人',
    icon: renderIcon(PersonAddOutline),
    children: [
      { key: '/candidates', label: '候选人管理' },
      { key: '/screenings', label: '简历筛选' },
      { key: '/talent-pool', label: '人才库' },
      { key: '/my-resumes', label: '我找的简历' },
    ],
  },
  {
    key: 'interview',
    label: '面试管理',
    icon: renderIcon(CalendarOutline),
    children: [
      { key: '/interviews', label: '面试安排' },
      { key: '/invitations', label: '邀约中心' },
    ],
  },
  {
    key: 'offer',
    label: 'Offer管理',
    icon: renderIcon(GiftOutline),
    children: [
      { key: '/offers', label: 'Offer列表' },
      { key: '/onboardings', label: '待入职' },
    ],
  },
  { key: '/referral', label: '内推中心', icon: renderIcon(ShareSocialOutline) },
  { key: '/report', label: '数据中心', icon: renderIcon(TrendingUpOutline) },
  { key: '/settings/account', label: '设置', icon: renderIcon(SettingsOutline) },
]

const userMenuOptions = computed(() => {
  const current = menuLayout.value
  return [
    { key: 'profile', label: '个人中心', icon: renderIcon(PersonOutline) },
    { key: 'settings', label: '账号设置', icon: renderIcon(CogOutline) },
    { type: 'divider', key: 'd1' },
    {
      key: 'menu-side',
      label: (current === 'side' ? '✓ ' : '') + '菜单：左侧竖排',
    },
    {
      key: 'menu-top',
      label: (current === 'top' ? '✓ ' : '') + '菜单：顶部横排',
    },
    { type: 'divider', key: 'd2' },
    { key: 'logout', label: '退出登录', icon: renderIcon(LogOutOutline) },
  ]
})

// 当前选中菜单项
// 优化方案：computed 兜底（路由 commit 后），optimisticKey 覆盖（点击时立即更新）
// 这样菜单的 :value 在 click handler 同步阶段就已切到目标 key，路由异步过程中
// 不再"看到旧的 A 高亮 100ms"——消除闪烁
const optimisticKey = ref('')
const optimisticTimer = ref<number>()

const selectedKey = computed(() => {
  if (optimisticKey.value) return optimisticKey.value
  if (route.path.startsWith('/settings')) return '/settings/account'
  return route.path
})
const expandedKeys = ref<string[]>([])

// 路由变化时自动展开父菜单
watch(
  () => route.path,
  (path) => {
    // 路由真正 commit 后，清掉 optimisticKey（避免手动改 URL 时被卡住）
    if (optimisticTimer.value) {
      window.clearTimeout(optimisticTimer.value)
      optimisticTimer.value = undefined
    }
    optimisticKey.value = ''
    // 找 path 在哪一层父级
    for (const item of menuOptions as any[]) {
      if (item.children) {
        for (const child of item.children) {
          if (child.children) {
            for (const grand of child.children) {
              if (grand.children) {
                for (const g of grand.children) {
                  if (g.key === path) {
                    expandedKeys.value = Array.from(new Set([...expandedKeys.value, item.key, child.key, grand.key]))
                  }
                }
              } else if (child.key === path || grand.key === path) {
                expandedKeys.value = Array.from(new Set([...expandedKeys.value, item.key, child.key]))
              }
            }
          } else if (child.key === path) {
            expandedKeys.value = Array.from(new Set([...expandedKeys.value, item.key]))
          }
        }
      }
    }
  },
  { immediate: true }
)

function onExpandedKeysChange(keys: string[]) {
  expandedKeys.value = keys
}

function handleMenuClick(key: string) {
  if (typeof key === 'string' && key.startsWith('/')) {
    // 立即更新菜单的 value——不等路由异步 commit
    // 用 nextTick 延迟，避免在 click handler 同步上下文中触发 Naive UI slot 警告
    nextTick(() => {
      optimisticKey.value = key
    })
    // 兜底清理（万一路由被守卫拦截没 commit）
    if (optimisticTimer.value) window.clearTimeout(optimisticTimer.value)
    optimisticTimer.value = window.setTimeout(() => {
      optimisticKey.value = ''
    }, 1000)
    router.push(key)
  }
}

function goToNotifications() {
  router.push('/notifications')
}

function handleUserMenu(key: string) {
  if (key === 'settings') router.push('/settings/account')
  if (key === 'menu-side' || key === 'menu-top') {
    const layout = key === 'menu-side' ? 'side' : 'top'
    if (layout === menuLayout.value) return
    userStore.setUiSettings({ menuLayout: layout })
    message.success(layout === 'top' ? '已切换为顶部横排菜单' : '已切换为左侧竖排菜单')
    return
  }
  if (key === 'logout') {
    userStore.logout()
    message.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.bg-gray-900 {
  background-color: #1f2937;
}
.bg-gray-50 {
  background-color: #f9fafb;
}
.search-box {
  background-color: #f3f4f6;
}

/* === 全局搜索触发按钮（顶栏） === */
.layout-header__search-trigger {
  padding: 0;
  height: auto;
}

/* === 顶栏返回按钮 === */
.layout-header__back {
  color: #6b7280;
  padding: 4px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}
.layout-header__back:hover {
  color: #2563eb;
  background: #eff6ff;
}
.kbd-hint {
  padding: 1px 6px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #ffffff;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  line-height: 1.2;
}

/* === ⌘K 全局搜索 Modal === */
:deep(.global-search-modal .n-card) {
  padding: 16px 20px;
}
:deep(.global-search-modal .n-card__content) {
  padding: 0;
}

/* === Logo 尺寸约束 === */
.logo-container {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 32px;
}
.logo-icon {
  width: 32px;
  height: 32px;
  min-width: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  color: #1f2937;
  flex-shrink: 0;
}
.logo-text {
  line-height: 1;
}

/* === 顶部横排：Logo + 水平菜单 === */
.top-logo {
  height: 32px;
}
.top-logo .logo-icon {
  width: 28px;
  height: 28px;
  min-width: 28px;
}
.top-menu {
  /* 只占 header 中间区域，子项超出可滚动 */
  overflow: hidden;
}
:deep(.top-menu .n-menu-item-content) {
  transition: none !important;
}
:deep(.top-menu .n-submenu-children .n-menu-item-content--selected) {
  font-weight: 600;
}

/* === 菜单项：彻底关掉所有 transition === */
/* Naive UI 默认在 .n-menu-item-content / icon / arrow 上有 300ms background-color + color 渐变
   这导致点击切换时新旧 item 的 active 态会"叠在一起"约 300ms（视觉上的闪烁）
   用 !important 强压，避免被 Naive UI 的 cssr 覆盖 */
:deep(.n-menu-item-content),
:deep(.n-menu-item-content::before),
:deep(.n-menu-item-content .n-menu-item-content-header),
:deep(.n-menu-item-content .n-icon),
:deep(.n-menu-item-content-arrow) {
  transition: none !important;
  animation: none !important;
}

/* === 激活菜单项左侧金色 accent bar（无渐变） === */
:deep(.n-menu-item-content--selected)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: #FBCE5B;
  border-radius: 0 2px 2px 0;
  transition: none !important;
}
:deep(.n-menu-item-content) {
  position: relative;
}
:deep(.n-menu-item-content--selected) {
  font-weight: 600;
}

/* === 整个 app 限定在 viewport 内, body 不滚 === */
.app-layout {
  height: 100vh;
  display: flex;
  overflow: hidden; /* 禁止 app 整体滚动, 滚动只发生在 .content-wrapper */
}
/* 侧边栏: 固定高度, 不随内容滚动 */
.app-sider {
  height: 100vh;
  flex-shrink: 0;
}
/* 主体区域: 占满剩余宽度, 纵向 flex (header 固定 + content 填充) */
.main-area {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* === 头部固定不滚动 === */
.app-layout :deep(.n-layout-header) {
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}

/* === 主内容区: 撑开剩余, 内容溢出时内部滚 === */
.layout-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0; /* 关键 */
  overflow: hidden; /* 内容溢出时, .content-wrapper 内部滚 */
}
.content-wrapper {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: auto; /* 关键: 内容超出时这个容器内部滚, header 不滚 */
}
</style>
