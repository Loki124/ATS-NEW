// 申请表和登记表配置：后端持久化 + 动态字段聚合
// 字段数据来源：动态字段模块 resource='Candidate'
// 配置落库端点：GET/POST/PUT /api/v1/standard-resume/application-form/（ApplicationFormConfigView）
// 单套配置：同时作用于候选人投递「申请表」与入职「登记表」，字段与校验规则统一。

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

export const APPLICATION_FORM_API = '/standard-resume/application-form/'

export interface ApplicationFormFieldConfig {
  fieldKey: string
  enabled: boolean // 是否显示在申请表中
  required: boolean // 是否必填
}

export interface ApplicationFormConfig {
  fields: ApplicationFormFieldConfig[]
  requiredStages: string[] // 本模块为单套配置，固定为空（无阶段维度）
}

export function defaultConfig(): ApplicationFormConfig {
  return { fields: [], requiredStages: [] }
}

// 从后端拉取申请表配置；空/异常时回退默认结构
export async function fetchConfig(): Promise<ApplicationFormConfig> {
  const r = await api.get(APPLICATION_FORM_API)
  const data = (r.data?.data ?? {}) as Partial<ApplicationFormConfig>
  return {
    fields: Array.isArray(data.fields) ? data.fields : [],
    requiredStages: Array.isArray(data.requiredStages) ? data.requiredStages : [],
  }
}

// 保存整份配置到后端，返回落库后的回显
export async function saveConfig(cfg: ApplicationFormConfig): Promise<ApplicationFormConfig> {
  const r = await api.put(APPLICATION_FORM_API, cfg)
  const data = (r.data?.data ?? {}) as Partial<ApplicationFormConfig>
  return {
    fields: Array.isArray(data.fields) ? data.fields : [],
    requiredStages: Array.isArray(data.requiredStages) ? data.requiredStages : [],
  }
}

// 重置为默认配置（清空字段显隐/必填）并落库
export async function resetConfig(): Promise<ApplicationFormConfig> {
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
  cfg: ApplicationFormConfig,
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
