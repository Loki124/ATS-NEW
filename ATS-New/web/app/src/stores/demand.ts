/**
 * 需求状态管理
 * 用于跨页面共享需求列表
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/auth'

export interface Demand {
  id: string
  code: string
  name: string
  departmentId: string
  positionCount: number
  hiredCount: number
  onBoardCount: number
  demandType: string
  demandStatus: string
  approvalStatus: string
  creatorId: string
  createdAt: string
  updatedAt: string
}

export const useDemandStore = defineStore('demand', () => {
  const demands = ref<Demand[]>([])
  const loading = ref(false)
  const lastFetched = ref<number>(0)

  const CACHE_TTL = 2 * 60 * 1000  // 需求变动频繁，缓存 2 分钟

  const loadDemands = async (force = false) => {
    if (!force && Date.now() - lastFetched.value < CACHE_TTL && demands.value.length > 0) {
      return
    }
    loading.value = true
    try {
      const res = await api.get('/demands')
      if (res.data?.success) {
        demands.value = res.data.data || []
        lastFetched.value = Date.now()
      }
    } finally {
      loading.value = false
    }
  }

  const getById = (id: string) => demands.value.find(d => d.id === id)
  const getByCode = (code: string) => demands.value.find(d => d.code === code)
  const getByDepartment = (deptId: string) =>
    demands.value.filter(d => d.departmentId === deptId)

  const invalidate = () => {
    lastFetched.value = 0
  }

  return { demands, loading, loadDemands, getById, getByCode, getByDepartment, invalidate }
})
