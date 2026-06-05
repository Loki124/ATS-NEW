import { createActor } from 'xstate';
import { referralRecordMachine } from '../machines/referralRecord.machine.js';
import { evaluate, getActiveMemberRestrictions } from './rule-evaluator.service.js';

/**
 * 创建内推记录（含去重 + 有效性判定）
 */
export async function createReferral(prisma, params) {
  const { referrerId, candidateId, positionId, resumeId, expertId, referralType } = params;

  // 1. 校验内推码状态
  const code = await prisma.referralCode.findUnique({ where: { userId: referrerId } });
  if (!code) {
    return { record: null, created: false, invalidReason: 'CODE_NOT_FOUND' };
  }
  if (code.status !== 'ACTIVE') {
    return { record: null, created: false, invalidReason: 'CODE_INVALID' };
  }

  // 2. 去重
  const existing = await prisma.referralRecord.findUnique({
    where: {
      uniq_candidate_position_referrer: { candidateId, positionId, referrerId },
    },
  });
  if (existing) {
    return { record: existing, created: false };
  }

  // 3. 成员限制
  const user = await prisma.user.findUnique({ where: { id: referrerId } });
  const position = await prisma.position.findUnique({ where: { id: positionId } });
  const restrictions = await getActiveMemberRestrictions(prisma);
  for (const rule of restrictions) {
    const blocked = evaluate(rule.conditions, {
      user: { ...user, positionLevel: position?.positionLevel },
      position,
    });
    if (blocked) {
      return { record: null, created: false, invalidReason: 'NOT_QUALIFIED' };
    }
  }

  // 4. 招聘专家
  let finalExpertId = expertId;
  if (!finalExpertId) {
    const config = await prisma.referralExpertConfig.findFirst({
      where: { userId: referrerId, isPrimary: true },
    });
    finalExpertId = config?.expertId ?? referrerId;
  }

  // 5. 保护期
  const protectionDays = 7;
  const protectionEndAt = new Date(Date.now() + protectionDays * 86400000);

  // 6. 创建
  const record = await prisma.referralRecord.create({
    data: {
      referrerId,
      referrerCode: code.code,
      candidateId,
      resumeId: resumeId ?? null,
      positionId,
      expertId: finalExpertId,
      referralType,
      referralStatus: 'NORMAL',
      protectionEndAt,
    },
  });

  return { record, created: true };
}

/**
 * 状态机推进
 */
export async function transitionRecord(prisma, recordId, event) {
  const record = await prisma.referralRecord.findUnique({ where: { id: recordId } });
  if (!record) throw new Error('record 不存在');

  if (['COMPLETED', 'INVALID'].includes(record.referralStatus)) {
    return record;
  }

  const actor = createActor(referralRecordMachine).start();
  actor.send(event);
  const next = actor.getSnapshot().value;

  if (next === record.referralStatus) return record;

  return prisma.referralRecord.update({
    where: { id: recordId },
    data: {
      referralStatus: next,
      statusChangedAt: new Date(),
      ...(event.reason ? { invalidReason: event.reason } : {}),
    },
  });
}

/**
 * 候选人阶段变化时批量更新
 */
export async function handleCandidateStageChange(prisma, candidateId, fromStage, toStage) {
  const records = await prisma.referralRecord.findMany({
    where: { candidateId, referralStatus: { in: ['NORMAL', 'PROTECTING'] } },
  });
  for (const r of records) {
    const isProtectionActive = r.protectionEndAt ? new Date(r.protectionEndAt) > new Date() : false;
    await transitionRecord(prisma, r.id, {
      type: 'STAGE_CHANGED',
      from: fromStage,
      to: toStage,
      isProtectionActive,
    });
  }
}

/**
 * 我的内推列表
 */
export async function listForReferrer(prisma, referrerId, opts = {}) {
  // 修复：query string 的 page/pageSize 是字符串
  const page = Number(opts.page) || 1;
  const pageSize = Number(opts.pageSize) || 20;
  const { status, positionId, includeInvalid = false } = opts;
  const where = { referrerId };
  if (positionId) where.positionId = positionId;
  if (status) where.referralStatus = status;
  else if (!includeInvalid) where.referralStatus = { not: 'INVALID' };

  const [list, total] = await Promise.all([
    prisma.referralRecord.findMany({
      where,
      include: { candidate: true, position: true, expert: true, rewards: true },
      orderBy: { createdAt: 'desc' },
      skip: (page - 1) * pageSize,
      take: pageSize,
    }),
    prisma.referralRecord.count({ where }),
  ]);

  return { list, total, page, pageSize };
}

/**
 * 管理端列表
 */
export async function listForManagement(prisma, filters = {}) {
  const { page = 1, pageSize = 20, referrerId, expertId, positionId, referralStatus } = filters;
  const where = {};
  if (referrerId) where.referrerId = referrerId;
  if (expertId) where.expertId = expertId;
  if (positionId) where.positionId = positionId;
  if (referralStatus) where.referralStatus = referralStatus;
  else where.referralStatus = { not: 'INVALID' };

  const [list, total] = await Promise.all([
    prisma.referralRecord.findMany({
      where,
      include: { referrer: true, candidate: true, position: true, expert: true, rewards: true },
      orderBy: { createdAt: 'desc' },
      skip: (page - 1) * pageSize,
      take: pageSize,
    }),
    prisma.referralRecord.count({ where }),
  ]);

  return { list, total, page, pageSize };
}
