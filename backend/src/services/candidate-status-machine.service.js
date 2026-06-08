// G44 - 候选人 11 状态详细字段状态机 (PRD §3.2)
//
// 11 个业务子状态:
//   1. evaluated              - 初评
//   2. hrbpFiltered           - HRBP 筛选
//   3. managerFiltered        - 用人经理筛选
//   4. seniorManagerFiltered  - 用人经理上级筛选
//   5. invited                - 邀约
//   6. jointInterview         - 联合面试
//   7. comprehensiveInterview - 综合面试
//   8. offerNegotiation       - Offer 沟通
//   9. backgroundCheck        - 背调
//  10. pendingOnboarding      - 待入职
//  11. onboarded              - 入职 (终态)

export const CANDIDATE_DETAIL_STATUSES = {
  evaluated:              { order: 1,  label: '初评',        terminal: false },
  hrbpFiltered:           { order: 2,  label: 'HRBP筛选',    terminal: false },
  managerFiltered:        { order: 3,  label: '用人经理筛选',terminal: false },
  seniorManagerFiltered:  { order: 4,  label: '用人经理上级',terminal: false },
  invited:                { order: 5,  label: '邀约',        terminal: false },
  jointInterview:         { order: 6,  label: '联合面试',    terminal: false },
  comprehensiveInterview: { order: 7,  label: '综合面试',    terminal: false },
  offerNegotiation:       { order: 8,  label: 'Offer沟通',   terminal: false },
  backgroundCheck:        { order: 9,  label: '背调',        terminal: false },
  pendingOnboarding:      { order: 10, label: '待入职',      terminal: false },
  onboarded:              { order: 11, label: '入职',        terminal: true  },
};

const VALID_VALUES = ['PENDING', 'PASS', 'FAIL'];

export function validateStatusDetails(key, nextValue, currentValue = 'PENDING') {
  if (!CANDIDATE_DETAIL_STATUSES[key]) {
    throw new Error(`Unknown status key: ${key}`);
  }
  if (!VALID_VALUES.includes(nextValue)) {
    throw new Error(`Invalid status value: ${nextValue}`);
  }
  if (CANDIDATE_DETAIL_STATUSES[key].terminal && nextValue === 'PENDING') {
    throw new Error(`Terminal status ${key} cannot be PENDING`);
  }
  // PASS / FAIL 是终值, 不能再 PENDING
  if (currentValue === 'PASS' && nextValue === 'PENDING') return false;
  if (currentValue === 'FAIL' && nextValue === 'PENDING') return false;
  return true;
}

export function isStatusPassed(key, details) {
  return details?.[key] === 'PASS';
}
export function isStatusFailed(key, details) {
  return details?.[key] === 'FAIL';
}
export function isStatusPending(key, details) {
  return !details?.[key] || details[key] === 'PENDING';
}

export function getStatusSummary(details) {
  if (!details) return { passed: 0, failed: 0, pending: 11 };
  const summary = { passed: 0, failed: 0, pending: 0 };
  for (const key of Object.keys(CANDIDATE_DETAIL_STATUSES)) {
    const v = details[key];
    if (v === 'PASS') summary.passed++;
    else if (v === 'FAIL') summary.failed++;
    else summary.pending++;
  }
  return summary;
}
