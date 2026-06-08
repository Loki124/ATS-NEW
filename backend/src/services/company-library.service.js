/**
 * G41 - 公司信息库 service
 * 复用 Company model, 提供搜索/详情/行业聚合/规模过滤
 */

import { prisma } from '../app.js';

export async function searchCompanies(keyword, { industry, scale, isBenchmark, page = 1, pageSize = 20 } = {}) {
  const where = { status: 'ACTIVE' };
  if (keyword) {
    where.OR = [
      { name: { contains: keyword } },
      { code: { contains: keyword } },
    ];
  }
  if (industry) where.industry = industry;
  if (scale) where.scale = scale;
  if (typeof isBenchmark === 'boolean') where.isBenchmark = isBenchmark;
  return prisma.company.findMany({
    where,
    skip: (page - 1) * pageSize,
    take: pageSize,
    orderBy: { code: 'asc' },
  });
}

export async function getCompanyById(id) {
  return prisma.company.findUnique({ where: { id } });
}

export async function listIndustries() {
  const all = await prisma.company.findMany({ where: { status: 'ACTIVE' }, select: { industry: true } });
  return Array.from(new Set(all.map(s => s.industry).filter(Boolean))).sort();
}

export async function filterByScale(scale) {
  return prisma.company.findMany({ where: { status: 'ACTIVE', scale } });
}
