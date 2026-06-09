/**
 * G35 - 通用数据导出 (CSV/JSON)
 * 不引入新依赖, CSV 用手写, 性能 OK
 */
import { prisma } from '../app.js';

const HEADER_LABELS = {
  Candidate: { name: '姓名', phone: '手机号', email: '邮箱', candidateStatus: '状态', createdAt: '创建时间' },
  Demand:    { code: '需求编号', title: '标题', status: '状态', createdAt: '创建时间' },
  Position:  { title: '职位', status: '状态', createdAt: '创建时间' },
  Offer:     { id: 'Offer ID', status: '状态', expectedJoinDate: '预计入职' },
  Interview: { id: '面试 ID', interviewDate: '面试时间', interviewStatus: '状态' },
  Onboarding:{ id: '入职 ID', expectedJoinDate: '预计入职', status: '状态' },
};

export function buildExportHeaders(resource, fields) {
  const labels = HEADER_LABELS[resource] || {};
  return fields.map(f => ({ key: f, label: labels[f] || f }));
}

export function exportToCsv(data, headers) {
  const cols = headers || (data.length ? Object.keys(data[0]).map(k => ({ key: k, label: k })) : []);
  const BOM = '﻿';  // Excel 中文
  const lines = [cols.map(c => escapeCsv(c.label)).join(',')];
  for (const row of data) {
    lines.push(cols.map(c => escapeCsv(row[c.key])).join(','));
  }
  return BOM + lines.join('\n');
}

function escapeCsv(v) {
  if (v == null) return '';
  const s = String(v);
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

export function exportToJson(data) {
  return JSON.stringify(data, null, 2);
}

export function summarizeData(data, field) {
  return data.reduce((sum, row) => sum + (Number(row[field]) || 0), 0);
}

const RESOURCE_GETTERS = {
  Candidate: () => prisma.candidate.findMany({ take: 1000 }),
  Demand:    () => prisma.demand.findMany({ take: 1000 }),
  Position:  () => prisma.position.findMany({ take: 1000 }),
  Offer:     () => prisma.offer.findMany({ take: 1000 }),
  Interview: () => prisma.interview.findMany({ take: 1000 }),
  Onboarding:() => prisma.onboarding.findMany({ take: 1000 }),
};

export async function exportResource(resource, format = 'csv', fields) {
  const getter = RESOURCE_GETTERS[resource];
  if (!getter) throw new Error(`Unknown resource: ${resource}`);
  const data = await getter();
  const headers = fields ? buildExportHeaders(resource, fields) : null;
  if (format === 'json') return exportToJson(data);
  return exportToCsv(data, headers);
}
