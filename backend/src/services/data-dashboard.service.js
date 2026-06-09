/**
 * G35 - 基础 KPI 看板 (业务侧 KPI 后续按需扩展)
 */
import { prisma } from '../app.js';

export async function getDashboardKpi() {
  const [
    totalCandidates, activeDemands, openPositions,
    ongoingInterviews, sentOffers, pendingOnboardings,
  ] = await Promise.all([
    prisma.candidate.count(),
    prisma.demand.count({ where: { status: { in: ['IN_PROGRESS', 'APPROVED'] } } }),
    prisma.position.count({ where: { status: 'ACTIVE' } }),
    prisma.interview.count({ where: { interviewStatus: { in: ['SCHEDULED', 'IN_PROGRESS'] } } }),
    prisma.offer.count({ where: { status: { in: ['SENT', 'NEGOTIATING'] } } }),
    prisma.onboarding.count({ where: { status: { in: ['PENDING_ONBOARD', 'CONFIRMED'] } } }),
  ]);
  return {
    totalCandidates, activeDemands, openPositions,
    ongoingInterviews, sentOffers, pendingOnboardings,
    generatedAt: new Date().toISOString(),
  };
}
