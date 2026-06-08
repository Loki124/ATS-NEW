// 12 条默认字段 ACL 规则
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

const RULES = [
  // Candidate
  { resource: 'Candidate', field: 'phone',           roleCode: 'INTERVIEWER', action: 'MASK', priority: 10, description: '面试官看手机号脱敏' },
  { resource: 'Candidate', field: 'email',           roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官看邮箱隐藏' },
  { resource: 'Candidate', field: 'expectedSalaryMin',roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官看期望薪资隐藏' },
  { resource: 'Candidate', field: 'expectedSalaryMax',roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官看期望薪资隐藏' },
  { resource: 'Candidate', field: 'phone',           roleCode: 'HRBP',        action: 'VIEW', priority: 5,  description: 'HRBP 看手机号正常' },
  { resource: 'Candidate', field: 'email',           roleCode: 'HRBP',        action: 'MASK', priority: 5,  description: 'HRBP 看邮箱脱敏' },
  { resource: 'Candidate', field: 'expectedSalaryMin',roleCode: 'HRBP',        action: 'VIEW', priority: 5,  description: 'HRBP 看期望薪资' },
  { resource: 'Candidate', field: 'phone',           roleCode: 'HR',          action: 'VIEW', priority: 1,  description: 'HR 看手机号正常' },
  // Resume
  { resource: 'Resume', field: 'phone',              roleCode: 'INTERVIEWER', action: 'MASK', priority: 10, description: '面试官简历手机号脱敏' },
  { resource: 'Resume', field: 'idCard',             roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官身份证隐藏' },
  { resource: 'Resume', field: 'idCard',             roleCode: 'HR',          action: 'MASK', priority: 1,  description: 'HR 身份证脱敏' },
  // Demand
  { resource: 'Demand', field: 'budgetMax',          roleCode: 'INTERVIEWER', action: 'HIDE', priority: 10, description: '面试官看需求预算隐藏' },
];

export async function seedFieldAcl() {
  for (const r of RULES) {
    // Prisma 的复合唯一约束 (resource, field, roleId) 不允许在 where 里传 null,
    // 这里用 findFirst 找现有的 roleId 为 null 的记录, 然后用 update 或 create
    const existing = await prisma.fieldAclRule.findFirst({
      where: { resource: r.resource, field: r.field, roleId: null },
    });
    if (existing) {
      await prisma.fieldAclRule.update({
        where: { id: existing.id },
        data: {
          roleCode: r.roleCode,
          action: r.action,
          maskPattern: r.maskPattern ?? null,
          priority: r.priority,
          description: r.description,
          isActive: true,
        },
      });
    } else {
      await prisma.fieldAclRule.create({
        data: { ...r, roleId: null, maskPattern: r.maskPattern ?? null },
      });
    }
  }
  console.log(`✅ 字段 ACL seed: ${RULES.length} 条规则`);
  await prisma.$disconnect();
}

if (import.meta.url === `file://${process.argv[1]}`) {
  seedFieldAcl();
}
