/**
 * G41 - 院校信息库 service
 * 复用 School model, 提供搜索/详情/省份聚合
 */

import { prisma } from '../app.js';

export async function searchSchools(keyword, { educationLevel, schoolType, province, city, page = 1, pageSize = 20 } = {}) {
  const where = { status: 'ACTIVE' };
  if (keyword) {
    where.OR = [
      { name: { contains: keyword } },
      { code: { contains: keyword } },
    ];
  }
  if (educationLevel) where.educationLevel = educationLevel;
  if (schoolType) where.schoolType = schoolType;
  if (province) where.province = province;
  if (city) where.city = city;
  return prisma.school.findMany({
    where,
    skip: (page - 1) * pageSize,
    take: pageSize,
    orderBy: { code: 'asc' },
  });
}

export async function getSchoolById(id) {
  return prisma.school.findUnique({ where: { id } });
}

export async function listProvinces() {
  const all = await prisma.school.findMany({ where: { status: 'ACTIVE' }, select: { province: true } });
  return Array.from(new Set(all.map(s => s.province).filter(Boolean))).sort();
}

export async function filterByLevel(level) {
  return prisma.school.findMany({ where: { status: 'ACTIVE', educationLevel: level } });
}
