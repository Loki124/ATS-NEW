<template>
  <!-- v2 液态玻璃：全局极光背景层（DESIGN.md §2 + §9 Agent Prompt #5） -->
  <div class="app-aurora">
    <div class="aurora-spot"></div>
  </div>

  <!-- P4 整改：跳转链接（a11y WCAG 2.4.1） -->
  <a class="skip-link" href="#main">跳到主内容</a>

  <n-layout has-sider class="app-layout">
    <!-- 侧边栏（左侧竖排模式 · v2 玻璃化 · 默认折叠 + hover 展开） [T6.2] -->
    <n-layout-sider
      v-if="menuLayout === 'side' && !isMobile"
      :width="siderWidth"
      :native-scrollbar="false"
      class="glass-sidebar app-sider"
      @mouseenter="hoverExpanded = true"
      @mouseleave="hoverExpanded = false"
    >
      <div class="logo-container">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.48 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
            </svg>
          </div>
          <span v-if="effectiveExpanded" class="logo-text text-white text-lg font-semibold whitespace-nowrap">ATS招聘系统</span>
        </div>
      </div>

      <n-menu
        :collapsed="!effectiveExpanded"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="selectedKey"
        :expanded-keys="expandedKeys"
        :theme-overrides="menuThemeOverrides"
        class="glass-sidebar sider-menu"
        @update:value="handleMenuClick"
        @update:expanded-keys="onExpandedKeysChange"
      />

      <!-- 底部 footer: 「设置」永久贴底(mt:auto 推到最底, hover 展开状态才显示文字) -->
      <div
        class="sider-footer"
        :class="{ 'sider-footer--collapsed': !effectiveExpanded, 'sider-footer--active': isOnSettingsRoute }"
        role="button"
        tabindex="0"
        aria-label="打开设置"
        @click="router.push('/settings/account')"
        @keydown.enter="router.push('/settings/account')"
      >
        <div class="sider-footer-icon">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
            <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41L9.25 5.35C8.66 5.59 8.12 5.92 7.63 6.29L5.24 5.33c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94 0 .31.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
          </svg>
        </div>
        <span v-if="effectiveExpanded" class="sider-footer-label">设置</span>
      </div>
    </n-layout-sider>

    <!-- 移动端侧栏抽屉 [T6.2] -->
    <n-drawer
      v-if="menuLayout === 'side'"
      v-model:show="mobileMenuOpen"
      :width="280"
      placement="left"
      class="mobile-sidebar-drawer"
    >
      <n-menu
        :options="menuOptions"
        :value="selectedKey"
        :expanded-keys="expandedKeys"
        :theme-overrides="menuThemeOverrides"
        @update:value="onDrawerMenu"
        @update:expanded-keys="onExpandedKeysChange"
      />
    </n-drawer>

    <!-- 主体 -->
    <n-layout class="main-area">
      <!-- 头部（v2 玻璃化 · DESIGN.md §4 Navigation） -->
      <n-layout-header :style="headerStyle" class="glass-panel glass-header px-6 flex items-center justify-between h-16">
        <!-- 左集群 -->
        <div class="flex items-center gap-4 min-w-0" :class="menuLayout === 'top' ? 'flex-1' : ''">
          <!-- 移动端汉堡按钮 [T6.2] -->
          <button
            v-if="isMobile && menuLayout === 'side'"
            class="hamburger-btn glass-input"
            aria-label="打开菜单"
            @click="mobileMenuOpen = true"
          >☰</button>
          <!-- 顶部横排：Logo -->
          <div v-if="menuLayout === 'top'" class="top-logo flex items-center gap-2 shrink-0">
            <div class="logo-icon">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.48 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
              </svg>
            </div>
            <span class="text-base font-semibold text-ink whitespace-nowrap">ATS招聘系统</span>
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

          <!-- 左侧竖排：搜索框在左（v2 玻璃化） -->
          <n-button v-if="menuLayout === 'side'" text class="layout-header__search-trigger shrink-0" aria-label="全局搜索" @click="onSearchClick">
            <div class="search-box glass-input flex items-center gap-2 w-80 cursor-pointer">
              <n-icon :component="SearchOutline" />
              <span class="flex-1 text-sm text-ink-faint text-left">搜索候选人、职位、需求...</span>
              <span class="text-xs kbd-hint">⌘K</span>
            </div>
          </n-button>
        </div>

        <!-- 右集群 -->
        <div class="flex items-center gap-4 shrink-0">
          <!-- 顶部横排：搜索框在右（v2 玻璃化） -->
          <n-button v-if="menuLayout === 'top'" text class="layout-header__search-trigger" aria-label="全局搜索" @click="onSearchClick">
            <div class="search-box glass-input flex items-center gap-2 w-72 cursor-pointer">
              <n-icon :component="SearchOutline" />
              <span class="flex-1 text-sm text-ink-faint text-left">搜索候选人、职位、需求...</span>
              <span class="text-xs kbd-hint">⌘K</span>
            </div>
          </n-button>

          <n-badge :value="5" :max="99">
            <n-button text aria-label="通知" @click="goToNotifications">
              <n-icon :component="NotificationsOutline" :size="20" />
            </n-button>
          </n-badge>

          <n-dropdown :options="userMenuOptions" trigger="click" @select="handleUserMenu">
            <div class="flex items-center gap-2 cursor-pointer">
              <n-avatar :size="36" round class="bg-primary-gradient text-white font-semibold">
                {{ userStore.user?.realName?.[0] || 'A' }}
              </n-avatar>
              <div class="flex flex-col leading-tight">
                <span class="text-sm font-medium text-ink">{{ userStore.user?.realName || '管理员' }}</span>
                <span class="text-xs text-ink-soft">{{ userStore.user?.roleType === 'SUPER_ADMIN' ? '超级管理员' : '用户' }}</span>
              </div>
            </div>
          </n-dropdown>
        </div>
      </n-layout-header>

      <!-- v2.7: 面包屑导航 [T8.5] -->
      <div class="layout-breadcrumb-wrap">
        <Breadcrumb />
      </div>

      <!-- 内容区（v2：透明背景让极光底透出） -->
      <n-layout-content class="layout-content">
        <!-- P4 整改：<main> 地标 + id=main 与 skip-link 联动（a11y WCAG 1.3.1） -->
        <main id="main" class="content-wrapper">
          <router-view />
        </main>
      </n-layout-content>

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
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, h, computed, watch, nextTick, onMounted, onUnmounted, onBeforeUnmount } from 'vue'
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
  // SettingsOutline, // 已迁移到 sider 底部 footer（不再用于 n-menu 菜单项）
} from '@vicons/ionicons5'
import GlobalSearch from '../components/common/GlobalSearch.vue'
import Breadcrumb from '../components/common/Breadcrumb.vue'
import { useShortcuts } from '../composables/useShortcuts'
import { useUserStore } from '../stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// v2.7: 全局键盘快捷键（`/` 聚焦搜索 / `?` 帮助 / `G D` 跳工作台）[T8.7]
useShortcuts()
const message = useMessage()

const collapsed = ref(true)
const hoverExpanded = ref(false)
// T11.x 主侧栏 hover-expand: 鼠标悬浮临时展开, 离开立即折叠
const effectiveExpanded = computed(() => !collapsed.value || hoverExpanded.value)
const siderWidth = computed(() => (effectiveExpanded.value ? 240 : 64))
// 「设置」footer 路由高亮: 位于 /settings/* 任意路径时点亮底色
const isOnSettingsRoute = computed(() => route.path.startsWith('/settings'))

// === 移动端响应式（≤768 折叠为 n-drawer）[T6.2]
// v2 bugfix P1-C：用 <= 768 包含边界值（严格 < 在 768 viewport 下仍判为桌面）
const isMobile = ref(false)
const mobileMenuOpen = ref(false)
function onDrawerMenu(key: string) {
  router.push(key)
  mobileMenuOpen.value = false
}
function updateIsMobile() {
  isMobile.value = window.innerWidth <= 768
}
onMounted(() => {
  updateIsMobile()
  window.addEventListener('resize', updateIsMobile)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', updateIsMobile)
})

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

// 菜单主题覆盖 —— 适配 v2 玻璃侧栏（DESIGN.md §4 Navigation）
// 浅底 + 墨色文字 + 品牌色激活（替换原金色 #FBCE5B + 深底白字 inverted 模式）
// 玻璃侧栏在深色模式下通过 CSS 变量自动切换（见 glass.css .glass-sidebar）
const menuThemeOverrides = {
  // === 未选中态（墨色 ink-soft）===
  itemTextColor: 'var(--ink-soft)',
  itemTextColorHover: 'var(--ink)',
  itemIconColor: 'var(--ink-soft)',
  itemIconColorHover: 'var(--ink)',

  // === 选中态：品牌色文字 + 品牌色浅底（更高对比度）===
  itemTextColorActive: 'var(--brand)',
  itemTextColorActiveHover: 'var(--brand)',
  itemIconColorActive: 'var(--brand)',
  itemIconColorActiveHover: 'var(--brand)',
  itemColorActive: 'var(--brand-soft)',
  itemColorActiveHover: 'var(--brand-soft)',
  itemColorActiveCollapsed: 'var(--brand-soft)',

  // === 子项激活：品牌色 ===
  itemTextColorChildActive: 'var(--brand)',
  itemTextColorChildActiveHover: 'var(--brand)',
  itemIconColorChildActive: 'var(--brand)',
  itemIconColorChildActiveHover: 'var(--brand)',

  // === 箭头 / 分组 ===
  arrowColor: 'var(--ink-faint)',
  arrowColorHover: 'var(--ink)',
  arrowColorActive: 'var(--brand)',
  arrowColorChildActive: 'var(--brand)',
  groupTextColor: 'var(--ink-faint)',

  borderRadius: '6px',
}

// 顶部横排菜单（玻璃 header 上）：浅色主题 + 品牌色激活
const topMenuThemeOverrides = {
  itemTextColor: 'var(--ink-soft)',
  itemTextColorHover: 'var(--ink)',
  itemTextColorActive: 'var(--brand)',
  itemTextColorActiveHover: 'var(--brand)',
  itemIconColor: 'var(--ink-soft)',
  itemIconColorHover: 'var(--ink)',
  itemIconColorActive: 'var(--brand)',
  itemColorActive: 'var(--brand-soft)',
  itemColorActiveHover: 'var(--brand-soft)',
  itemColorActiveCollapsed: 'var(--brand-soft)',
  itemTextColorChildActive: 'var(--brand)',
  itemTextColorChildActiveHover: 'var(--brand)',
  itemIconColorChildActive: 'var(--brand)',
  itemColorActiveTop: 'var(--brand-soft)',
  itemColorActiveHoverTop: 'var(--brand-soft)',
  borderRadius: '6px',
}

const menuLayout = computed<'side' | 'top'>(() =>
  userStore.uiSettings?.menuLayout === 'top' ? 'top' : 'side',
)

// header 固定定位后宽度需跟随侧边栏展开/折叠及移动端状态
const headerStyle = computed(() => {
  if (menuLayout.value === 'top') {
    return { left: '0px', width: '100vw' }
  }
  if (isMobile.value) {
    return { left: '0px', width: '100vw' }
  }
  const w = siderWidth.value
  return {
    left: `${w}px`,
    width: `calc(100vw - ${w}px)`,
  }
})

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
  // 设置已迁到 sider footer 永久贴底（hover 展开时显示文字）
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
/* v2 液态玻璃：移除硬编码 hex，全部走 tokens.css 变量（DESIGN.md §7 Don'ts #4）*/

/* === 全局搜索触发按钮（顶栏） === */
.layout-header__search-trigger {
  padding: 0;
  height: auto;
}

/* === 顶栏返回按钮 === */
.layout-header__back {
  color: var(--ink-soft);
  padding: 4px;
  border-radius: 6px;
  transition: color var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out);
}
.layout-header__back:hover {
  color: var(--brand);
  background: var(--brand-tint);
}

/* === ⌘K 快捷键提示 === */
.kbd-hint {
  padding: 1px 6px;
  border: 1px solid var(--border-hairline);
  border-radius: 4px;
  background: var(--surface);
  color: var(--ink-faint);
  font-family: var(--font-mono);
  line-height: 1.2;
}

/* === ⌘K 全局搜索 Modal === */
:deep(.global-search-modal .n-card) {
  padding: 16px 20px;
}
:deep(.global-search-modal .n-card__content) {
  padding: 0;
}

/* === Logo 容器（玻璃侧栏顶部） === */
.logo-container {
  padding: 16px;
  border-bottom: 1px solid var(--border-hairline);
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
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-grad-a) 100%);
  color: #ffffff;
  flex-shrink: 0;
}
.logo-text {
  line-height: 1;
  color: var(--ink);
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

/* === 激活菜单项左侧品牌色 accent bar（无渐变） === */
:deep(.n-menu-item-content--selected)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: var(--brand);
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
  height: 100dvh; /* P5 整改：100vh -> 100dvh，移动端地址栏不裁切 */
  display: flex;
  overflow: hidden; /* 禁止 app 整体滚动, 滚动只发生在 .content-wrapper */
}
/* 侧边栏: 高度由内容决定（"高度自适应页面高度" = 内容驱动，
   align-self:flex-start 阻止被拉伸到 .app-layout 的高度）；
   height:auto !important 覆盖 n-layout-sider 自带的 height:100% */
.app-sider {
  height: auto !important;
  align-self: flex-start;
  flex-shrink: 0;
}
/* === v2 主侧栏：去掉背景色（兵哥反馈"背景色太突兀"）
   -------------------------------------------------------------
   改为透明，让 .app-aurora 极光底直接透出；保留 backdrop-filter
   让背后极光产生轻微模糊（与右半区视觉同源）。border-right 仍走
   全局 .glass-sidebar 的细线作为侧栏与主区的分隔（settings-sider
   仍走全局 .glass-sidebar，不动）。*/
.app-sider.glass-sidebar {
  background: transparent !important;
}
/* 透明侧栏不再画顶部白罩高光（无需模拟玻璃反光） */
/* 主体区域: 占满剩余宽度, 纵向 flex (header 固定 + content 填充) */
.layout-breadcrumb-wrap {
  padding: 0 var(--space-6);
  background: transparent;
}
.main-area {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  /* header 固定定位脱离文档流，主内容区顶部留出 header 高度 */
  padding-top: 64px;
  overflow: hidden;
}

/* === 头部固定不滚动（v2 玻璃 header） === */
.app-layout :deep(.n-layout-header) {
  position: fixed;
  top: 0;
  z-index: var(--z-header);
  border-bottom: 1px solid var(--border-hairline);
}
/* 玻璃 header 顶部圆角与侧栏对齐：左侧贴合侧栏 0 圆角，右侧保留 */
.glass-header {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

/* === 主内容区: 撑开剩余, 内容溢出时内部滚 === */
.layout-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0; /* 关键 */
  height: 100%;
  overflow: hidden; /* 内容溢出时, .content-wrapper 内部滚 */
  background: transparent; /* 让 .app-aurora 极光底透出 */
}
.content-wrapper {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow: auto; /* 关键: 内容超出时这个容器内部滚, header 不滚 */
  padding: 0; /* 内边距下放到页面根容器（.page-container / .cc-page 等）自管 */
}

/* === T6.2 移动端响应式 === */
.hamburger-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(var(--glass-blur-input));
  -webkit-backdrop-filter: blur(var(--glass-blur-input));
  cursor: pointer;
  font-size: 18px;
  color: var(--ink);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.hamburger-btn:hover {
  background: var(--brand-soft);
}
.mobile-sidebar-drawer :deep(.n-drawer-body-content-wrapper) {
  padding: 0;
}

/* === T11 主侧栏 footer（设置固定贴底）===
   让 n-menu flex:1 占满剩余高度, footer mt:auto 推到最底 */
/* 强制 sider 内部竖向排列（n-layout-sider 默认横向）*/
.app-sider.glass-sidebar {
  display: flex !important;
  flex-direction: column !important;
}
.sider-menu {
  min-height: 0;
  /* 内容驱动: 不强制 flex:1 占满，让整个侧栏自然紧凑 */
}
.sider-footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-hairline);
  color: var(--ink-soft);
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
  outline: none;
}
.sider-footer:hover,
.sider-footer:focus-visible {
  background: var(--brand-tint);
  color: var(--brand);
}
.sider-footer:active {
  background: var(--brand-soft);
}
.sider-footer-icon {
  width: 32px;
  height: 32px;
  min-width: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: currentColor;
}
.sider-footer-label {
  font-size: 14px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
}
.sider-footer--collapsed {
  justify-content: center;
  padding: 12px 8px;
}
.sider-footer--collapsed .sider-footer-label {
  display: none;
}
/* 折叠态激活态(选中设置路由时高亮) */
.sider-footer--active {
  color: var(--brand);
  background: var(--brand-soft);
}
</style>
