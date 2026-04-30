import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface User {
  id: string
  username: string
  realName: string
  email?: string
  phone?: string
  avatar?: string
  role?: string
  roleType?: string
  departmentId?: string
  department?: any
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const token = ref<string>('')

  const setUser = (userData: User) => {
    user.value = userData
  }

  const setToken = (tokenData: string) => {
    token.value = tokenData
    localStorage.setItem('token', tokenData)
  }

  const setUserData = (userData: User, tokenData: string) => {
    user.value = userData
    token.value = tokenData
    localStorage.setItem('token', tokenData)
    localStorage.setItem('user', JSON.stringify(userData))
  }

  const logout = () => {
    user.value = null
    token.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return {
    user,
    token,
    setUser,
    setToken,
    setUserData,
    logout
  }
})