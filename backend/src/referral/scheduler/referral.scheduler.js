import cron from 'node-cron';
import { transitionRecord } from '../services/record.service.js';
import { triggerRewardsForCandidate } from '../services/reward.service.js';

const tasks = [];

async function scanExpiredProtection(prisma) {
  const now = new Date();
  const records = await prisma.referralRecord.findMany({
    where: {
      protectionEndAt: { lte: now },
      referralStatus: { in: ['NORMAL', 'PROTECTING'] },
    },
    select: { id: true },
  });
  for (const r of records) {
    await transitionRecord(prisma, r.id, { type: 'PROTECTION_EXPIRED' });
  }
  if (records.length) console.log(`[referral-scheduler] expired protection: ${records.length}`);
}

async function scanOnboardedCandidates(prisma) {
  try {
    const onboardings = await prisma.onboarding.findMany({
      where: { status: 'ONBOARDED' },
      include: { application: { include: { candidate: true } } },
    });
    for (const ob of onboardings) {
      const candidateId = ob.application?.candidateId;
      if (candidateId) {
        await triggerRewardsForCandidate(prisma, candidateId, 'ONBOARDED');
      }
    }
  } catch (e) {
    console.error('[referral-scheduler] scanOnboarded failed:', e.message);
  }
}

async function scanInvalidCodes(_prisma) {
  // event-driven only in Phase 1
  console.log('[referral-scheduler] scanInvalidCodes: skipped (event-driven)');
}

export function startReferralScheduler(prisma) {
  if (!prisma) {
    console.warn('[referral-scheduler] no prisma instance provided, scheduler disabled');
    return;
  }
  tasks.push(cron.schedule('0 * * * *', () => scanExpiredProtection(prisma).catch(console.error)));
  tasks.push(cron.schedule('*/15 * * * *', () => scanOnboardedCandidates(prisma).catch(console.error)));
  tasks.push(cron.schedule('0 0 * * *', () => scanInvalidCodes(prisma).catch(console.error)));
  console.log('[referral-scheduler] started with 3 cron tasks');
}

export function stopReferralScheduler() {
  for (const t of tasks) {
    if (t && typeof t.stop === 'function') t.stop();
  }
  tasks.length = 0;
  console.log('[referral-scheduler] stopped');
}
