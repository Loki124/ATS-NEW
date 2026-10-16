/**
 * 简历锁定人「为空/不为空」无值运算符回归（兵哥 2026-10-15：「选不了」）。
 *
 * 该 bug 有三段断链，本文件锁定后两段（第一段在 RuleConfigModal.test.ts）：
 *   1. 受控下拉回弹（RuleConfigModal.unifiedOperatorValue 折叠）——组件测试覆盖；
 *   2. 预览句退化成「属于 []」空列表 / 裸渲染 dimension key —— previewOf 覆盖；
 *   3. 保存预校验被「请为每条条件选择业务值」误拦 —— validate() 覆盖。
 *
 * 后端口径（勿在前端放宽/收紧不一致）：expr_compiler._compile_lock_owner_condition
 * 对 is_empty/is_not_empty 忽略 values；compile 的保存校验对 lock_owner 空值
 * 运算符整体放行。前端必须同口径，否则「选为空 → 保存」必失败。
 */
import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useRoleDataPerm, previewOf, REL_NOVALUE_OPS } from '@/composables/useRoleDataPerm'
import type { ModulePerm, PermCondition } from '@/api/data-permission'

const lockOwner = (over: Partial<PermCondition> = {}): PermCondition => ({
  id: 'c1',
  kind: 'relationship',
  dimension: 'lock_owner',
  operator: 'is_empty',
  values: [],
  ...over,
})

const scopeModule = (conditions: PermCondition[]): ModulePerm => ({
  moduleKey: 'candidate',
  mode: 'scope',
  expr: '',
  groups: [{ id: 'g1', expr: '', conditions }],
  featureGranted: true,
})

describe('简历锁定人无值运算符（为空/不为空）', () => {
  describe('预览句 previewOf', () => {
    it('is_empty 渲染「简历锁定人 为空」', () => {
      expect(previewOf(scopeModule([lockOwner()]))).toBe('（简历锁定人 为空）')
    })

    it('is_not_empty 渲染「简历锁定人 不为空」', () => {
      expect(previewOf(scopeModule([lockOwner({ operator: 'is_not_empty' })])))
        .toBe('（简历锁定人 不为空）')
    })

    it('不裸渲染 dimension key（DIMENSION_LABELS 兜底映射必须在）', () => {
      expect(previewOf(scopeModule([lockOwner()]))).not.toContain('lock_owner')
    })

    it('有值运算符预览句不变（向后兼容锚点）', () => {
      expect(previewOf(scopeModule([
        lockOwner({ operator: 'in', values: [{ id: 'u1', label: '张三' }] }),
      ]))).toBe('（简历锁定人 属于 [张三]）')
    })
  })

  describe('保存预校验 validate()', () => {
    /** 直接灌 saved/draft（不发起任何请求），与 useRoleDataPerm.split.test.ts 同手法 */
    const setup = (conditions: PermCondition[]) => {
      const dp = useRoleDataPerm(ref('role-1'))
      const modules: ModulePerm[] = [scopeModule(conditions)]
      dp.saved.value = JSON.parse(JSON.stringify(modules))
      dp.draft.value = JSON.parse(JSON.stringify(modules))
      return dp
    }

    it('为空（values 为空）不被「请选择业务值」误拦', () => {
      const dp = setup([lockOwner()])
      expect(dp.validate()).toEqual([])
      expect(dp.errors.value).toEqual({})
    })

    it('不为空（values 为空）同样放行', () => {
      const dp = setup([lockOwner({ operator: 'is_not_empty' })])
      expect(dp.validate()).toEqual([])
    })

    it('有值运算符 in 却没选值 → 仍被拦（防放宽过头的回归锚点）', () => {
      const dp = setup([lockOwner({ operator: 'in' })])
      expect(dp.validate()).toEqual(['candidate'])
      expect(dp.errors.value.candidate).toContain('请为每条条件选择业务值')
    })

    it('REL_NOVALUE_OPS 与后端 lock_owner 空值运算符集合一致', () => {
      expect([...REL_NOVALUE_OPS].sort()).toEqual(['is_empty', 'is_not_empty'])
    })
  })
})
