import { defineStore } from 'pinia'
import { ref } from 'vue'
import { me as apiMe } from '../api/auth'
import { deriveRoleType } from '../utils/role'

export interface User {
  id: string | number
  username: string
  /** 中文/真实姓名 (后端 emit full_name, Login.vue 桥接到此字段 — FE 约定 realName) */
  realName?: string
  email?: string
  phone?: string
  avatar?: string
  /** 工号 (后端 emit employee_id) */
  employeeId?: string
  /** 部门 id (后端 emit department) */
  departmentId?: string | number
  /** RBAC 角色 codes 列表 — 真值, 后端 apps/core/views_auth.py 直接 emit */
  roles?: string[]
  /** 按 ROLE_PRIORITY 派生的便利字段, 给路由 guard / 顶栏 UI 用. 数组为空时为 null. */
  roleType?: string | null
  /** 用户 UI 偏好（菜单布局等），跟随账号 */
  uiSettings?: {
    menuLayout?: 'side' | 'top'
    [key: string]: any
  }
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string>('')
  const refreshToken = ref<string>('')
  // 用户 UI 偏好（菜单布局等）。后端为源，localStorage 仅作首屏缓存（避免刷新闪烁）。
  const uiSettings = ref<Record<string, any>>({})

  // 从 localStorage 水合 (避免刷新页面后 user/token 丢失)
  // Fix 8: 兼容老 key 'token' → 升级到 'accessToken', 然后清掉老 key
  try {
    const legacyToken = localStorage.getItem('token')
    if (legacyToken && !localStorage.getItem('accessToken')) {
      localStorage.setItem('accessToken', legacyToken)
    }
    localStorage.removeItem('token')

    const cachedUser = localStorage.getItem('user')
    if (cachedUser) user.value = JSON.parse(cachedUser)
    const cachedAccess = localStorage.getItem('accessToken')
    if (cachedAccess) accessToken.value = cachedAccess
    const cachedRefresh = localStorage.getItem('refreshToken')
    if (cachedRefresh) refreshToken.value = cachedRefresh
    const cachedUi = localStorage.getItem('uiSettings')
    if (cachedUi) uiSettings.value = JSON.parse(cachedUi)
  } catch (e) {
    // localStorage 数据损坏，清空避免反复报错
    localStorage.removeItem('user')
    localStorage.removeItem('uiSettings')
  }

  const setUser = (userData: User | null) => {
    user.value = userData
    if (userData) {
      localStorage.setItem('user', JSON.stringify(userData))
      if (userData.uiSettings) setUiSettings(userData.uiSettings)
    } else {
      localStorage.removeItem('user')
    }
  }

  /**
   * 写入用户 UI 偏好（合并到现有，不整体覆盖）。同时持久化到 localStorage 缓存。
   * @param persist 是否同步到后端（默认 true）。极少数场景（如仅本地草稿）可传 false。
   */
  const setUiSettings = (data: Record<string, any>, persist = true) => {
    uiSettings.value = { ...uiSettings.value, ...data }
    try {
      localStorage.setItem('uiSettings', JSON.stringify(uiSettings.value))
    } catch {
      /* 容量溢出忽略 */
    }
    if (persist && data.menuLayout) {
      // 异步同步到后端，失败不影响本地（下次 me 会修正）
      import('../api/auth').then(({ updateUiSettings }) => {
        updateUiSettings({ menuLayout: data.menuLayout }).catch(() => {})
      })
    }
  }

  const setAccessToken = (token: string) => {
    accessToken.value = token
    if (token) {
      localStorage.setItem('accessToken', token)
    } else {
      localStorage.removeItem('accessToken')
    }
  }

  const setRefreshToken = (token: string) => {
    refreshToken.value = token
    if (token) {
      localStorage.setItem('refreshToken', token)
    } else {
      localStorage.removeItem('refreshToken')
    }
  }

  /**
   * 兼容旧版 API：单一 token 字段
   * @deprecated 请使用 setAccessToken
   */
  const setToken = (token: string) => {
    setAccessToken(token)
  }

  const setUserData = (userData: User, access: string, refresh?: string) => {
    setUser(userData)
    setAccessToken(access)
    if (refresh) setRefreshToken(refresh)
  }

  const logout = () => {
    user.value = null
    accessToken.value = ''
    refreshToken.value = ''
    // 修复: 同时清掉旧 key 'token' (27 个老 API 文件还在用)
    // 修复前: logout 后 localStorage.token 仍残留, 路由守卫 fallback 读到 -> 误判已登录 -> 跳不到 /login
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  /**
   * 从服务端拉取当前用户最新状态, 覆盖本地 (Pinia + localStorage).
   *
   * 用途: main.ts 启动时如有 accessToken 就 await 一次, 防止旧 Login.vue 写入的
   *       stale localStorage (缺 roles / 字段名漂移) 永久卡死 RBAC guard.
   *
   * 行为:
   *   - 成功 → setUser(后端 snake_case → camelCase), 派生 roleType, 返回 true
   *   - 401/403 → logout() 强制重登, 返回 false
   *   - 网络抖动/5xx → 保留 step 1 (localStorage rehydrate 的快照), 返回 false
   *                     后续 API 401 时由 axios 拦截器再触发 logout
   */
  const fetchMe = async (): Promise<boolean> => {
    try {
      const response = await apiMe()
      const body = response.data
      if (!body?.success || !body.data) {
        console.warn('[user] fetchMe: non-success response', body)
        return false
      }
      const d = body.data
      const roles = d.roles ?? []
      setUser({
        id: d.id,
        username: d.username,
        realName: d.fullName,
        email: d.email,
        phone: d.phone,
        employeeId: d.employeeId,
        departmentId: (d.department ?? undefined) as string | number | undefined,
        roles,
        roleType: deriveRoleType(roles),
        uiSettings: d.uiSettings,
      })
      return true
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 401 || status === 403) {
        console.warn('[user] fetchMe: token invalid, logging out')
        logout()
      } else {
        console.warn('[user] fetchMe failed (transient/network?), keeping cached state:', err?.message ?? err)
      }
      return false
    }
  }

  return {
    user,
    accessToken,
    refreshToken,
    uiSettings,
    setUser,
    setToken,
    setAccessToken,
    setRefreshToken,
    setUserData,
    setUiSettings,
    fetchMe,
    logout
  }
})
