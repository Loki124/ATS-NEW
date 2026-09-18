/**
 * G46 - 码表库 API
 * 只读端点：行政区划 / 国家区号 / 民族 / 语言 / 币种 / 行业
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

/** 币种（ISO 4217） */
export interface Currency {
  code: string;
  codeNumeric: string;
  symbol: string;
  nameCn: string;
  nameEn: string;
}

/** 行业（GB/T 4754，level 1门类 2大类 3中类 4小类） */
export interface Industry {
  code: string;
  name: string;
  level: number;
  parentCode: string;
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

/** 币种（ISO 4217 全量，按 code 升序） */
export const fetchCurrencies = (params?: {
  keyword?: string; page?: number; page_size?: number;
}): Promise<Paged<Currency>> => api.get('/code-tables/currencies/', { params }).then((r) => r.data);

/** 行业（GB/T 4754，支持 level / parentCode 过滤） */
export const fetchIndustries = (params?: {
  level?: number; parentCode?: string; keyword?: string; page?: number; page_size?: number;
}): Promise<Paged<Industry>> => api.get('/code-tables/industries/', { params }).then((r) => r.data);

export default api;
