// G41 - 院校/公司信息库 前端 API 客户端
import { api } from '../utils/request'

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
  affiliatedTo?: string;
  tags?: string; // '|' 分隔，如 985|211|双一流
  formerNames?: string; // 曾用名，'|' 分隔
  updatedAt?: string;
  isCustomized?: boolean; // 人工编辑过 → 导入不会覆盖
  status?: string;
}

export interface SchoolFacets {
  schoolTypes: string[];
  schoolCategories: string[];
  educationLevels: string[];
  provinces: string[];
  tags: string[];
}

export const searchSchools = (params?: any) =>
  api.get('/library/schools/', { params }).then((r) => r.data.data);

export const getSchool = (id: string) =>
  api.get(`/library/schools/${id}/`).then((r) => r.data.data);

export const listSchoolProvinces = () =>
  api.get('/library/schools/provinces/').then((r) => r.data.data);

export const getSchoolFacets = (): Promise<SchoolFacets> =>
  api.get('/library/schools/facets/').then((r) => r.data.data);

// 人工维护（新建 / 编辑 / 软删）。编辑过的记录会被标记 isCustomized，
// 导入命令默认跳过，不会被下次导入覆盖。
export const createSchool = (data: Partial<School>) =>
  api.post('/library/schools/', data).then((r) => r.data.data);

export const updateSchool = (id: string, data: Partial<School>) =>
  api.patch(`/library/schools/${id}/`, data).then((r) => r.data.data);

export const deleteSchool = (id: string) =>
  api.delete(`/library/schools/${id}/`).then((r) => r.data.data);

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
  api.get('/library/companies/', { params }).then((r) => r.data.data);

export const getCompany = (id: string) =>
  api.get(`/library/companies/${id}/`).then((r) => r.data.data);

export const listCompanyIndustries = () =>
  api.get('/library/companies/industries/').then((r) => r.data.data);

// ===== Major（专业库 — 阳光高考专业库导入）=====
export interface Major {
  id: string;
  specId: string;
  code: string;
  name: string;
  educationLevel?: string;
  educationLevelCode?: string;
  discipline?: string;
  disciplineCode?: string;
  category?: string;
  categoryCode?: string;
  dataYear?: string;
  intro?: string;
  detailUrl?: string;
  updatedAt?: string;
  isCustomized?: boolean;
}

export interface MajorFacets {
  disciplines: string[];
  categories: string[];
  educationLevels: string[];
}

export const searchMajors = (params?: any) =>
  api.get('/library/majors/', { params }).then((r) => r.data.data);

export const getMajorFacets = () =>
  api.get('/library/majors/facets/').then((r) => r.data.data);

export const createMajor = (data: Partial<Major>) =>
  api.post('/library/majors/', data).then((r) => r.data.data);

export const updateMajor = (id: string, data: Partial<Major>) =>
  api.patch(`/library/majors/${id}/`, data).then((r) => r.data.data);

export const deleteMajor = (id: string) =>
  api.delete(`/library/majors/${id}/`).then((r) => r.data.data);

export default api;
