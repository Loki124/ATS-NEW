/**
 * Plan L Task 3a: 表达式实时校验 service 测试
 *
 * 覆盖 (8 测试):
 *   1. 空/单值
 *   2. AND 简单
 *   3. OR 简单
 *   4. AND+OR 混合 (顶层)
 *   5. 括号未闭
 *   6. 数字超界
 *   7. 嵌套括号非法
 *   8. 同组 AND+OR 混用非法
 */

import { describe, it, expect } from '@jest/globals';
import { validateExpression } from '../condition-expression-validator.service.js';

describe('Plan L · validateExpression: 空/单值', () => {
  it('空字符串 → valid=true, empty=true', () => {
    expect(validateExpression('', 5)).toEqual({ valid: true, empty: true });
  });

  it('null → valid=true, empty=true', () => {
    expect(validateExpression(null, 5)).toEqual({ valid: true, empty: true });
  });

  it('单值 "1" → valid=true', () => {
    const r = validateExpression('1', 5);
    expect(r.valid).toBe(true);
    expect(r.normalized).toBe('1');
  });
});

describe('Plan L · validateExpression: AND/OR 顶层组合', () => {
  it('AND 简单 "1 AND 2" → valid=true', () => {
    const r = validateExpression('1 AND 2', 5);
    expect(r.valid).toBe(true);
  });

  it('OR 简单 "1 OR 2 OR 3" → valid=true', () => {
    const r = validateExpression('1 OR 2 OR 3', 5);
    expect(r.valid).toBe(true);
  });

  it('AND+OR 顶层混合 "(1 AND 2) OR (3 AND 4)" → valid=true', () => {
    const r = validateExpression('(1 AND 2) OR (3 AND 4)', 5);
    expect(r.valid).toBe(true);
  });

  it('大小写宽容 "(1 and 2) or 3" → valid=true', () => {
    const r = validateExpression('(1 and 2) or 3', 5);
    expect(r.valid).toBe(true);
  });
});

describe('Plan L · validateExpression: 非法场景', () => {
  it('括号未闭 "(1 AND 2" → valid=false', () => {
    const r = validateExpression('(1 AND 2', 5);
    expect(r.valid).toBe(false);
    expect(r.error).toMatch(/括号/);
  });

  it('数字超界 "6" 当 itemCount=5 → valid=false', () => {
    const r = validateExpression('6', 5);
    expect(r.valid).toBe(false);
    expect(r.error).toMatch(/6.*范围/);
  });

  it('嵌套括号非法 "(1 AND (2 OR 3))" → valid=false', () => {
    const r = validateExpression('(1 AND (2 OR 3))', 5);
    expect(r.valid).toBe(false);
  });

  it('同括号内 AND+OR 混用非法 "(1 AND 2 OR 3)" → valid=false', () => {
    const r = validateExpression('(1 AND 2 OR 3)', 5);
    expect(r.valid).toBe(false);
    expect(r.error).toMatch(/AND 和 OR/);
  });

  it('非法字符 "1 # 2" → valid=false', () => {
    const r = validateExpression('1 # 2', 5);
    expect(r.valid).toBe(false);
    expect(r.error).toMatch(/非法字符/);
  });
});
