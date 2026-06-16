import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface User {
  id: string | number
  username: string
  realName?: string
  full_name?: string
  email?: string
  phone?: string
  avatar?: string
  role?: string
  roleType?: string
  departmentId?: string
  department?: any
  employee_id?: string
  roles?: string[]
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string>('')
  const refreshToken = ref<string>('')

  const setUser = (userData: User | null) => {
    user.value = userData
    if (userData) {
      localStorage.setItem('user', JSON.stringify(userData))
    } else {
      localStorage.removeItem('user')
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
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  }

  return {
    user,
    accessToken,
    refreshToken,
    setUser,
    setToken,
    setAccessToken,
    setRefreshToken,
    setUserData,
    logout
  }
})
