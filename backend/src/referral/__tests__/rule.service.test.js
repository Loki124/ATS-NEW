import { jest } from '@jest/globals';
import { createRule, updateRule, toggleRule, listRules, validateConditions } from '../services/rule.service.js';

const mockPrisma = {
  referralRule: {
    create: jest.fn(),
    update: jest.fn(),
    findMany: jest.fn(),
    findUnique: jest.fn(),
  },
};

describe('rule.service', () => {
  beforeEach(() => jest.clearAllMocks());

  it('createRule 校验 conditions 合法性', async () => {
    await expect(
      createRule(mockPrisma, {
        name: 'X',
        ruleType: 'REWARD',
        conditions: { logic: 'ALL', conditions: [{ key: 'unknown', op: 'EQ', value: 'X' }] },
        createdBy: 'u1',
      })
    ).rejects.toThrow(/unknown key/);
  });

  it('createRule 调用 prisma.create', async () => {
    mockPrisma.referralRule.create.mockResolvedValue({ id: 'r1' });
    const r = await createRule(mockPrisma, {
      name: 'Test',
      ruleType: 'MEMBER_RESTRICTION',
      conditions: { logic: 'ALL', conditions: [{ key: 'isManager', op: 'EQ', value: 'NO' }] },
      createdBy: 'u1',
    });
    expect(mockPrisma.referralRule.create).toHaveBeenCalled();
    expect(r.id).toBe('r1');
  });

  it('updateRule INACTIVE 状态不允许改 conditions', async () => {
    mockPrisma.referralRule.findUnique.mockResolvedValue({ id: 'r1', status: 'INACTIVE' });
    await expect(
      updateRule(mockPrisma, 'r1', { conditions: { logic: 'ALL', conditions: [] } })
    ).rejects.toThrow(/INACTIVE/);
  });

  it('toggleRule 切换状态', async () => {
    mockPrisma.referralRule.findUnique.mockResolvedValue({ id: 'r1', status: 'ACTIVE' });
    mockPrisma.referralRule.update.mockResolvedValue({ id: 'r1', status: 'INACTIVE' });
    await toggleRule(mockPrisma, 'r1');
    expect(mockPrisma.referralRule.update).toHaveBeenCalledWith({
      where: { id: 'r1' },
      data: { status: 'INACTIVE' },
    });
  });

  it('listRules 支持 type/status 过滤', async () => {
    mockPrisma.referralRule.findMany.mockResolvedValue([]);
    await listRules(mockPrisma, { ruleType: 'REWARD', status: 'ACTIVE' });
    expect(mockPrisma.referralRule.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { ruleType: 'REWARD', status: 'ACTIVE' },
      })
    );
  });
});
