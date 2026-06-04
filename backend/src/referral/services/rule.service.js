import { evaluate } from './rule-evaluator.service.js';

export function validateConditions(conditions) {
  if (!conditions || !Array.isArray(conditions.conditions) || conditions.conditions.length === 0) {
    throw new Error('conditions 必须是非空数组');
  }
  for (const cond of conditions.conditions) {
    if (!cond.key || !cond.op) throw new Error('condition 缺少 key 或 op');
  }
  try {
    evaluate(conditions, { user: {}, position: {} });
  } catch (e) {
    throw e;
  }
}

export async function createRule(prisma, data) {
  validateConditions(data.conditions);
  return prisma.referralRule.create({
    data: {
      name: data.name,
      ruleType: data.ruleType,
      positionLevel: data.positionLevel ?? null,
      triggerStage: data.triggerStage ?? null,
      conditions: data.conditions,
      amount: data.amount ?? null,
      createdBy: data.createdBy,
    },
  });
}

export async function updateRule(prisma, id, patch) {
  if (patch.conditions) {
    const existing = await prisma.referralRule.findUnique({ where: { id } });
    if (existing && existing.status === 'INACTIVE') {
      throw new Error('INACTIVE 状态的规则不允许修改 conditions');
    }
    validateConditions(patch.conditions);
  }
  return prisma.referralRule.update({
    where: { id },
    data: patch,
  });
}

export async function toggleRule(prisma, id) {
  const r = await prisma.referralRule.findUnique({ where: { id } });
  if (!r) throw new Error('规则不存在');
  return prisma.referralRule.update({
    where: { id },
    data: { status: r.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE' },
  });
}

export async function listRules(prisma, filters = {}) {
  return prisma.referralRule.findMany({
    where: {
      ...(filters.ruleType && { ruleType: filters.ruleType }),
      ...(filters.status && { status: filters.status }),
    },
    orderBy: { createdAt: 'desc' },
  });
}
