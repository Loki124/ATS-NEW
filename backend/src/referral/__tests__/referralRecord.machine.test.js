import { createActor } from 'xstate';
import { referralRecordMachine } from '../machines/referralRecord.machine.js';

describe('referralRecordMachine', () => {
  it('初始状态为 NORMAL', () => {
    const a = createActor(referralRecordMachine).start();
    expect(a.getSnapshot().value).toBe('NORMAL');
  });

  it('NORMAL → PROTECTING (STAGE_CHANGED 离开流程)', () => {
    const a = createActor(referralRecordMachine).start();
    a.send({ type: 'STAGE_CHANGED', from: 'RESUME_REVIEW', to: 'REJECTED', isProtectionActive: true });
    expect(a.getSnapshot().value).toBe('PROTECTING');
  });

  it('PROTECTING → EXPIRED (PROTECTION_EXPIRED)', () => {
    const a = createActor(referralRecordMachine).start();
    a.send({ type: 'STAGE_CHANGED', from: 'RESUME_REVIEW', to: 'REJECTED', isProtectionActive: true });
    a.send({ type: 'PROTECTION_EXPIRED' });
    expect(a.getSnapshot().value).toBe('EXPIRED');
  });

  it('NORMAL → COMPLETED (CANDIDATE_ONBOARDED + allRewardsIssued)', () => {
    const a = createActor(referralRecordMachine).start();
    a.send({ type: 'CANDIDATE_ONBOARDED', allRewardsIssued: true });
    expect(a.getSnapshot().value).toBe('COMPLETED');
  });

  it('NORMAL → INVALID (MARK_INVALID)', () => {
    const a = createActor(referralRecordMachine).start();
    a.send({ type: 'MARK_INVALID', reason: 'OVER_3_TIMES' });
    expect(a.getSnapshot().value).toBe('INVALID');
  });
});
