import { jest } from '@jest/globals';
import { evaluate, getActiveMemberRestrictions, getActiveRewardRule } from '../services/rule-evaluator.service.js';

const mockPrisma = {
  referralRule: {
    findMany: jest.fn(),
    findFirst: jest.fn(),
  },
};

describe('rule-evaluator.evaluate', () => {
  const user = { isManager: 'NO', internalPosition: 'P5' };
  const position = { positionSeries: 'TECH', positionLevel: 'P5' };

  it('logic=ALL 全部满足 → true', () => {
    const rule = {
      logic: 'ALL',
      conditions: [
        { key: 'isManager', op: 'EQ', value: 'NO' },
        { key: 'internalPosition', op: 'EQ', value: 'P5' },
      ],
    };
    expect(evaluate(rule, { user, position })).toBe(true);
  });

  it('logic=ALL 一条不满足 → false', () => {
    const rule = {
      logic: 'ALL',
      conditions: [
        { key: 'isManager', op: 'EQ', value: 'NO' },
        { key: 'internalPosition', op: 'EQ', value: 'P6' },
      ],
    };
    expect(evaluate(rule, { user, position })).toBe(false);
  });

  it('logic=ANY 一条满足 → true', () => {
    const rule = {
      logic: 'ANY',
      conditions: [
        { key: 'isManager', op: 'EQ', value: 'YES' },
        { key: 'positionSeries', op: 'CONTAINS', value: 'TECH' },
      ],
    };
    expect(evaluate(rule, { user, position })).toBe(true);
  });

  it('EQ 操作符', () => {
    expect(evaluate({ logic: 'ALL', conditions: [{ key: 'isManager', op: 'EQ', value: 'NO' }] }, { user })).toBe(true);
  });

  it('IN 操作符', () => {
    expect(evaluate({ logic: 'ALL', conditions: [{ key: 'positionSeries', op: 'IN', value: ['TECH', 'PRODUCT'] }] }, { user, position })).toBe(true);
  });

  it('NOT_IN 操作符', () => {
    expect(evaluate({ logic: 'ALL', conditions: [{ key: 'positionSeries', op: 'NOT_IN', value: ['SALES'] }] }, { user, position })).toBe(true);
  });

  it('CONTAINS 操作符', () => {
    expect(evaluate({ logic: 'ALL', conditions: [{ key: 'positionSeries', op: 'CONTAINS', value: 'TECH' }] }, { user, position })).toBe(true);
  });

  it('NOT_CONTAINS 操作符', () => {
    expect(evaluate({ logic: 'ALL', conditions: [{ key: 'positionSeries', op: 'NOT_CONTAINS', value: 'SALES' }] }, { user, position })).toBe(true);
  });

  it('GT/GTE/LT/LTE 数值', () => {
    const ctx = { referralCount: 3, user, position };
    expect(evaluate({ logic: 'ALL', conditions: [{ key: 'referralCount', op: 'GT', value: 2 }] }, ctx)).toBe(true);
    expect(evaluate({ logic: 'ALL', conditions: [{ key: 'referralCount', op: 'GTE', value: 3 }] }, ctx)).toBe(true);
    expect(evaluate({ logic: 'ALL', conditions: [{ key: 'referralCount', op: 'LT', value: 5 }] }, ctx)).toBe(true);
    expect(evaluate({ logic: 'ALL', conditions: [{ key: 'referralCount', op: 'LTE', value: 3 }] }, ctx)).toBe(true);
  });

  it('未知 key 抛错', () => {
    expect(() => evaluate({ logic: 'ALL', conditions: [{ key: 'unknown', op: 'EQ', value: 'X' }] }, { user })).toThrow(/unknown key/);
  });

  it('未知 op 抛错', () => {
    expect(() => evaluate({ logic: 'ALL', conditions: [{ key: 'isManager', op: 'WTF', value: 'X' }] }, { user })).toThrow(/unknown op/);
  });

  it('空 conditions 视为 false', () => {
    expect(evaluate({ logic: 'ALL', conditions: [] }, { user })).toBe(false);
  });
});

describe('rule-evaluator.getActive*', () => {
  beforeEach(() => mockPrisma.referralRule.findMany.mockClear());

  it('getActiveMemberRestrictions 调用 prisma', async () => {
    mockPrisma.referralRule.findMany.mockResolvedValue([]);
    await getActiveMemberRestrictions(mockPrisma);
    expect(mockPrisma.referralRule.findMany).toHaveBeenCalledWith({
      where: { ruleType: 'MEMBER_RESTRICTION', status: 'ACTIVE' },
    });
  });

  it('getActiveRewardRule 调用 prisma', async () => {
    mockPrisma.referralRule.findFirst.mockResolvedValue(null);
    await getActiveRewardRule(mockPrisma, 'P5', 'ONBOARDED');
    expect(mockPrisma.referralRule.findFirst).toHaveBeenCalledWith({
      where: { ruleType: 'REWARD', positionLevel: 'P5', triggerStage: 'ONBOARDED', status: 'ACTIVE' },
    });
  });
});
