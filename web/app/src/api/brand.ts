/**
 * G43 - 品牌信息管理 API
 * 单例配置端点 /api/v1/brand/ : GET 读取 / PUT 全量更新 / PATCH 部分更新
 * 后端统一包裹 {'data': ...}, 经 camel_case 中间件 → 前端 camelCase 字段。
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

/** 社交 / 官网链接单项 */
export interface SocialLink {
  platform: string; // wechat | weibo | linkedin | official_site | other
  label: string;
  url: string;
}

export interface BrandInfo {
  id: string;
  companyName: string;
  brandSlogan: string;
  brandIntro: string;
  logoUrl: string;
  portalTitle: string;
  portalSubtitle: string;
  portalBannerUrl: string;
  primaryColor: string;
  contactEmail: string;
  contactPhone: string;
  socialLinks: SocialLink[];
  createdAt: string;
  updatedAt: string;
}

/** GET /api/v1/brand/ — 读取当前品牌信息(后端不存在时惰性创建) */
export const fetchBrandInfo = (): Promise<BrandInfo> =>
  api.get('/brand/').then((r) => r.data.data);

/** PUT /api/v1/brand/ — 全量更新品牌信息 */
export const updateBrandInfo = (data: Partial<BrandInfo>): Promise<BrandInfo> =>
  api.put('/brand/', data).then((r) => r.data.data);

/** POST /api/v1/brand/logo/ — 上传 Logo 图片, 返回可访问 URL 字符串 */
export const uploadBrandLogo = (file: File): Promise<string> => {
  const form = new FormData();
  form.append('file', file);
  return api
    .post<{ data: { url: string } }>('/brand/logo/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data.data.url);
};
