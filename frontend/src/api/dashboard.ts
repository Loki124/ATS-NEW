/**
 * Dashboard 数据 API (studied-DNA)
 * 优先用现有 /candidates /positions /demands /interviews /recruitment-processes 端点,
 * 数据为空/失败时优雅 fallback mock, 不报红, 不阻塞渲染。
 */

import axios from 'axios'
import config from '../config'
import type { ScheduleItem, JobCardData, ScreeningItemData } from '../components/dashboard'
import type { MatterItem } from '../components/dashboard/MatterList.vue'

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

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
  source: 'api' | 'mock' | 'mixed'
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

function todayIso(offset = 0): string {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

// ===== Mock fallback (与设计 DNA 一致, 中文, 数量级合理) =====

const MOCK_STATS: DashboardStats = {
  pendingInitial: 21,
  pendingTodo: 3,
  pendingRecommend: 3,
  pendingScreening: 23,
}

const MOCK_INTERVIEWS: ScheduleItem[] = [
  { id: 'm1', date: todayIso(0), time: '10:00', candidateName: '李婉婷', position: '高级 UI 设计师' },
  { id: 'm2', date: todayIso(0), time: '14:30', candidateName: '王浩然', position: '前端工程师' },
  { id: 'm3', date: todayIso(1), time: '11:00', candidateName: '张子墨', position: '产品经理' },
  { id: 'm4', date: todayIso(1), time: '15:00', candidateName: '陈思颖', position: '数据分析师' },
  { id: 'm5', date: todayIso(2), time: '09:30', candidateName: '刘子涵', position: 'Java 工程师' },
  { id: 'm6', date: todayIso(3), time: '14:00', candidateName: '赵思琪', position: '运营专员' },
  { id: 'm7', date: todayIso(4), time: '10:30', candidateName: '孙宇辰', position: '测试工程师' },
]

const MOCK_JOBS: JobCardData[] = [
  { id: 'j1', title: '高级 UI 设计师 - PaaS', location: '北京', salary: '30-50K', company: 'PaaS 事业部', candidateCount: 12, urgent: true },
  { id: 'j2', title: '资深前端工程师 (低代码方向)', location: '上海', salary: '35-60K', company: '前端架构组', candidateCount: 8 },
  { id: 'j3', title: '高级 Java 工程师', location: '杭州', salary: '30-55K', company: '基础架构部', candidateCount: 6 },
  { id: 'j4', title: '数据分析师 (BI 方向)', location: '深圳', salary: '20-35K', company: '数据中台', candidateCount: 4 },
]

const MOCK_SCREENINGS: ScreeningItemData[] = [
  { id: 's1', title: '高级 UI 设计师 - PaaS', department: 'PaaS 事业部', location: '北京', salary: '30-50K', postedAt: '今天 09:12', applicantCount: 18, tag: '实习', tagType: 'info' },
  { id: 's2', title: '产品经理 (C 端)', department: '用户增长', location: '上海', salary: '25-40K', postedAt: '昨天 18:30', applicantCount: 9, tag: '实习', tagType: 'info' },
  { id: 's3', title: 'Java 工程师 (中间件)', department: '基础架构', location: '杭州', salary: '28-50K', postedAt: '3 天前', applicantCount: 5 },
]

const MOCK_MATTERS: Record<string, MatterItem[]> = {
  recruit: [
    { id: 'r1', title: '招聘需求「前端架构师」待审批', meta: '由 张磊 提交', time: '2 小时前', tone: 'urgent', actionLabel: '去审批' },
    { id: 'r2', title: '需求 HC 调整 - 数据组 +3', meta: 'HRBP 已确认', time: '今天 11:24' },
  ],
  position: [
    { id: 'p1', title: '「高级 UI 设计师」职位描述待复核', meta: '招聘官 王雪', time: '昨天 17:00', tone: 'warning', actionLabel: '查看' },
  ],
  interview: [
    { id: 'i1', title: '李婉婷 面试反馈待填写', meta: '一面 · 高级 UI 设计师', time: '今天 16:00', tone: 'urgent', actionLabel: '填写反馈' },
  ],
  offer: [
    { id: 'o1', title: '王浩然 Offer 谈判中', meta: '期望 45K · 提议 42K', time: '今天 10:00', tone: 'warning', actionLabel: '跟进' },
  ],
  recommend: [
    { id: 'rc1', title: '3 份推荐简历待你确认', meta: '来自 猎头 A', time: '今天 09:00' },
  ],
  other: [
    { id: 'x1', title: '猎头合同 5 天后到期', meta: 'ACN 猎头', time: '5 天后', tone: 'warning', actionLabel: '续签' },
    { id: 'x2', title: '候选人评估报告 7 份待审', meta: '本季度 评估官', time: '3 天前' },
  ],
}

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
    const { data } = await api.get('/candidates', { params: { page: 1, pageSize: 50 } })
    return {
      list: extractList<{ candidateStatus?: string; id: string }>(data),
      total: safeNum((data as { data?: { total?: number } })?.data?.total),
    }
  } catch {
    return null
  }
}

async function fetchPositions(): Promise<Array<{ id: string; name?: string; code?: string; status?: string }>> {
  try {
    const { data } = await api.get('/positions', { params: { page: 1, pageSize: 20 } })
    return extractList<{ id: string; name?: string; code?: string; status?: string }>(data)
  } catch {
    return []
  }
}

async function fetchDemands(): Promise<Array<{ id: string; name?: string; code?: string }>> {
  try {
    const { data } = await api.get('/demands', { params: { page: 1, pageSize: 20 } })
    return extractList<{ id: string; name?: string; code?: string }>(data)
  } catch {
    return []
  }
}

async function fetchInterviews(): Promise<ScheduleItem[]> {
  try {
    const { data } = await api.get('/interviews', { params: { page: 1, pageSize: 50 } })
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
        : (iv.scheduledDate ?? todayIso(0))
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
  // 并行拉取 (任一失败不影响整体)
  const [candidates, positions, demands, interviews] = await Promise.all([
    fetchCandidates(),
    fetchPositions(),
    fetchDemands(),
    fetchInterviews(),
  ])

  let source: 'api' | 'mock' | 'mixed' = 'mock'
  const stats: DashboardStats = { ...MOCK_STATS }
  let jobs: JobCardData[] = MOCK_JOBS
  let matters: Record<string, MatterItem[]> = MOCK_MATTERS

  if (candidates && candidates.list.length > 0) {
    source = 'mixed'
    const list = candidates.list
    // 按 candidateStatus 聚合 (G44 11 状态). 简化: PENDING/未归档视为"待处理"
    const pending = list.filter((c) => {
      const s = (c.candidateStatus ?? '').toUpperCase()
      return s === 'PENDING' || s === '' || s === 'ACTIVE'
    }).length
    stats.pendingInitial = pending
    stats.pendingScreening = Math.max(pending - 3, 0)
  }

  if (positions.length > 0) {
    source = source === 'mock' ? 'api' : 'mixed'
    jobs = positions.slice(0, 4).map((p) => ({
      id: p.id,
      title: p.name ?? p.code ?? '职位',
      location: '不限',
      salary: '面议',
      candidateCount: 0,
    }))
  }

  // demands 不直接展示, 但用 total 当 "我发的筛选" 来源
  const screenings: ScreeningItemData[] = demands.length > 0
    ? demands.slice(0, 5).map((d, i) => ({
        id: d.id,
        title: d.name ?? d.code ?? `需求 #${i + 1}`,
        department: '招聘组',
        location: '不限',
        salary: '面议',
        postedAt: '近期',
        applicantCount: 0,
      }))
    : MOCK_SCREENINGS

  // matters: 真实数据为空时, 保留 mock (参考图原本就有 12 条提醒)
  // 当前 backend 无 /matters 端点, 一律 fallback
  if (source === 'api') {
    // 真实有数据时, 清空 mock, 走空态
    matters = { recruit: [], position: [], interview: [], offer: [], recommend: [], other: [] }
  }

  const matterCounts: Record<string, number> = {
    recruit: matters.recruit.length,
    position: matters.position.length,
    interview: matters.interview.length,
    offer: matters.offer.length,
    recommend: matters.recommend.length,
    other: matters.other.length,
  }

  const quickCounts = {
    archivedResumes: 0,
    watchingPositions: positions.length,
    watchingCandidates: candidates?.list.length ?? 0,
    lockedCandidates: 0,
  }

  return {
    stats,
    interviews: interviews.length > 0 ? interviews : MOCK_INTERVIEWS,
    jobs,
    screenings,
    matters,
    matterCounts,
    quickCounts,
    source,
  }
}

export default { loadDashboardData }
