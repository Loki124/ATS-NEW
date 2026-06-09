/**
 * Plan L Task 4: 循环依赖检测 service 测试
 *
 * 覆盖 (6 测试):
 *   1. 无依赖 → no cycle
 *   2. 线性依赖 → no cycle
 *   3. 2 节点环 (A↔B) → cycle
 *   4. 3 节点环 (A→B→C→A) → cycle
 *   5. 自环 (A→A) → cycle
 *   6. 跨 stage 环 (validateStageDependency) → cycle
 */

import { describe, it, expect } from '@jest/globals';
import { detectCycle, validateStageDependency } from '../cycle-detector.service.js';

describe('Plan L · detectCycle: 无环场景', () => {
  it('1. 无依赖 (3 个独立节点) → hasCycle=false', () => {
    const r = detectCycle([
      { id: 'A', dependsOn: [] },
      { id: 'B', dependsOn: [] },
      { id: 'C', dependsOn: [] },
    ]);
    expect(r.hasCycle).toBe(false);
    expect(r.cycle).toBeNull();
  });

  it('2. 线性依赖 A→B→C → hasCycle=false', () => {
    const r = detectCycle([
      { id: 'A', dependsOn: [] },
      { id: 'B', dependsOn: ['A'] },
      { id: 'C', dependsOn: ['B'] },
    ]);
    expect(r.hasCycle).toBe(false);
  });
});

describe('Plan L · detectCycle: 有环场景', () => {
  it('3. 2 节点环 A↔B → hasCycle=true, cycle 包含 A,B', () => {
    const r = detectCycle([
      { id: 'A', dependsOn: ['B'] },
      { id: 'B', dependsOn: ['A'] },
    ]);
    expect(r.hasCycle).toBe(true);
    expect(r.cycle).toEqual(expect.arrayContaining(['A', 'B']));
    expect(r.cycle.length).toBeGreaterThanOrEqual(2);
  });

  it('4. 3 节点环 A→B→C→A → hasCycle=true', () => {
    const r = detectCycle([
      { id: 'A', dependsOn: ['C'] },
      { id: 'B', dependsOn: ['A'] },
      { id: 'C', dependsOn: ['B'] },
    ]);
    expect(r.hasCycle).toBe(true);
    expect(r.cycle).toEqual(expect.arrayContaining(['A', 'B', 'C']));
  });

  it('5. 自环 A→A → hasCycle=true', () => {
    const r = detectCycle([
      { id: 'A', dependsOn: ['A'] },
    ]);
    expect(r.hasCycle).toBe(true);
  });
});

describe('Plan L · validateStageDependency: 跨 stage 环', () => {
  it('6. link1.refStage=stage3, link3.refStage=stage1 (经 stageIdToLinkId 映射) → hasCycle=true', () => {
    // 假定 3 个 link (L1, L2, L3), 3 个 stage (S1, S2, S3)
    // L1 的 entryCondition 引用 S3 → L1.dependsOn = L3
    // L3 的 entryCondition 引用 S1 → L3.dependsOn = L1
    // 形成 L1 ↔ L3 环
    const stageIdToLinkId = { S1: 'L1', S2: 'L2', S3: 'L3' };
    const items = [
      { linkId: 'L1', refStageIds: ['S3'] },
      { linkId: 'L2', refStageIds: [] },
      { linkId: 'L3', refStageIds: ['S1'] },
    ];
    const r = validateStageDependency(items, stageIdToLinkId);
    expect(r.hasCycle).toBe(true);
    expect(r.cycle).toEqual(expect.arrayContaining(['L1', 'L3']));
  });
});
