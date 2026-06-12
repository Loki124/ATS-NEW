/**
 * 跨实体搜索服务 - Plan T1
 *
 * 6 实体 Prisma union,字段裁剪 + 软删除过滤
 * 不引 ES,纯子查询并行,数据量 < 100k 性能可接受
 *
 * 注:本服务 select 字段对齐 schema (Demand.name / Position.name / Interview.application
 *    / Offer.application / ReferralRecord.candidate);软删除条件 deletedAt: null 由
 *    soft-delete.middleware 自动注入,这里显式加上保持显式语义。
 */

import { prisma } from '../app.js'

const ENTITY_KEYS = ['candidate', 'demand', 'position', 'interview', 'offer', 'referral']

const SEARCHERS = {
  candidate: async (q, limit) =>
    prisma.candidate.findMany({
      where: {
        OR: [
          { name:  { contains: q } },
          { phone: { contains: q } },
          { email: { contains: q } },
        ],
        deletedAt: null,
      },
      select: {
        id: true,
        name: true,
        phone: true,
        email: true,
        candidateStatus: true,
        expectedPosition: true,
        code: true,
      },
      orderBy: { updatedAt: 'desc' },
      take: limit,
    }),

  demand: async (q, limit) =>
    prisma.demand.findMany({
      where: {
        OR: [
          { name:        { contains: q } },
          { description: { contains: q } },
        ],
        deletedAt: null,
      },
      select: {
        id: true,
        name: true,
        demandStatus: true,
        positionCount: true,
        hiredCount: true,
        department: { select: { name: true } },
      },
      orderBy: { updatedAt: 'desc' },
      take: limit,
    }),

  position: async (q, limit) =>
    prisma.position.findMany({
      where: {
        OR: [
          { name: { contains: q } },
          { code: { contains: q } },
        ],
        deletedAt: null,
      },
      select: {
        id: true,
        name: true,
        code: true,
        positionStatus: true,
        priority: true,
        department: { select: { name: true } },
      },
      orderBy: { updatedAt: 'desc' },
      take: limit,
    }),

  interview: async (q, limit) =>
    prisma.interview.findMany({
      where: {
        OR: [
          { roundName:        { contains: q } },
          { interviewerNames: { contains: q } },
          { application: { candidate: { name: { contains: q } } } },
          { application: { position:  { name: { contains: q } } } },
        ],
        deletedAt: null,
      },
      select: {
        id: true,
        interviewDate: true,
        interviewStatus: true,
        roundName: true,
        application: {
          select: {
            id: true,
            candidate: { select: { id: true, name: true } },
            position:  { select: { id: true, name: true } },
          },
        },
      },
      orderBy: { interviewDate: 'desc' },
      take: limit,
    }),

  offer: async (q, limit) =>
    prisma.offer.findMany({
      where: {
        OR: [
          { jobTitle: { contains: q } },
          { application: { candidate: { name: { contains: q } } } },
          { application: { position:  { name: { contains: q } } } },
        ],
        deletedAt: null,
      },
      select: {
        id: true,
        onboardingStatus: true,
        expectedJoinDate: true,
        jobTitle: true,
        lastYearAvgSalary: true,
        application: {
          select: {
            id: true,
            candidate: { select: { id: true, name: true } },
            position:  { select: { id: true, name: true } },
          },
        },
      },
      orderBy: { updatedAt: 'desc' },
      take: limit,
    }),

  referral: async (q, limit) =>
    prisma.referralRecord.findMany({
      where: {
        OR: [
          { candidate: { name:  { contains: q } } },
          { candidate: { phone: { contains: q } } },
          { referrer:  { realName: { contains: q } } },
        ],
        deletedAt: null,
      },
      select: {
        id: true,
        referralStatus: true,
        referralType: true,
        recommendedAt: true,
        candidate: { select: { id: true, name: true, phone: true } },
        referrer:  { select: { id: true, realName: true } },
        position:  { select: { id: true, name: true } },
      },
      orderBy: { recommendedAt: 'desc' },
      take: limit,
    }),
}

/**
 * @param {object} args
 * @param {string} args.q
 * @param {string[]} [args.types]
 * @param {number} [args.limit]
 * @param {string} [args.userId]
 */
export async function search({ q, types, limit = 5, userId }) {
  const t0 = Date.now()
  const safeLimit = Math.min(Math.max(parseInt(limit, 10) || 5, 1), 20)
  const wanted = types?.length
    ? types.filter((t) => ENTITY_KEYS.includes(t))
    : ENTITY_KEYS

  const results = await Promise.all(
    wanted.map(async (type) => {
      const searcher = SEARCHERS[type]
      if (!searcher) return null
      try {
        const items = await searcher(q, safeLimit)
        return { type, total: items.length, items }
      } catch (err) {
        console.error(`[search] ${type} failed:`, err.message)
        return { type, total: 0, items: [], error: err.message }
      }
    }),
  )

  return {
    query: q,
    took: Date.now() - t0,
    totalGroups: results.filter((r) => r && r.total > 0).length,
    groups: results.filter(Boolean),
  }
}
