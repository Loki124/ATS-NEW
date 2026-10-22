/**
 * 「校招生管理」数据权限卡 —— 前端接线回归（2026-10-21 S5-35）。
 *
 * 需求：数据权限中增加针对校招生管理模块的单独配置，条件支持选择
 * 「员工HRBP / 班长 / 班主任 / 导师」，判断符为包含/不包含，
 * 校验值为固定/当前登录用户。
 *
 * 本文件锁住**前端侧**三件事（后端下发与编译由
 * apps/data_permission/tests/test_campus_module_dimension.py 覆盖）：
 *   1. 新模块键进入 MODULE_KEYS —— 否则抽屉不渲染该卡（后端下发也会被丢弃）；
 *   2. 四个维度有中文兜底标签 —— 否则预览句裸渲染 dimension key
 *      （如 "class_monitor 属于 [张三]"），管理员读不懂自己配的规则；
 *   3. 预览句按「包含/不包含」+「当前登录用户」渲染，与需求文案一致。
 */
import { describe, it, expect } from 'vitest'
import {
  MODULE_KEYS, DIMENSION_LABELS, previewOf,
} from '@/composables/useRoleDataPerm'
import type { ModulePerm, PermCondition } from '@/api/data-permission'

const CAMPUS_MODULE_KEY = 'campus_arrangement'

/** 需求指定的四个条件维度 -> 期望的中文标签 */
const CAMPUS_DIMS: Array<[string, string]> = [
  ['hrbp', '员工HRBP'],
  ['class_monitor', '班长'],
  ['head_teacher', '班主任'],
  ['mentor', '导师'],
]

const cond = (over: Partial<PermCondition> = {}): PermCondition => ({
  id: 'c1',
  kind: 'relationship',
  dimension: 'class_monitor',
  operator: 'in',
  valueSource: 'static',
  values: [{ id: 'u1', label: '张三' }],
  ...over,
})

const scopeModule = (conditions: PermCondition[]): ModulePerm => ({
  moduleKey: CAMPUS_MODULE_KEY,
  mode: 'scope',
  expr: '',
  groups: [{ id: 'g1', expr: '', conditions }],
  featureGranted: true,
})

describe('校招生管理数据权限卡（S5-35）', () => {
  it('新模块键进入 MODULE_KEYS（抽屉据此渲染该卡）', () => {
    expect(MODULE_KEYS).toContain(CAMPUS_MODULE_KEY)
  })

  it('模块键排在末位（校招域独立于社招五模块）', () => {
    expect(MODULE_KEYS[MODULE_KEYS.length - 1]).toBe(CAMPUS_MODULE_KEY)
  })

  it('四个维度都有中文兜底标签（预览句不裸渲染 key）', () => {
    for (const [key, label] of CAMPUS_DIMS) {
      expect(DIMENSION_LABELS[key]).toBe(label)
    }
  })

  it('静态固定值预览句渲染为「<维度> 属于 [人员]」', () => {
    for (const [key, label] of CAMPUS_DIMS) {
      const text = previewOf(scopeModule([cond({ dimension: key })]))
      expect(text).toBe(`（${label} 属于 [张三]）`)
      expect(text).not.toContain(key)
    }
  })

  it('「不包含」渲染为「不属于」', () => {
    expect(previewOf(scopeModule([cond({ operator: 'not_in' })])))
      .toBe('（班长 不属于 [张三]）')
  })

  it('动态「当前登录用户」渲染为中文可读句', () => {
    const text = previewOf(scopeModule([cond({
      dimension: 'class_monitor',
      valueSource: 'dynamic',
      dynamicKey: 'currentUser.id',
      values: [],
    })]))
    expect(text).toBe('（班长 是 当前登录用户）')
    expect(text).not.toContain('class_monitor')
  })
})
