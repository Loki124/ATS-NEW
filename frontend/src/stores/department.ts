/**
 * 部门状态管理
 * 用于跨页面共享部门数据
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/auth'

export interface Department {
  id: string
  name: string
  code: string
  parentId?: string | null
  level?: number
  path?: string
  managerId?: string | null
  manager2Id?: string | null
  manager3Id?: string | null
  hrbpId?: string | null
  status: string
  sortOrder?: number
  manager?: { id: string; realName: string; username: string } | null
  manager2?: { id: string; realName: string; username: string } | null
  manager3?: { id: string; realName: string; username: string } | null
  hrbp?: { id: string; realName: string; username: string } | null
}

export const useDepartmentStore = defineStore('department', () => {
  const departments = ref<Department[]>([])
  const loading = ref(false)
  const lastFetched = ref<number>(0)

  /** 5 分钟内的缓存不重新拉取 */
  const CACHE_TTL = 5 * 60 * 1000

  const loadDepartments = async (force = false) => {
    if (!force && Date.now() - lastFetched.value < CACHE_TTL && departments.value.length > 0) {
      return
    }
    loading.value = true
    try {
      const res = await api.get('/departments')
      if (res.data?.success) {
        departments.value = res.data.data || []
        lastFetched.value = Date.now()
      }
    } finally {
      loading.value = false
    }
  }

  const getById = (id: string) => departments.value.find(d => d.id === id)
  const getByCode = (code: string) => departments.value.find(d => d.code === code)

  const invalidate = () => {
    lastFetched.value = 0
  }

  return { departments, loading, loadDepartments, getById, getByCode, invalidate }
})
