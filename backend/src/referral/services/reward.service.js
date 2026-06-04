import { getActiveRewardRule } from './rule-evaluator.service.js';

export async function triggerRewardsForCandidate(prisma, candidateId, stage) {
  const records = await prisma.referralRecord.findMany({
    where: { candidateId },
    include: { position: true },
  });
  if (records.length === 0) return [];

  const created = [];
  for (const record of records) {
    const level = record.position?.positionLevel;
    if (!level) continue;
    const rule = await getActiveRewardRule(prisma, level, stage);
    if (!rule) continue;

    const existing = await prisma.referralReward.findFirst({
      where: { recordId: record.id, triggerStage: stage },
    });
    if (existing) continue;

    const reward = await prisma.referralReward.create({
      data: {
        recordId: record.id,
        candidateId,
        amount: rule.amount,
        reason: `${stage} 奖励 - ${rule.name}`,
        triggerStage: stage,
        status: 'PENDING',
        ruleId: rule.id,
      },
    });
    created.push(reward);
  }
  return created;
}

const ALLOWED_FOR_CONFIRM = ['PENDING', 'TO_CONFIRM'];
const ALLOWED_FOR_REJECT = ['PENDING', 'TO_CONFIRM'];
const ALLOWED_FOR_ISSUE = ['CONFIRMED'];

export async function confirmReward(prisma, rewardId, hrbpId) {
  const r = await prisma.referralReward.findUnique({ where: { id: rewardId } });
  if (!r) throw new Error('reward 不存在');
  if (!ALLOWED_FOR_CONFIRM.includes(r.status)) {
    throw new Error(`当前状态 ${r.status} 不允许确认`);
  }
  return prisma.referralReward.update({
    where: { id: rewardId },
    data: { status: 'CONFIRMED', confirmedBy: hrbpId, confirmedAt: new Date() },
  });
}

export async function rejectReward(prisma, rewardId, hrbpId, reason) {
  const r = await prisma.referralReward.findUnique({ where: { id: rewardId } });
  if (!r) throw new Error('reward 不存在');
  if (!ALLOWED_FOR_REJECT.includes(r.status)) {
    throw new Error(`当前状态 ${r.status} 不允许拒绝`);
  }
  return prisma.referralReward.update({
    where: { id: rewardId },
    data: {
      status: 'REJECTED',
      confirmedBy: hrbpId,
      confirmedAt: new Date(),
      rejectedAt: new Date(),
      rejectReason: reason,
    },
  });
}

export async function markIssued(prisma, rewardId) {
  const r = await prisma.referralReward.findUnique({ where: { id: rewardId } });
  if (!r) throw new Error('reward 不存在');
  if (!ALLOWED_FOR_ISSUE.includes(r.status)) {
    throw new Error(`当前状态 ${r.status} 不允许发放`);
  }
  return prisma.referralReward.update({
    where: { id: rewardId },
    data: { status: 'ISSUED', issuedAt: new Date() },
  });
}

export async function listRewardsForReferrer(prisma, referrerId, opts = {}) {
  const { page = 1, pageSize = 20, status } = opts;
  const records = await prisma.referralRecord.findMany({
    where: { referrerId },
    select: { id: true },
  });
  const recordIds = records.map(r => r.id);
  if (recordIds.length === 0) {
    return { list: [], total: 0, page, pageSize };
  }

  const where = { recordId: { in: recordIds } };
  if (status) where.status = status;

  const [list, total] = await Promise.all([
    prisma.referralReward.findMany({
      where,
      include: { candidate: true, record: { include: { position: true } } },
      orderBy: { triggeredAt: 'desc' },
      skip: (page - 1) * pageSize,
      take: pageSize,
    }),
    prisma.referralReward.count({ where }),
  ]);
  return { list, total, page, pageSize };
}

export async function getRewardSummary(prisma, referrerId) {
  const records = await prisma.referralRecord.findMany({
    where: { referrerId },
    select: { id: true },
  });
  const recordIds = records.map(r => r.id);
  if (recordIds.length === 0) {
    return { TO_CONFIRM: 0, CONFIRMED: 0, ISSUED: 0, REJECTED: 0 };
  }

  const groups = await prisma.referralReward.groupBy({
    by: ['status'],
    where: { recordId: { in: recordIds } },
    _sum: { amount: true },
  });

  const summary = { TO_CONFIRM: 0, CONFIRMED: 0, ISSUED: 0, REJECTED: 0 };
  for (const g of groups) {
    const amt = Number(g._sum.amount ?? 0);
    if (g.status in summary) summary[g.status] = amt;
  }
  return summary;
}
