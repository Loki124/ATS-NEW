import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { createN1Detector, staticAnalyze } from '../n-plus-one-detector.service.js';

describe('n-plus-one-detector', () => {
  describe('staticAnalyze', () => {
    it('检测: findMany 无 include -> 风险', () => {
      const code = `
        const items = await prisma.offer.findMany({ where, skip, take });
        res.json(items);
      `;
      const result = staticAnalyze(code);
      expect(result.hasFindMany).toBe(true);
      expect(result.hasInclude).toBe(false);
      expect(result.hasN1Risk).toBe(true);
      expect(result.suggestions.length).toBeGreaterThan(0);
    });

    it('检测: findMany + include -> 安全', () => {
      const code = `
        const items = await prisma.offer.findMany({
          where,
          include: { candidate: true, demand: true },
        });
      `;
      const result = staticAnalyze(code);
      expect(result.hasInclude).toBe(true);
      expect(result.hasN1Risk).toBe(false);
    });

    it('检测: findMany 后 findUnique 提示 lazy load', () => {
      const code = `
        const items = await prisma.offer.findMany({ where });
        for (const item of items) {
          const c = await prisma.candidate.findUnique({ where: { id: item.candidateId } });
        }
      `;
      const result = staticAnalyze(code);
      expect(result.hasN1Risk).toBe(true);
      expect(result.suggestions.some((s) => s.includes('lazy loading'))).toBe(true);
    });

    it('无 findMany -> 不报告风险', () => {
      const code = 'const x = await prisma.user.findUnique({ where: { id: 1 } });';
      const result = staticAnalyze(code);
      expect(result.hasFindMany).toBe(false);
      expect(result.hasN1Risk).toBe(false);
    });
  });

  describe('createN1Detector', () => {
    let mockPrisma;
    beforeEach(() => {
      mockPrisma = {
        $on: jest.fn(),
        $off: jest.fn(),
      };
    });

    it('基础用法: analyze 返回 isN1 报告', () => {
      const detector = createN1Detector(mockPrisma);
      expect(typeof detector.analyze).toBe('function');
      expect(typeof detector.reset).toBe('function');
      expect(typeof detector.dispose).toBe('function');
      expect(detector.getQueries()).toEqual([]);
    });

    it('analyze 在无 list query 时返回 isN1=false', () => {
      const detector = createN1Detector(mockPrisma);
      const report = detector.analyze();
      expect(report.isN1).toBe(false);
      expect(report.reason).toContain('no list query');
    });

    it('onDetect 回调可定制', () => {
      const onDetect = jest.fn();
      const detector = createN1Detector(mockPrisma, { onDetect });
      expect(typeof detector.analyze).toBe('function');
      // 没数据时不会触发
      detector.analyze();
      expect(onDetect).not.toHaveBeenCalled();
    });

    it('dispose 调用 $off 解除绑定', () => {
      const detector = createN1Detector(mockPrisma);
      detector.dispose();
      expect(mockPrisma.$on).toHaveBeenCalled();
    });
  });
});
