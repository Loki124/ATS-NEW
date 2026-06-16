/**
 * 全局搜索 API 客户端 - Plan T3
 */

import axios from 'axios'
import config from '../config'

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 5000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// ===== 类型 =====

export type SearchEntityType =
  | 'candidate'
  | 'demand'
  | 'position'
  | 'interview'
  | 'offer'
  | 'referral'

export interface SearchResultItem {
  id: string
  [key: string]: unknown
}

export interface SearchGroup {
  type: SearchEntityType
  total: number
  items: SearchResultItem[]
  error?: string
}

export interface SearchResponse {
  query: string
  took: number
  totalGroups: number
  groups: SearchGroup[]
}

export interface SearchParams {
  q: string
  types?: SearchEntityType[]
  limit?: number
}

// ===== API =====

const ENTITY_LABELS: Record<SearchEntityType, string> = {
  candidate: '候选人',
  demand: '招聘需求',
  position: '职位',
  interview: '面试',
  offer: 'Offer',
  referral: '内推',
}

export function entityLabel(t: SearchEntityType): string {
  return ENTITY_LABELS[t]
}

/**
 * 调后端 /api/search
 * 自动截断 q 到 64 字符
 */
export async function searchApi(params: SearchParams): Promise<SearchResponse> {
  const q = params.q.slice(0, 64)
  const types = params.types?.length ? params.types.join(',') : undefined
  const limit = params.limit ?? 5

  const res = await api.get<SearchResponse>('/search', {
    params: { q, types, limit },
  })
  return res.data
}

/**
 * 实体类型 → 详情页路由
 */
export function routeForEntity(type: SearchEntityType, id: string): string {
  const map: Record<SearchEntityType, string> = {
    candidate: `/candidate/detail/${id}`,
    demand: `/demand/detail/${id}`,
    position: `/position/detail/${id}`,
    interview: `/interview/detail/${id}`,
    offer: `/offer/detail/${id}`,
    referral: `/referral/detail/${id}`,
  }
  return map[type]
}
