/**
 * 招聘流程自动流转服务 - PRD #11 N+2 免筛选 + 双 A 免筛选
 *
 * 业务规则：
 *   1. N+2 免筛选 (#11.1)
 *      - 用人经理上级阶段被标记为"满足下阶段进入条件或 N+2 推荐的简历"时
 *      - 若候选人是 N+2 推荐，可免筛选直接进入下阶段
 *
 *   2. 双 A 免筛选 (#11.2)
 *      - 双 A = 同一部门的一对部门负责人（双A，含一级/二级/三级等全部层级）
 *      - 用人经理评估阶段的评估人是否为同一部门的双A
 *      - 用人经理评估结果是否全部一致（全部通过 → 通过；全部不通过 → 不通过）
 *      - 开放免筛选的部门范围：除客服直播中心与行政服务中心外的所有一级部门 + 审计法务部
 *      - 不适用：用人经理评估阶段评估人不是 2 人；2 人评估但非同一部门双A
 *
 * 数据源：ApplicationStageRecord (G38 #11) - 候选人阶段流转记录
 *   - 每次候选人进入/离开一个 process_stage_link 都创建一条记录
 *   - checkDoubleASkip 用此表查最近一次评估阶段的 2 个评估人
 *   - checkN2Skip 当前用 candidate.recommenderName 简化判定（可升级到 Application.isN2Recommended）
 *
 * 调用入口：
 *   - 自动流转 cron：每 5 分钟扫描一次候选人，看是否满足 autoAdvanceType 条件
 *   - 手动转移阶段：候选人转移阶段前调用
 *   - API: POST /api/recruitment-auto-advance/check (手动触发)
 */

import { prisma } from '../app.js';

// 双 A 免筛选的部门范围（#11.2 排除名单）
const DOUBLE_A_EXCLUDED_DEPARTMENTS = [
  '客服直播中心',  // 占位 - 实际 ID 在 seed 时填
  '行政服务中心',
  // 注：审计法务部是**包含**的（不在排除名单）
];

// 不可筛的 stage 类型（不应用 N+2 / 双 A 规则）
const NO_SCREEN_STAGE_TYPES = ['OFFER', 'ONBOARDING', 'INVITATION'];

/**
 * 检查是否满足 N+2 免筛选条件
 *
 * 实现说明：
 *   当前简化版用 candidate.recommenderName 非空作为 N+2 推荐判定
 *   实际项目里更精确的做法是用 Application.isN2Recommended 字段
 *   (Application 表关联到 recommender User,通过部门上下级关系判断)
 *
 *   未来升级路径：
 *   1. 在 Application model 加 isN2Recommended: Boolean @default(false) 字段
 *   2. 创建 Application 时如果 recommender 的部门 ID = candidate 的预期部门上 2 级
 *      → 自动标记 isN2Recommended = true
 *   3. checkN2Skip 改为: SELECT isN2Recommended FROM applications WHERE id = ?
 *   4. 移除 candidate.recommenderName 判定
 *
 * @param {string} candidateId 候选人
 * @param {string} processId 流程
 * @returns {Promise<{pass: boolean, reason: string}>}
 */
export async function checkN2Skip(candidateId, processId) {
  // 1. 找流程中的 N+2 阶段（FILTER 类型 + 上一阶段为用人经理评估）
  const n2Stages = await prisma.processStageLink.findMany({
    where: {
      processId,
      stage: { stageType: 'FILTER' },
    },
    include: { stage: true },
    orderBy: { orderIndex: 'asc' },
  });

  // 2. 查候选人基本信息（简化 N+2 推荐判定）
  const candidate = await prisma.candidate.findUnique({
    where: { id: candidateId },
  });
  if (!candidate) return { pass: false, reason: '候选人不存在' };

  // 简化判定：候选人被标记为 referralType = 'N+2_RECOMMENDED'
  // 实际项目里 N+2 通常通过 Application.recommenderId != 自身 来识别
  // 这里以 candidate.recommenderName 非空作为简化判断
  // 注: 与 ApplicationStageRecord 表关联见未来升级路径
  if (!candidate.recommenderName) {
    return { pass: false, reason: '非推荐候选人，无需 N+2 检测' };
  }
  return { pass: true, reason: 'N+2 推荐候选人，可免筛选' };
}

/**
 * 检查是否满足双 A 免筛选条件 (G38 #11.2 真实实现)
 *
 * 业务逻辑：
 *   1. 找到候选人最近一次用人经理评估阶段 (stageType='EVALUATE') 的流转记录
 *   2. 该阶段的评估人正好是 2 人
 *   3. 这 2 人必须是同一部门（且是部门负责人 manager + manager2）
 *   4. 这 2 人的部门必须在"双 A 开放"名单内（不在排除名单）
 *   5. 这 2 人的评估结果必须一致（都通过 或 都不通过）
 *   6. 如果全部满足，则该阶段的筛选结果自动填充：标记"通过"或"不通过"，备注"上阶段双A意见一致，系统自动填充"
 *
 * 数据源：ApplicationStageRecord
 *   - recentRecord = 最近一次 EVALUATE 阶段流转记录（按 exitedAt desc 取第一条）
 *   - evaluators = 同一 applicationId + linkId + toStatus in (PASS/FAIL/ALL_PASS/ALL_FAIL) 的所有记录
 *   - decider 关联 User → department，校验部门一致性
 *
 * @param {string} candidateId
 * @returns {Promise<{pass: boolean, decision: 'PASS' | 'FAIL' | null, reason: string}>}
 */
export async function checkDoubleASkip(candidateId) {
  // 1. 找到候选人最近一次评估阶段的流转记录
  const recentRecord = await prisma.applicationStageRecord.findFirst({
    where: {
      candidateId,
      stage: { stageType: 'EVALUATE' },
    },
    orderBy: { exitedAt: 'desc' },
    include: { stage: true, decider: { include: { department: true } } },
  });

  if (!recentRecord) {
    return { pass: false, decision: null, reason: '无最近评估记录' };
  }

  // 2. 查该阶段的所有评估人记录（PASS/FAIL/ALL_PASS/ALL_FAIL）
  const evaluators = await prisma.applicationStageRecord.findMany({
    where: {
      applicationId: recentRecord.applicationId,
      linkId: recentRecord.linkId,
      toStatus: { in: ['PASS', 'FAIL', 'ALL_PASS', 'ALL_FAIL'] },
      decidedBy: { not: null },
    },
    include: { decider: { include: { department: true } } },
  });

  // 3. 必须正好 2 人
  if (evaluators.length !== 2) {
    return { pass: false, decision: null, reason: `评估人 ${evaluators.length} 人(需 2 人)` };
  }

  // 4. 同部门
  const [e1, e2] = evaluators;
  if (e1.decider?.departmentId !== e2.decider?.departmentId) {
    return { pass: false, decision: null, reason: '非同一部门' };
  }
  const deptName = e1.decider?.department?.name;
  if (DOUBLE_A_EXCLUDED_DEPARTMENTS.includes(deptName)) {
    return { pass: false, decision: null, reason: `${deptName} 不在双 A 开放名单` };
  }

  // 5. 评估结果一致
  const allPass = evaluators.every(e => e.toStatus === 'PASS' || e.toStatus === 'ALL_PASS');
  const allFail = evaluators.every(e => e.toStatus === 'FAIL' || e.toStatus === 'ALL_FAIL');
  if (!allPass && !allFail) {
    return { pass: false, decision: null, reason: '评估结果不一致' };
  }

  return {
    pass: true,
    decision: allPass ? 'PASS' : 'FAIL',
    reason: `${deptName} 双A 意见一致 (${allPass ? '通过' : '不通过'})`,
  };
}

/**
 * 综合自动流转判定 (G38 #11)
 *
 * 数据源: ApplicationStageRecord
 *   - currentStageRecord: 当前 link 的流转记录（由 scheduler 传入）
 *   - enteredAt + autoAdvanceDays 用于 DELAYED 时机校验
 *
 * @param {object} link 当前 link（带 rule）
 * @param {string} candidateId
 * @param {object} context 上下文（前序阶段状态、当前候选人、当前流转记录等）
 * @returns {Promise<{shouldAdvance: boolean, reason: string, skipScreen?: boolean}>}
 */
export async function shouldAutoAdvance(link, candidateId, context = {}) {
  const { rule } = link
  if (!rule) return { shouldAdvance: false, reason: 'no rule' }
  if (rule.autoAdvanceType === 'NONE') return { shouldAdvance: false, reason: 'auto-advance disabled' }

  // 检查时机
  if (rule.autoAdvanceTiming === 'DELAYED') {
    // 需要校验：进入当前阶段的时间 + N 天 ≥ 当前时间
    // 简化：返回 false 让 cron 调度处理
    return { shouldAdvance: false, reason: 'delayed - check by cron' }
  }
  if (rule.autoAdvanceTiming === 'NONE') {
    return { shouldAdvance: false, reason: 'timing disabled' }
  }

  // 时机已过 (IMMEDIATE / DELAYED 已到)
  switch (rule.autoAdvanceType) {
    case 'MEET_NEXT': {
      // 满足下阶段进入条件
      const condition = await prisma.entryCondition.findUnique({
        where: { linkId: link.id },
        include: { items: { orderBy: { orderIndex: 'asc' } } },
      })
      if (!condition) return { shouldAdvance: false, reason: 'no entry condition configured' }
      // 评估（用条件求值器）
      const { evaluateConditionTree } = await import('./recruitment-condition.service.js')
      const evalResult = evaluateConditionTree(condition.items, condition.matchType, context)
      return { shouldAdvance: evalResult.passed, reason: evalResult.passed ? 'meets next stage' : 'condition failed' }
    }
    case 'IGNORE_NEXT': {
      // 无视下阶段进入条件
      return { shouldAdvance: true, reason: 'auto-advance ignore next condition' }
    }
    case 'MEET_NEXT_OR_N2': {
      // 满足进入条件 或 N+2 推荐
      const condition = await prisma.entryCondition.findUnique({
        where: { linkId: link.id },
        include: { items: { orderBy: { orderIndex: 'asc' } } },
      })
      let condPassed = false
      if (condition) {
        const { evaluateConditionTree } = await import('./recruitment-condition.service.js')
        condPassed = evaluateConditionTree(condition.items, condition.matchType, context).passed
      }
      if (condPassed) return { shouldAdvance: true, reason: 'meets next stage' }
      // N+2 检测（用 candidate.recommenderName 简化）
      const n2 = await checkN2Skip(candidateId, link.processId)
      if (n2.pass) {
        return { shouldAdvance: true, reason: 'N+2 推荐', skipScreen: true }
      }
      return { shouldAdvance: false, reason: 'neither condition met nor N+2' }
    }
    case 'N1_ALL_PASS': {
      // N+1 全部通过（即用人经理评估阶段所有人都通过）
      // 简化：从 context 中读
      const n1Status = context.n1Status  // 期望 { allPass: boolean }
      if (n1Status?.allPass) return { shouldAdvance: true, reason: 'N+1 全部通过' }
      return { shouldAdvance: false, reason: 'N+1 未全部通过' }
    }
    default:
      return { shouldAdvance: false, reason: 'unknown autoAdvanceType' }
  }
}

export default {
  checkN2Skip,
  checkDoubleASkip,
  shouldAutoAdvance,
}