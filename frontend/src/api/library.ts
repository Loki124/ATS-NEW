// G41 - 院校/公司信息库 前端 API 客户端

import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// ===== School =====
export interface School {
  id: string;
  name: string;
  code: string;
  location?: string;
  province?: string;
  city?: string;
  educationLevel?: string;
  schoolType?: string;
  schoolCategory?: string;
  status?: string;
}

export const searchSchools = (params?: any) =>
  api.get('/library/schools', { params }).then((r) => r.data.data);

export const getSchool = (id: string) =>
  api.get(`/library/schools/${id}`).then((r) => r.data.data);

export const listSchoolProvinces = () =>
  api.get('/library/schools/provinces').then((r) => r.data.data);

// ===== Company =====
export interface Company {
  id: string;
  name: string;
  code: string;
  industry?: string;
  scale?: string;
  isBenchmark?: boolean;
  description?: string;
  status?: string;
}

export const searchCompanies = (params?: any) =>
  api.get('/library/companies', { params }).then((r) => r.data.data);

export const getCompany = (id: string) =>
  api.get(`/library/companies/${id}`).then((r) => r.data.data);

export const listCompanyIndustries = () =>
  api.get('/library/companies/industries').then((r) => r.data.data);

export default api;
