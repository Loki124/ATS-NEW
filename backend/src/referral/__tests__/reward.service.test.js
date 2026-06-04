import { jest } from '@jest/globals';
import { triggerRewardsForCandidate, confirmReward, listRewardsForReferrer, getRewardSummary } from '../services/reward.service.js';

const mockPrisma = {
  referralRecord: { findMany: jest.fn() },
  referralRule: { findFirst: jest.fn() },
  referralReward: { findFirst: jest.fn(), findUnique: jest.fn(), create: jest.fn(), findMany: jest.fn(), count: jest.fn(), update: jest.fn(), groupBy: jest.fn() },
};

describe('triggerRewardsForCandidate', () => {
  beforeEach(() => jest.clearAllMocks());

  it('无 record → 返回空', async () => {
    mockPrisma.referralRecord.findMany.mockResolvedValue([]);
    const r = await triggerRewardsForCandidate(mockPrisma, 'cand1', 'ONBOARDED');
    expect(r).toEqual([]);
  });

  it('record 存在，规则匹配 → 创建 PENDING', async () => {
    mockPrisma.referralRecord.findMany.mockResolvedValue([{ id: 'r1', position: { positionLevel: 'P5' } }]);
    mockPrisma.referralRule.findFirst.mockResolvedValue({ id: 'rule1', amount: 3000 });
    mockPrisma.referralReward.findFirst.mockResolvedValue(null);
    mockPrisma.referralReward.create.mockResolvedValue({ id: 'reward1' });
    const r = await triggerRewardsForCandidate(mockPrisma, 'cand1', 'ONBOARDED');
    expect(r.length).toBe(1);
  });

  it('已有 reward → 跳过', async () => {
    mockPrisma.referralRecord.findMany.mockResolvedValue([{ id: 'r1', position: { positionLevel: 'P5' } }]);
    mockPrisma.referralRule.findFirst.mockResolvedValue({ id: 'rule1', amount: 3000 });
    mockPrisma.referralReward.findFirst.mockResolvedValue({ id: 'existing' });
    const r = await triggerRewardsForCandidate(mockPrisma, 'cand1', 'ONBOARDED');
    expect(r).toEqual([]);
  });
});

describe('confirmReward', () => {
  it('PENDING → CONFIRMED', async () => {
    mockPrisma.referralReward.findUnique.mockResolvedValue({ id: 'rw1', status: 'PENDING' });
    mockPrisma.referralReward.update.mockResolvedValue({ id: 'rw1', status: 'CONFIRMED' });
    const r = await confirmReward(mockPrisma, 'rw1', 'hrbp1');
    expect(r.status).toBe('CONFIRMED');
  });

  it('非 PENDING/TO_CONFIRM 抛错', async () => {
    mockPrisma.referralReward.findUnique.mockResolvedValue({ id: 'rw1', status: 'ISSUED' });
    await expect(confirmReward(mockPrisma, 'rw1', 'h1')).rejects.toThrow(/不允许/);
  });
});

describe('getRewardSummary', () => {
  it('汇总各状态金额', async () => {
    mockPrisma.referralRecord.findMany.mockResolvedValue([{ id: 'r1' }]);
    mockPrisma.referralReward.groupBy.mockResolvedValue([
      { status: 'TO_CONFIRM', _sum: { amount: 3000 } },
      { status: 'ISSUED', _sum: { amount: 5000 } },
    ]);
    const s = await getRewardSummary(mockPrisma, 'u1');
    expect(s.TO_CONFIRM).toBe(3000);
    expect(s.ISSUED).toBe(5000);
    expect(s.CONFIRMED).toBe(0);
  });
});
