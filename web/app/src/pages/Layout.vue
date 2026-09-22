<template>
  <!-- v2 液态玻璃：全局极光背景层（DESIGN.md §2 + §9 Agent Prompt #5） -->
  <div class="app-aurora">
    <div class="aurora-spot"></div>
  </div>

  <!-- P4 整改：跳转链接（a11y WCAG 2.4.1） -->
  <a class="skip-link" href="#main">跳到主内容</a>

  <n-layout has-sider class="app-layout" :class="{ 'app-layout--top': menuLayout === 'top' }">
    <!-- 侧边栏（左侧竖排模式 · v2 玻璃化 · 默认折叠 + hover 浮层展开） [T6.2] -->
    <!--
      2026-08-24 21:31 兵哥反馈：默认充满全高 + hover 展开不压缩主页面
      - :width 固定传 64（物理折叠态），CSS 类 .app-sider--floating 在 hover 时强制 width:240 + position:fixed
      - 这样 flex 容器始终按 64px 偏移算 main-area，hover 展开变浮层不占 flex 流 → main-area 不收缩
      - n-menu :collapsed=!effectiveExpanded 控制内部菜单项图标/文字显示
    -->
    <n-layout-sider
      v-if="menuLayout === 'side' && !isMobile"
      :width="64"
      :native-scrollbar="false"
      :class="['glass-sidebar', 'app-sider', { 'app-sider--floating': effectiveExpanded }]"
      @mouseenter="hoverExpanded = true"
      @mouseleave="hoverExpanded = false"
    >
      <div class="logo-container">
        <div class="logo">
          <div v-if="brandStore.logoUrl" class="logo-icon logo-icon--img">
            <img :src="brandStore.logoUrl" alt="Logo" />
          </div>
          <div v-else class="logo-icon">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.48 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
            </svg>
          </div>
          <span v-if="effectiveExpanded" class="logo-text text-white text-lg font-semibold whitespace-nowrap">{{ brandStore.systemName }}</span>
        </div>
        <!-- G-2026-09-23：社会招聘 / 校园招聘 双系统切换入口（logo 下方独立行，64px 折叠宽度放不下载体 pill） -->
        <div class="logo-switch-row" :class="{ 'logo-switch-row--collapsed': !effectiveExpanded }">
          <SystemSwitcher :collapsed="!effectiveExpanded" />
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
            <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41L9.25 5.35C8.66 5.59 8.12 5.92 7.63 6.29L5.24 5.33c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94 0 .31.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" />
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
          >
            <NIcon :size="20" aria-hidden="true"><Menu /></NIcon>
          </button>
          <!-- 顶部横排：Logo -->
          <div v-if="menuLayout === 'top'" class="top-logo flex items-center gap-2 shrink-0">
            <div v-if="brandStore.logoUrl" class="logo-icon logo-icon--img">
              <img :src="brandStore.logoUrl" alt="Logo" />
            </div>
            <div v-else class="logo-icon">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.48 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
              </svg>
            </div>
            <span class="text-base font-semibold text-ink whitespace-nowrap">{{ brandStore.systemName }}</span>
            <!-- G-2026-09-23：双系统切换（top 横排：logo 右侧） -->
            <SystemSwitcher />
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
              <span class="flex-1 text-sm text-ink-faint text-left">搜索...</span>
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
              <span class="flex-1 text-sm text-ink-faint text-left">搜索...</span>
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
  MenuOutline,
  SwapVerticalOutline,
  // SettingsOutline, // 已迁移到 sider 底部 footer（不再用于 n-menu 菜单项）
} from '@vicons/ionicons5'
import { Menu, Check } from 'lucide-vue-next'
import GlobalSearch from '../components/common/GlobalSearch.vue'
import Breadcrumb from '../components/common/Breadcrumb.vue'
import SystemSwitcher from '../components/common/SystemSwitcher.vue'
import { useShortcuts } from '../composables/useShortcuts'
import { useUserStore } from '../stores/user'
import { useBrandStore } from '../stores/brand'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const brandStore = useBrandStore()

// v2.7: 全局键盘快捷键（`/` 聚焦搜索 / `?` 帮助 / `G D` 跳工作台）[T8.7]
useShortcuts()
const message = useMessage()

const collapsed = ref(true)
const hoverExpanded = ref(false)
// T11.x 主侧栏 hover-expand: 鼠标悬浮临时展开, 离开立即折叠
const effectiveExpanded = computed(() => !collapsed.value || hoverExpanded.value)
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

// header 固定定位后宽度需跟随布局模式（2026-08-24 21:31 改范式后 sider 不再影响 header：
// - hover 展开走 position: fixed 浮层，不占 flex 流，header 不再变化
// - 始终按默认折叠态 64px 偏移计算 header 位置）
const headerStyle = computed(() => {
  if (menuLayout.value === 'top') {
    return { left: '0px', width: '100vw' }
  }
  if (isMobile.value) {
    return { left: '0px', width: '100vw' }
  }
  // side 模式（桌面）: sider 折叠态 64px 偏移，hover 展开走浮层不占位
  return {
    left: '64px',
    width: 'calc(100vw - 64px)',
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
    /* ⚠️ 22:45 统一范式 + 设置按钮可见性修复：
       - top 模式没有 sider（v-if 不渲染），原 .sider-footer（设置按钮）在 main-area 里位置错乱
       - 把设置入口集成到 dropdown menu（与个人中心/账号设置等菜单项统一范式）
       - 路由跳转 /settings/account（设置主页），保留账号设置（个人中心）独立入口
       - 2026-08-25：移除「账号设置」冗余入口（与上方「设置」重复且未配置路由功能） */
    { key: '/settings/account', label: '设置', icon: renderIcon(CogOutline) },
    { type: 'divider', key: 'd1' },
    {
      key: 'menu-side',
      label: () => h('span', { style: 'display:inline-flex;align-items:center;gap:6px' }, [
        current === 'side' ? h(NIcon, { size: 14 }, { default: () => h(Check) }) : h('span', { style: 'display:inline-block;width:14px' }),
        '菜单：左侧竖排',
      ]),
      icon: renderIcon(MenuOutline),
    },
    {
      key: 'menu-top',
      label: () => h('span', { style: 'display:inline-flex;align-items:center;gap:6px' }, [
        current === 'top' ? h(NIcon, { size: 14 }, { default: () => h(Check) }) : h('span', { style: 'display:inline-block;width:14px' }),
        '菜单：顶部横排',
      ]),
      icon: renderIcon(SwapVerticalOutline),
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
  /* ⚠️ 22:45 统一范式：dropdown 加的「设置」入口，路由跳转 settings 主页
     （与「账号设置」区分：账号设置 = 个人偏好；设置 = 完整设置模块入口）
     2026-08-25：移除「账号设置」冗余入口（与「设置」重复），对应 handler 同步清理 */
  if (typeof key === 'string' && key.startsWith('/settings')) router.push(key)
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
  padding: var(--space-1);
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
  padding: var(--space-4) 20px;
}
:deep(.global-search-modal .n-card__content) {
  padding: 0;
}

/* === Logo 容器（玻璃侧栏顶部） === */
.logo-container {
  padding: var(--space-4);
  /* ⚠️ 22:14 兵哥反馈"多个容器边线"：去掉 logo 容器底部横线（var(--border-hairline)） */
  border-bottom: none !important;
}
.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
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
  overflow: hidden;
}
.logo-icon--img {
  background: transparent;
  padding: 2px;
}
.logo-icon--img img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.logo-text {
  line-height: 1;
  color: var(--ink);
}

/* === 双系统切换行（logo 下方） === */
.logo-switch-row {
  margin-top: var(--space-2);
  display: flex;
}
.logo-switch-row--collapsed {
  justify-content: center;
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
/* ⚠️ 22:20 兵哥反馈"其他按钮被压缩"：
   - Naive UI n-menu horizontal mode 默认 .n-menu-item-content 是 display:grid
   - 实测 gridTemplateColumns: "32px 23.3281px 0px" —— 第二列 label 硬限到 23.33px（auto 1fr auto 计算）
   - 中文字符（"工作台"~42px）被截断显示"工."（实测 header_w=23）
   - 即使 !important 覆盖 grid-template-columns，Vue 响应式仍会重设（实测 inline 32px 100px 0px 都失效）
   - 改用 flex 布局完全绕过 Naive UI grid 模板 —— .n-menu-item-content 由 grid 改 flex
   - icon + header 按内容撑开，菜单项按内容自然展开
   - 缩小 padding/gap 让 8 项菜单总和适应 viewport 1440（避免挤压右侧搜索框/用户区） */
.top-menu :deep(.n-menu-item-content) {
  display: flex !important;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-2) !important;
  height: 100% !important;
}
.top-menu :deep(.n-menu-item-content__icon) {
  flex-shrink: 0;
}
.top-menu :deep(.n-menu-item-content-header) {
  white-space: nowrap !important;
}
/* ⚠️ 22:20 兵哥反馈"设置按钮不可见/其他按钮被压缩"：
   - top 模式下菜单项按内容撑开后总宽超 viewport，挤压右侧搜索框+通知+用户头像
   - 缩小搜索框宽度 w-72(288) → w-48(192)，省 96px 让出空间给菜单项
   - 配合上面的菜单项 padding 缩窄，整 header 总宽 1440 内能容纳 */
.layout-header__search-trigger .search-box {
  width: 12rem !important; /* w-48 = 12rem = 192px，从 w-72 (288px) 缩到 192px */
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
   用 !important 强压，避免被 Naive UI 的 cssr 覆盖
   ⚠️ 22:09 兵哥反馈"展开时文字和图标的动效去掉"：
   - n-menu 自身 transition: background-color 0.3s（背景色过渡）
   - 子菜单展开/折叠的 Vue Transition（slide-down + fade）
   - collapsed 切换时 label fade
   全部 * 子选择器覆盖（不影响 .sider-footer 的 hover 色彩过渡） */
:deep(.n-menu),
:deep(.n-menu *),
:deep(.n-menu-item-content),
:deep(.n-menu-item-content::before),
:deep(.n-menu-item-content .n-menu-item-content-header),
:deep(.n-menu-item-content .n-icon),
:deep(.n-menu-item-content-arrow),
:deep(.n-submenu),
:deep(.n-submenu *),
:deep(.n-submenu-children),
:deep(.v-enter-active),
:deep(.v-leave-active) {
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

/* === 整个 app 限定在 viewport 内, body 不滚 ===
   2026-08-24 21:31 改范式: 用 :deep 改 Naive UI 内部 flex 容器为 grid（n-layout has-sider 时
   内部 .n-layout-scroll-container 设了 display:flex + flex-direction:row + width:100%，
   我们的 sider + main 实际是这个 flex 容器的子项，必须改它才能锁列）
   ⚠️ 21:31 修：选择器必须用 > 限定到 .app-layout 的**直接子级**，否则会污染 main-area
   内部嵌套的 .n-layout-scroll-container（让内部也变成 64px+1376px 两列布局，导致
   breadcrumb-wrap 占第 1 列 64px 把 layout-content 挤到第 2 列右侧，dashboard 内容被
   压成 64px 窄列——兵哥 21:43 截图"页面被压缩"即此因） */
.app-layout {
  height: 100dvh; /* P5 整改：100vh -> 100dvh，移动端地址栏不裁切 */
  overflow: hidden; /* 禁止 app 整体滚动, 滚动只发生在 .content-wrapper */
}
/* 改 Naive UI 直接子级 scroll-container 为 grid: 第 1 列 64px 给 sider, 第 2 列 1fr 给 main
   > 直接子级限定：避免 main-area 内部嵌套的 scroll-container 被误改（该走默认 flex column）
   ⚠️ 22:20 兵哥反馈 top 横排布局 4 个问题：
   - top 模式下没有 sider（v-if 不渲染），但 grid 模板仍分配 64px 给第 1 列
   - main-area 占第 2 列 x=64 → 主页面左侧 64px 空白 + settings-sider 错位 + 顶部菜单被挤压
   - top 模式必须取消 grid，单列布局让 main-area 占满全宽 */
.app-layout:not(.app-layout--top) > :deep(.n-layout-scroll-container) {
  display: grid !important;
  grid-template-columns: 64px calc(100vw - 64px) !important;
  width: 100% !important;
}
/* top 模式单列布局（无 sider，main-area 占满全宽，避免左侧 64px 空白） */
.app-layout.app-layout--top > :deep(.n-layout-scroll-container) {
  display: block !important;
  width: 100% !important;
}
/* 侧边栏: 2026-08-24 21:31 兵哥反馈改范式 —— 默认充满全高 + hover 浮层不压缩主页面
   - 默认（折叠）: height: 100dvh !important 充满全视口（替换原 height: auto 内容驱动）
   - hover 展开（.app-sider--floating）: position: fixed 脱离 grid 流，浮层显示 240px 宽（box-shadow 投影），
     main-area 仍占 grid 第 2 列固定 1376px 宽不变 */
.app-sider {
  height: 100dvh !important;
  flex-shrink: 0;
  overflow: visible !important; /* 让 n-menu hover 展开文字不被 sider 容器裁剪 */
  transition: none !important; /* 关闭 width 过渡, hover 瞬切避免视觉抖动 */
}
.app-sider.app-sider--floating {
  position: fixed !important;
  left: 0 !important;
  top: 0 !important;
  /* n-layout-sider inline style 写 max-width: 64px 限制 width 上限，必须一起覆盖 */
  width: 240px !important;
  max-width: 240px !important;
  height: 100dvh !important;
  z-index: 1000;
  /* ⚠️ 22:09 兵哥反馈"去掉边框"：浮层不要 box-shadow 投影（视觉边界）和 border-right（白色实线） */
  box-shadow: none !important;
  -webkit-backdrop-filter: blur(var(--glass-blur-panel));
  backdrop-filter: blur(var(--glass-blur-panel));
}
/* === v2 主侧栏：去掉背景色（兵哥反馈"背景色太突兀"）
   -------------------------------------------------------------
   改为透明，让 .app-aurora 极光底直接透出；保留 backdrop-filter
   让背后极光产生轻微模糊（与右半区视觉同源）。border-right 仍走
   全局 .glass-sidebar 的细线作为侧栏与主区的分隔（settings-sider
   仍走全局 .glass-sidebar，不动）。*/
.app-sider.glass-sidebar {
  background: transparent !important;
  /* ⚠️ 22:09 兵哥反馈"去掉边框"：全局 .glass-sidebar 自带 border-right:1px solid rgba(255,255,255,.7)，
     浮层右边显示一条白线，与极光底视觉冲突，去掉 */
  border-right: none !important;
}
/* 透明侧栏不再画顶部白罩高光（无需模拟玻璃反光） */
/* 主体区域: 占满剩余宽度, 纵向 flex (header 固定 + content 填充)
   2026-08-24 21:31 改范式后: 用 grid grid-template-columns 锁死 main-area 始终占第 2 列 1376px 宽，
   即使 sider hover 浮层展开也不变 —— 浮层叠在内容上方不占位 */
.layout-breadcrumb-wrap {
  padding: 0 var(--space-6);
  background: transparent;
}
.main-area {
  /* grid 子项: 显式 grid-column: 2 强制占第 2 列（避免 sider 切 fixed 后 grid 重排让 main 跳到第 1 列） */
  grid-column: 2;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  /* header 固定定位脱离文档流，主内容区顶部留出 header 高度 */
  padding-top: var(--space-16);
  overflow: hidden;
}
/* 兜底：n-layout-scroll-container 不存在时（无 sider 模式），直接靠 .app-layout 兜住 */
.app-layout:not(:has(.n-layout-scroll-container)) {
  display: grid;
  grid-template-columns: 64px calc(100vw - 64px);
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
  /* ⚠️ 22:35 兵哥反馈"顶部导航栏移除右侧圆角边框样式，保持边缘直角设计"：
     - 之前 border-top-left-radius: 0 + border-bottom-left-radius: 0（让 header 左下角与 sider 对齐）
     - 右侧仍是 20px 圆角（来自 .glass-panel 全局）
     - 现在 header 整宽横跨 viewport（1440px），不需要任何圆角（边缘直角）
     - 4 角都设 0，与整体页面直角风格一致 */
  border-radius: 0 !important;
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
  font-size: var(--fs-18);
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
/* ⚠️ 21:58 兵哥反馈 footer 不在最底：
   - .sider-footer 在 Naive UI 的 .n-scrollbar-content 内部
   - .n-scrollbar-content 的高度由 Naive UI JS 算为内容自然高度（实测 512px = logo 65 + menu 390 + footer 57）
   - 不是父级 .n-scrollbar-container 的 800px → footer 后面没有"剩余空间"可推
   - 即使 .n-scrollbar-content 是 flex column + .sider-menu flex:1，容器高度就是内容高度，撑不开
   - 修复：用 position:absolute 把 footer 直接钉到 .app-sider 底部，绕开 n-scrollbar 的高度约束 */
.app-sider {
  position: relative !important; /* 给 absolute footer 提供定位基准 */
}
/* ⚠️ 21:58 兵哥反馈"去掉背景色"：
   - n-menu 自带 .glass-sidebar 全局规则（background: rgba(255,255,255,.55) + blur）
   - 这导致 hover 浮层时整个侧栏呈现半透明白底+紫色极光透出（视觉上是深紫色块）
   - 改 transparent：让极光直接透出（暗色区域），侧栏视觉上是"无背景"
   - 只覆盖 .sider-menu 自身，settings-sider 全局 .glass-sidebar 不动
   ⚠️ 22:14 兵哥反馈"边线还在"：全局 .glass-sidebar 仍带 border-right:1px solid rgba(255,255,255,.7)
   → 浮层右边缘那条白线其实是 .sider-menu 的 border-right（不是 .app-sider 自身），
   → 必须再加 border-right: none 才能彻底去掉 */
.app-sider :deep(.sider-menu.glass-sidebar) {
  background: transparent !important;
  border-right: none !important;
  -webkit-backdrop-filter: none !important;
  backdrop-filter: none !important;
}
/* footer 绝对定位到 .app-sider 最底，绕开 n-scrollbar 高度约束 */
.app-sider :deep(.sider-footer) {
  position: absolute !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 2 !important; /* 在 menu 之上（如果内容超出，footer 浮在底部） */
}
.sider-footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  /* ⚠️ 22:14 兵哥反馈"多个容器边线"：去掉 footer 顶部横线（var(--border-hairline)） */
  border-top: none !important;
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
  font-size: var(--fs-14);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
}
.sider-footer--collapsed {
  justify-content: center;
  padding: var(--space-3) var(--space-2);
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
