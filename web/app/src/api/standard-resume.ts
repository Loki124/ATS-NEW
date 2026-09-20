// 标准简历配置：后端持久化 + 动态字段聚合
// 字段数据来源：动态字段模块 resource='Candidate'
// 配置落库端点：GET/POST/PUT /api/v1/standard-resume/（StandardResumeConfigView）

import axios from 'axios'
import config from '../config'
import type { FieldDefinition, FieldModule } from './dynamic-field'

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})
api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export const STANDARD_RESUME_API = '/standard-resume/'

export interface ResumeStage {
  key: string
  label: string
}

// 必填项阶段规则：8 个硬编码招聘阶段（A3：阶段硬编码，与招聘流程阶段对齐）
export const STANDARD_RESUME_STAGES: ResumeStage[] = [
  { key: 'screening', label: '简历筛选' },
  { key: 'initial', label: '初试' },
  { key: 'retest', label: '复试' },
  { key: 'final', label: '终面' },
  { key: 'offer', label: 'Offer' },
  { key: 'background_check', label: '背景调查' },
  { key: 'onboarding', label: '入职' },
  { key: 'regularization', label: '转正' },
]

export interface StandardResumeFieldConfig {
  fieldKey: string
  enabled: boolean // 是否显示在标准简历中
  required: boolean // 是否必填
}

/**
 * 标准简历全局配置（标准 JSON 字段）。
 *
 * 2026-09-17 (寇豆码) 拖拽排序增强:
 *  - 新增 ``moduleOrder`` 字段, 存模块 code 数组 (前端拖拽模块顺序后 PUT 写回)
 *  - 字段顺序**不再**由 ``fields[]`` 顺序决定, 改复用
 *    ``DynamicField.order_index``, 由前端拖拽后批量 PATCH 写回。
 *  - 兼容旧数据: ``moduleOrder`` 缺失/为空时, 由 ``groupFieldsByModule``
 *    按 ``DynamicField.order_index`` 推断首现顺序生成, 不破坏存量页面。
 */
export interface StandardResumeConfig {
  fields: StandardResumeFieldConfig[]
  requiredStages: string[] // 命中必填校验的阶段 key 列表
  /** 模块展示顺序: FieldModule.code 数组; 未分组虚拟模块使用哨兵 '__ungrouped' */
  moduleOrder?: string[]
}

export function defaultConfig(): StandardResumeConfig {
  return { fields: [], requiredStages: [], moduleOrder: [] }
}

// 从后端拉取标准简历配置；空/异常时回退默认结构
export async function fetchConfig(): Promise<StandardResumeConfig> {
  const r = await api.get(STANDARD_RESUME_API)
  const data = (r.data?.data ?? {}) as Partial<StandardResumeConfig>
  return normalizeConfig(data)
}

// 保存整份配置到后端，返回落库后的回显
export async function saveConfig(cfg: StandardResumeConfig): Promise<StandardResumeConfig> {
  const r = await api.put(STANDARD_RESUME_API, cfg)
  const data = (r.data?.data ?? {}) as Partial<StandardResumeConfig>
  return normalizeConfig(data)
}

/**
 * 把后端返回的 config dict 归一为强类型结构,
 * 任何字段缺失都安全降级为空数组, 避免页面崩。
 */
function normalizeConfig(data: Partial<StandardResumeConfig>): StandardResumeConfig {
  return {
    fields: Array.isArray(data.fields) ? data.fields : [],
    requiredStages: Array.isArray(data.requiredStages) ? data.requiredStages : [],
    moduleOrder: Array.isArray(data.moduleOrder)
      ? data.moduleOrder.filter((s): s is string => typeof s === 'string')
      : [],
  }
}

// 重置为默认配置（清空字段显隐/必填 + 清空必填阶段 + 清空模块顺序）并落库
export async function resetConfig(): Promise<StandardResumeConfig> {
  return saveConfig(defaultConfig())
}

export interface MergedResumeField {
  field: FieldDefinition
  enabled: boolean
  required: boolean
}

// 把动态字段与配置合并，返回按 orderIndex 排序的完整列表（含 enabled/required 标志）
export function mergeFields(
  allFields: FieldDefinition[],
  cfg: StandardResumeConfig,
): MergedResumeField[] {
  const map = new Map(cfg.fields.map((f) => [f.fieldKey, f]))
  return [...allFields]
    .sort((a, b) => a.orderIndex - b.orderIndex)
    .map((field) => {
      const c = map.get(field.fieldKey)
      return {
        field,
        enabled: c ? c.enabled : field.isVisible,
        required: c ? c.required : field.isRequired,
      }
    })
}

// 仅返回启用的字段（用于预览渲染）
export function selectEnabledFields(merged: MergedResumeField[]): MergedResumeField[] {
  return merged.filter((m) => m.enabled)
}

/** 未分组虚拟模块的哨兵 code — module 为 null 的字段归到该模块 */
export const UNGROUPED_MODULE_CODE = '__ungrouped'

/** 模块分组结果: 一个模块 + 其下字段列表 */
export interface ModuleGroup {
  /** 模块唯一 key: FieldModule.code 或 UNGROUPED_MODULE_CODE */
  key: string
  /** 模块对象; 未分组时为 null */
  module: FieldModule | null
  /** 该模块下的字段（已按 DynamicField.orderIndex 升序） */
  fields: MergedResumeField[]
}

/**
 * 把 merged 字段按 FieldModule.code 分组, 同时按 moduleOrder 控制模块排列顺序。
 *
 * 规则:
 *  1. moduleOrder 缺失 / 为空时, 按 merged 中 module.code 的**首次出现顺序**
 *     生成 (天然沿用 DynamicField.orderIndex)。
 *  2. moduleOrder 中已声明但 merged 中无字段的模块, 直接跳过 (避免空模块占位)。
 *  3. merged 中有字段但 moduleOrder 没声明的模块, **追加到末尾**,
 *     保证「全量字段都有模块展示」。
 *  4. module 为 null 的字段归到 UNGROUPED_MODULE_CODE 虚拟模块, 永远置末尾。
 *
 * Args:
 *  merged: 已按 DynamicField.orderIndex 升序排列的字段列表
 *  moduleOrder: 后端存的标准简历模块顺序 (模块 code 数组, 可缺省)
 *
 * Returns:
 *  ModuleGroup[]  按展示顺序排列, 字段在组内已按 orderIndex 升序
 */
export function groupFieldsByModule(
  merged: MergedResumeField[],
  moduleOrder: string[] | undefined,
): ModuleGroup[] {
  const buckets = new Map<string, MergedResumeField[]>()
  for (const m of merged) {
    const code = m.field.module?.code || UNGROUPED_MODULE_CODE
    const arr = buckets.get(code)
    if (arr) arr.push(m)
    else buckets.set(code, [m])
  }

  // 收集 merged 中实际出现过的模块 code (首现顺序)
  const presentCodes: string[] = []
  const seen = new Set<string>()
  for (const m of merged) {
    const code = m.field.module?.code || UNGROUPED_MODULE_CODE
    if (!seen.has(code)) {
      seen.add(code)
      presentCodes.push(code)
    }
  }

  // 合并 moduleOrder + presentCodes: order 优先, 其余追加到末尾
  const orderedCodes: string[] = []
  const used = new Set<string>()
  if (Array.isArray(moduleOrder)) {
    for (const code of moduleOrder) {
      if (!buckets.has(code)) continue
      if (used.has(code)) continue
      orderedCodes.push(code)
      used.add(code)
    }
  }
  // 把 order 中没有、但 presentCodes 有的 code 追加到末尾
  // UNGROUPED_MODULE_CODE 永远置末尾 (即使后端 moduleOrder 里误写了它)
  const ungroupedIndex = orderedCodes.indexOf(UNGROUPED_MODULE_CODE)
  for (const code of presentCodes) {
    if (used.has(code)) continue
    if (code === UNGROUPED_MODULE_CODE) continue
    orderedCodes.push(code)
    used.add(code)
  }
  // 未分组永远最后
  if (buckets.has(UNGROUPED_MODULE_CODE)) {
    if (ungroupedIndex >= 0) orderedCodes.splice(ungroupedIndex, 1)
    orderedCodes.push(UNGROUPED_MODULE_CODE)
  }

  return orderedCodes.map((code) => {
    const fields = buckets.get(code) || []
    const firstField = fields[0]
    return {
      key: code,
      module: firstField?.field.module ?? null,
      fields,
    }
  })
}
