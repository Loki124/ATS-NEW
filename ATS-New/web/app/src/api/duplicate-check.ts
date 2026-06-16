/**
 * 简历查重 + OCR 解析 API (G45)
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

export interface DuplicateCandidate {
  candidate: { id: string; name: string; phone?: string; email?: string }
  score: number
  matchType: 'phone' | 'email' | 'name'
}

export interface CheckDuplicatePayload {
  name?: string
  phone?: string
  email?: string
  threshold?: number
}

/**
 * 主动查重: 在表单填写完时实时检查
 */
export async function checkDuplicate(payload: CheckDuplicatePayload) {
  const { data } = await api.post('/duplicate-check/check', payload)
  return data
}

/**
 * OCR 解析简历 (返回结构化数据)
 */
export async function ocrParse() {
  const { data } = await api.post('/duplicate-check/ocr-parse')
  return data
}
