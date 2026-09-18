/**
 * G46 - 码表库 API
 * 只读端点：行政区划 / 国家区号 / 民族 / 语言
 * 后端统一信封 { data: [...], pagination: { total } }
 */

import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

/** 通用分页信封 */
export interface Paged<T> {
  data: T[];
  pagination: { total: number };
}

/** 行政区划（1省 2市 3区县 4镇乡） */
export interface Region {
  code: string;
  name: string;
  level: number;
  parentCode: string;
}

/** 国家 / 地区（ISO 3166-1 + 国际电话区号） */
export interface Country {
  code: string;
  code3: string;
  nameCn: string;
  nameEn: string;
  phoneCode: string;
}

/** 民族（GB/T 3304） */
export interface Ethnicity {
  code: string;
  name: string;
  letterCode: string;
}

/** 语言（ISO 639） */
export interface Language {
  code: string;
  nameCn: string;
  nameEn: string;
}

export const fetchRegions = (params?: {
  level?: number; parentCode?: string; keyword?: string; page?: number; page_size?: number;
}): Promise<Paged<Region>> => api.get('/code-tables/regions/', { params }).then((r) => r.data);

export const fetchCountries = (params?: {
  keyword?: string; page?: number; page_size?: number;
}): Promise<Paged<Country>> => api.get('/code-tables/countries/', { params }).then((r) => r.data);

export const fetchEthnicities = (params?: {
  keyword?: string; page?: number; page_size?: number;
}): Promise<Paged<Ethnicity>> => api.get('/code-tables/ethnicities/', { params }).then((r) => r.data);

export const fetchLanguages = (params?: {
  keyword?: string; page?: number; page_size?: number;
}): Promise<Paged<Language>> => api.get('/code-tables/languages/', { params }).then((r) => r.data);

/** 业务码表（自定义枚举）— 用户可维护的枚举值 */
export interface BusinessCode {
  id: string;
  category: string;
  code: string;
  name: string;
  description: string;
  parentCode: string;
  sortOrder: number;
  isCustomized: boolean;
  updatedAt: string;
}

/** 业务枚举类别（与后端 BusinessCode.CATEGORY_CHOICES 对齐） */
export const BUSINESS_CATEGORIES = [
  { label: '学历', value: 'EDUCATION' },
  { label: '职位类别', value: 'JOB_CATEGORY' },
  { label: '招聘渠道', value: 'RECRUIT_CHANNEL' },
  { label: '离职原因', value: 'OFFBOARD_REASON' },
  { label: '合同类型', value: 'CONTRACT_TYPE' },
  { label: '币种', value: 'CURRENCY' },
  { label: '行业', value: 'INDUSTRY' },
];

/** 业务码表信封（list 返回 {success, data:[...]}） */
export interface BusinessCodeEnvelope {
  success: boolean;
  data: BusinessCode[];
}

export const fetchBusinessCodes = (params?: {
  category?: string; keyword?: string;
}): Promise<BusinessCodeEnvelope> => api.get('/code-tables/business/', { params }).then((r) => r.data);

export const createBusinessCode = (payload: {
  category: string; code: string; name: string;
  description?: string; parent_code?: string; sort_order?: number;
}): Promise<{ success: boolean; data: BusinessCode }> =>
  api.post('/code-tables/business/', payload).then((r) => r.data);

export const updateBusinessCode = (
  id: string,
  payload: Partial<{
    category: string; code: string; name: string;
    description?: string; parent_code?: string; sort_order?: number;
  }>,
): Promise<{ success: boolean; data: BusinessCode }> =>
  api.patch(`/code-tables/business/${id}/`, payload).then((r) => r.data);

export const deleteBusinessCode = (id: string): Promise<{ success: boolean; data: { id: string } }> =>
  api.delete(`/code-tables/business/${id}/`).then((r) => r.data);

export default api;
