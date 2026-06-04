const KEY_PATHS = {
  isManager: c => c.user?.isManager,
  positionSeries: c => c.position?.positionSeries,
  demandStakeholder: c => c.position?.demandStakeholder,
  internalPosition: c => c.user?.internalPosition ?? c.user?.positionLevel,
  referralCount: c => c.referralCount ?? (c.referralHistory?.length ?? 0),
  referralIntervalDays: c => c.daysSinceLastReferral,
  positionLevel: c => c.position?.positionLevel,
};

const OP_FNS = {
  EQ: (actual, expected) => actual === expected,
  IN: (actual, expected) => Array.isArray(expected) && expected.includes(actual),
  NOT_IN: (actual, expected) => Array.isArray(expected) && !expected.includes(actual),
  CONTAINS: (actual, expected) => typeof actual === 'string' && actual.includes(String(expected)),
  NOT_CONTAINS: (actual, expected) => typeof actual === 'string' && !actual.includes(String(expected)),
  GT: (actual, expected) => Number(actual) > Number(expected),
  GTE: (actual, expected) => Number(actual) >= Number(expected),
  LT: (actual, expected) => Number(actual) < Number(expected),
  LTE: (actual, expected) => Number(actual) <= Number(expected),
};

export function evaluate(rule, context) {
  if (!rule || !Array.isArray(rule.conditions) || rule.conditions.length === 0) {
    return false;
  }
  const logic = rule.logic ?? 'ALL';
  const results = rule.conditions.map((cond) => {
    const path = KEY_PATHS[cond.key];
    if (!path) throw new Error(`rule-evaluator: unknown key "${cond.key}"`);
    const fn = OP_FNS[cond.op];
    if (!fn) throw new Error(`rule-evaluator: unknown op "${cond.op}"`);
    const actual = path(context);
    return fn(actual, cond.value);
  });
  return logic === 'ANY' ? results.some(Boolean) : results.every(Boolean);
}

export async function getActiveMemberRestrictions(prisma) {
  return prisma.referralRule.findMany({
    where: { ruleType: 'MEMBER_RESTRICTION', status: 'ACTIVE' },
  });
}

export async function getActiveRewardRule(prisma, positionLevel, triggerStage) {
  return prisma.referralRule.findFirst({
    where: { ruleType: 'REWARD', positionLevel, triggerStage, status: 'ACTIVE' },
  });
}
