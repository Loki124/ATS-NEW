/**
 * 候选人 API (PRD G9 批量操作 / G10 阶段进入 / G13 批量筛选)
 */

import axios from 'axios'
import config from '../config'

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export interface Candidate {
  id: string
  name: string
  gender?: string
  age?: number
  phone?: string
  email?: string
  highestEducation?: string
  firstEducation?: string
  currentCompany?: string
  currentPosition?: string
  workYears?: number
  source?: string
  candidateStatus?: string
  archiveReason?: string
  createdAt: string
  updatedAt: string
}

// 列表
export async function listCandidates(params: { page?: number; pageSize?: number; candidateStatus?: string; keyword?: string } = {}) {
  const { data } = await api.get('/candidates', { params })
  return data
}

// 详情
export async function getCandidate(id: string) {
  const { data } = await api.get(`/candidates/${id}`)
  return data
}

// G9 批量推荐
export async function batchRecommend(payload: { candidateIds: string[]; positionId: string; comment?: string }) {
  const { data } = await api.post('/candidates/batch/recommend', payload)
  return data
}

// G9 批量归档
export async function batchArchive(payload: { candidateIds: string[]; reason?: string }) {
  const { data } = await api.post('/candidates/batch/archive', payload)
  return data
}

// G9 批量分配
export async function batchAssign(payload: { candidateIds: string[]; recruiterId: string }) {
  const { data } = await api.post('/candidates/batch/assign', payload)
  return data
}

// G9 批量导出
export async function batchExport(payload: { candidateIds?: string[]; filter?: any } = {}) {
  const { data } = await api.post('/candidates/batch/export', payload, { responseType: 'blob' })
  return data
}

// G13 批量筛选
export async function batchScreen(payload: { candidateIds: string[]; result: 'PASS' | 'FAIL'; comment?: string }) {
  const { data } = await api.post('/candidates/batch/screen', payload)
  return data
}

// G11 倒序推荐
export async function recommendReverse(payload: { positionId: string; candidateIds?: string[] }) {
  const { data } = await api.post('/candidates/recommend-reverse', payload)
  return data
}

export default api
