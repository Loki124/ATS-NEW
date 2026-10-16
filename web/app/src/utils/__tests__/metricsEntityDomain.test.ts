/**
 * metricsEntityDomain.test.ts — 实体引用型值域纯逻辑 单测。
 *
 * 覆盖从 useMetricsWorkspace.ts 下沉的业务规则：
 *   - toEntityOptions：接口行归一（多名字字段回退 / 去重 / 脏数据丢弃）
 *   - 全选哨兵项协议：isAllSelected / withSelectAllOption / applySelectAll 三种情形
 *   - makeEntityOption：候选生成（自动生效类走 i18n，指定类拼快照 label）
 *   - normalizeValueDomain / buildSaveEntityDomain：载入与保存的归一
 */
import { describe, it, expect } from 'vitest'
import {
  toEntityOptions,
  entityTypeNeedsPicker,
  entityAutoLabelKey,
  isSelectAllValue,
  isAllSelected,
  withSelectAllOption,
  applySelectAll,
  makeEntityOption,
  normalizeValueDomain,
  buildSaveEntityDomain,
  SELECT_ALL,
} from '../metricsEntityDomain'

// 纯函数不接 i18n 的 t，改注入「已解析好的文案函数」；identity mock 让断言只关心选键逻辑。
const labels = {
  selectAll: () => 'ALL',
  selectAllOff: () => 'ALL_OFF',
  currentUser: () => 'CU',
  currentUserDept: () => 'CU_DEPT',
}
const opts = [
  { label: '张三', value: 'u1' },
  { label: '李四', value: 'u2' },
  { label: '王五', value: 'u3' },
]

describe('toEntityOptions', () => {
  it('按名字字段优先级取名', () => {
    expect(toEntityOptions([{ id: '1', fullName: '甲', realName: '乙' }], ['fullName', 'realName']))
      .toEqual([{ id: '1', name: '甲', label: '甲' }])
  })

  it('首个名字字段为空时回退到下一个', () => {
    expect(toEntityOptions([{ id: '1', fullName: '  ', name: '乙' }], ['fullName', 'name'])[0].name).toBe('乙')
  })

  it('label 与 name 同值', () => {
    expect(toEntityOptions([{ id: '1', name: '甲' }], ['name'])[0]).toEqual({ id: '1', name: '甲', label: '甲' })
  })

  it('id 缺失的行丢弃', () => {
    expect(toEntityOptions([{ name: '无 id' }], ['name'])).toEqual([])
  })

  it('id 为 null 时回退 pk / value', () => {
    expect(toEntityOptions([{ pk: '9', name: '甲' }], ['name'])[0].id).toBe('9')
    expect(toEntityOptions([{ value: '8', name: '甲' }], ['name'])[0].id).toBe('8')
  })

  it('名字为空的行丢弃', () => {
    expect(toEntityOptions([{ id: '1', name: '   ' }], ['name'])).toEqual([])
  })

  it('同 id 只保留首次出现', () => {
    expect(toEntityOptions([{ id: '1', name: '甲' }, { id: '1', name: '乙' }], ['name'])).toHaveLength(1)
  })

  it('null 行跳过不抛错', () => {
    expect(toEntityOptions([null, { id: '1', name: '甲' }], ['name'])).toHaveLength(1)
  })

  it('空数组返回空数组', () => {
    expect(toEntityOptions([], ['name'])).toEqual([])
  })
})

describe('entityTypeNeedsPicker', () => {
  it('当前登录人 / 所在部门无需选对象', () => {
    expect(entityTypeNeedsPicker('current_user')).toBe(false)
    expect(entityTypeNeedsPicker('current_user_dept')).toBe(false)
  })

  it('指定人员 / 身份需选对象', () => {
    expect(entityTypeNeedsPicker('specified')).toBe(true)
    expect(entityTypeNeedsPicker('identity')).toBe(true)
  })
})

describe('entityAutoLabelKey', () => {
  it('所在部门与当前登录人走不同 i18n 键', () => {
    expect(entityAutoLabelKey('current_user_dept')).toBe('metrics.tpl.entityCurrentUserDept')
    expect(entityAutoLabelKey('current_user')).toBe('metrics.tpl.entityCurrentUser')
  })
})

describe('全选哨兵项协议', () => {
  it('isSelectAllValue 只认哨兵常量', () => {
    expect(isSelectAllValue(SELECT_ALL)).toBe(true)
    expect(isSelectAllValue('u1')).toBe(false)
  })

  it('覆盖全部候选 → 判为全选', () => {
    expect(isAllSelected(opts, ['u1', 'u2', 'u3'])).toBe(true)
  })

  it('缺一即非全选', () => {
    expect(isAllSelected(opts, ['u1', 'u2'])).toBe(false)
  })

  it('候选为空时永远非全选（避免空数组 every 为真）', () => {
    expect(isAllSelected([], [])).toBe(false)
  })

  it('未全选时顶部项显示「全部」', () => {
    expect(withSelectAllOption(opts, ['u1'], labels)[0]).toEqual({ label: 'ALL', value: SELECT_ALL })
  })

  it('已全选时顶部项切换为「取消全部」', () => {
    expect(withSelectAllOption(opts, ['u1', 'u2', 'u3'], labels)[0])
      .toEqual({ label: 'ALL_OFF', value: SELECT_ALL })
  })

  it('顶部项之后的候选原序保留', () => {
    expect(withSelectAllOption(opts, [], labels).slice(1)).toEqual(opts)
  })

  it('情形1 勾上哨兵 → 全选', () => {
    expect(applySelectAll([SELECT_ALL], opts, false)).toEqual(['u1', 'u2', 'u3'])
  })

  it('情形2 原本全选、只取消哨兵 → 清空', () => {
    expect(applySelectAll(['u1', 'u2', 'u3'], opts, true)).toEqual([])
  })

  it('情形3 原本全选、取消某个具体项 → 保留剩余', () => {
    expect(applySelectAll(['u1', 'u3'], opts, true)).toEqual(['u1', 'u3'])
  })

  it('非全选时逐项挑选 → 剔除哨兵', () => {
    expect(applySelectAll(['u1', SELECT_ALL, 'u3'], opts, false)).toEqual(['u1', 'u2', 'u3'])
  })

  it('清空选择 → 返回空数组', () => {
    expect(applySelectAll([], opts, false)).toEqual([])
  })
})

describe('makeEntityOption', () => {
  it('指定类：ids 去重、label 按传入顺序拼对象名（不去重，沿用原实现）', () => {
    expect(makeEntityOption('specified', ['u1', 'u1', 'u2'], opts, labels))
      .toEqual({ type: 'specified', ids: ['u1', 'u2'], label: '张三、张三、李四' })
  })

  it('指定类：未知 id 以 id 本身兜底', () => {
    expect(makeEntityOption('specified', ['zzz'], opts, labels).label).toBe('zzz')
  })

  it('指定类：剔除空 id', () => {
    expect(makeEntityOption('specified', ['u1', ''], opts, labels).ids).toEqual(['u1'])
  })

  it('当前登录人：ids 强制为空，label 走 i18n', () => {
    expect(makeEntityOption('current_user', ['u1'], opts, labels))
      .toEqual({ type: 'current_user', ids: [], label: 'CU' })
  })

  it('当前登录人所在部门：走部门 i18n 键', () => {
    expect(makeEntityOption('current_user_dept', [], opts, labels).label).toBe('CU_DEPT')
  })
})

describe('normalizeValueDomain', () => {
  it('带 kind 的实体型：保留 kind 与 options', () => {
    expect(normalizeValueDomain({ kind: 'person', options: [{ type: 'specified', ids: ['u1'], label: '张三' }] }))
      .toEqual({ kind: 'person', options: [{ type: 'specified', ids: ['u1'], label: '张三' }] })
  })

  it('实体型 options 缺 id 数组 → 补空数组', () => {
    expect(normalizeValueDomain({ kind: 'person', options: [{ type: 'specified' }] }))
      .toEqual({ kind: 'person', options: [{ type: 'specified', ids: [], label: '' }] })
  })

  it('实体型 options 非数组 → 空数组', () => {
    expect(normalizeValueDomain({ kind: 'department', options: 'x' }))
      .toEqual({ kind: 'department', options: [] })
  })

  it('丢弃无 type 的脏候选', () => {
    const r = normalizeValueDomain({ kind: 'person', options: [{ ids: ['u1'] }] })
    expect(r).toEqual({ kind: 'person', options: [] })
  })

  it('非法 kind 视为历史值域', () => {
    expect(normalizeValueDomain({ kind: 'robot', options: [] })).toEqual({ segments: [] })
  })

  it('历史值域：深拷贝 segments 不共享引用', () => {
    const segs = [{ min: 1 }]
    const r = normalizeValueDomain({ segments: segs }) as { segments: any[] }
    expect(r.segments).toEqual(segs)
    expect(r.segments[0]).not.toBe(segs[0])
  })

  it('null / 非对象入参兜底为空 segments', () => {
    expect(normalizeValueDomain(null)).toEqual({ segments: [] })
    expect(normalizeValueDomain('bad')).toEqual({ segments: [] })
  })
})

describe('buildSaveEntityDomain', () => {
  it('落 kind + 清理后的候选清单', () => {
    expect(buildSaveEntityDomain({ options: [{ type: 'specified', ids: ['u1'], label: '张三' }] }, 'person'))
      .toEqual({ kind: 'person', options: [{ type: 'specified', ids: ['u1'], label: '张三' }] })
  })

  it('ids 剔除空白项', () => {
    expect(buildSaveEntityDomain({ options: [{ type: 'specified', ids: ['u1', '  '], label: 'x' }] }, 'person')
      .options[0].ids).toEqual(['u1'])
  })

  it('label 去首尾空白', () => {
    expect(buildSaveEntityDomain({ options: [{ type: 'specified', ids: [], label: '  张三  ' }] }, 'person')
      .options[0].label).toBe('张三')
  })

  it('丢弃无 type 的脏候选', () => {
    expect(buildSaveEntityDomain({ options: [{ ids: ['u1'] }] }, 'person').options).toEqual([])
  })

  it('options 非数组 → 空数组', () => {
    expect(buildSaveEntityDomain({ options: null }, 'department').options).toEqual([])
  })

  it('kind 取调用方传入值', () => {
    expect(buildSaveEntityDomain({}, 'department').kind).toBe('department')
  })
})
