// 表单设置配置：后端持久化 + 动态字段聚合
// 字段数据来源：动态字段模块 resource='Demand' / 'Position'
// 配置落库端点：GET/PUT /api/v1/standard-resume/form-config/?resource=<Resource>
// 复用 standard-resume.ts 的字段聚合工具（mergeFields / groupFieldsByGroup / UNGROUPED_GROUP_CODE），
// 配置结构与标准简历一致（fields / groupOrder），但无「必填阶段」概念。
import { api } from '../utils/request'

import config from '../config'
import {
  type FieldDefinition,
  type FieldGroup,
  extractApiError,
} from './dynamic-field'
import {
  mergeFields,
  groupFieldsByGroup,
  UNGROUPED_GROUP_CODE,
  type MergedResumeField,
  type FieldGroupBucket,
} from './standard-resume'

export const FORM_CONFIG_API = '/standard-resume/form-config/'

export interface FormFieldConfig {
  fieldKey: string
  enabled: boolean // 是否在表单中显示
  required: boolean // 是否必填
}

export interface FormConfig {
  fields: FormFieldConfig[]
  /** 分组展示顺序：FieldGroup.code 数组；未分组虚拟分组使用哨兵 '__ungrouped' */
  groupOrder?: string[]
}

export function defaultFormConfig(): FormConfig {
  return { fields: [], groupOrder: [] }
}

// 从后端拉取表单配置；空/异常时回退默认结构
export async function fetchFormConfig(resource: string): Promise<FormConfig> {
  const r = await api.get(FORM_CONFIG_API, { params: { resource } })
  const data = (r.data?.data ?? {}) as Partial<FormConfig>
  return normalizeConfig(data)
}

// 保存整份配置到后端，返回落库后的回显
export async function saveFormConfig(resource: string, cfg: FormConfig): Promise<FormConfig> {
  const r = await api.put(FORM_CONFIG_API, cfg, { params: { resource } })
  const data = (r.data?.data ?? {}) as Partial<FormConfig>
  return normalizeConfig(data)
}

// 重置为默认配置（清空字段显隐/必填 + 清空分组顺序）并落库
export async function resetFormConfig(resource: string): Promise<FormConfig> {
  return saveFormConfig(resource, defaultFormConfig())
}

function normalizeConfig(data: Partial<FormConfig>): FormConfig {
  return {
    fields: Array.isArray(data.fields) ? data.fields : [],
    groupOrder: Array.isArray(data.groupOrder)
      ? data.groupOrder.filter((s): s is string => typeof s === 'string')
      : [],
  }
}

// 把后端返回的 config dict 归一为强类型结构，任何字段缺失都安全降级为空数组
export { extractApiError }
export type {
  FieldDefinition,
  FieldGroup,
  MergedResumeField,
  FieldGroupBucket,
}
export { mergeFields, groupFieldsByGroup, UNGROUPED_GROUP_CODE }
