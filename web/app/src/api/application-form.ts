// 申请表和登记表（多套）配置 API
// 后端端点：
//   GET    /api/v1/standard-resume/application-form/          → 列表
//   POST   /api/v1/standard-resume/application-form/          → 新建
//   PUT    /api/v1/standard-resume/application-form/<pk>/     → 更新
//   DELETE /api/v1/standard-resume/application-form/<pk>/     → 软删除
// 数据来源：动态字段模块 resource='Candidate'，字段配置引用其 fieldKey。

import axios from 'axios'
import config from '../config'

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

// 单个字段配置项（引用动态字段的 fieldKey，并带本表单内的显隐/必填/分组）
export interface RegistrationFormField {
  fieldKey: string
  enabled: boolean
  required: boolean
  group?: string
}

export type RegistrationFormType = 'application' | 'registration'

// 一套申请表 / 登记表
export interface RegistrationForm {
  id: number
  name: string
  formType: RegistrationFormType
  departments: string[]
  mode: string
  fields: RegistrationFormField[]
  orderIndex: number
  isActive: boolean
  createdAt?: string
  updatedAt?: string
}

function unwrap<T>(r: { data: { success: boolean; data: T } }): T {
  return r.data.data
}

// 列表（仅未软删的表单，按 orderIndex, id 排序）
export async function listRegistrationForms(): Promise<RegistrationForm[]> {
  const r = await api.get('/standard-resume/application-form/')
  return unwrap<RegistrationForm[]>(r)
}

// 新建（后端补全审计时间，返回完整对象）
export async function createRegistrationForm(
  payload: Partial<RegistrationForm>,
): Promise<RegistrationForm> {
  const r = await api.post('/standard-resume/application-form/', payload)
  return unwrap<RegistrationForm>(r)
}

// 更新（局部字段，主键走路径参数）
export async function updateRegistrationForm(
  id: number,
  payload: Partial<RegistrationForm>,
): Promise<RegistrationForm> {
  const r = await api.put(`/standard-resume/application-form/${id}/`, payload)
  return unwrap<RegistrationForm>(r)
}

// 软删除（仅置 deleted_at，可恢复）
export async function deleteRegistrationForm(id: number): Promise<void> {
  await api.delete(`/standard-resume/application-form/${id}/`)
}
