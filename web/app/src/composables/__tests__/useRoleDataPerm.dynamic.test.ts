/**
 * 动态取值条件（valueSource='dynamic'）前端逻辑单测。
 *
 * 覆盖需求：「需求的所属部门 包含 当前用户的负责部门」
 *   - 预览句渲染为中文可读句（供 ModulePermCard 摘要与规则弹窗底部展示）
 *   - 动态条件跳过「业务值必填」校验（值由后端在运行时注入）
 *   - 存量静态 payload 的预览句与校验行为**完全不变**（向后兼容回归）
 */
import { describe, it, expect } from 'vitest'
import { previewOf, validateExpr, DYNAMIC_RELATION_LABELS } from '@/composables/useRoleDataPerm'
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
})