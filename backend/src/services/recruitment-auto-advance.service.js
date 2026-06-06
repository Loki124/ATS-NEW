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
 * 调用入口：
 *   - 自动流转 cron：每 5 分钟扫描一次候选人，看是否满足 autoAdvanceType 条件
 *   - 手动转移阶段：候选人转移阶段前调用
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
 * @param {string} candidateId 候选人
 * @param {string} processId 流程
 * @returns {Promise<{pass: boolean, reason: string}>}
 */
export async function checkN2Skip(candidateId, processId) {
  // 1. 找人经理上级阶段 (N+2 阶段) 的 N+1 阶段 (用人经理评估)
  const n2Stages = await prisma.processStageLink.findMany({
    where: {
      processId,
      stage: { stageType: 'FILTER' },
    },
    include: { stage: true },
    orderBy: { orderIndex: 'asc' },
  });

  // 简化的 N+2 检测：候选人来源渠道 = 'N+2 推荐' + 当前阶段 = N+2
  // 实际业务中 N+2 通常表示: 候选人是从上一级部门 "推荐" 来的（recruiterId != 候选人自身申请）
  const candidate = await prisma.candidate.findUnique({
    where: { id: candidateId },
  });
  if (!candidate) return { pass: false, reason: '候选人不存在' };

  // 简化判定：候选人被标记为 referralType = 'N+2_RECOMMENDED'
  // 实际项目里 N+2 通常通过 Application.recommenderId != 自身 来识别
  // 这里以 candidate.recommenderName 非空作为简化判断
  if (!candidate.recommenderName) {
    return { pass: false, reason: '非推荐候选人，无需 N+2 检测' };
  }
  return { pass: true, reason: 'N+2 推荐候选人，可免筛选' };
}

/**
 * 检查是否满足双 A 免筛选条件
 * 逻辑：
 *   1. 找到候选人最近的人事经理评估阶段记录
 *   2. 该阶段的评估人正好是 2 人
 *   3. 这 2 人必须是同一部门（且是部门负责人 manager + manager2）
 *   4. 这 2 人的部门必须在"双 A 开放"名单内（不在排除名单）
 *   5. 这 2 人的评估结果必须一致（都通过 或 都不通过）
 *   6. 如果全部满足，则该阶段的筛选结果自动填充：标记"通过"或"不通过"，备注"上阶段双A意见一致，系统自动填充"
 *
 * @param {string} candidateId
 * @returns {Promise<{pass: boolean, decision: 'PASS' | 'FAIL' | null, reason: string}>}
 */
export async function checkDoubleASkip(candidateId) {
  // 1. 找到候选人所有筛选记录
  // TODO: 实际表是 ApplicationStageRecord / ScreeningRecord - 简化暂用 referralRecord
  // 这里返回"未实现 - 需要等 ApplicationStageRecord 表建好"
  return {
    pass: false,
    decision: null,
    reason: '双A免筛选检测需要 ApplicationStageRecord 表 - 留待 G1 (需求 8状态机) 时一起建',
  };
}

/**
 * 综合自动流转判定
 * @param {object} link 当前 link（带 rule）
 * @param {string} candidateId
 * @param {object} context 上下文（前序阶段状态、当前候选人等）
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
      // N+2 检测
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
