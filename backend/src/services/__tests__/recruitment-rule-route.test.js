/**
 * Plan K - Task 3: 阶段规则 + 进入条件 测试 (PRD G38)
 *
 * 覆盖:
 *   1. evaluateConditionTree: ALL matchType, 多条件 AND 嵌套
 *   2. evaluateConditionTree: ANY matchType, 数组运算符 (IN)
 *   3. buildFailedPrompt: 包含失败项 + 自定义 prompt 优先
 */

import { describe, it, expect } from '@jest/globals';
import { evaluateConditionTree, buildFailedPrompt } from '../recruitment-condition.service.js';

const baseContext = {
  candidate: {
    AGE: 28,
    GENDER: 'M',
    MARRIAGE: 'NO',
    HIGHEST_EDU: 'BACHELOR',
    COMPANY: 'Acme Corp',
    LEVEL: 'P5',
  },
  stageStatuses: {
    's-hr': 'PASS',
    's-mgr': 'FAIL',
  },
};

describe('Plan K · evaluateConditionTree: ALL matchType (AND 嵌套)', () => {
  it('3 条条件全部满足 → passed=true', () => {
    const items = [
      { id: 'i1', parentId: null, relationToParent: null, field: 'AGE', operator: 'GT', value: 18, orderIndex: 0 },
      { id: 'i2', parentId: null, relationToParent: null, field: 'AGE', operator: 'LT', value: 60, orderIndex: 1 },
      { id: 'i3', parentId: null, relationToParent: null, field: 'HIGHEST_EDU', operator: 'EQ', value: 'BACHELOR', orderIndex: 2 },
    ];
    const r = evaluateConditionTree(items, 'ALL', baseContext);
    expect(r.passed).toBe(true);
    expect(r.failedItems).toEqual([]);
  });

  it('3 条条件中 1 条失败 → passed=false, 失败项入 failedItems', () => {
    const items = [
      { id: 'i1', parentId: null, relationToParent: null, field: 'AGE', operator: 'GT', value: 18, orderIndex: 0 },
      { id: 'i2', parentId: null, relationToParent: null, field: 'AGE', operator: 'LT', value: 25, orderIndex: 1 },  // 28 < 25 = false
      { id: 'i3', parentId: null, relationToParent: null, field: 'HIGHEST_EDU', operator: 'EQ', value: 'BACHELOR', orderIndex: 2 },
    ];
    const r = evaluateConditionTree(items, 'ALL', baseContext);
    expect(r.passed).toBe(false);
    expect(r.failedItems.length).toBeGreaterThanOrEqual(1);
    expect(r.failedItems[0].id).toBe('i2');
  });

  it('空 items 视为全部满足', () => {
    const r = evaluateConditionTree([], 'ALL', baseContext);
    expect(r.passed).toBe(true);
    expect(r.failedItems).toEqual([]);
  });
});

describe('Plan K · evaluateConditionTree: ANY matchType (OR 关系)', () => {
  it('ANY 模式, 数组运算符 IN 命中 → passed=true', () => {
    const items = [
      { id: 'i1', parentId: null, relationToParent: null, field: 'HIGHEST_EDU', operator: 'IN', value: ['PHD', 'MASTER'], orderIndex: 0 },
      { id: 'i2', parentId: null, relationToParent: null, field: 'COMPANY', operator: 'CONTAINS', value: 'Acme', orderIndex: 1 },
    ];
    const r = evaluateConditionTree(items, 'ANY', baseContext);
    expect(r.passed).toBe(true);
  });

  it('ANY 模式, 全部失败 → passed=false', () => {
    const items = [
      { id: 'i1', parentId: null, relationToParent: null, field: 'HIGHEST_EDU', operator: 'EQ', value: 'PHD', orderIndex: 0 },
      { id: 'i2', parentId: null, relationToParent: null, field: 'AGE', operator: 'GT', value: 100, orderIndex: 1 },
    ];
    const r = evaluateConditionTree(items, 'ANY', baseContext);
    expect(r.passed).toBe(false);
    expect(r.failedItems.length).toBe(2);
  });

  it('STAGE_STATUS 类型 → 引用 stageStatuses[refStageId]', () => {
    const items = [
      { id: 'i1', parentId: null, relationToParent: null, field: 'STAGE_STATUS', operator: 'EQ', value: 'PASS', refStageId: 's-hr', orderIndex: 0 },
    ];
    const r = evaluateConditionTree(items, 'ALL', baseContext);
    expect(r.passed).toBe(true);
  });
});

describe('Plan K · buildFailedPrompt: 自定义 prompt 优先 + 默认模板', () => {
  it('customPrompt 存在 → 直接返回', () => {
    const failed = [{ id: 'i1', field: 'AGE', operator: 'GT', value: 100 }];
    const r = buildFailedPrompt([], failed, baseContext, '【自定义】不通过');
    expect(r).toBe('【自定义】不通过');
  });

  it('failedItems 为空 → 返回 null', () => {
    const r = buildFailedPrompt([], [], baseContext, null);
    expect(r).toBeNull();
  });

  it('无 customPrompt + 有 failedItems → 返回默认模板', () => {
    const items = [
      { id: 'i1', field: 'AGE', operator: 'GT', value: 100 },
    ];
    const r = buildFailedPrompt(items, items, baseContext, null);
    expect(r).toContain('未满足');
    expect(r).toContain('年龄');
    expect(r).toContain('大于');
  });
});
