/**
 * Plan L Task 7: 流程名称/描述长度校验 测试
 *
 * 覆盖 (3 测试):
 *   1. 名称超长 (> 50 字符) → 抛 AppError 400
 *   2. 描述超长 (> 100 字符) → 抛 AppError 400
 *   3. 正常 → 不抛
 */

import { describe, it, expect } from '@jest/globals';
import { validateProcessPayload } from '../recruitment-process-validator.service.js';

describe('Plan L · validateProcessPayload: 名称/描述长度', () => {
  it('1. 名称超长 60 字符 → 抛 AppError 400', () => {
    expect(() => validateProcessPayload('A'.repeat(60), null)).toThrow(/2-50/);
  });

  it('2. 描述超长 150 字符 → 抛 AppError 400', () => {
    expect(() => validateProcessPayload('OK流程', 'A'.repeat(150))).toThrow(/100/);
  });

  it('3. 正常 名称 5 字符 + 描述 50 字符 → 不抛', () => {
    expect(() => validateProcessPayload('技术部流程', 'A'.repeat(50))).not.toThrow();
  });
});
