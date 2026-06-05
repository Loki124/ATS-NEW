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

export interface Demand {
  id: string;
  code: string;
  name: string;
  demandStatus: string;
  demandType: string;
  positionCount: number;
  hiredCount: number;
  onBoardCount: number;
}

export interface Position {
  id: string;
  code: string;
  name: string;
  status: string;
  priority: number;
}

/** 获取需求列表（用于内推选职位） */
export const listDemands = (params?: { keyword?: string; status?: string }) =>
  api
    .get<{ success: boolean; data: { list: Demand[]; total: number } }>('/demands', { params })
    .then((r) => r.data.data.list ?? []);

/** 获取需求详情（含 active 职位列表） */
export const getDemand = (id: string) =>
  api
    .get<{ success: boolean; data: Demand & { positions: Position[] } }>(`/demands/${id}`)
    .then((r) => r.data.data);

export default { listDemands, getDemand };
