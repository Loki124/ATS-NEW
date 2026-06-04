import { setup, assign } from 'xstate';

const VALID_REASONS = new Set(['LEAVER', 'EXPERT_LEAVER', 'EXPERT_CHANGED', 'NO_EXPERT']);

export const referralCodeMachine = setup({
  guards: {
    isValidReason: ({ event }) => VALID_REASONS.has(event.reason),
  },
  actions: {
    setInvalidReason: assign({
      invalidReason: ({ event }) => event.reason,
    }),
    clearInvalidReason: assign({
      invalidReason: null,
    }),
  },
}).createMachine({
  id: 'referralCode',
  initial: 'ACTIVE',
  context: {
    invalidReason: null,
  },
  states: {
    ACTIVE: {
      on: {
        INVALIDATE: {
          guard: 'isValidReason',
          target: 'INVALID',
          actions: 'setInvalidReason',
        },
      },
    },
    INVALID: {
      on: {
        REACTIVATE: {
          target: 'ACTIVE',
          actions: 'clearInvalidReason',
        },
      },
    },
  },
});
