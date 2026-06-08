/**
 * G19 - 面试历史评价自动预填
 *
 * 提供:
 *  - aggregateHistory: 聚合统计 pass/fail/total
 *  - shouldAutoPrefill: 是否需要自动预填
 *  - buildPreviousFeedbackString: 生成中文预填字符串
 *  - getCandidateHistory: 从 DB 拉取该候选人所有历史反馈
 */

import { prisma } from '../app.js'

/**
 * 聚合统计
 * @param {Array<{result: string}>} feedbacks
 */
export function aggregateHistory(feedbacks) {
  if (!feedbacks?.length) return { passCount: 0, failCount: 0, total: 0 }
  return {
    passCount: feedbacks.filter(f => f.result === 'PASS').length,
    failCount: feedbacks.filter(f => f.result === 'FAIL').length,
    total: feedbacks.length,
  }
}

/**
 * 是否需要自动预填 (有历史才预填)
 */
export function shouldAutoPrefill(summary) {
  return summary.total > 0
}

/**
 * 生成预填字符串 (中文模板)
 */
export function buildPreviousFeedbackString({ passCount, failCount, total, feedbacks }) {
  if (total === 0) return ''
  const lines = [
    `【历史评价汇总】共 ${total} 次面试, ${passCount} 次通过, ${failCount} 次未通过`,
    '',
  ]
  for (const f of feedbacks) {
    const tag = f.result === 'PASS' ? '[PASS]' : '[FAIL]'
    const reason = f.reason ? ` - ${f.reason}` : ''
    const roundLabel = f.roundName || '面试'
    lines.push(`${tag} ${roundLabel} · ${f.interviewerName} · ${f.result}${reason}`)
  }
  return lines.join('\n')
}

/**
 * 获取候选人所有历史面试反馈
 * @param {string} candidateId
 */
export async function getCandidateHistory(candidateId) {
  // 通过 interview.application.candidateId 过滤
  const feedbacks = await prisma.interviewFeedback.findMany({
    where: { interview: { application: { candidateId } } },
    include: {
      interview: {
        include: {
          round: true,
        },
      },
    },
    orderBy: { feedbackAt: 'desc' },
  })

  // 标准化字段: roundName 来自 interview.round.roundName, fallback interview.roundName
  const normalized = feedbacks
    .map(f => ({
      id: f.id,
      result: f.result,
      reason: f.reason,
      interviewerName: f.interviewerName,
      feedbackAt: f.feedbackAt,
      roundName: f.interview?.round?.roundName || f.interview?.roundName || f.roundName || '面试',
    }))
    .sort((a, b) => {
      // 内存中按 feedbackAt 倒序 (DB 排序作为最佳努力, 防止 mock/手工数据乱序)
      const ta = a.feedbackAt ? new Date(a.feedbackAt).getTime() : 0
      const tb = b.feedbackAt ? new Date(b.feedbackAt).getTime() : 0
      return tb - ta
    })

  const summary = aggregateHistory(normalized)
  const previousFeedback = buildPreviousFeedbackString({
    ...summary,
    feedbacks: normalized,
  })
  return { ...summary, previousFeedback, feedbacks: normalized }
}
