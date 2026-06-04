import { createActor } from 'xstate';
import { referralCodeMachine } from '../machines/referralCode.machine.js';

describe('referralCodeMachine', () => {
  it('初始状态为 ACTIVE', () => {
    const actor = createActor(referralCodeMachine).start();
    expect(actor.getSnapshot().value).toBe('ACTIVE');
  });

  it('INVALIDATE 事件转换为 INVALID', () => {
    const actor = createActor(referralCodeMachine).start();
    actor.send({ type: 'INVALIDATE', reason: 'LEAVER' });
    const snap = actor.getSnapshot();
    expect(snap.value).toBe('INVALID');
    expect(snap.context.invalidReason).toBe('LEAVER');
  });

  it('REACTIVATE 事件从 INVALID 回到 ACTIVE', () => {
    const actor = createActor(referralCodeMachine).start();
    actor.send({ type: 'INVALIDATE', reason: 'NO_EXPERT' });
    actor.send({ type: 'REACTIVATE' });
    const snap = actor.getSnapshot();
    expect(snap.value).toBe('ACTIVE');
    expect(snap.context.invalidReason).toBeNull();
  });

  it('ACTIVE 状态收到无效 reason 不转换', () => {
    const actor = createActor(referralCodeMachine).start();
    actor.send({ type: 'INVALIDATE', reason: 'BOGUS' });
    expect(actor.getSnapshot().value).toBe('ACTIVE');
  });
});
