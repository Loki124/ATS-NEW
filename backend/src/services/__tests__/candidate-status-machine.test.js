/**
 * 候选人 11 状态详细字段状态机测试 - PRD G44
 */

import { describe, it, expect } from '@jest/globals';
import {
  CANDIDATE_DETAIL_STATUSES,
  validateStatusDetails,
  isStatusPassed,
  isStatusFailed,
  isStatusPending,
  getStatusSummary
} from '../candidate-status-machine.service.js';

describe('candidate-status-machine', () => {
  // 11 个状态定义完整性
  it('exports 11 业务子状态', () => {
    expect(Object.keys(CANDIDATE_DETAIL_STATUSES)).toHaveLength(11);
    ['evaluated', 'hrbpFiltered', 'managerFiltered', 'seniorManagerFiltered',
     'invited', 'jointInterview', 'comprehensiveInterview', 'offerNegotiation',
     'backgroundCheck', 'pendingOnboarding', 'onboarded']
      .forEach(k => expect(CANDIDATE_DETAIL_STATUSES[k]).toBeDefined());
  });

  it('evaluate PENDING→PASS 合法', () => {
    expect(validateStatusDetails('evaluated', 'PASS', 'PENDING')).toBe(true);
  });

  it('evaluate PASS→PENDING 非法 (终态不能回退)', () => {
    expect(validateStatusDetails('evaluated', 'PENDING', 'PASS')).toBe(false);
  });

  it('isStatusPassed 识别 PASS', () => {
    expect(isStatusPassed('evaluated', { evaluated: 'PASS' })).toBe(true);
    expect(isStatusPassed('evaluated', { evaluated: 'FAIL' })).toBe(false);
  });

  it('isStatusFailed 识别 FAIL', () => {
    expect(isStatusFailed('hrbpFiltered', { hrbpFiltered: 'FAIL' })).toBe(true);
  });

  it('isStatusPending 识别 PENDING', () => {
    expect(isStatusPending('invited', { invited: 'PENDING' })).toBe(true);
  });

  it('getStatusSummary 聚合统计', () => {
    const summary = getStatusSummary({ evaluated: 'PASS', invited: 'FAIL' });
    expect(summary).toEqual({ passed: 1, failed: 1, pending: 9 });
  });

  it('NULL details 全部 pending', () => {
    const summary = getStatusSummary(null);
    expect(summary.pending).toBe(11);
  });

  it('unknown key 抛错', () => {
    expect(() => validateStatusDetails('unknown', 'PASS', 'PENDING'))
      .toThrow('Unknown status key');
  });

  it('unknown value 抛错', () => {
    expect(() => validateStatusDetails('evaluated', 'INVALID', 'PENDING'))
      .toThrow('Invalid status value');
  });

  it('onboarded 是终态, 不能 PENDING', () => {
    expect(CANDIDATE_DETAIL_STATUSES.onboarded.terminal).toBe(true);
  });
});
