/**
 * recommendation.ts - PRD G31
 * 候选人 ↔ 职位 双向推荐 API
 */
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

export interface RecommendedPosition {
  id: string;
  name?: string;
  title?: string;
  code?: string;
  workLocation?: string;
  education?: string;
  minExperience?: number;
  maxExperience?: number;
  score: number;
  matchReason?: string;
}

export interface RecommendedCandidate {
  id: string;
  name: string;
  highestEducation?: string;
  workExperience?: string;
  expectedPosition?: string;
  householdLocation?: string;
  score: number;
}

/** 给定候选人 → 推荐职位列表 */
export async function recommendPositionsForCandidate(candidateId: string, limit = 10) {
  const { data } = await api.get(`/recommendations/positions/for-candidate/${candidateId}`, { params: { limit } });
  return data.data as RecommendedPosition[];
}

/** 给定职位 → 推荐候选人列表 */
export async function recommendCandidatesForPosition(positionId: string, limit = 10) {
  const { data } = await api.get(`/recommendations/candidates/for-position/${positionId}`, { params: { limit } });
  return data.data as RecommendedCandidate[];
}

export default api;
