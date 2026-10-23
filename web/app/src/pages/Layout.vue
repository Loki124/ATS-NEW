<template>
  <!-- v2 液态玻璃：全局极光背景层（DESIGN.md §2 + §9 Agent Prompt #5） -->
  <div class="app-aurora">
    <div class="aurora-spot"></div>
  </div>

  <!-- P4 整改：跳转链接（a11y WCAG 2.4.1） -->
  <a class="skip-link" href="#main">{{ t('pages.Layout.s1') }}</a>

  <n-layout
    has-sider
    class="app-layout"
    :class="{
      'app-layout--top': menuLayout === 'top',
      'app-layout--pinned': menuLayout === 'side' && !isMobile && siderPinned,
    }"
  >
    <!-- 侧边栏（左侧竖排模式 · v2 玻璃化 · 固定/折叠双态 + hover 浮层展开） [T6.2] -->
    <!--
      {{ t('pages.Layout.s10') }}
      {{ t('pages.Layout.s11') }}
      {{ t('pages.Layout.s12') }}
      - n-menu :collapsed=!effectiveExpanded 控制内部菜单项图标/文字显示
      - 2026-10-21：固定态（siderPinned）占位 240px；折叠态 64px 仅图标，hover 浮层展开
    -->
    <n-layout-sider
      v-if="menuLayout === 'side' && !isMobile"
      :width="siderWidth"
      :native-scrollbar="false"
      :class="['glass-sidebar', 'app-sider', { 'app-sider--pinned': siderPinned }]"
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
        :key="`sider-menu-${systemStore.current}`"
        :collapsed="!effectiveExpanded"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="selectedKey"
        :expanded-keys="expandedKeys"
        :theme-overrides="menuThemeOverrides"
        :class="['glass-sidebar', 'sider-menu', { 'sider-menu--switching': systemSwitched }]"
        @update:value="handleMenuClick"
        @update:expanded-keys="onExpandedKeysChange"
      />

      <!-- 底部一行：「设置」+ 「固定/折叠」图标按钮（2026-10-21 兵哥指令）
           固定 = 常驻 240px 并占位（主区右移）；折叠 = 64px 只显示菜单 icon。
           ⚠️ 两个要点：① 切换控件必须**放在侧栏内部**（早前做成悬浮在右缘的把手会被主区面板盖住 → 点不到）；
           ② 与「设置」同处一行、**只显示图标不带文字**（折叠态 64px 放不下文字）。 -->
      <div class="sider-footer-row" :class="{ 'sider-footer-row--collapsed': !effectiveExpanded }">
        <!-- 「设置」永久贴底(mt:auto 由外层 row 承担) -->
        <div
          class="sider-footer"
          :class="{ 'sider-footer--collapsed': !effectiveExpanded, 'sider-footer--active': isOnSettingsRoute }"
          role="button"
          tabindex="0"
          :aria-label="t('pages.Layout.s5')"
          @click="router.push('/settings/account')"
          @keydown.enter="router.push('/settings/account')"
        >
          <div class="sider-footer-icon">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
              <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41L9.25 5.35C8.66 5.59 8.12 5.92 7.63 6.29L5.24 5.33c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94 0 .31.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" />
            </svg>
          </div>
          <span v-if="effectiveExpanded" class="sider-footer-label">{{ t('pages.Layout.s2') }}</span>
        </div>

        <!-- 固定 / 折叠 切换：只显示图标（文字在 title / aria-label 里） -->
        <button
          class="sider-toggle"
          type="button"
          :aria-label="siderPinned ? t('pages.Layout.sider.collapse') : t('pages.Layout.sider.pin')"
          :title="siderPinned ? t('pages.Layout.sider.collapse') : t('pages.Layout.sider.pin')"
          @click.stop="toggleSiderPinned"
        >
          <n-icon :component="siderPinned ? PinOutline : Pin" :size="18" />
        </button>
      </div>
    </n-layout-sider>

    <!-- 2026-10-21 (整改卡 E2 · AGENTS.md R-224): 移动端侧栏回改居中弹窗。
         原为 placement="left" 的侧滑抽屉 (响应式导航 [T6.2]); 按「默认 = 居中,
         例外 = 抽屉」统一回改, 菜单内容 / 选中 / 展开交互保持不变,
         内容区零内边距沿用原视觉 (见 .mobile-sidebar-drawer 样式)。 -->
    <n-modal
      v-if="menuLayout === 'side'"
      v-model:show="mobileMenuOpen"
      preset="card"
      :style="{ width: '280px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(520px, calc(88vh - 180px))', overflowY: 'auto', padding: '0' }"
      :mask-closable="false"
      :bordered="false"
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
    </n-modal>

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
            :aria-label="t('pages.Layout.s6')"
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
            :key="`top-menu-${systemStore.current}`"
            mode="horizontal"
            :options="menuOptions"
            :value="selectedKey"
            :theme-overrides="topMenuThemeOverrides"
            :class="['top-menu', 'flex-1', 'min-w-0', { 'sider-menu--switching': systemSwitched }]"
            @update:value="handleMenuClick"
          />

          <!-- 左侧竖排：搜索框在左（v2 玻璃化） -->
          <n-button v-if="menuLayout === 'side'" text class="layout-header__search-trigger shrink-0" :aria-label="t('pages.Layout.s7')" @click="onSearchClick">
            <div class="search-box glass-input flex items-center gap-2 w-80 cursor-pointer">
              <n-icon :component="SearchOutline" />
              <span class="flex-1 text-sm text-ink-faint text-left">{{ t('pages.Layout.s3') }}</span>
              <span class="text-xs kbd-hint">⌘K</span>
            </div>
          </n-button>
        </div>

        <!-- 右集群 -->
        <div class="flex items-center gap-4 shrink-0">
          <!-- 顶部横排：搜索框在右（v2 玻璃化） -->
          <n-button v-if="menuLayout === 'top'" text class="layout-header__search-trigger" :aria-label="t('pages.Layout.s8')" @click="onSearchClick">
            <div class="search-box glass-input flex items-center gap-2 w-72 cursor-pointer">
              <n-icon :component="SearchOutline" />
              <span class="flex-1 text-sm text-ink-faint text-left">{{ t('pages.Layout.s4') }}</span>
              <span class="text-xs kbd-hint">⌘K</span>
            </div>
          </n-button>

          <!-- 通知中心铃铛：按功能权限显隐（2026-10-20 补登记；canAccess fail-open，
               未配置功能权限的账号恒可见，与菜单裁剪语义一致） -->
          <n-badge v-if="canAccess('recruit:notification:menu:view')" :value="5" :max="99">
            <n-button text :aria-label="t('pages.Layout.s9')" @click="goToNotifications">
              <n-icon :component="NotificationsOutline" :size="20" />
            </n-button>
          </n-badge>

          <n-dropdown
            :options="userMenuOptions"
            :menu-props="() => ({ class: 'user-menu-dropdown' })"
            trigger="click"
            @select="handleUserMenu"
          >
            <div class="flex items-center gap-2 cursor-pointer">
              <n-avatar :size="36" round class="bg-primary-gradient text-white font-semibold">
                {{ userStore.user?.realName?.[0] || 'A' }}
              </n-avatar>
              <div class="flex flex-col leading-tight">
                <span class="text-sm font-medium text-ink">{{ userStore.user?.realName || t('pages.Layout.s13') }}</span>
                <span class="text-xs text-ink-soft">{{ userStore.user?.roleType === 'SUPER_ADMIN' ? t('pages.Layout.s14') : t('pages.Layout.s15') }}</span>
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
import { useI18n } from 'vue-i18n'
import { ref, h, computed, watch, nextTick, onMounted, onUnmounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, NIcon, NModal, NSwitch } from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import { usePermission } from '../composables/usePermission'
import { filterMenuByPermission } from '../utils/permissionMenu'
import {
  SpeedometerOutline,
  DocumentTextOutline,
  PeopleOutline,
  PersonAddOutline,
  CalendarOutline,
  TrendingUpOutline,
  NotificationsOutline,
  CogOutline,
  LogOutOutline,
  SearchOutline,
  PersonOutline,
  MenuOutline,
  SwapVerticalOutline,
  LanguageOutline,
  ClipboardOutline,
  Pin,
  PinOutline,
  // SettingsOutline, // 已迁移到 sider 底部 footer（不再用于 n-menu 菜单项）
} from '@vicons/ionicons5'
import { MenuOutline as Menu, CheckmarkOutline as Check } from '@vicons/ionicons5'
import GlobalSearch from '../components/common/GlobalSearch.vue'
import Breadcrumb from '../components/common/Breadcrumb.vue'
import SystemSwitcher from '../components/common/SystemSwitcher.vue'
import { useShortcuts } from '../composables/useShortcuts'
import { currentLocale } from '../locales'
import { useUserStore } from '../stores/user'
import { useBrandStore } from '../stores/brand'
import { useSystemStore } from '../stores/system'
const { t } = useI18n()

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const brandStore = useBrandStore()

// v2.7: 全局键盘快捷键（`/` 聚焦搜索 / `?` 帮助 / `G D` 跳工作台）[T8.7]
useShortcuts()
const message = useMessage()

const collapsed = ref(true)
// 2026-10-21 兵哥指令：侧栏「固定 / 折叠」双态
//   - 固定（pinned）：侧栏常驻 240px 并占位，主区整体右移；
//   - 折叠（默认）：64px 只显示一级菜单 icon，**悬停分组图标 → 右侧浮出该组二级菜单**
//     （naive-ui 原生 dropdown：菜单 collapsed 时 Submenu 自动启用浮出，VS Code 式）。
//   ⚠️ 原先的「鼠标悬停整个侧栏就整体展开」（peek）已下线：它会让菜单进入展开态，
//      正好顶掉上面的原生浮出能力 —— 折叠态就永远看不到二级菜单了（兵哥反馈）。
// 状态存 userStore.uiSettings.siderPinned（跟账号走，刷新/换设备保持）。
const siderPinned = computed(() => userStore.uiSettings?.siderPinned === true)
const SIDER_WIDTH_EXPANDED = 240
const SIDER_WIDTH_COLLAPSED = 64
const siderWidth = computed(() => (siderPinned.value ? SIDER_WIDTH_EXPANDED : SIDER_WIDTH_COLLAPSED))
/** 菜单项内容（icon + 文字）是否展开显示：只有固定态才展开，折叠态交给原生浮出 */
const effectiveExpanded = computed(() => siderPinned.value)

function toggleSiderPinned() {
  userStore.setUiSettings({ siderPinned: !siderPinned.value })
}
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

// G-2026-09-23（2026-10-19 兵哥调整）：菜单按系统差异（双系统）。社招/校招共享主功能菜单；校招模式额外追加
// 两个一级入口：「校招生管理」分组（轮岗安排/轮岗资源/客服部门/班级管理/人员管理）+「编制管控」叶子菜单。
// 原「校园招聘」分组壳已拆散；「校园大使/宣讲会」迁移到系统设置「雇主品牌」分组。切换系统时菜单实时刷新（computed 依赖 systemStore）。
const systemStore = useSystemStore()
const { canAccess } = usePermission()
const menuOptions = computed(() => {
  const base = [
    { key: '/dashboard', label: '工作台', icon: renderIcon(SpeedometerOutline) },
    {
      key: 'demand-position',
      label: '需求与职位',
      icon: renderIcon(DocumentTextOutline),
      children: [
        { key: '/demands', label: '需求管理' },
        { key: '/positions', label: '职位管理' },
      ],
    },
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
    { key: '/report', label: '数据中心', icon: renderIcon(TrendingUpOutline) },
    // 设置已迁到 sider footer 永久贴底（hover 展开时显示文字）
  ]
  if (systemStore.isCampus) {
    // 校招生管理：轮岗 / 班级 / 档案等校招运营功能汇总分组（兵哥 2026-10-19 调整）
    base.push({
      key: 'campus-recruit-mgmt',
      label: '校招生管理',
      icon: renderIcon(PeopleOutline),
      children: [
        { key: '/campus/rotation-arrangement', label: '轮岗安排' },
        // 2026-10-21 兵哥：轮岗资源合并为单入口，页签承载 BU汇总 / 直播间 / 客服部门
        { key: '/campus/rotation-resource', label: '轮岗资源' },
        { key: '/campus/class-room', label: '班级管理' },
        // 2026-10-21 兵哥：菜单名由「校招生档案」更名为「人员管理」
        { key: '/campus/person', label: '人员管理' },
        // 2026-10-23 校招生全生命周期移植（逆向自 workbuddy.link《校招生管理系统》演示环境）：
        // 考核域 / 学习与社区 / 定岗与结算 / 批次规则，共 12 个新入口。
        // 顺序按「培养 → 考核 → 定岗 → 经营」的业务流排列，便于按角色只开一段。
        { key: '/campus/assessment', label: '轮岗考核' },
        { key: '/campus/attendance', label: '考勤管理' },
        { key: '/campus/monthly-report', label: '月报管理' },
        { key: '/campus/feedback', label: '反馈记录' },
        { key: '/campus/course', label: '课程管理' },
        { key: '/campus/exam', label: '考试管理' },
        { key: '/campus/activity', label: '活动竞技' },
        { key: '/campus/forum', label: '交流论坛' },
        { key: '/campus/placement', label: '定岗双选' },
        { key: '/campus/placement-track', label: '定岗跟踪' },
        { key: '/campus/settlement', label: '交易和结算' },
        { key: '/campus/batch-rule', label: '批次规则' },
      ],
    })
    // 编制管控（原「校招管控」，2026-10-19 更名）：campus 模式下的一级叶子菜单（路由 /campus/control，已脱离 settings）
    base.push({
      key: '/campus/control',
      label: '编制管控',
      icon: renderIcon(ClipboardOutline),
    })
  }
  // G4: 按功能权限裁剪菜单（fail-open：未配置功能权限时全部可见）
  return filterMenuByPermission(base as MenuOption[], canAccess) as any[]
})

// 2026-10-21 兵哥反馈「系统切换导致页面波动」：
// 社招 ↔ 校招 切换时侧栏菜单会整组增删（「校招生管理」分组 + 「编制管控」），
// 条目逐个弹出 / 消失会造成明显跳动。这里在**切换之后**给菜单加一次性淡入动画，
// 让整块菜单作为一个整体重绘 —— 视觉上只剩「淡入」，而不是「抖」。
// ⚠️ 实现要点：n-menu 上用 :key="systemStore.current" 强制重建节点，
//    Vue 在新节点插入 DOM 时会重放 CSS animation（首次挂载不播，靠 systemSwitched 兜住）。
const systemSwitched = ref(false)
watch(
  () => systemStore.current,
  () => {
    systemSwitched.value = true
  },
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
  // side 模式（桌面）: 折叠态 64px 偏移；固定态 240px 偏移（主区整体右移）
  const offset = siderPinned.value ? SIDER_WIDTH_EXPANDED : SIDER_WIDTH_COLLAPSED
  return {
    left: `${offset}px`,
    width: `calc(100vw - ${offset}px)`,
  }
})

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}


/**
 * 下拉行：图标 + 文字 + 右侧控件（**全部自绘**）。
 * 为什么不用 naive 的 icon prop：naive 的 prefix 图标列宽会随「同组兄弟有没有图标」变化
 * （有图标 32px / 无图标半宽 / 无图标的普通项 14px）⇒ 行与行左缘天然对不齐，
 * 表现就是「歪歪扭扭」。这里把 naive 的 prefix 槽归零、图标文字自绘，
 * 与系统切换器（sys-switch-dropdown 紧凑变体）同一套路，列宽由网格固定。
 */
const userMenuRow = (icon: any, labelText: string, control?: any) =>
  h('div', { class: 'user-menu-row' }, [
    h(NIcon, { size: 18, class: 'user-menu-row-icon' }, { default: () => h(icon) }),
    h('span', { class: 'user-menu-row-label' }, labelText),
    control ? h('span', { class: 'user-menu-row-control' }, [control]) : null,
  ])

const userMenuOptions = computed(() => {
  const current = menuLayout.value
  return [
    // 账户
    { key: 'profile', label: () => userMenuRow(PersonOutline, t('pages.Layout.userMenu.profile')) },
    /* ⚠️ 22:45 统一范式 + 设置按钮可见性修复：
       - top 模式没有 sider（v-if 不渲染），原 .sider-footer（设置按钮）在 main-area 里位置错乱
       - 把设置入口集成到 dropdown menu（与个人中心/账号设置等菜单项统一范式）
       - 路由跳转 /settings/account（设置主页），保留账号设置（个人中心）独立入口
       - 2026-08-25：移除「账号设置」冗余入口（与上方「设置」重复且未配置路由功能） */
    { key: '/settings/account', label: () => userMenuRow(CogOutline, t('pages.Layout.userMenu.settings')) },
    {
      key: 'language',
      label: () =>
        userMenuRow(
          LanguageOutline,
          t('pages.Layout.userMenu.language'),
          h(NSwitch, {
            value: currentLocale.value === 'en-US',
            uncheckedValue: false,
            checkedValue: true,
            size: 'small',
            'onUpdate:value': (v: boolean) => {
              currentLocale.value = v ? 'en-US' : 'zh-CN'
            },
          }, {
            unchecked: () => t('pages.Layout.s16'),
            checked: () => 'EN',
          }),
        ),
    },
    { type: 'divider', key: 'd1' },
    // 视图
    {
      key: 'section-layout',
      label: () => h('div', { class: 'user-menu-section-label' }, t('pages.Layout.userMenu.menuLayout')),
      disabled: true,
    },
    {
      key: 'menu-side',
      label: () =>
        userMenuRow(
          MenuOutline,
          t('pages.Layout.userMenu.menuSide'),
          current === 'side'
            ? h(NIcon, { size: 16, class: 'user-menu-check' }, { default: () => h(Check) })
            : null,
        ),
    },
    {
      key: 'menu-top',
      label: () =>
        userMenuRow(
          SwapVerticalOutline,
          t('pages.Layout.userMenu.menuTop'),
          current === 'top'
            ? h(NIcon, { size: 16, class: 'user-menu-check' }, { default: () => h(Check) })
            : null,
        ),
    },
    { type: 'divider', key: 'd2' },
    // 会话
    { key: 'logout', label: () => userMenuRow(LogOutOutline, t('pages.Layout.userMenu.logout')), props: { class: 'user-menu-logout' } },
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
    for (const item of menuOptions.value as any[]) {
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
    return
  }
  // 分组项（折叠态点分组图标）：naive 折叠态下 Submenu 只走 doSelect（不 toggleExpand），
  // 这里接管 → 固定侧栏并展开该组，让「折叠态点图标」有明确出口（不点也能悬停浮出）。
  if (typeof key === 'string' && key && !effectiveExpanded.value) {
    openGroup(key)
  }
}

/** 固定侧栏 + 展开指定分组（折叠态点击分组图标时用）。 */
function openGroup(key: string) {
  if (!siderPinned.value) userStore.setUiSettings({ siderPinned: true })
  if (!expandedKeys.value.includes(key)) {
    expandedKeys.value = [...expandedKeys.value, key]
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
    message.success(layout === 'top' ? t('pages.Layout.s17') : t('pages.Layout.s18'))
    return
  }
  if (key === 'logout') {
    userStore.logout()
    message.success(t('pages.Layout.s19'))
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
  color: var(--brand-fg);
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
/* 固定态（2026-10-21）：侧栏常驻 240px 并**占位**（第 1 列 240px），主区整体右移；
   折叠态仍是 64px 仅图标 + hover 浮层展开（不占位）。 */
.app-layout.app-layout--pinned:not(.app-layout--top) > :deep(.n-layout-scroll-container) {
  grid-template-columns: 240px calc(100vw - 240px) !important;
}
/* top 模式单列布局（无 sider，main-area 占满全宽，避免左侧 64px 空白） */
.app-layout.app-layout--top > :deep(.n-layout-scroll-container) {
  display: block !important;
  width: 100% !important;
}
/* 侧边栏: 2026-08-24 21:31 兵哥反馈改范式 —— 默认充满全高
   - 折叠（默认）: height: 100dvh !important 充满全视口（替换原 height: auto 内容驱动）+ 64px 仅一级 icon
   - 固定（.app-sider--pinned）: 240px 常驻、在文档流内占位，主区随之右移
   ⚠️ 2026-10-21：原「hover 浮层展开」（.app-sider--floating）已下线 —— 它会把菜单置为展开态，
      正好顶掉 naive-ui 原生的「折叠态悬停分组图标 → 右侧浮出二级菜单」，导致折叠态看不到子菜单。 */
.app-sider {
  height: 100dvh !important;
  flex-shrink: 0;
  overflow: visible !important; /* 让 n-menu 折叠态的二级菜单浮层不被 sider 容器裁剪 */
  transition: none !important; /* 关闭 width 过渡, 状态切换瞬切避免视觉抖动 */
  position: relative;
}
/* 固定态（2026-10-21 兵哥指令）：常驻 240px、**在文档流内占位**（不是浮层），
   主区随之右移；固定态下 hover 不再触发浮层（本来就是展开的）。 */
.app-sider.app-sider--pinned {
  position: relative !important;
  left: auto !important;
  top: auto !important;
  width: 240px !important;
  max-width: 240px !important;
  z-index: auto;
}
/* 底部一行：「设置」+「固定/折叠」图标按钮（同一行；切换按钮只显示图标，不带文字）。
   ⚠️ 不能做成悬浮在侧栏右缘的把手 —— 主区面板会盖住它，鼠标点到的是面板（兵哥实测点不到）。
   贴底由 .app-sider .sider-footer-row 的绝对定位承担（absolute 元素 auto margin 无效）。 */
.sider-footer-row {
  margin-top: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
}
/* 折叠态 64px 放不下「设置文字 + 图标文字」→ 只留两个图标，压缩横向内边距 */
.sider-footer-row--collapsed {
  gap: 0;
  padding-left: var(--space-1);
  padding-right: var(--space-1);
}
.sider-toggle {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink-soft);
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}
.sider-toggle:hover {
  color: var(--brand);
  background: var(--surface);
}
.sider-toggle:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: -2px;
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
/* 2026-10-21 (整改卡 E2): 侧栏已由 n-drawer 回改为居中弹窗, 原
   `.n-drawer-body-content-wrapper` 选择器失效 → 改挂弹窗内容区, 保持"菜单贴边零内边距"。*/
.mobile-sidebar-drawer :deep(.n-card__content) {
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
/* 系统切换时菜单整体淡入（2026-10-21 兵哥：切换系统导致页面波动）
   - 只动 opacity / transform（R-206），220ms 属「元素出现」档（200–300ms）
   - 首次挂载不播（systemSwitched 只在真正切换过一次后为 true）
   - prefers-reduced-motion 下关闭 */
@keyframes sider-menu-switch-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.sider-menu--switching {
  animation: sider-menu-switch-in 220ms var(--ease-out);
}
@media (prefers-reduced-motion: reduce) {
  .sider-menu--switching {
    animation-duration: 0.01ms;
  }
}
/* 底部行（「设置」+ 固定/折叠图标）绝对定位到 .app-sider 最底，绕开 n-scrollbar 高度约束。
   ⚠️ 2026-10-21 修正：原先是把 **.sider-footer（设置）单独**绝对定位，
   于是「设置」脱离 flex 流 → 同一行的图钉被挤到行首、设置仍浮在底部（兵哥截图）。
   现在绝对定位的是**整行**，设置与图钉作为同一行的两个 flex 子项并排。 */
.app-sider .sider-footer-row {
  position: absolute !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 2 !important; /* 在 menu 之上（内容超出时底部行浮在底部） */
}
.sider-footer {
  /* ⚠️ 贴底由外层 .sider-footer-row 的绝对定位承担；
     设置本身必须留在行内（普通 flex 子项），一旦被绝对定位就会脱离 flex 流。 */
  margin-top: 0;
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0; /* 横向内边距交给外层 row */
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
  color: var(--brand-fg);
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
  /* 折叠态横向内边距归零：外层 row 还要给右侧的固定/折叠图标按钮留位，
     64px = 4(row) + 28(设置区) + 28(图标按钮) + 4(row) */
  padding: var(--space-2) 0;
}
.sider-footer--collapsed .sider-footer-label {
  display: none;
}
/* 折叠态激活态(选中设置路由时高亮) */
.sider-footer--active {
  color: var(--brand-fg-on-soft);
  background: var(--brand-soft);
}
</style>

<style>
/* === 头像下拉菜单视觉（menu 通过 teleport 挂到 body，需全局样式） ===
 *
 * 遵循 docs/04-ui/DROPDOWN_POPOVER_SPEC.md：
 *   §2.2 面板圆角 / 玻璃底 / 阴影 / 上下 8px padding → 全局 L2（glass.css）负责，**不在这里重复定义**
 *   §2.3 行高 36px / 水平 padding 12px / prefix 列宽用 naive token / hover 高亮「层叠圆角」→ 全局 L3 负责
 *   §2.4 分割线 1px + --border-hairline + 上下 8px + 水平缩进 8px → 全局 L3 负责
 *
 * 本块只做「标准之外」的差异项：面板宽度、分组标题、语言行、布局勾选、退出登录。
 * 2026-10-22 优化：此前本地给 hover 铺了整块方角底 + 把图标文字染成品牌色，
 *   与全局「层叠圆角」高亮叠加 → 出现截图里那块方角浅紫；已改为完全交回全局标准。
 */

</style>
