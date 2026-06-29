/**
 * G40 - 法人公司外部同步 API
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

export type ExternalSystem = 'MOKA' | 'EMAIL';

export interface CompanySync {
  id: string;
  companyId: string;
  externalSystem: ExternalSystem;
  externalId: string | null;
  syncStatus: 'PENDING' | 'SUCCESS' | 'FAILED' | 'RETRY';
  lastSyncAt: string | null;
  lastSyncBy: string | null;
  lastError: string | null;
  retryCount: number;
  updatedAt: string;
}

export const triggerCompanySync = (companyId: string, system: ExternalSystem) =>
  api
    .post(`/external-sync/sync/${companyId}/${system}`)
    .then((r) => r.data.data);

export const fetchSyncs = (params?: { system?: string; status?: string }) =>
  api
    .get('/external-sync/syncs', { params })
    .then((r) => r.data.data);

export const retrySync = (syncId: string) =>
  api
    .post(`/external-sync/syncs/${syncId}/retry`)
    .then((r) => r.data.data);
