<template>
  <a-layout class="app-layout">
    <a-layout-sider
      :trigger="null"
      :collapsible="true"
      v-model:collapsed="collapsed"
      class="app-sider"
      :width="240"
      theme="dark"
    >
      <div class="logo-container">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
          </div>
          <span v-if="!collapsed" class="logo-text">ATS招聘系统</span>
        </div>
      </div>

      <a-menu
        theme="dark"
        mode="inline"
        v-model:selectedKeys="selectedKeys"
        v-model:openKeys="openKeys"
        :items="menuItems"
        @click="handleMenuClick"
        class="side-menu"
      />
    </a-layout-sider>

    <a-layout :style="{ marginLeft: collapsed ? '80px' : '240px', transition: 'margin-left 0.2s' }">
      <a-layout-header class="app-header">
        <div class="header-left">
          <button class="trigger-btn" @click="toggleCollapsed">
            <MenuUnfoldOutlined v-if="collapsed" />
            <MenuFoldOutlined v-else />
          </button>

          <div class="search-box">
            <SearchOutlined class="search-icon" />
            <input type="text" placeholder="搜索候选人、职位、需求..." />
          </div>
        </div>

        <div class="header-right">
          <a-badge :count="5" :size="'small'">
            <button class="header-icon-btn" @click="goToNotifications">
              <BellOutlined />
            </button>
          </a-badge>

          <a-dropdown :trigger="['click']" placement="bottomRight">
            <div class="user-info">
              <a-avatar :size="36" class="user-avatar">
                {{ userStore.user?.realName?.[0] || 'A' }}
              </a-avatar>
              <div class="user-details">
                <span class="user-name">{{ userStore.user?.realName || '管理员' }}</span>
                <span class="user-role">{{ userStore.user?.roleType === 'SUPER_ADMIN' ? '超级管理员' : '用户' }}</span>
              </div>
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item key="profile">
                  <UserAddOutlined /> 个人中心
                </a-menu-item>
                <a-menu-item key="settings" @click="goToAccountSettings">
                  <SettingOutlined /> 账号设置
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item key="logout" @click="handleLogout">
                  <LogoutOutlined /> 退出登录
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <a-layout-content class="app-content">
        <div class="content-wrapper">
          <router-view />
        </div>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, watch, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  DashboardOutlined,
  FileTextOutlined,
  TeamOutlined,
  UserAddOutlined,
  CalendarOutlined,
  GiftOutlined,
  RiseOutlined,
  BellOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
} from '@ant-design/icons-vue'
import { useUserStore } from '../stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const collapsed = ref(false)

const selectedKeys = ref<string[]>([])
const openKeys = ref<string[]>([])

const menuItems = [
  {
    key: '/dashboard',
    icon: () => h(DashboardOutlined),
    label: '工作台',
  },
  {
    key: '/demands',
    icon: () => h(FileTextOutlined),
    label: '需求管理',
  },
  {
    key: '/positions',
    icon: () => h(TeamOutlined),
    label: '职位管理',
  },
  {
    key: 'candidate',
    icon: () => h(TeamOutlined),
    label: '候选人',
    children: [
      { key: '/candidates', label: '候选人管理' },
      { key: '/screenings', label: '简历筛选' },
      { key: '/talent-pool', label: '人才库' },
      { key: '/my-resumes', label: '我找的简历' },
    ],
  },
  {
    key: 'interview',
    icon: () => h(CalendarOutlined),
    label: '面试管理',
    children: [
      { key: '/interviews', label: '面试安排' },
      { key: '/invitations', label: '邀约中心' },
    ],
  },
  {
    key: 'offer',
    icon: () => h(GiftOutlined),
    label: 'Offer管理',
    children: [
      { key: '/offers', label: 'Offer列表' },
      { key: '/onboardings', label: '待入职' },
    ],
  },
  {
    key: '/report',
    icon: () => h(RiseOutlined),
    label: '数据中心',
  },
  {
    key: 'settings',
    icon: () => h(SettingOutlined),
    label: '系统管理',
    children: [
      { key: 'basic-info', label: '基本信息', children: [
        { key: 'org', label: '组织机构管理', children: [
          { key: '/settings/department', label: '部门管理' },
          { key: '/settings/user-management', label: '用户管理' },
          { key: '/settings/permission', label: '权限管理' },
          { key: '/settings/mou', label: 'MOU权限管理' },
        ]},
      ]},
      { key: '/settings/account', label: '账号设置' },
      { key: '/settings/company', label: '公司信息' },
      { key: 'process', label: '过程管理', children: [
        { key: '/settings/demand-config', label: '招聘需求设置' },
        { key: '/settings/dictionary', label: '数据字典' },
        { key: '/settings/scoring', label: '评分规则' },
      ]},
      { key: 'speedup', label: '招聘提速', children: [
        { key: 'recruitment-flow', label: '流程管理', children: [
          { key: '/settings/process-management', label: '招聘流程配置' },
          { key: '/settings/stage', label: '招聘阶段配置' },
        ]},
      ]},
    ],
  },
]

const toggleCollapsed = () => {
  collapsed.value = !collapsed.value
}

const handleMenuClick = ({ key }: { key: string }) => {
  if (typeof key === 'string' && key.startsWith('/')) {
    router.push(key)
  }
}

const goToNotifications = () => {
  router.push('/notifications')
}

const goToAccountSettings = () => {
  router.push('/settings/account')
}

const handleLogout = () => {
  userStore.logout()
  message.success('已退出登录')
  router.push('/login')
}

const updateSelectedKeys = () => {
  const path = route.path
  selectedKeys.value = [path]

  // Find parent key for current path and add to open keys if not already present
  menuItems.forEach((item: any) => {
    if (item?.children) {
      item.children.forEach((child: any) => {
        if (child?.key === path && !openKeys.value.includes(item.key)) {
          openKeys.value = [...openKeys.value, item.key]
        }
      })
    }
  })
}

// Watch route changes
watch(() => route.path, () => {
  updateSelectedKeys()
}, { immediate: true })
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-sider {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  overflow: auto;
}

.logo-container {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 16px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  color: white;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.logo-text {
  color: white;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}

.side-menu {
  border-right: none;
}

.app-header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.trigger-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #595959;
  transition: color 0.3s;
}

.trigger-btn:hover {
  color: #1890ff;
}

.search-box {
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 6px;
  padding: 8px 12px;
  min-width: 300px;
}

.search-box input {
  border: none;
  background: transparent;
  outline: none;
  margin-left: 8px;
  width: 100%;
  font-size: 14px;
}

.search-icon {
  color: #8c8c8c;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-icon-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #595959;
  border-radius: 50%;
  transition: all 0.3s;
}

.header-icon-btn:hover {
  background: #f5f5f5;
  color: #1890ff;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.3s;
}

.user-info:hover {
  background: #f5f5f5;
}

.user-avatar {
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  color: #000;
  font-weight: 600;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: #262626;
  line-height: 1.2;
}

.user-role {
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.2;
}

.app-content {
  padding: 24px;
  min-height: calc(100vh - 64px);
  background: #f5f5f5;
}

.content-wrapper {
  background: white;
  border-radius: 8px;
  min-height: 100%;
  padding: 24px;
}
</style>