<template>
  <n-layout has-sider class="min-h-screen">
    <!-- 侧边栏 -->
    <n-layout-sider
      bordered
      :width="240"
      :collapsed-width="64"
      show-trigger
      collapse-mode="width"
      :collapsed="collapsed"
      :native-scrollbar="false"
      @collapse="collapsed = true"
      @expand="collapsed = false"
      class="bg-gray-900"
      :style="{ position: 'sticky', top: 0, height: '100vh', overflow: 'hidden' }"
    >
      <div class="logo-container">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.48 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
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
        @update:value="handleMenuClick"
        @update:expanded-keys="onExpandedKeysChange"
        class="bg-gray-900"
      />
    </n-layout-sider>

    <!-- 主体 -->
    <n-layout>
      <!-- 头部 -->
      <n-layout-header bordered class="bg-white px-6 flex items-center justify-between h-16">
        <div class="flex items-center gap-4">
          <div class="search-box flex items-center gap-2 px-3 py-1.5 rounded-md bg-gray-100 w-80">
            <n-icon :component="SearchOutline" />
            <input type="text" placeholder="搜索候选人、职位、需求..." class="bg-transparent border-0 outline-none flex-1 text-sm" />
          </div>
        </div>

        <div class="flex items-center gap-4">
          <n-badge :value="5" :max="99">
            <n-button text @click="goToNotifications">
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
      <n-layout-content class="bg-gray-50 layout-content">
        <div class="content-wrapper p-6">
          <router-view />
        </div>
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, h, computed, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, NIcon } from 'naive-ui'
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
import { useUserStore } from '../stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const message = useMessage()

const collapsed = ref(false)

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

const userMenuOptions = [
  { key: 'profile', label: '个人中心', icon: renderIcon(PersonOutline) },
  { key: 'settings', label: '账号设置', icon: renderIcon(CogOutline) },
  { type: 'divider', key: 'd1' },
  { key: 'logout', label: '退出登录', icon: renderIcon(LogOutOutline) },
]

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

/* === 内容区填满剩余高度 === */
.layout-content {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 64px); /* 减掉头部 64px */
}
.content-wrapper {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 100%;
}
</style>
