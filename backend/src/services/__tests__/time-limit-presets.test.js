/**
 * Plan L Task 5: 阶段限时预置规则 测试
 *
 * 覆盖 (5 测试):
 *   1. PRESIDENT → 90 天 = 2160 小时
 *   2. DIRECTOR → 60 天 = 1440 小时
 *   3. OTHER → 30 天 = 720 小时
 *   4. 未知 level → 抛错
 *   5. listPresetLevels 返回 3 项
 */

import { describe, it, expect } from '@jest/globals';
import { buildTimeLimitPresets, listPresetLevels, TIME_LIMIT_PRESETS } from '../time-limit-presets.service.js';

describe('Plan L · buildTimeLimitPresets: 三档级别', () => {
  it('1. PRESIDENT → 90 天 = 2160 小时', () => {
    const r = buildTimeLimitPresets('PRESIDENT');
    expect(r.timeLimit).toBe(90 * 24);
    expect(r.timeLimit).toBe(2160);
    expect(r.name).toContain('90');
    expect(r.enabled).toBe(true);
  });

  it('2. DIRECTOR → 60 天 = 1440 小时', () => {
    const r = buildTimeLimitPresets('DIRECTOR');
    expect(r.timeLimit).toBe(60 * 24);
    expect(r.timeLimit).toBe(1440);
    expect(r.name).toContain('60');
  });

  it('3. OTHER → 30 天 = 720 小时', () => {
    const r = buildTimeLimitPresets('OTHER');
    expect(r.timeLimit).toBe(30 * 24);
    expect(r.timeLimit).toBe(720);
    expect(r.name).toContain('30');
  });

  it('4. 未知 level → 抛错', () => {
    expect(() => buildTimeLimitPresets('UNKNOWN')).toThrow(/未知级别/);
  });

  it('5. listPresetLevels 返回 3 项 (PRESIDENT, DIRECTOR, OTHER)', () => {
    const r = listPresetLevels();
    expect(r).toHaveLength(3);
    expect(r.map((x) => x.level)).toEqual(expect.arrayContaining(['PRESIDENT', 'DIRECTOR', 'OTHER']));
    expect(TIME_LIMIT_PRESETS.PRESIDENT.days).toBe(90);
    expect(TIME_LIMIT_PRESETS.DIRECTOR.days).toBe(60);
    expect(TIME_LIMIT_PRESETS.OTHER.days).toBe(30);
  });
});
