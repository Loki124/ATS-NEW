// G30 - RPA 简历抓取 API 客户端
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

export interface ScrapedResume {
  id: string;
  source: string;
  sourceUrl?: string;
  scraperType: string;
  scraperJobName?: string;
  scrapedAt: string;
  status: 'PENDING' | 'SCRAPED' | 'IMPORTED' | 'FAILED' | 'DUPLICATE';
  resumes?: Array<{ name: string; phone?: string; email?: string; source?: string; sourceUrl?: string }>;
  candidateId?: string;
  importError?: string;
}

export const triggerScrape = (payload: { source?: string; jobTitle?: string; city?: string; scraperJobName?: string }) =>
  api.post<{ success: boolean; data: ScrapedResume }>('/scraped-resumes/scrape', payload).then(r => r.data.data);

export const listScrapedResumes = (params?: { status?: string; page?: number; pageSize?: number }) =>
  api.get<{ success: boolean; data: ScrapedResume[] }>('/scraped-resumes', { params }).then(r => r.data.data);

export const importScrapedResume = (id: string, candidateId: string) =>
  api.post<{ success: boolean; data: ScrapedResume }>(`/scraped-resumes/${id}/import`, { candidateId }).then(r => r.data.data);

export default api;
