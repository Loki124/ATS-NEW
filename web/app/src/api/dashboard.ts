/**
 * Dashboard 数据 API (studied-DNA)
 * 优先用现有 /candidates /positions /demands /interviews /recruitment-processes 端点,
 * 数据为空/失败时优雅 fallback mock, 不报红, 不阻塞渲染。
 */
import { createApi } from '../utils/request'

import type { ScheduleItem, JobCardData, ScreeningItemData } from '../components/dashboard'
import type { MatterItem } from '../components/dashboard/MatterList.vue'

const api = createApi({ timeout: 10000 })
// ===== 类型 =====

export interface DashboardStats {
  pendingInitial: number   // 待初筛
  pendingTodo: number       // 待处理待办
  pendingRecommend: number // 待处理推荐
  pendingScreening: number // 待处理初筛
}

export interface DashboardData {
  stats: DashboardStats
  interviews: ScheduleItem[]
  jobs: JobCardData[]
  screenings: ScreeningItemData[]
  matters: Record<string, MatterItem[]>
  matterCounts: Record<string, number>
  quickCounts: {
    archivedResumes: number
    watchingPositions: number
    watchingCandidates: number
    lockedCandidates: number
  }
  source: 'api' | 'empty'
}

// ===== 工具 =====

function safeNum(v: unknown, fallback = 0): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string') {
    const n = Number(v)
    if (Number.isFinite(n)) return n
  }
  return fallback
}

// 重要求职数据全部来自真实端点，本文件不再保留任何 mock 兜底常量。
// 「重要事项」(matters) 后端暂无聚合端点，统一返回空（见 loadDashboardData）。

// ===== 单独 API 拉取函数 (失败吞掉, 返回 null) =====

interface ApiListResponse<T> {
  success?: boolean
  data?: { list?: T[]; total?: number } | T[]
}

function extractList<T>(raw: unknown): T[] {
  if (!raw) return []
  const r = raw as ApiListResponse<T>
  if (Array.isArray(r?.data)) return r.data
  if (r?.data && Array.isArray((r.data as { list?: T[] }).list)) {
    return (r.data as { list: T[] }).list
  }
  return []
}

async function fetchCandidates(): Promise<{ list: Array<{ candidateStatus?: string; id: string }>; total: number } | null> {
  try {
    const { data } = await api.get('/candidates/', { params: { page: 1, pageSize: 50 } })
    return {
      list: extractList<{ candidateStatus?: string; id: string }>(data),
      total: safeNum((data as { data?: { total?: number } })?.data?.total),
    }
  } catch {
    return null
  }
}

// 2026-09-27: 导出供新增候选人 Step2 复用; PositionListSerializer 返回的是 title(非 name)
export interface PositionLite {
  id: string
  title?: string
  name?: string
  code?: string
  status?: string
}
export async function fetchPositions(): Promise<PositionLite[]> {
  try {
    const { data } = await api.get('/positions/', { params: { page: 1, pageSize: 50 } })
    return extractList<PositionLite>(data)
  } catch {
    return []
  }
}

async function fetchDemands(): Promise<Array<{ id: string; name?: string; code?: string }>> {
  try {
    const { data } = await api.get('/demands/', { params: { page: 1, pageSize: 20 } })
    return extractList<{ id: string; name?: string; code?: string }>(data)
  } catch {
    return []
  }
}

async function fetchInterviews(): Promise<ScheduleItem[]> {
  try {
    const { data } = await api.get('/interviews/', { params: { page: 1, pageSize: 50 } })
    const list = extractList<{
      id: string
      scheduledAt?: string
      scheduledDate?: string
      time?: string
      candidateName?: string
      position?: string
      positionName?: string
    }>(data)
    return list.map((iv) => {
      const dt = iv.scheduledAt ? new Date(iv.scheduledAt) : null
      const date = dt
        ? `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
        : (iv.scheduledDate ?? new Date().toISOString().slice(0, 10))
      const time = iv.time ?? (dt ? `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}` : '09:00')
      return {
        id: iv.id,
        date,
        time,
        candidateName: iv.candidateName ?? '候选人',
        position: iv.position ?? iv.positionName ?? '面试',
      }
    })
  } catch {
    return []
  }
}

// ===== 主入口: 拉取 + fallback =====

export async function loadDashboardData(): Promise<DashboardData> {
  // 全部走真实端点，无任何 mock 兜底；数据为空时返回零值/空数组（UI 自带空态）
  const [candidates, positions, demands, interviews] = await Promise.all([
    fetchCandidates(),
    fetchPositions(),
    fetchDemands(),
    fetchInterviews(),
  ])

  const candidateList = candidates?.list ?? []
  const hasReal =
    candidateList.length > 0 || positions.length > 0 || demands.length > 0 || interviews.length > 0
  const source: 'api' | 'empty' = hasReal ? 'api' : 'empty'

  // 待初筛/初筛中：按候选人状态聚合（G44 11 状态，简化: PENDING/空/ACTIVE 视为待处理）
  const pending = candidateList.filter((c) => {
    const s = (c.candidateStatus ?? '').toUpperCase()
    return s === 'PENDING' || s === '' || s === 'ACTIVE'
  }).length
  const stats: DashboardStats = {
    pendingInitial: pending,
    pendingTodo: 0,
    pendingRecommend: 0,
    pendingScreening: Math.max(pending - 3, 0),
  }

  const jobs: JobCardData[] = positions.slice(0, 4).map((p) => ({
    id: p.id,
    title: p.title ?? p.name ?? p.code ?? '职位',
    location: '不限',
    salary: '面议',
    candidateCount: 0,
  }))

  const screenings: ScreeningItemData[] = demands.slice(0, 5).map((d, i) => ({
    id: d.id,
    title: d.name ?? d.code ?? `需求 #${i + 1}`,
    department: '招聘组',
    location: '不限',
    salary: '面议',
    postedAt: '近期',
    applicantCount: 0,
  }))

  // 重要事项：后端暂无 /matters 聚合端点，统一返回空（不注入任何伪造提醒）
  const matters: Record<string, MatterItem[]> = {
    recruit: [], position: [], interview: [], offer: [], recommend: [], other: [],
  }
  const matterCounts: Record<string, number> = {
    recruit: 0, position: 0, interview: 0, offer: 0, recommend: 0, other: 0,
  }

  const quickCounts = {
    archivedResumes: 0,
    watchingPositions: positions.length,
    watchingCandidates: candidateList.length,
    lockedCandidates: 0,
  }

  return {
    stats,
    interviews,
    jobs,
    screenings,
    matters,
    matterCounts,
    quickCounts,
    source,
  }
}

export default { loadDashboardData }
