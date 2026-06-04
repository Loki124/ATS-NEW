import { jest } from '@jest/globals';
import { generateCode, createCodeForUser, validateCode } from '../services/code.service.js';

const mockPrisma = {
  referralCode: {
    findUnique: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
  },
};

describe('code.service - generate', () => {
  it('generateCode 返回 6 位 字母数字', () => {
    const code = generateCode();
    expect(code).toMatch(/^[A-Za-z0-9]{6}$/);
  });

  it('generateCode 1000 个不重复', () => {
    const codes = new Set(Array.from({ length: 1000 }, () => generateCode()));
    expect(codes.size).toBeGreaterThan(990);
  });
});

describe('code.service - createCodeForUser', () => {
  beforeEach(() => jest.clearAllMocks());

  it('已存在则返回现有', async () => {
    mockPrisma.referralCode.findUnique.mockResolvedValue({ id: 'c1', code: 'ABC123', userId: 'u1' });
    const r = await createCodeForUser(mockPrisma, 'u1');
    expect(r.id).toBe('c1');
    expect(mockPrisma.referralCode.create).not.toHaveBeenCalled();
  });

  it('不存在则创建（去重碰撞）', async () => {
    mockPrisma.referralCode.findUnique
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ id: 'conflict' })
      .mockResolvedValueOnce(null);
    mockPrisma.referralCode.create.mockResolvedValue({ id: 'c2' });
    const r = await createCodeForUser(mockPrisma, 'u1');
    expect(mockPrisma.referralCode.create).toHaveBeenCalledTimes(1);
    expect(r.id).toBe('c2');
  });
});

describe('code.service - validateCode', () => {
  beforeEach(() => jest.clearAllMocks());

  it('不存在 → valid=false reason=NOT_FOUND', async () => {
    mockPrisma.referralCode.findUnique.mockResolvedValue(null);
    const r = await validateCode(mockPrisma, 'NOPE12');
    expect(r).toEqual({ valid: false, reason: 'NOT_FOUND' });
  });

  it('INVALID → valid=false', async () => {
    mockPrisma.referralCode.findUnique.mockResolvedValue({
      id: 'c1', code: 'X', status: 'INVALID', invalidReason: 'LEAVER',
    });
    const r = await validateCode(mockPrisma, 'X');
    expect(r.valid).toBe(false);
    expect(r.reason).toBe('LEAVER');
  });

  it('ACTIVE → valid=true', async () => {
    mockPrisma.referralCode.findUnique.mockResolvedValue({ id: 'c1', code: 'X', status: 'ACTIVE' });
    const r = await validateCode(mockPrisma, 'X');
    expect(r.valid).toBe(true);
    expect(r.code.id).toBe('c1');
  });
});
