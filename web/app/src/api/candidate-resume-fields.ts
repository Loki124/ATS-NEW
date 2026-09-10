/**
 * 候选人扩展简历字段值 API
 * 对应后端 CandidateResumeFieldsView: /api/v1/candidates/<pk>/resume-fields/
 * GET  -> { success, data: { fieldKey: value } }
 * PUT  -> { values: { fieldKey: value } } -> upsert 每个 field_key
 * 用于「候选人详情 - 编辑简历」: 标准简历配置中无 Candidate 模型列的扩展字段值存取。
 */

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

export type ResumeFieldValues = Record<string, any>

/** 读取候选人的扩展简历字段值 (fieldKey -> value) */
export async function getResumeFields(candidateId: string): Promise<ResumeFieldValues> {
  const { data } = await api.get(`/candidates/${candidateId}/resume-fields/`)
  return (data && data.data) || {}
}

/** 批量 upsert 候选人的扩展简历字段值 */
export async function putResumeFields(
  candidateId: string,
  values: ResumeFieldValues,
): Promise<ResumeFieldValues> {
  const { data } = await api.put(`/candidates/${candidateId}/resume-fields/`, { values })
  return (data && data.data) || {}
}
