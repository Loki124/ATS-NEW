/**
 * 校招批次规则（campus_control 追加域）· API。
 *
 * 后端挂既有 /api/v1/campus/，camelCase 自动转换（请求体也转）。
 *
 * 端点（技术契约 §4.2）：
 *  - batch-rules/            批次区间规则 CRUD（可增删改、启停）
 *  - batch-rules/preview/    GET 实时预览：给定 template / seq_width / seq_start / cycle / date_field
 *                            → 生成样例 + 每规则命中人数 + 未命中人数 + 无批次人数
 *  - batch-rules/apply/      POST 按规则回写人员批次（只补空值，不覆盖人工填过）
 *  - batch-rules/recalc/     POST 按命名规则重算全部批次号，返回「原批次 → 新批次」变更清单；
 *                            **不带 apply 时只返回预览不落库**，带 { apply: true } 才落库
 *  - batch-naming/           GET / PUT 批次命名配置（单例）
 *
 * ⚠️ 本模块对预览 / 重算的返回做了**归一化**（后端字段命名可能有多种形态）：
 *   预览 → { samples[], ruleHits[], unmatched, noBatch }
 *   重算 → { changes[], raw }
 *   页面只消费归一化后的结构，避免把后端字段形状的差异扩散到 8 个页面里。
 */
import { api } from '../utils/request'

/** 列表解包：兼容 { success, data } 信封与 DRF 分页 { count, results }。 */
const listData = <T>(r: any): T[] => (r?.data?.data ?? r?.data?.results ?? []) as T[]
/** 对象解包：兼容 { success, data } 信封与裸对象。 */
const objData = <T>(r: any): T => (r?.data?.data ?? r?.data) as T

/* ============================ 类型定义 ============================ */

/** 批次区间规则（BatchRule）。 */
export interface BatchRule {
  id: string
  /** 批次号 */
  code: string
  /** 批次名称 */
  name: string
  /** 区间起始日 */
  startDate: string
  /** 区间结束日 */
  endDate: string
  enabled: boolean
  sort: number
}

/** 序号循环粒度。 */
export type BatchCycle = 'month' | 'year' | 'none'
/** 区间判定依据。 */
export type BatchDateField = 'entryDate' | 'hireDate'

/** 批次命名配置（BatchNaming，单例）。 */
export interface BatchNaming {
  /** 命名模板，支持 {YYYY}{YY}{MM}{M}{DD}{SEQ}{N} */
  template: string
  /** 序号位数 1-4 */
  seqWidth: number
  /** 序号起始值 1-99 */
  seqStart: number
  /** 序号循环粒度：每月归零 / 每年归零 / 全局递增 */
  cycle: BatchCycle
  /** 区间判定依据：入职日期 / 录用日期 */
  dateField: BatchDateField
  /** 新增人员时自动按区间归属批次 */
  autoApply: boolean
}

/** 预览：单条规则的命中人数。 */
export interface BatchRuleHit {
  code: string
  name: string
  count: number
}

/** 预览结果（归一化）。 */
export interface BatchPreviewResult {
  /** 生成样例批次号 */
  samples: string[]
  /** 每条规则的命中人数 */
  ruleHits: BatchRuleHit[]
  /** 未命中任何区间的人数 */
  unmatched: number
  /** 无批次人数 */
  noBatch: number
}

/** 重算：单人的批次号变更。 */
export interface BatchRecalcChange {
  person: string
  personName?: string
  /** 原批次 */
  oldBatch?: string
  /** 新批次 */
  newBatch?: string
}

/** 重算结果（归一化）。 */
export interface BatchRecalcResult {
  changes: BatchRecalcChange[]
  /** 后端原始返回，便于排查 */
  raw: any
}

/** 应用（回写人员批次）的结果。 */
export interface BatchApplyResult {
  /** 实际回写条数 */
  updated: number
  raw: any
}

/* ============================ 批次规则 ============================ */

/** 批次规则列表。 */
export const listBatchRules = () =>
  api.get('/campus/batch-rules/', { params: { page_size: 200 } }).then((r) => listData<BatchRule>(r))

export const createBatchRule = (payload: Partial<BatchRule> & { code: string; name: string }) =>
  api.post('/campus/batch-rules/', payload).then((r) => objData<BatchRule>(r))

export const updateBatchRule = (id: string, payload: Partial<BatchRule>) =>
  api.put(`/campus/batch-rules/${id}/`, payload).then((r) => objData<BatchRule>(r))

export const deleteBatchRule = (id: string) => api.delete(`/campus/batch-rules/${id}/`).then((r) => r.data)

/**
 * 实时预览：给定命名参数 → 生成样例 + 每规则命中人数 + 未命中人数 + 无批次人数。
 * 参数用后端约定的 snake_case（query 串不参与 camelCase 转换）。
 */
export const previewBatchRules = (params: {
  template: string
  seq_width: number
  seq_start: number
  cycle: BatchCycle
  date_field: BatchDateField
}) =>
  api.get('/campus/batch-rules/preview/', { params }).then((r) => {
    const d = objData<any>(r) || {}
    const samples: string[] = d.samples ?? (d.sample ? [d.sample] : [])
    const hitsRaw: any[] = d.rules ?? d.ruleHits ?? d.hits ?? []
    const ruleHits: BatchRuleHit[] = hitsRaw.map((x: any) => ({
      code: x.code ?? x.batch ?? x.batchNo ?? '',
      name: x.name ?? x.batchName ?? '',
      count: Number(x.count ?? x.hitCount ?? x.matched ?? 0),
    }))
    return {
      samples,
      ruleHits,
      unmatched: Number(d.unmatched ?? d.unmatchedCount ?? 0),
      noBatch: Number(d.noBatch ?? d.noBatchCount ?? 0),
    } as BatchPreviewResult
  })

/** 按规则回写人员批次（只补空值，不覆盖人工填过）。 */
export const applyBatchRules = () =>
  api.post('/campus/batch-rules/apply/', {}).then((r) => {
    const d = objData<any>(r) || {}
    return { updated: Number(d.updated ?? d.count ?? 0), raw: d } as BatchApplyResult
  })

/**
 * 重算批次号。
 *  - 不传 apply → 只返回「原批次 → 新批次」变更预览，**不落库**
 *  - 传 { apply: true } → 落库
 */
export const recalcBatchRules = (payload?: { apply?: boolean }) =>
  api.post('/campus/batch-rules/recalc/', payload || {}).then((r) => {
    const d = objData<any>(r)
    const rawList: any[] = Array.isArray(d) ? d : (d?.changes ?? d?.list ?? d?.items ?? [])
    const changes: BatchRecalcChange[] = rawList.map((x: any) => ({
      person: x.person ?? x.personId ?? x.id ?? '',
      personName: x.personName ?? x.name ?? '',
      oldBatch: x.oldBatch ?? x.from ?? x.old ?? '',
      newBatch: x.newBatch ?? x.to ?? x.new ?? '',
    }))
    return { changes, raw: d } as BatchRecalcResult
  })

/* ============================ 命名配置（单例） ============================ */

/** 读取批次命名配置。 */
export const getBatchNaming = () => api.get('/campus/batch-naming/').then((r) => objData<BatchNaming>(r))

/** 覆盖保存批次命名配置（PUT，单例）。 */
export const saveBatchNaming = (payload: BatchNaming) =>
  api.put('/campus/batch-naming/', payload).then((r) => objData<BatchNaming>(r))
