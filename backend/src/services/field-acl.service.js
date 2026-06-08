// G43 - 字段 ACL 规则 service

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export async function listRules({ resource, roleCode } = {}) {
  const where = { isActive: true };
  if (resource) where.resource = resource;
  if (roleCode) where.roleCode = roleCode;
  return prisma.fieldAclRule.findMany({ where, orderBy: { priority: 'desc' } });
}

export async function getMatrix() {
  const rules = await prisma.fieldAclRule.findMany({
    where: { isActive: true },
    orderBy: { resource: 'asc', field: 'asc' },
  });
  // 转换为矩阵: resources → fields → roles → action
  const matrix = {};
  for (const r of rules) {
    if (!matrix[r.resource]) matrix[r.resource] = {};
    if (!matrix[r.resource][r.field]) matrix[r.resource][r.field] = {};
    matrix[r.resource][r.field][r.roleCode || '*'] = r.action;
  }
  return matrix;
}

export async function upsertRule({ resource, field, roleId, roleCode, action, maskPattern, priority, description }) {
  return prisma.fieldAclRule.upsert({
    where: { resource_field_roleId: { resource, field, roleId: roleId || null } },
    create: { resource, field, roleId: roleId || null, roleCode, action, maskPattern, priority: priority || 0, description },
    update: { roleCode, action, maskPattern, priority, description, isActive: true },
  });
}

export async function deleteRule(id) {
  return prisma.fieldAclRule.update({ where: { id }, data: { isActive: false } });
}

export async function queryAudit({ userId, resource, field, limit = 50 } = {}) {
  const where = {};
  if (userId) where.userId = userId;
  if (resource) where.resource = resource;
  if (field) where.field = field;
  return prisma.fieldAclAudit.findMany({
    where, orderBy: { createdAt: 'desc' }, take: limit,
  });
}
