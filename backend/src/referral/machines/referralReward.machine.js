import { setup, assign } from 'xstate';

export const referralRewardMachine = setup({
  actions: {
    setRejectReason: assign({
      rejectReason: ({ event }) => event.reason,
    }),
  },
}).createMachine({
  id: 'referralReward',
  initial: 'PENDING',
  context: { rejectReason: null },
  states: {
    PENDING: {
      on: { TRIGGER: 'TO_CONFIRM' },
    },
    TO_CONFIRM: {
      on: {
        CONFIRM: 'CONFIRMED',
        REJECT: { target: 'REJECTED', actions: 'setRejectReason' },
      },
    },
    CONFIRMED: {
      on: { ISSUE: 'ISSUED' },
    },
    ISSUED: { type: 'final' },
    REJECTED: { type: 'final' },
  },
});
