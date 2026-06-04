import { jest } from '@jest/globals';
import {
  createReferral,
  transitionRecord,
  listForReferrer,
  handleCandidateStageChange,
} from '../services/record.service.js';

const mockPrisma = {
  referralCode: { findUnique: jest.fn() },
  referralRecord: { findUnique: jest.fn(), findMany: jest.fn(), create: jest.fn(), update: jest.fn(), count: jest.fn() },
  user: { findUnique: jest.fn() },
  position: { findUnique: jest.fn() },
  referralExpertConfig: { findFirst: jest.fn() },
  referralRule: { findMany: jest.fn() },
};

describe('createReferral', () => {
  beforeEach(() => jest.clearAllMocks());

  it('有效内推：创建 record', async () => {
    mockPrisma.referralCode.findUnique.mockResolvedValue({ id: 'c1', userId: 'u1', status: 'ACTIVE', code: 'ABC123' });
    mockPrisma.referralRecord.findUnique.mockResolvedValue(null);
    mockPrisma.user.findUnique.mockResolvedValue({ id: 'u1', isManager: 'NO' });
    mockPrisma.position.findUnique.mockResolvedValue({ id: 'p1', positionLevel: 'P5' });
    mockPrisma.referralRule.findMany.mockResolvedValue([]);
    mockPrisma.referralRecord.create.mockResolvedValue({ id: 'r1' });

    const r = await createReferral(mockPrisma, {
      referrerId: 'u1', candidateId: 'cand1', positionId: 'p1', referralType: 'REFERRER_HELP',
    });
    expect(r.record.id).toBe('r1');
    expect(r.created).toBe(true);
  });

  it('内推码失效：返回无效', async () => {
    mockPrisma.referralCode.findUnique.mockResolvedValue({ status: 'INVALID', invalidReason: 'LEAVER' });
    const r = await createReferral(mockPrisma, { referrerId: 'u1', candidateId: 'c1', positionId: 'p1', referralType: 'X' });
    expect(r.created).toBe(false);
    expect(r.invalidReason).toBe('CODE_INVALID');
  });

  it('重复推荐：返回 existing', async () => {
    mockPrisma.referralCode.findUnique.mockResolvedValue({ status: 'ACTIVE', code: 'X' });
    mockPrisma.referralRecord.findUnique.mockResolvedValue({ id: 'r_existing' });
    const r = await createReferral(mockPrisma, { referrerId: 'u1', candidateId: 'c1', positionId: 'p1', referralType: 'X' });
    expect(r.created).toBe(false);
    expect(r.record.id).toBe('r_existing');
  });
});

describe('listForReferrer', () => {
  beforeEach(() => jest.clearAllMocks());

  it('默认隐藏 INVALID', async () => {
    mockPrisma.referralRecord.findMany.mockResolvedValue([]);
    mockPrisma.referralRecord.count.mockResolvedValue(0);
    await listForReferrer(mockPrisma, 'u1', { page: 1, pageSize: 20 });
    const call = mockPrisma.referralRecord.findMany.mock.calls[0][0];
    expect(call.where.referralStatus).toEqual({ not: 'INVALID' });
  });
});
