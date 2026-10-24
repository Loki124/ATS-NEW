/**
 * 校招生考核域（campus_assessment）API 层。
 *
 * 后端挂 /api/v1/campus-assessment/（`api` 实例 baseURL 已是 /api/v1），
 * snake_case ↔ camelCase 自动转换（出参 snake→camel，入参 camel→snake）。
 *
 * 端点（技术契约 §2.2，唯一权威）：
 *   monthly-assessments/      月度考核 CRUD + {id}/check/ + {id}/adjust/
 *   assessment-templates/     考核模板 CRUD（含 items 嵌套写入）
 *   five-forces/              五行五力 CRUD
 *   attendance-records/       每日打卡 CRUD + attendance-records/daily-ranking/
 *   attendance-monthly/       月度考勤汇总 CRUD
 *   feedback-records/         反馈记录 CRUD + {id}/resolve/
 *   monthly-reports/          月报 CRUD + {id}/submit/ + {id}/score/
 *   probations/               试用期 CRUD + {id}/decide/
 *   ranking/composite/        综合排名（dim=comp|kpi|learn|force|add）
 *   ranking/teacher/          班主任排名
 *   stats/overview/           反馈 4 卡 + 考勤汇总
 *
 * 响应解包（照抄 campusControl.ts 的 listData 写法，契约 §1.4）：
 *   列表 → r.data?.data ?? r.data?.results ?? []
 *   对象 → r.data?.data ?? r.data
 *
 * ⚠️ 排名 / 统计类端点，契约只给了端点与计算口径、未逐字段定义返回体。
 *    故本层对关键字段做「多候选键」兼容取值（camelCase 优先 → snake_case 兜底），
 *    归一化后页面只消费归一化字段，不直接依赖后端原始字段名。
 *    若后端最终字段名与此处候选不同，只需改本层 normalize 函数，页面无需改动。
 */
import { api } from '../utils/request'

/** 后端前缀 */
const BASE = '/campus-assessment/'

/* ============================ 响应解包 ============================ */

/** 列表解包：兼容 {success,data:[…]} / {count,results:[…]} / 裸数组。 */
const listData = <T>(r: any): T[] => {
  const d = r?.data
  if (Array.isArray(d?.data)) return d.data as T[]
  if (Array.isArray(d?.results)) return d.results as T[]
  if (Array.isArray(d)) return d as T[]
  return []
}

/** 单对象解包：{success,data:{…}} → 内层对象；裸对象 → 自身。 */
const objectData = <T>(r: any): T => (r?.data?.data ?? r?.data) as T

/** 对象型列表解包：排名 / 统计端点可能返回 {results:[…]} 或 {rows:[…]}。 */
const rowsData = <T>(r: any, keys: string[] = ['results', 'rows', 'list', 'items']): T[] => {
  const candidates = [r?.data?.data, r?.data?.results, r?.data?.rows, r?.data]
  for (const c of candidates) {
    if (Array.isArray(c)) return c as T[]
    if (c && typeof c === 'object') {
      for (const k of keys) {
        const v = (c as any)[k]
        if (Array.isArray(v)) return v as T[]
      }
    }
  }
  return []
}

/** 多候选键取值（camelCase 优先，snake_case 兜底）；全缺返回 fallback。 */
const pick = <T = any>(row: any, keys: string[], fallback?: T): T => {
  for (const k of keys) {
    const v = row?.[k]
    if (v !== undefined && v !== null && v !== '') return v as T
  }
  return fallback as T
}

/** 数字归一（后端 Decimal 序列化为字符串）。 */
const num = (v: unknown): number => {
  if (v === undefined || v === null || v === '') return 0
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

/** 文本归一（null/undefined → 空串）。 */
const str = (v: unknown): string => (v === undefined || v === null ? '' : String(v))

/* ============================ 枚举与文案 ============================ */

/** 月度考核状态：draft=待核对 / checked=已核对 */
export const ASSESSMENT_STATUS_LABEL: Record<string, string> = {
  draft: '待核对',
  checked: '已核对',
}
/** 模板适用范围：all=全部 / dept=按部门 / class=按班级 */
export const SCOPE_TYPE_LABEL: Record<string, string> = {
  all: '全部',
  dept: '按部门',
  class: '按班级',
}
/** 模板绑定阶段：post=定岗后 / stage1~3=轮岗第 1~3 阶段 */
export const STAGE_LABEL: Record<string, string> = {
  post: '定岗后',
  stage1: '第1阶段',
  stage2: '第2阶段',
  stage3: '第3阶段',
}
/** 模板周期类型：stage=阶段末考核 / monthly=月度考核 */
export const PERIOD_TYPE_LABEL: Record<string, string> = {
  stage: '阶段末考核',
  monthly: '月度考核',
}
/** 反馈分类：issue=问题·情况记录 / mentor=导师带教反馈 */
export const FEEDBACK_CATEGORY_LABEL: Record<string, string> = {
  issue: '问题·情况记录',
  mentor: '导师带教反馈',
}
/** 反馈状态 */
export const FEEDBACK_STATUS_LABEL: Record<string, string> = {
  处理中: '处理中',
  已解决: '已解决',
  已闭环: '已闭环',
}
/** 月报状态：draft=待提交 / submitted=待评分 / scored=已评分 */
export const REPORT_STATUS_LABEL: Record<string, string> = {
  draft: '待提交',
  submitted: '待评分',
  scored: '已评分',
}
/** 试用期处理类型 */
export const PROBATION_DECISION_LABEL: Record<string, string> = {
  转正: '转正',
  延期转正: '延期转正',
  不合格: '不合格',
}
/** 排名维度（契约 §2.2 的 dim 取值） */
export const RANK_DIM_LABEL: Record<string, string> = {
  comp: '综合',
  kpi: 'KPI',
  learn: '学习成长',
  force: '五行五力',
  add: '附加分',
}
/** 五行五力维度（契约 §2.1：中文名固定） */
export const FIVE_FORCE_DIMS: { key: string; label: string }[] = [
  { key: 'learning', label: '学习力' },
  { key: 'execution', label: '执行力' },
  { key: 'collaboration', label: '协作力' },
  { key: 'innovation', label: '创新力' },
  { key: 'resilience', label: '抗压适应力' },
]
/** 每日打卡状态 */
export const ATTENDANCE_STATUS_LABEL: Record<string, string> = {
  正常: '正常',
  迟到: '迟到',
  请假: '请假',
  缺勤: '缺勤',
  加班: '加班',
}
/** 月报 5 个子项（逆向清单 A7：业务导师 / 成长导师各一套） */
export const REPORT_SUB_ITEMS: { key: string; label: string }[] = [
  { key: 'case', label: '案例' },
  { key: 'insight', label: '洞察' },
  { key: 'problem', label: '问题' },
  { key: 'clarity', label: '表达' },
  { key: 'executable', label: '可执行' },
]
/** 评分角色：business=业务导师 / growth=成长导师（综合分 = 业务×0.7 + 成长×0.3） */
export const REPORT_ROLE_LABEL: Record<string, string> = {
  business: '业务导师',
  growth: '成长导师',
}

/* ============================ 类型定义 ============================ */

/** 月度考核行（归一化后）。 */
export interface MonthlyAssessmentRow {
  id: string
  /** 校招生 Person 主键 */
  person: string | null
  personName: string
  classRoom: string | null
  classRoomName: string
  /** 轮岗部门 */
  dept: string
  /** 月份，格式 yyyy-mm */
  ym: string
  kpi: number
  exam: number
  adjust: number
  /** 月度总分 = round(KPI×0.6 + 考试×0.4) + 加减分（逆向清单 A1） */
  total: number
  /** draft=待核对 / checked=已核对 */
  status: string
  note: string
  checkedByName: string
  checkedAt: string | null
}

/** 考核模板维度项。 */
export interface TemplateItem {
  id?: string
  name: string
  /** 权重（百分比整数，合计应为 100） */
  weight: number
  /** 目标要求 */
  target: string
}

/** 考核模板（归一化后）。 */
export interface AssessmentTemplateRow {
  id: string
  name: string
  /** all / dept / class */
  scopeType: string
  /** 适用范围取值（部门 id / 班级 id 列表） */
  scopeValues: string[]
  /** post / stage1 / stage2 / stage3 */
  stage: string
  /** stage=阶段末考核 / monthly=月度考核 */
  periodType: string
  enabled: boolean
  items: TemplateItem[]
  /** 权重合计（%）；≠100 时页面给出告警 */
  weightSum: number
}

/** 每日打卡排名行。 */
export interface DailyRankingRow {
  id: string
  rank: number
  person: string | null
  personName: string
  classRoomName: string
  /** 打卡时间（HH:mm 或 HH:mm:ss） */
  punchTime: string
  /** 正常 / 迟到 / 请假 / 缺勤 / 加班 */
  status: string
  /** 与第 1 名的差距（分钟；后端未给时前端按打卡时间差折算） */
  gapToFirst: number | null
  /** 与第 1 名差距的展示文案（后端直接给文案时优先用） */
  gapText: string
}

/** 月度考勤汇总行。 */
export interface AttendanceMonthlyRow {
  id: string
  person: string | null
  personName: string
  classRoomName: string
  /** 轮岗部门 */
  dept: string
  ym: string
  attendDays: number
  lateCount: number
  leaveDays: number
  status: string
}

/** 反馈记录行。 */
export interface FeedbackRecordRow {
  id: string
  /** 记录日期 */
  date: string
  person: string | null
  personName: string
  /** 记录人 */
  reporterName: string
  /** issue=问题·情况记录 / mentor=导师带教反馈 */
  category: string
  /** 类型 */
  type: string
  /** 描述 */
  content: string
  /** 处理方式 */
  handling: string
  /** 处理中 / 已解决 / 已闭环 */
  status: string
  /** 证据（附件列表） */
  attachments: string[]
  handlerName: string
  handledAt: string | null
}

/** 月报行（归一化后）。 */
export interface MonthlyReportRow {
  id: string
  person: string | null
  personName: string
  classRoomName: string
  ym: string
  submittedAt: string | null
  /** draft / submitted / scored */
  status: string
  businessScore: number
  growthScore: number
  finalScore: number
  comment: string
}

/** 试用期行（归一化后）。 */
export interface ProbationRow {
  id: string
  person: string | null
  personName: string
  classRoomName: string
  /** 定岗部门 */
  dept: string
  /** 岗位 */
  post: string
  /** 轮岗阶段考核（综合） */
  rotationResult: number
  /** 轮岗阶段等级 */
  rotationLevel: string
  /** 定岗 3 个月考核 · KPI */
  p3mKpi: number | null
  /** 定岗 3 个月考核 · 能力项 */
  p3mCompetency: string
  /** 转正 / 延期转正 / 不合格 */
  decision: string
  decidedByName: string
  decidedAt: string | null
  decisionNote: string
}

/** 综合排名行（归一化后；实际值 + 折算得分）。 */
export interface CompositeRankingRow {
  rank: number
  person: string | null
  personName: string
  classRoomName: string
  /** 各维度「实际值」 */
  actual: { kpi: number; learn: number; force: number; add: number }
  /** 各维度「折算得分」（按综合权重折算后的贡献分） */
  score: { kpi: number; learn: number; force: number; add: number }
  /** 综合得分 */
  comp: number
}

/** 班主任排名行（归一化后）。 */
export interface TeacherRankingRow {
  rank: number
  /** 班主任名 */
  teacherName: string
  /** 分管班级 */
  classRooms: string
  /** 所带学生数 */
  studentCount: number
  /** 所带学生累计综合均分 */
  avgTotal: number
  /** 各维度名次均值 */
  rankAvg: { total: number; kpi: number; exam: number; learn: number; attend: number }
}

/** 概览统计（反馈 4 卡 + 考勤汇总，归一化后）。 */
export interface OverviewStats {
  /** 反馈总数 */
  feedbackTotal: number
  /** 处理中 */
  feedbackPending: number
  /** 已解决 + 已闭环 */
  feedbackResolved: number
  /** 含证据记录 */
  feedbackWithEvidence: number
  /** 考勤汇总 */
  attendDays: number
  lateCount: number
  leaveDays: number
}

/* ============================ 归一化 ============================ */

const normalizeMonthly = (r: any): MonthlyAssessmentRow => {
  const kpi = num(pick(r, ['kpi']))
  const exam = num(pick(r, ['exam']))
  const adjust = num(pick(r, ['adjust']))
  return {
    id: str(pick(r, ['id'], '')),
    person: pick(r, ['person'], null) as string | null,
    personName: str(pick(r, ['personName', 'person_name', 'name', 'person'])),
    classRoom: pick(r, ['classRoom', 'class_room'], null) as string | null,
    classRoomName: str(pick(r, ['classRoomName', 'class_room_name', 'className', 'class_name'])),
    dept: str(pick(r, ['dept', 'deptName', 'department', 'rotationDept', 'currentDept'])),
    ym: str(pick(r, ['ym', 'month'])),
    kpi,
    exam,
    adjust,
    total: num(pick(r, ['total', 'totalScore'], Math.round(kpi * 0.6 + exam * 0.4) + adjust)),
    status: str(pick(r, ['status'], 'draft')),
    note: str(pick(r, ['note', 'remark'])),
    checkedByName: str(pick(r, ['checkedByName', 'checked_by_name'])),
    checkedAt: pick(r, ['checkedAt', 'checked_at'], null) as string | null,
  }
}

const normalizeTemplate = (r: any): AssessmentTemplateRow => {
  const rawItems = pick<any[]>(r, ['items'], []) ?? []
  const items: TemplateItem[] = (Array.isArray(rawItems) ? rawItems : []).map((it: any) => ({
    id: it?.id ? str(it.id) : undefined,
    name: str(pick(it, ['name', 'dimension'])),
    weight: num(pick(it, ['weight'])),
    target: str(pick(it, ['target', 'requirement'])),
  }))
  return {
    id: str(pick(r, ['id'], '')),
    name: str(pick(r, ['name'], '未命名模板')),
    scopeType: str(pick(r, ['scopeType', 'scope_type'], 'all')),
    scopeValues: (pick<any[]>(r, ['scopeValues', 'scope_values'], []) ?? []).map((v) => str(v)),
    stage: str(pick(r, ['stage'], 'stage1')),
    periodType: str(pick(r, ['periodType', 'period_type'], 'monthly')),
    enabled: Boolean(pick(r, ['enabled', 'isActive', 'is_active'], false)),
    items,
    weightSum: items.reduce((sum, it) => sum + it.weight, 0),
  }
}

const normalizeDailyRanking = (r: any): DailyRankingRow => {
  const gapRaw = pick(r, ['gapToFirst', 'gap_to_first', 'gap', 'diffFromFirst'])
  return {
    id: str(pick(r, ['id'], '')),
    rank: num(pick(r, ['rank', 'rankNo', 'no'], 0)),
    person: pick(r, ['person'], null) as string | null,
    personName: str(pick(r, ['personName', 'person_name', 'name'])),
    classRoomName: str(pick(r, ['classRoomName', 'class_room_name', 'className'])),
    punchTime: str(pick(r, ['punchTime', 'punch_time', 'punchAt'])),
    status: str(pick(r, ['status'], '正常')),
    gapToFirst: gapRaw === undefined || gapRaw === null ? null : num(gapRaw),
    gapText: str(pick(r, ['gapText', 'gap_text', 'gapLabel'])),
  }
}

const normalizeAttendanceMonthly = (r: any): AttendanceMonthlyRow => ({
  id: str(pick(r, ['id'], '')),
  person: pick(r, ['person'], null) as string | null,
  personName: str(pick(r, ['personName', 'person_name', 'name'])),
  classRoomName: str(pick(r, ['classRoomName', 'class_room_name', 'className'])),
  dept: str(pick(r, ['dept', 'deptName', 'rotationDept', 'currentDept'])),
  ym: str(pick(r, ['ym', 'month'])),
  attendDays: num(pick(r, ['attendDays', 'attend_days'])),
  lateCount: num(pick(r, ['lateCount', 'late_count'])),
  leaveDays: num(pick(r, ['leaveDays', 'leave_days'])),
  status: str(pick(r, ['status'])),
})

const normalizeFeedback = (r: any): FeedbackRecordRow => {
  const att = pick<any[]>(r, ['attachments', 'evidence'], []) ?? []
  return {
    id: str(pick(r, ['id'], '')),
    date: str(pick(r, ['date'])),
    person: pick(r, ['person'], null) as string | null,
    personName: str(pick(r, ['personName', 'person_name', 'name'])),
    reporterName: str(pick(r, ['reporterName', 'reporter_name', 'reporter'])),
    category: str(pick(r, ['category'], 'issue')),
    type: str(pick(r, ['type', 'handleType'])),
    content: str(pick(r, ['content', 'issue', 'description'])),
    handling: str(pick(r, ['handling', 'handleType2', 'handle'])),
    status: str(pick(r, ['status'], '处理中')),
    attachments: (Array.isArray(att) ? att : []).map((a: any) => (typeof a === 'string' ? a : str(pick(a, ['url', 'name'])))),
    handlerName: str(pick(r, ['handlerName', 'handler_name', 'handler'])),
    handledAt: pick(r, ['handledAt', 'handled_at'], null) as string | null,
  }
}

const normalizeReport = (r: any): MonthlyReportRow => ({
  id: str(pick(r, ['id'], '')),
  person: pick(r, ['person'], null) as string | null,
  personName: str(pick(r, ['personName', 'person_name', 'name'])),
  classRoomName: str(pick(r, ['classRoomName', 'class_room_name', 'className'])),
  ym: str(pick(r, ['ym', 'month'])),
  submittedAt: pick(r, ['submittedAt', 'submitted_at'], null) as string | null,
  status: str(pick(r, ['status'], 'draft')),
  businessScore: num(pick(r, ['businessScore', 'business_score'])),
  growthScore: num(pick(r, ['growthScore', 'growth_score'])),
  finalScore: num(pick(r, ['finalScore', 'final_score'])),
  comment: str(pick(r, ['comment', 'content'])),
})

const normalizeProbation = (r: any): ProbationRow => {
  const p3m = pick(r, ['p3mKpi', 'p3m_kpi'])
  return {
    id: str(pick(r, ['id'], '')),
    person: pick(r, ['person'], null) as string | null,
    personName: str(pick(r, ['personName', 'person_name', 'name'])),
    classRoomName: str(pick(r, ['classRoomName', 'class_room_name', 'className'])),
    dept: str(pick(r, ['dept', 'deptName', 'placementDept', 'finalDept'])),
    post: str(pick(r, ['post', 'position', 'jobName', 'postName'])),
    rotationResult: num(pick(r, ['rotationResult', 'rotation_result'])),
    rotationLevel: str(pick(r, ['rotationLevel', 'rotation_level'])),
    p3mKpi: p3m === undefined || p3m === null ? null : num(p3m),
    p3mCompetency: str(pick(r, ['p3mCompetency', 'p3m_competency'])),
    decision: str(pick(r, ['decision'])),
    decidedByName: str(pick(r, ['decidedByName', 'decided_by_name'])),
    decidedAt: pick(r, ['decidedAt', 'decided_at'], null) as string | null,
    decisionNote: str(pick(r, ['decisionNote', 'decision_note'])),
  }
}

const normalizeComposite = (r: any): CompositeRankingRow => {
  const kpi = num(pick(r, ['kpi', 'kpiValue', 'kpiActual', 'dimKpi']))
  const learn = num(pick(r, ['learn', 'learning', 'learnActual', 'dimLearn', 'study']))
  const force = num(pick(r, ['force', 'fiveForce', 'forceActual', 'dimForce']))
  const add = num(pick(r, ['add', 'additional', 'addActual', 'dimAdd', 'bonus']))
  return {
    rank: num(pick(r, ['rank', 'rankNo', 'no'], 0)),
    person: pick(r, ['person'], null) as string | null,
    personName: str(pick(r, ['personName', 'person_name', 'name'])),
    classRoomName: str(pick(r, ['classRoomName', 'class_room_name', 'className'])),
    actual: { kpi, learn, force, add },
    score: {
      kpi: num(pick(r, ['kpiScore', 'kpi_score', 'kpiConverted'], Math.round(kpi * 0.5))),
      learn: num(pick(r, ['learnScore', 'learn_score', 'learnConverted'], Math.round(learn * 0.3))),
      force: num(pick(r, ['forceScore', 'force_score', 'forceConverted'], Math.round(force * 0.2))),
      add: num(pick(r, ['addScore', 'add_score', 'addConverted'], add)),
    },
    comp: num(pick(r, ['comp', 'compScore', 'composite', 'total', 'overall'])),
  }
}

const normalizeTeacher = (r: any): TeacherRankingRow => {
  const rankAvg = pick<any>(r, ['rankAvg', 'rank_avg'], {}) ?? {}
  const flat = (key: string): number =>
    num(pick(r, [`rankAvg${key}`, `rank_avg_${key}`], num(pick(rankAvg, [key]))))
  return {
    rank: num(pick(r, ['rank', 'rankNo'], 0)),
    teacherName: str(pick(r, ['teacherName', 'teacher_name', 'name', 'teacher'])),
    classRooms: str(pick(r, ['classRooms', 'class_rooms', 'classes', 'classNames'])),
    studentCount: num(pick(r, ['studentCount', 'student_count', 'studentTotal', 'count'])),
    avgTotal: num(pick(r, ['avgTotal', 'avg_total'])),
    rankAvg: {
      total: flat('total'),
      kpi: flat('kpi'),
      exam: flat('exam'),
      learn: flat('learn'),
      attend: flat('attend'),
    },
  }
}

const normalizeStats = (r: any): OverviewStats => {
  const fb = pick<any>(r, ['feedback', 'feedbackStats', 'feedback_stats'], {}) ?? {}
  const at = pick<any>(r, ['attendance', 'attendanceStats', 'attendance_stats'], {}) ?? {}
  return {
    feedbackTotal: num(pick(r, ['feedbackTotal', 'feedback_total', 'total'], num(pick(fb, ['total'])))),
    feedbackPending: num(
      pick(r, ['feedbackPending', 'feedback_pending', 'pending', 'processing'], num(pick(fb, ['pending', 'processing']))),
    ),
    feedbackResolved: num(
      // 「已解决·已闭环」= resolved + closed。后端给了合并值 resolved_total（优先用），
      // 没有时自己相加 —— 否则只取 resolved 会在「全是已闭环」的数据上显示 0（假数）。
      pick(
        r,
        ['feedbackResolved', 'feedback_resolved', 'resolvedTotal', 'resolved_total'],
        num(pick(fb, ['resolvedTotal', 'resolved_total'])) ||
          num(pick(fb, ['resolved'])) + num(pick(fb, ['closed'])),
      ),
    ),
    feedbackWithEvidence: num(
      pick(r, ['feedbackWithEvidence', 'feedback_with_evidence', 'withEvidence', 'evidenceCount'], num(pick(fb, ['withEvidence', 'evidenceCount']))),
    ),
    attendDays: num(pick(r, ['attendDays', 'attend_days', 'attend'], num(pick(at, ['attendDays', 'attend'])))),
    lateCount: num(pick(r, ['lateCount', 'late_count', 'late'], num(pick(at, ['lateCount', 'late'])))),
    leaveDays: num(pick(r, ['leaveDays', 'leave_days', 'leave'], num(pick(at, ['leaveDays', 'leave'])))),
  }
}

/* ============================ 月度考核 ============================ */

/** 月度考核列表。 */
export const listMonthlyAssessments = (params?: {
  ym?: string
  person?: string
  status?: string
  class?: string
}) =>
  api
    .get(`${BASE}monthly-assessments/`, { params: { page_size: 200, ...(params ?? {}) } })
    .then((r) => listData<MonthlyAssessmentRow>(r).map(normalizeMonthly))

/** 核对通过（锁定当月，status=checked）。 */
export const checkMonthlyAssessment = (id: string) =>
  api.post(`${BASE}monthly-assessments/${id}/check/`).then((r) => objectData<MonthlyAssessmentRow>(r))

/** 加减分（body: { adjust, reason }）。 */
export const adjustMonthlyAssessment = (id: string, payload: { adjust: number; reason: string }) =>
  api
    .post(`${BASE}monthly-assessments/${id}/adjust/`, payload)
    .then((r) => objectData<MonthlyAssessmentRow>(r))

/* ============================ 考核模板 ============================ */

/** 考核模板列表。 */
export const listAssessmentTemplates = (params?: { scopeType?: string; stage?: string; enabled?: string }) =>
  api
    .get(`${BASE}assessment-templates/`, { params: { page_size: 200, ...(params ?? {}) } })
    .then((r) => listData<AssessmentTemplateRow>(r).map(normalizeTemplate))

/** 模板新增 / 编辑入参（items 嵌套写入）。 */
export interface AssessmentTemplatePayload {
  name: string
  scopeType: string
  scopeValues: string[]
  stage: string
  periodType: string
  enabled: boolean
  items: { name: string; weight: number; target: string }[]
}

/** 新增考核模板。 */
export const createAssessmentTemplate = (payload: AssessmentTemplatePayload) =>
  api.post(`${BASE}assessment-templates/`, payload).then((r) => objectData<AssessmentTemplateRow>(r))

/** 编辑考核模板。 */
export const updateAssessmentTemplate = (id: string, payload: AssessmentTemplatePayload) =>
  api.put(`${BASE}assessment-templates/${id}/`, payload).then((r) => objectData<AssessmentTemplateRow>(r))

/** 删除考核模板（软删）。 */
export const deleteAssessmentTemplate = (id: string) => api.delete(`${BASE}assessment-templates/${id}/`).then((r) => r.data)

/* ============================ 五行五力 ============================ */

/** 五行五力评分列表。 */
export const listFiveForces = (params?: { person?: string }) =>
  api
    .get(`${BASE}five-forces/`, { params: { page_size: 200, ...(params ?? {}) } })
    .then((r) => listData<any>(r))

/* ============================ 考勤 ============================ */

/** 每日打卡记录列表。 */
export const listAttendanceRecords = (params?: { dateFrom?: string; dateTo?: string; person?: string }) =>
  api
    .get(`${BASE}attendance-records/`, {
      params: {
        page_size: 200,
        ...(params?.dateFrom ? { date_from: params.dateFrom } : {}),
        ...(params?.dateTo ? { date_to: params.dateTo } : {}),
        ...(params?.person ? { person: params.person } : {}),
      },
    })
    .then((r) => listData<any>(r))

/** 当日打卡排名（含「与第 1 名差距」）。 */
export const fetchDailyRanking = (params?: { date?: string }) =>
  api
    .get(`${BASE}attendance-records/daily-ranking/`, { params: { ...(params ?? {}) } })
    .then((r) => rowsData<DailyRankingRow>(r).map(normalizeDailyRanking))

/** 月度考勤汇总列表。 */
export const listAttendanceMonthly = (params?: { ym?: string; person?: string }) =>
  api
    .get(`${BASE}attendance-monthly/`, { params: { page_size: 200, ...(params ?? {}) } })
    .then((r) => listData<AttendanceMonthlyRow>(r).map(normalizeAttendanceMonthly))

/* ============================ 反馈记录 ============================ */

/** 反馈记录列表（category=issue|mentor，status，kw 关键词，person）。 */
export const listFeedbackRecords = (params?: {
  category?: string
  status?: string
  kw?: string
  person?: string
}) =>
  api
    .get(`${BASE}feedback-records/`, { params: { page_size: 200, ...(params ?? {}) } })
    .then((r) => listData<FeedbackRecordRow>(r).map(normalizeFeedback))

/** 新增反馈记录入参。 */
export interface FeedbackPayload {
  person?: string
  date: string
  category: string
  type: string
  content: string
  handling?: string
  attachments?: string[]
}

/** 新增反馈记录。 */
export const createFeedbackRecord = (payload: FeedbackPayload) =>
  api.post(`${BASE}feedback-records/`, payload).then((r) => objectData<FeedbackRecordRow>(r))

/** 办结反馈记录（status → 已解决，记录 handler / handled_at）。 */
export const resolveFeedbackRecord = (id: string) =>
  api.post(`${BASE}feedback-records/${id}/resolve/`, {}).then((r) => objectData<FeedbackRecordRow>(r))

/* ============================ 月报 ============================ */

/** 月报列表（ym / person / status / pending）。
 *
 * ⚠️ `pending=1` = 「待评分」（还有角色未评），**不能用 status 表达** ——
 *    契约 §2.2 规定「评分落库即置 scored」，只评一侧的月报状态也是 scored。
 */
export const listMonthlyReports = (params?: {
  ym?: string
  person?: string
  status?: string
  pending?: string
}) =>
  api
    .get(`${BASE}monthly-reports/`, { params: { page_size: 200, ...(params ?? {}) } })
    .then((r) => listData<MonthlyReportRow>(r).map(normalizeReport))

/** 新增月报（草稿）。 */
export const createMonthlyReport = (payload: { person?: string; ym: string; comment?: string }) =>
  api.post(`${BASE}monthly-reports/`, payload).then((r) => objectData<MonthlyReportRow>(r))

/** 提交月报（status → submitted）。 */
export const submitMonthlyReport = (id: string) =>
  api.post(`${BASE}monthly-reports/${id}/submit/`, {}).then((r) => objectData<MonthlyReportRow>(r))

/** 月报评分：body { role, case, insight, problem, clarity, executable, comment }。 */
export const scoreMonthlyReport = (
  id: string,
  payload: {
    role: 'business' | 'growth'
    case: number
    insight: number
    problem: number
    clarity: number
    executable: number
    comment?: string
  },
) => api.post(`${BASE}monthly-reports/${id}/score/`, payload).then((r) => objectData<MonthlyReportRow>(r))

/* ============================ 试用期 ============================ */

/** 试用期列表。 */
export const listProbations = (params?: { person?: string }) =>
  api
    .get(`${BASE}probations/`, { params: { page_size: 200, ...(params ?? {}) } })
    .then((r) => listData<ProbationRow>(r).map(normalizeProbation))

/** 试用期处理：body { decision: '转正'|'延期转正'|'不合格', note }。 */
export const decideProbation = (id: string, payload: { decision: string; note?: string }) =>
  api.post(`${BASE}probations/${id}/decide/`, payload).then((r) => objectData<ProbationRow>(r))

/* ============================ 排名与统计 ============================ */

/** 综合排名（dim=comp|kpi|learn|force|add）。 */
export const fetchCompositeRanking = (params: {
  dim: 'comp' | 'kpi' | 'learn' | 'force' | 'add'
  ym?: string
  class?: string
}) =>
  api
    .get(`${BASE}ranking/composite/`, { params: { ...params } })
    .then((r) => rowsData<CompositeRankingRow>(r).map(normalizeComposite))

/** 班主任排名（teachers[] + dims[] + 学生分项名次明细）。 */
export const fetchTeacherRanking = (params?: { ym?: string; class?: string }) =>
  api
    .get(`${BASE}ranking/teacher/`, { params: { ...(params ?? {}) } })
    .then((r) => {
      const body = objectData<any>(r)
      const raw = body?.teachers ?? body?.results ?? body?.rows ?? []
      return (Array.isArray(raw) ? raw : []).map(normalizeTeacher)
    })

/** 概览统计（反馈 4 卡 + 考勤汇总）。 */
export const fetchOverviewStats = () =>
  api.get(`${BASE}stats/overview/`).then((r) => normalizeStats(objectData<any>(r)))
