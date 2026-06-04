import { createActor } from 'xstate';
import { referralRewardMachine } from '../machines/referralReward.machine.js';

describe('referralRewardMachine', () => {
  it('初始状态为 PENDING', () => {
    const a = createActor(referralRewardMachine).start();
    expect(a.getSnapshot().value).toBe('PENDING');
  });

  it('PENDING → TO_CONFIRM (TRIGGER)', () => {
    const a = createActor(referralRewardMachine).start();
    a.send({ type: 'TRIGGER' });
    expect(a.getSnapshot().value).toBe('TO_CONFIRM');
  });

  it('TO_CONFIRM → CONFIRMED (CONFIRM)', () => {
    const a = createActor(referralRewardMachine).start();
    a.send({ type: 'TRIGGER' });
    a.send({ type: 'CONFIRM' });
    expect(a.getSnapshot().value).toBe('CONFIRMED');
  });

  it('TO_CONFIRM → REJECTED (REJECT with reason)', () => {
    const a = createActor(referralRewardMachine).start();
    a.send({ type: 'TRIGGER' });
    a.send({ type: 'REJECT', reason: '候选人未达 3 个月' });
    const snap = a.getSnapshot();
    expect(snap.value).toBe('REJECTED');
    expect(snap.context.rejectReason).toBe('候选人未达 3 个月');
  });
});
