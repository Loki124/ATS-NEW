import { setup, assign } from 'xstate';

/**
 * 内推记录状态机
 *
 * NORMAL     - 有效内推，候选人处于简历审核
 * PROTECTING - 有效内推，简历不在流程中但还在保护期
 * EXPIRED    - 保护期结束
 * COMPLETED  - 达成所有奖励要求（终态）
 * INVALID    - 无效内推（终态）
 */

const IN_PROCESS_STAGES = new Set(['RESUME_REVIEW', 'HRBP_SCREEN', 'HR_SCREEN', 'INTERVIEW', 'OFFER', 'ONBOARDING']);

export const referralRecordMachine = setup({
  guards: {
    leftProcess: ({ event }) => {
      if (event.type !== 'STAGE_CHANGED') return false;
      return IN_PROCESS_STAGES.has(event.from) && !IN_PROCESS_STAGES.has(event.to);
    },
    enteredProcess: ({ event }) => {
      if (event.type !== 'STAGE_CHANGED') return false;
      return !IN_PROCESS_STAGES.has(event.from) && IN_PROCESS_STAGES.has(event.to);
    },
    allRewardsIssued: ({ event }) => event.allRewardsIssued === true,
  },
  actions: {
    setInvalidReason: assign({
      invalidReason: ({ event }) => event.reason,
    }),
  },
}).createMachine({
  id: 'referralRecord',
  initial: 'NORMAL',
  context: { invalidReason: null },
  states: {
    NORMAL: {
      on: {
        STAGE_CHANGED: [
          { guard: 'leftProcess', target: 'PROTECTING' },
          { guard: 'enteredProcess', target: 'NORMAL' },
        ],
        CANDIDATE_ONBOARDED: { target: 'COMPLETED', guard: 'allRewardsIssued' },
        MARK_INVALID: { target: 'INVALID', actions: 'setInvalidReason' },
      },
    },
    PROTECTING: {
      on: {
        STAGE_CHANGED: [
          { guard: 'enteredProcess', target: 'NORMAL' },
        ],
        PROTECTION_EXPIRED: { target: 'EXPIRED' },
        CANDIDATE_ONBOARDED: { target: 'COMPLETED', guard: 'allRewardsIssued' },
        MARK_INVALID: { target: 'INVALID', actions: 'setInvalidReason' },
      },
    },
    EXPIRED: {
      on: {
        CANDIDATE_ONBOARDED: { target: 'COMPLETED', guard: 'allRewardsIssued' },
        MARK_INVALID: { target: 'INVALID', actions: 'setInvalidReason' },
      },
    },
    COMPLETED: { type: 'final' },
    INVALID: { type: 'final' },
  },
});
