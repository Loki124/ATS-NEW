/**
 * 校招定岗与结算（campus_placement）· API。
 *
 * 后端挂 /api/v1/campus-placement/，camelCase 自动转换（请求体也转，故前端传 openEnabled）。
 *
 * 端点（技术契约 §4.2 / §4.3）：
 *  - position-demands/          岗位需求 CRUD，?need_status=&scope_type=&dept=
 *      {id}/review/              审核：{ action: 'approve' | 'reject', note }
 *      {id}/open/                开放 / 关闭报名：{ openEnabled: boolean }
 *      {id}/withdraw/            HRBP 撤回需求申请
 *  - applications/               志愿 CRUD，?person=&batch=&status=；填报 { positionId, order }
 *      {id}/push/                推送下一志愿给业务 BP
 *      {id}/accept/              BP 录取（后续志愿自动释放）
 *      {id}/reject/              BP 放弃（下一志愿自动推送）
 *      {id}/assign/              指定分配（班主任 / 管理员）
 *  - selection-flows/            撮合流程 CRUD，?batch=；{id}/start/ 启动撮合
 *  - placement-records/          定岗跟踪主表 CRUD，?dept=&status=
 *  - placement-goals/            定岗目标 CRUD
 *  - placement-metrics/          定岗数据 CRUD
 *  - placement-assessments/      定岗考核 CRUD
 *  - price-schemes/              定价方案 CRUD（tiers 内含排名分档 → 单价 / 底价）
 *  - price-bids/                 出价 CRUD
 *  - revenue-records/            输出台账 CRUD，?ym=&output_dept=
 *  - bills/                      结算账单 CRUD，?period=&status=
 *  - settlement/stat/            收入统计聚合
 *  - settlement/price/           定价管理视图（方案 + 分档 + 默认方案）
 *
 * ⚠️ 撮合状态机（契约 §4.3）由后端保证，前端只发起动作并如实展示返回状态：
 *   录取 → 后续志愿自动释放；放弃 → 下一志愿自动推送；两志愿均未被选 → 进入人才市场。
 */
import { api } from '../utils/request'

/** 列表解包：兼容 { success, data } 信封与 DRF 分页 { count, results }。 */
const listData = <T>(r: any): T[] => (r?.data?.data ?? r?.data?.results ?? []) as T[]
/** 对象解包：兼容 { success, data } 信封与裸对象。 */
const objData = <T>(r: any): T => (r?.data?.data ?? r?.data) as T

/* ============================ 类型定义 ============================ */

/** 岗位需求（PositionDemand）。 */
export interface PositionDemand {
  id: string
  name: string
  /** 用人部门 */
  dept: string
  /** 业务部门 */
  businessDept: string
  /** 需求数量 */
  headcount: number
  submitter: string | null
  submitterName?: string
  /** 待审核 / 已通过 / 已驳回 / 已发布 */
  needStatus: string
  needDesc: string
  bizIntro: string
  deptIntro: string
  assessReq: string
  needTime: string
  workLocation: string
  /** 负责 BP */
  bp: string | null
  bpName?: string
  /** 发布范围：all / batch / intentDept */
  scopeType: string
  scopeBatch: string
  scopeIntentDepts: string[]
  /** 是否开放报名 */
  openEnabled: boolean
  openStart: string | null
  openEnd: string | null
  openBatchNo: string
}

/** 志愿（PositionApplication）。 */
export interface PositionApplication {
  id: string
  person: string
  personName?: string
  className?: string
  /** 累计均分（后端补的校招生档案字段，缺省时前端回落为 '—'） */
  avgScore?: number | null
  position: string
  positionName?: string
  businessDept?: string
  /** 志愿顺序 1 / 2 */
  order: number
  /** 志愿 / 指定 */
  channel: string
  /** 已填报 / 推送中 / 已录取 / 已放弃 / 已释放 / 人才市场 */
  status: string
  pushedAt: string | null
  pushedBy: string | null
  /** 接受 / 拒绝 */
  decision: string | null
  decidedAt: string | null
  createdAt?: string
}

/** 撮合流程（SelectionFlow，按批次推进）。 */
export interface SelectionFlow {
  id: string
  batch: string
  /** 是否已启动（启动后校招生不可再改志愿） */
  started: boolean
  startTime: string | null
  /** 志愿数上限，null = 继承全局默认 2 */
  wishLimit: number | null
}

/** 定岗跟踪主表（PlacementRecord）。 */
export interface PlacementRecord {
  id: string
  person: string
  personName?: string
  className?: string
  batch?: string
  dept: string
  positionName: string
  placeDate: string
  /** 跟踪年数 */
  trackYears: number
  /** 最近绩效 */
  latestPerf: string
  /** 待跟踪 / 跟踪中 / 已结束 */
  status: string
}

/** 定岗目标（PlacementGoal）。 */
export interface PlacementGoal {
  id: string
  record: string
  name: string
  /** 衡量指标 */
  metric: string
  targetValue: string
  /** 权重 % */
  weight: number
  dueDate: string
  status: string
}

/** 定岗数据（PlacementMetric）。 */
export interface PlacementMetric {
  id: string
  record: string
  /** 月份 YYYY-MM */
  ym: string
  metric: string
  actualValue: string
  remark: string
}

/** 定岗考核（PlacementAssessment）。 */
export interface PlacementAssessment {
  id: string
  record: string
  /** 考核周期 */
  period: string
  score: number
  /** 绩效等级 */
  perfLevel: string
  assessedAt: string
  comment: string
}

/** 定价分档：排名区间 → 结算单价 / 底价 / 交易价允许区间。 */
export interface PriceTier {
  /** 排名区间，如 "1-10" */
  rank: string
  /** 结算单价 */
  price: number
  /** 底价 */
  floor?: number | null
  /** 交易价允许区间下限 */
  min?: number | null
  /** 交易价允许区间上限 */
  max?: number | null
}

/** 定价方案（PriceScheme）。 */
export interface PriceScheme {
  id: string
  name: string
  /** FIXED / BID / CONTEST */
  type: string
  batch: string
  selFlowBatch: string
  tiers: PriceTier[]
  isDefault: boolean
  enabled: boolean
}

/** 出价（PriceBid）。 */
export interface PriceBid {
  id: string
  scheme: string
  person: string
  personName?: string
  price: number
  createdAt?: string
}

/** 输出台账（RevenueRecord）。 */
export interface RevenueRecord {
  id: string
  person: string
  personName?: string
  /** 月份 YYYY-MM */
  ym: string
  outputDept: string
  stage: string
  attendDays: number
  /** 计价规则 */
  rule: string
  unitPrice: number
  amount: number
  /** 待确认 / 已确认 */
  status: string
}

/** 结算账单（Bill）。 */
export interface Bill {
  id: string
  billNo: string
  businessDept: string
  /** 账期 */
  period: string
  personCount: number
  amount: number
  /** 待确认 / 已确认 */
  status: string
  confirmedAt: string | null
}

/** 收入统计行（GET settlement/stat/）。 */
export interface SettlementStatRow {
  ym: string
  outputDept: string
  stage: string
  attendDays: number
  unitPrice: number
  amount: number
  personCount?: number
}

/** 定价管理视图（GET settlement/price/）。 */
export interface SettlementPriceView {
  schemes: PriceScheme[]
  defaultSchemeId?: string
  batches?: string[]
}

/* ============================ 岗位需求 ============================ */

/** 岗位需求列表（岗位池 / 需求审核共用）。 */
export const listPositionDemands = (params?: { needStatus?: string; scopeType?: string; dept?: string; search?: string }) =>
  api
    .get('/campus-placement/position-demands/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<PositionDemand>(r))

export const createPositionDemand = (payload: Partial<PositionDemand> & { name: string }) =>
  api.post('/campus-placement/position-demands/', payload).then((r) => objData<PositionDemand>(r))

export const updatePositionDemand = (id: string, payload: Partial<PositionDemand>) =>
  api.put(`/campus-placement/position-demands/${id}/`, payload).then((r) => objData<PositionDemand>(r))

export const deletePositionDemand = (id: string) =>
  api.delete(`/campus-placement/position-demands/${id}/`).then((r) => r.data)

/** 恢复已删除岗位需求（软删模型统一 restore 动作，端点口径同 campusControl 的 restoreDimension）。 */
export const restorePositionDemand = (id: string) =>
  api.post(`/campus-placement/position-demands/${id}/restore/`).then((r) => r.data)

/** 审核岗位需求：通过（approve） / 驳回（reject，须填原因）。 */
export const reviewPositionDemand = (id: string, payload: { action: 'approve' | 'reject'; note?: string }) =>
  api.post(`/campus-placement/position-demands/${id}/review/`, payload).then((r) => objData<PositionDemand>(r))

/** 开放 / 关闭报名。 */
export const openPositionDemand = (id: string, openEnabled: boolean) =>
  api.post(`/campus-placement/position-demands/${id}/open/`, { openEnabled }).then((r) => objData<PositionDemand>(r))

/** HRBP 撤回需求申请。 */
export const withdrawPositionDemand = (id: string) =>
  api.post(`/campus-placement/position-demands/${id}/withdraw/`, {}).then((r) => objData<PositionDemand>(r))

/* ============================ 志愿 ============================ */

/** 志愿列表（志愿推送 / 人才市场 / 双选进度共用）。 */
export const listApplications = (params?: { person?: string; batch?: string; status?: string; position?: string }) =>
  api
    .get('/campus-placement/applications/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<PositionApplication>(r))

/** 填报志愿（撮合启动后后端拒绝）。 */
export const createApplication = (payload: { person: string; position: string; order: number; channel?: string }) =>
  api.post('/campus-placement/applications/', payload).then((r) => objData<PositionApplication>(r))

export const updateApplication = (id: string, payload: Partial<PositionApplication>) =>
  api.put(`/campus-placement/applications/${id}/`, payload).then((r) => objData<PositionApplication>(r))

export const deleteApplication = (id: string) =>
  api.delete(`/campus-placement/applications/${id}/`).then((r) => r.data)

/** 恢复已删除志愿。 */
export const restoreApplication = (id: string) =>
  api.post(`/campus-placement/applications/${id}/restore/`).then((r) => r.data)

/** 推送下一志愿给岗位所属业务 BP。 */
export const pushApplication = (id: string) =>
  api.post(`/campus-placement/applications/${id}/push/`, {}).then((r) => objData<PositionApplication>(r))

/** BP 录取：后续志愿自动释放。 */
export const acceptApplication = (id: string) =>
  api.post(`/campus-placement/applications/${id}/accept/`, {}).then((r) => objData<PositionApplication>(r))

/** BP 放弃：下一志愿自动推送。 */
export const rejectApplication = (id: string) =>
  api.post(`/campus-placement/applications/${id}/reject/`, {}).then((r) => objData<PositionApplication>(r))

/** 指定分配（班主任 / 管理员）。 */
export const assignApplication = (id: string, payload?: { position?: string; note?: string }) =>
  api.post(`/campus-placement/applications/${id}/assign/`, payload || {}).then((r) => objData<PositionApplication>(r))

/* ============================ 撮合流程 ============================ */

/** 撮合流程列表（按批次独立推进）。 */
export const listSelectionFlows = (params?: { batch?: string }) =>
  api
    .get('/campus-placement/selection-flows/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<SelectionFlow>(r))

export const createSelectionFlow = (payload: Partial<SelectionFlow> & { batch: string }) =>
  api.post('/campus-placement/selection-flows/', payload).then((r) => objData<SelectionFlow>(r))

export const updateSelectionFlow = (id: string, payload: Partial<SelectionFlow>) =>
  api.put(`/campus-placement/selection-flows/${id}/`, payload).then((r) => objData<SelectionFlow>(r))

/** 启动撮合：started=True，启动后校招生不可再修改志愿。 */
export const startSelectionFlow = (id: string) =>
  api.post(`/campus-placement/selection-flows/${id}/start/`, {}).then((r) => objData<SelectionFlow>(r))

/* ============================ 定岗跟踪 ============================ */

/** 定岗跟踪主表列表。 */
export const listPlacementRecords = (params?: { dept?: string; status?: string; search?: string }) =>
  api
    .get('/campus-placement/placement-records/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<PlacementRecord>(r))

export const createPlacementRecord = (payload: Partial<PlacementRecord> & { person: string }) =>
  api.post('/campus-placement/placement-records/', payload).then((r) => objData<PlacementRecord>(r))

export const updatePlacementRecord = (id: string, payload: Partial<PlacementRecord>) =>
  api.put(`/campus-placement/placement-records/${id}/`, payload).then((r) => objData<PlacementRecord>(r))

export const deletePlacementRecord = (id: string) =>
  api.delete(`/campus-placement/placement-records/${id}/`).then((r) => r.data)

/** 恢复已删除定岗记录。 */
export const restorePlacementRecord = (id: string) =>
  api.post(`/campus-placement/placement-records/${id}/restore/`).then((r) => r.data)

/** 定岗目标列表。 */
export const listPlacementGoals = (params?: { record?: string }) =>
  api
    .get('/campus-placement/placement-goals/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<PlacementGoal>(r))

export const createPlacementGoal = (payload: Partial<PlacementGoal> & { record: string; name: string }) =>
  api.post('/campus-placement/placement-goals/', payload).then((r) => objData<PlacementGoal>(r))

export const updatePlacementGoal = (id: string, payload: Partial<PlacementGoal>) =>
  api.put(`/campus-placement/placement-goals/${id}/`, payload).then((r) => objData<PlacementGoal>(r))

export const deletePlacementGoal = (id: string) =>
  api.delete(`/campus-placement/placement-goals/${id}/`).then((r) => r.data)

/** 恢复已删除定岗目标。 */
export const restorePlacementGoal = (id: string) =>
  api.post(`/campus-placement/placement-goals/${id}/restore/`).then((r) => r.data)

/** 定岗数据列表。 */
export const listPlacementMetrics = (params?: { record?: string; ym?: string }) =>
  api
    .get('/campus-placement/placement-metrics/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<PlacementMetric>(r))

export const createPlacementMetric = (payload: Partial<PlacementMetric> & { record: string; ym: string }) =>
  api.post('/campus-placement/placement-metrics/', payload).then((r) => objData<PlacementMetric>(r))

export const updatePlacementMetric = (id: string, payload: Partial<PlacementMetric>) =>
  api.put(`/campus-placement/placement-metrics/${id}/`, payload).then((r) => objData<PlacementMetric>(r))

export const deletePlacementMetric = (id: string) =>
  api.delete(`/campus-placement/placement-metrics/${id}/`).then((r) => r.data)

/** 恢复已删除定岗数据。 */
export const restorePlacementMetric = (id: string) =>
  api.post(`/campus-placement/placement-metrics/${id}/restore/`).then((r) => r.data)

/** 定岗考核列表。 */
export const listPlacementAssessments = (params?: { record?: string }) =>
  api
    .get('/campus-placement/placement-assessments/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<PlacementAssessment>(r))

export const createPlacementAssessment = (payload: Partial<PlacementAssessment> & { record: string }) =>
  api.post('/campus-placement/placement-assessments/', payload).then((r) => objData<PlacementAssessment>(r))

export const updatePlacementAssessment = (id: string, payload: Partial<PlacementAssessment>) =>
  api.put(`/campus-placement/placement-assessments/${id}/`, payload).then((r) => objData<PlacementAssessment>(r))

export const deletePlacementAssessment = (id: string) =>
  api.delete(`/campus-placement/placement-assessments/${id}/`).then((r) => r.data)

/** 恢复已删除定岗考核。 */
export const restorePlacementAssessment = (id: string) =>
  api.post(`/campus-placement/placement-assessments/${id}/restore/`).then((r) => r.data)

/* ============================ 定价 / 台账 / 账单 ============================ */

/** 定价方案列表。 */
export const listPriceSchemes = (params?: { batch?: string }) =>
  api
    .get('/campus-placement/price-schemes/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<PriceScheme>(r))

export const createPriceScheme = (payload: Partial<PriceScheme> & { name: string }) =>
  api.post('/campus-placement/price-schemes/', payload).then((r) => objData<PriceScheme>(r))

export const updatePriceScheme = (id: string, payload: Partial<PriceScheme>) =>
  api.put(`/campus-placement/price-schemes/${id}/`, payload).then((r) => objData<PriceScheme>(r))

export const deletePriceScheme = (id: string) => api.delete(`/campus-placement/price-schemes/${id}/`).then((r) => r.data)

/** 出价列表。 */
export const listPriceBids = (params?: { scheme?: string }) =>
  api
    .get('/campus-placement/price-bids/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<PriceBid>(r))

export const createPriceBid = (payload: Partial<PriceBid> & { scheme: string; person: string; price: number }) =>
  api.post('/campus-placement/price-bids/', payload).then((r) => objData<PriceBid>(r))

/** 输出台账列表。 */
export const listRevenueRecords = (params?: { ym?: string; outputDept?: string; status?: string }) =>
  api
    .get('/campus-placement/revenue-records/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<RevenueRecord>(r))

export const updateRevenueRecord = (id: string, payload: Partial<RevenueRecord>) =>
  api.put(`/campus-placement/revenue-records/${id}/`, payload).then((r) => objData<RevenueRecord>(r))

/** 结算账单列表。 */
export const listBills = (params?: { period?: string; status?: string }) =>
  api
    .get('/campus-placement/bills/', { params: { page_size: 200, ...(params || {}) } })
    .then((r) => listData<Bill>(r))

export const updateBill = (id: string, payload: Partial<Bill>) =>
  api.put(`/campus-placement/bills/${id}/`, payload).then((r) => objData<Bill>(r))

/** 收入统计聚合。 */
export const getSettlementStat = (params?: { ym?: string; outputDept?: string }) =>
  api.get('/campus-placement/settlement/stat/', { params: params || {} }).then((r) => listData<SettlementStatRow>(r))

/** 定价管理视图（方案 + 分档 + 默认方案）。 */
export const getSettlementPrice = (params?: { batch?: string }) =>
  api
    .get('/campus-placement/settlement/price/', { params: params || {} })
    .then((r) => objData<SettlementPriceView>(r))
