/**
 * G26 - Offer 手动背调 (4 等级 + 报告)
 *
 * 4 等级:
 *  - PASS         通过 (100 分, terminal)
 *  - WARN         有保留通过 (70 分, terminal, 允许 3 个 risk)
 *  - INCONCLUSIVE 资料不足 (50 分, terminal)
 *  - FAIL         不通过 (0 分, terminal)
 *
 * 状态机: ACTIVE → {PASS|WARN|INCONCLUSIVE|FAIL}, 终态不可再转
 */

import { prisma } from '../app.js'

export const BG_CHECK_LEVELS = {
  PASS:         { level: 'PASS',         label: '通过',       color: 'success',  terminal: true,  riskAllowed: 0,   description: '完全符合要求, 可正常录用' },
  WARN:         { level: 'WARN',         label: '有保留通过', color: 'warning',  terminal: true,  riskAllowed: 3,   description: '有小问题但可接受, 建议入职后关注' },
  INCONCLUSIVE: { level: 'INCONCLUSIVE', label: '资料不足',   color: 'info',     terminal: true,  riskAllowed: 0,   description: '关键信息缺失, 建议补充材料后重新评估' },
  FAIL:         { level: 'FAIL',         label: '不通过',     color: 'error',    terminal: true,  riskAllowed: 999, description: '存在重大问题, 不建议录用' },
}

const TRANSITIONS = {
  ACTIVE: ['PASS', 'WARN', 'INCONCLUSIVE', 'FAIL'],
  PASS: [],
  WARN: [],
  INCONCLUSIVE: [],
  FAIL: [],
}

export function validateLevelTransition(from, to) {
  return (TRANSITIONS[from] || []).includes(to)
}

export function mapLevelToScore(level) {
  return { PASS: 100, WARN: 70, INCONCLUSIVE: 50, FAIL: 0 }[level] ?? null
}

export function isPassingLevel(level) {
  return level === 'PASS' || level === 'WARN'
}

/**
 * 组装 PDF 报告所需数据
 */
export function buildReportData({ offer, candidate, record, supplier } = {}) {
  const candidateName = candidate?.name || '未知候选人'
  const levelInfo = record?.level ? BG_CHECK_LEVELS[record.level] : null
  const levelLabel = levelInfo?.label || (record?.level ? BG_CHECK_LEVELS[record.level]?.label : null) || record?.level || '-'
  const supplierName = supplier || record?.supplier || '内部'
  return {
    title: `背调报告 - ${candidateName}`,
    candidateName,
    sections: [
      {
        heading: '基本信息',
        content: [
          { label: '候选人', value: candidate?.name },
          { label: '候选人电话', value: candidate?.phone },
          { label: 'Offer ID', value: offer?.id },
          { label: '职位', value: offer?.positionName },
          { label: '背调供应商', value: supplierName },
          { label: '背调类型', value: record?.checkType },
        ],
      },
      {
        heading: '背调结论',
        content: [
          { label: '等级', value: levelLabel },
          { label: '说明', value: levelInfo?.description || '-' },
          { label: '评分', value: record?.score ?? '-' },
          { label: '完成时间', value: record?.completedAt ? new Date(record.completedAt).toISOString() : '-' },
        ],
      },
      {
        heading: '风险项',
        content: record?.risks || [],
      },
    ],
  }
}

/**
 * 列出指定 offer 的所有 ACTIVE 背调记录
 */
export async function listBackgroundChecks(offerId) {
  return prisma.backgroundCheckRecord.findMany({
    where: { offerId, status: 'ACTIVE' },
    orderBy: { createdAt: 'desc' },
  })
}

/**
 * 创建一条新的背调记录 (status=ACTIVE)
 */
export async function createBackgroundCheck({ offerId, checkType, supplier, note }) {
  return prisma.backgroundCheckRecord.create({
    data: { offerId, checkType, supplier, note, status: 'ACTIVE' },
  })
}

/**
 * 完成背调: 写 level + score (自动) + risks + completedAt
 */
export async function completeBackgroundCheck(id, { level, risks, reportPath, reportUrl, reportSize }) {
  if (!validateLevelTransition('ACTIVE', level)) {
    throw new Error(`Invalid level transition to ${level}`)
  }
  return prisma.backgroundCheckRecord.update({
    where: { id },
    data: {
      level,
      score: mapLevelToScore(level),
      risks: risks || [],
      reportPath,
      reportUrl,
      reportSize,
      completedAt: new Date(),
    },
  })
}
