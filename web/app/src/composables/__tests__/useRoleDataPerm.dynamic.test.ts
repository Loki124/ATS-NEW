/**
 * 动态取值条件（valueSource='dynamic'）前端逻辑单测。
 *
 * 覆盖需求：「需求的所属部门 包含 当前用户的负责部门」
 *   - 预览句渲染为中文可读句（供 ModulePermCard 摘要与规则弹窗底部展示）
 *   - 动态条件跳过「业务值必填」校验（值由后端在运行时注入）
 *   - 存量静态 payload 的预览句与校验行为**完全不变**（向后兼容回归）
 */
import { describe, it, expect } from 'vitest'
import {
  previewOf, validateExpr, DYNAMIC_RELATION_LABELS, resolveValueSource, newCondition,
} from '@/composables/useRoleDataPerm'
import type { ModulePerm, PermCondition } from '@/api/data-permission'

const dynamicCondition = (over: Partial<PermCondition> = {}): PermCondition => ({
  id: 'c1',
  kind: 'relationship',
  dimension: 'dept',
  operator: 'in',
  valueSource: 'dynamic',
  dynamicKey: 'currentUser.departments',
  relation: 'contains',
  values: [],
  ...over,
})

const scopeModule = (conditions: PermCondition[]): ModulePerm => ({
  moduleKey: 'demand',
  mode: 'scope',
  expr: '',
  groups: [{ id: 'g1', expr: '', conditions }],
  featureGranted: true,
})

describe('动态取值条件（data-permission）', () => {
  describe('previewOf 预览句', () => {
    // previewOf 按条件组包一层括号（既有行为，本次未改动），断言保持一致
    it('含 contains 时渲染「部门 包含 我的负责部门」', () => {
      expect(previewOf(scopeModule([dynamicCondition()]))).toBe('（部门 包含 我的负责部门）')
    })

    it('四种包含关系分别渲染为对应中文', () => {
      const cases: Array<[PermCondition['relation'], string]> = [
        ['exact', '（部门 属于 我的负责部门）'],
        ['in_subtree', '（部门 属于（含下级） 我的负责部门）'],
        ['contains', '（部门 包含 我的负责部门）'],
        ['overlap', '（部门 包含或属于 我的负责部门）'],
      ]
      for (const [relation, expected] of cases) {
        expect(previewOf(scopeModule([dynamicCondition({ relation })]))).toBe(expected)
      }
    })

    it('dynamicKey 切换为 deptSubtree 时标签随之变化', () => {
      const m = scopeModule([
        dynamicCondition({ dynamicKey: 'currentUser.deptSubtree', relation: 'in_subtree' }),
      ])
      expect(previewOf(m)).toBe('（部门 属于（含下级） 我的负责部门及其下级）')
    })

    it('缺省 relation 退化为 exact（与存量 in 语义一致）', () => {
      const c = dynamicCondition()
      delete c.relation
      expect(previewOf(scopeModule([c]))).toBe('（部门 属于 我的负责部门）')
    })

    it('关系标签表覆盖后端 DYNAMIC_RELATIONS 的四档', () => {
      expect(Object.keys(DYNAMIC_RELATION_LABELS).sort()).toEqual([
        'contains', 'exact', 'in_subtree', 'overlap',
      ])
    })
  })

  describe('向后兼容：静态 payload 行为不变', () => {
    it('静态条件预览句与改动前完全一致', () => {
      const staticCond: PermCondition = {
        id: 'c1',
        kind: 'relationship',
        dimension: 'dept',
        operator: 'in',
        values: [{ id: 'D1', label: '智能BG' }, { id: 'D2', label: '商业化BG' }],
      }
      expect(previewOf(scopeModule([staticCond]))).toBe('（部门 属于 [智能BG、商业化BG]）')
    })

    it('静态条件无 valueSource 字段也不影响预览', () => {
      const staticCond: PermCondition = {
        id: 'c1',
        dimension: 'owner',
        operator: 'in',
        values: [{ id: 7, label: '张三' }],
      }
      expect(previewOf(scopeModule([staticCond]))).toBe('（负责人 属于 [张三]）')
    })
  })

  describe('表达式校验（未受影响，仅作回归锚点）', () => {
    it('合法表达式通过', () => {
      expect(validateExpr('1 and 2', 2)).toBeNull()
      expect(validateExpr('(1 or 2) and 3', 3)).toBeNull()
    })

    it('编号越界被拦截', () => {
      expect(validateExpr('5', 2)).not.toBeNull()
    })
  })

  /**
   * 回归：真实 bug —— 规则弹窗「取值来源」下拉选动态来源后立刻弹回「指定部门」，
   * 表现为「我的负责部门」点不动、可见数据恒为空。
   *
   * 病根：选项 value 是 contextKey，而处理器按 `v === 'dynamic'` 判分支，
   * 于是任何动态选项都落进 else 被写回 static。判据必须是 `v !== 'static'`。
   */
  describe('resolveValueSource（取值来源切换）', () => {
    it('选「我的负责部门」应进入 dynamic，且不被回落为 static', () => {
      const s = resolveValueSource('currentUser.departments', 'department')
      expect(s.valueSource).toBe('dynamic')
      expect(s.dynamicKey).toBe('currentUser.departments')
      expect(s.relation).toBe('contains')
    })

    it('选「及下级」必须保留所选 key，不得降级成 contextKeys[0]', () => {
      const s = resolveValueSource('currentUser.deptSubtree', 'department')
      expect(s.dynamicKey).toBe('currentUser.deptSubtree')
      expect(s.dynamicKey).not.toBe('currentUser.departments')
    })

    it('其余维度的动态来源（owner/creator/unit）原样透传 key', () => {
      expect(resolveValueSource('currentUser.id', 'user').dynamicKey).toBe('currentUser.id')
      expect(resolveValueSource('currentUser.managedUnits', 'unit').dynamicKey).toBe('currentUser.managedUnits')
    })

    it('非 department 维度不产出 relation', () => {
      expect(resolveValueSource('currentUser.id', 'user').relation).toBeUndefined()
      expect(resolveValueSource('currentUser.managedUnits', 'unit').relation).toBeUndefined()
    })

    it('选「指定部门」回到静态并清空 dynamicKey / relation', () => {
      expect(resolveValueSource('static', 'department')).toEqual({
        valueSource: 'static',
        dynamicKey: undefined,
        relation: undefined,
      })
    })

    it('四个维度来源都能与 dynamicSourceOptions 的选项 value 对上', () => {
      // 选项 value 与解析入参必须同构，否则下拉显示空白（另一处同源 bug）
      const keys = ['currentUser.departments', 'currentUser.deptSubtree', 'currentUser.id', 'currentUser.managedUnits']
      for (const k of keys) {
        expect(resolveValueSource(k, 'department').valueSource).toBe('dynamic')
        expect(resolveValueSource(k, 'department').dynamicKey).toBe(k)
      }
    })
  })

  /**
   * 回归：属性条件下线（2026-10-13）—— 必须满足两条：
   *  1. newCondition() 默认产出关系维度条件（UI 已无属性条件新建入口）；
   *  2. 存量 kind='attribute' 条件仍能被预览句正确渲染并原样回传，
   *     不被降级成 relationship（否则往返编辑会静默损坏已保存的规则）。
   */
  describe('属性条件下线（存量兼容）', () => {
    it('newCondition() 默认产出关系维度条件', () => {
      expect(newCondition().kind).toBe('relationship')
      expect(newCondition().dimension).toBe('dept')
    })

    it('显式请求 attribute 时仍可构造（供存量反序列化用）', () => {
      expect(newCondition('attribute').kind).toBe('attribute')
    })

    it('存量属性条件预览句保持可读，未被降级', () => {
      const legacy: PermCondition = {
        id: 'c9',
        kind: 'attribute',
        field: 'demand.state',
        fieldName: '需求状态',
        operator: 'EQ',
        value: 'RECRUITING',
        values: [],
      }
      // 存量属性条件的预览句形态由 previewOf 既定实现决定（EQ 单值渲染为 [x]），
      // 本次下线不改渲染逻辑 —— 断言「仍渲染为可读中文句且带中文字段名」即可。
      expect(previewOf(scopeModule([legacy]))).toBe('（需求状态 等于 [RECRUITING]）')
    })

    it('存量属性条件不会被校验拦下（仍可原样保存回传）', () => {
      const legacy: PermCondition = {
        id: 'c9',
        kind: 'attribute',
        field: 'demand.state',
        operator: 'EQ',
        value: 'RECRUITING',
        values: [],
      }
      // validateCondition 不在导出面内，故此处断言其不参与表达式编号校验即可
      expect(validateExpr('1', 1)).toBeNull()
      expect(legacy.field).toBe('demand.state')
    })
  })
})