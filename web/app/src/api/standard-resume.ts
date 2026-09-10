// 标准简历配置：后端持久化 + 动态字段聚合
// 字段数据来源：动态字段模块 resource='Candidate'
// 配置落库端点：GET/POST/PUT /api/v1/standard-resume/（StandardResumeConfigView）

import axios from 'axios'
import config from '../config'
import type { FieldDefinition } from './dynamic-field'

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

export interface StandardResumeConfig {
  fields: StandardResumeFieldConfig[]
  requiredStages: string[] // 命中必填校验的阶段 key 列表
}

export function defaultConfig(): StandardResumeConfig {
  return { fields: [], requiredStages: [] }
}

// 从后端拉取标准简历配置；空/异常时回退默认结构
export async function fetchConfig(): Promise<StandardResumeConfig> {
  const r = await api.get(STANDARD_RESUME_API)
  const data = (r.data?.data ?? {}) as Partial<StandardResumeConfig>
  return {
    fields: Array.isArray(data.fields) ? data.fields : [],
    requiredStages: Array.isArray(data.requiredStages) ? data.requiredStages : [],
  }
}

// 保存整份配置到后端，返回落库后的回显
export async function saveConfig(cfg: StandardResumeConfig): Promise<StandardResumeConfig> {
  const r = await api.put(STANDARD_RESUME_API, cfg)
  const data = (r.data?.data ?? {}) as Partial<StandardResumeConfig>
  return {
    fields: Array.isArray(data.fields) ? data.fields : [],
    requiredStages: Array.isArray(data.requiredStages) ? data.requiredStages : [],
  }
}

// 重置为默认配置（清空字段显隐/必填 + 清空必填阶段）并落库
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
