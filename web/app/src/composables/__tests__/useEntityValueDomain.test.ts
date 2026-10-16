/**
 * useEntityValueDomain.test.ts — 实体引用型值域（人员 / 部门 / 身份）域 composable 单测。
 *
 * 覆盖从 useMetricsWorkspace.ts 下沉到本 composable 的业务规则：
 *   - 三份下拉数据源的懒加载与 fail-soft（Promise.allSettled，单个失败不阻断其余）；
 *   - 人员型 / 部门型取值方式清单差异；
 *   - 「全部」哨兵项协议在已配置行 / 草稿行上的三处一致行为；
 *   - 新增候选的校验顺序（选方式 → 不重复 → 指定类必须有对象）；
 *   - 改人后 label 快照同步刷新；
 *   - 取值方式配齐后隐藏添加入口。
 *
 * 为什么值得测：全选哨兵在 Naive UI 里不可区分「取消勾选全选项」与「逐个勾满」，
 * 这段三态协议判错就是「点一次全选却把已有选择清空」的用户可见 bug；
 * 而 fail-soft 判错会让单个接口失败拖垮整个值域配置区。
 *
 * mock 说明：3 个接口用 vi.mock 全量替换（工厂必须逐个列出被测文件的具名导出）。
 * i18n 的 t 与 naive-ui 的 useMessage 由 src/__tests__/setup.ts 全局 mock。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, nextTick } from 'vue'

vi.mock('@/api/users', () => ({ listUsers: vi.fn() }))
vi.mock('@/api/role-v2', () => ({ listRoles: vi.fn() }))
vi.mock('@/api/management-unit', () => ({ listManagementUnits: vi.fn() }))

import { listUsers } from '@/api/users'
import { listRoles } from '@/api/role-v2'
import { listManagementUnits } from '@/api/management-unit'
import { useEntityValueDomain } from '../useEntityValueDomain'
import { SELECT_ALL } from '@/utils/metricsEntityDomain'

const mocked = {
  users: listUsers as unknown as ReturnType<typeof vi.fn>,
  roles: listRoles as unknown as ReturnType<typeof vi.fn>,
  units: listManagementUnits as unknown as ReturnType<typeof vi.fn>,
}

const USERS = [
  { id: 'u1', fullName: '张三' },
  { id: 'u2', fullName: '李四' },
  { id: 'u3', name: '王五' },
]
const ROLES = [{ id: 'r1', roleName: '技术面试官' }, { id: 'r2', name: 'HRBP' }]
const UNITS = [{ id: 'm1', unitName: '研发部' }, { id: 'm2', name: '产品部' }]

function setup(kind: 'person' | 'department' | '' = 'person') {
  const tplForm = ref<any>({ valueDomain: { kind, options: [] } })
  const api = useEntityValueDomain({
    tplForm,
    entityKind: ref(kind as any),
    isDeptOutput: ref(kind === 'department'),
  })
  return { tplForm, api }
}

beforeEach(() => {
  vi.clearAllMocks()
  mocked.users.mockResolvedValue(USERS)
  mocked.roles.mockResolvedValue(ROLES)
  mocked.units.mockResolvedValue(UNITS)
})

describe('下拉数据源加载', () => {
  it('首次加载拉三份列表并归一为 {id,name,label}', async () => {
    const { api } = setup('person')
    await api.ensureEntityOptions()
    expect(mocked.users).toHaveBeenCalledTimes(1)
    expect(mocked.roles).toHaveBeenCalledTimes(1)
    expect(mocked.units).toHaveBeenCalledTimes(1)
    expect(api.entityUsers.value.map((u) => u.label)).toEqual(['张三', '李四', '王五'])
    expect(api.entityIdentities.value.map((u) => u.label)).toEqual(['技术面试官', 'HRBP'])
    expect(api.entityUnits.value.map((u) => u.label)).toEqual(['研发部', '产品部'])
    expect(api.entityOptionsLoaded.value).toBe(true)
    expect(api.entityOptionsLoading.value).toBe(false)
  })

  it('懒加载：已加载过不再重复请求', async () => {
    const { api } = setup('person')
    await api.ensureEntityOptions()
    await api.ensureEntityOptions()
    expect(mocked.users).toHaveBeenCalledTimes(1)
  })

  it('🔴 fail-soft：单个接口失败不阻断其余两份', async () => {
    mocked.users.mockRejectedValue(new Error('boom'))
    const { api } = setup('person')
    await api.ensureEntityOptions()
    expect(api.entityUsers.value).toEqual([])
    expect(api.entityIdentities.value).toHaveLength(2)
    expect(api.entityUnits.value).toHaveLength(2)
    expect(api.entityOptionsLoading.value).toBe(false)
  })

  it('身份/部门接口返回分页信封时也能取到 rows', async () => {
    mocked.roles.mockResolvedValue({ items: ROLES })
    mocked.units.mockResolvedValue({ results: UNITS })
    const { api } = setup('person')
    await api.ensureEntityOptions()
    expect(api.entityIdentities.value).toHaveLength(2)
    expect(api.entityUnits.value).toHaveLength(2)
  })

  it('toEntityOptions 直接透出纯函数结果', () => {
    const { api } = setup('person')
    expect(api.toEntityOptions(USERS, ['fullName'])).toEqual([
      { id: 'u1', name: '张三', label: '张三' },
      { id: 'u2', name: '李四', label: '李四' },
    ])
  })
})

describe('取值方式清单', () => {
  it('人员型：指定人员 / 指定身份 / 当前登录人', () => {
    const { api } = setup('person')
    expect(api.entitySelectorOptions.value.map((o) => o.value)).toEqual([
      'specified',
      'identity',
      'current_user',
    ])
    expect(api.entityDefaultSelector.value).toBe('specified')
  })

  it('部门型：指定部门 / 当前登录人部门', () => {
    const { api } = setup('department')
    expect(api.entitySelectorOptions.value.map((o) => o.value)).toEqual(['specified', 'current_user_dept'])
  })

  it('entityDomain：valueDomain 缺失时补默认形状', () => {
    const tplForm = ref<any>({})
    const api = useEntityValueDomain({
      tplForm,
      entityKind: ref('person'),
      isDeptOutput: ref(false),
    })
    expect(api.entityDomain.value).toEqual({ kind: 'person', selector: '', multiple: true })
  })

  it('entityOptionsForType 按类型取对应数据源', async () => {
    const { api } = setup('person')
    await api.ensureEntityOptions()
    expect(api.entityOptionsForType('identity').map((o) => o.label)).toEqual(['技术面试官', 'HRBP'])
    expect(api.entityOptionsForType('specified').map((o) => o.label)).toEqual(['张三', '李四', '王五'])

    const dept = setup('department')
    await dept.api.ensureEntityOptions()
    expect(dept.api.entityOptionsForType('specified').map((o) => o.label)).toEqual(['研发部', '产品部'])
  })

  it('entityTypeNeedsPicker：当前登录人两类无需选对象', () => {
    const { api } = setup('person')
    expect(api.entityTypeNeedsPicker('specified')).toBe(true)
    expect(api.entityTypeNeedsPicker('identity')).toBe(true)
    expect(api.entityTypeNeedsPicker('current_user')).toBe(false)
    expect(api.entityTypeNeedsPicker('current_user_dept')).toBe(false)
    expect(api.entityAutoLabelKey('current_user_dept')).toBe('metrics.tpl.entityCurrentUserDept')
    expect(api.entityAutoLabelKey('current_user')).toBe('metrics.tpl.entityCurrentUser')
  })
})

describe('全选哨兵项', () => {
  it('已配置行的下拉顶部插入哨兵项，选中值含哨兵', async () => {
    const { tplForm, api } = setup('person')
    await api.ensureEntityOptions()
    tplForm.value.valueDomain.options = [{ type: 'specified', ids: ['u1', 'u2', 'u3'], label: '张三、李四、王五' }]
    const opts = api.entityRowPickerOptions(0)
    expect(opts[0].value).toBe(SELECT_ALL)
    expect(api.entityRowPickerValue(0)).toEqual([SELECT_ALL, 'u1', 'u2', 'u3'])
    expect(api.entityRowIsAll(0)).toBe(true)
  })

  it('部分选中时不给哨兵项', async () => {
    const { tplForm, api } = setup('person')
    await api.ensureEntityOptions()
    tplForm.value.valueDomain.options = [{ type: 'specified', ids: ['u1'], label: '张三' }]
    expect(api.entityRowPickerValue(0)).toEqual(['u1'])
    expect(api.entityRowIsAll(0)).toBe(false)
  })

  it('行不存在时三个接口都安全返回空', () => {
    const { api } = setup('person')
    expect(api.entityRowPickerOptions(9)).toEqual([])
    expect(api.entityRowPickerValue(9)).toEqual([])
    expect(api.entityRowIsAll(9)).toBe(false)
  })

  it('草稿行的哨兵项与全选判定同款', async () => {
    const { api } = setup('person')
    await api.ensureEntityOptions()
    api.entityDraft.value = { type: 'specified', ids: [] }
    // entityDraftPickerOptions 是纯候选源（不含哨兵），哨兵只出现在 ...All 版本
    expect(api.entityDraftPickerOptions().map((o) => o.value)).toEqual(['u1', 'u2', 'u3'])
    expect(api.entityDraftPickerOptionsAll.value[0].value).toBe(SELECT_ALL)
    expect(api.entityDraftPickerValue.value).toEqual([])
    expect(api.entityDraftIsAll.value).toBe(false)

    api.entityDraft.value = { type: 'specified', ids: ['u1', 'u2', 'u3'] }
    expect(api.entityDraftPickerValue.value).toEqual([SELECT_ALL, 'u1', 'u2', 'u3'])
    expect(api.entityDraftIsAll.value).toBe(true)
  })

  it('勾上哨兵 → 全选；已全选只取消哨兵 → 清空；已全选取消某项 → 保留其余', async () => {
    const { tplForm, api } = setup('person')
    await api.ensureEntityOptions()
    tplForm.value.valueDomain.options = [{ type: 'specified', ids: ['u1'], label: '张三' }]
    const base = api.entityOptionsForType('specified')

    // 1. 勾上哨兵 → 全选
    api.handleEntityRowPickerUpdate(0, [SELECT_ALL])
    expect(tplForm.value.valueDomain.options[0].ids).toEqual(['u1', 'u2', 'u3'])

    // 2. 原本全选、只取消哨兵 → 清空
    api.handleEntityRowPickerUpdate(0, ['u1', 'u2', 'u3'])
    expect(tplForm.value.valueDomain.options[0].ids).toEqual([])

    // 3. 原本全选、取消某个具体项（哨兵随之被移除，raw 只剩真实 id 且数量 < 全部）→ 保留剩余
    tplForm.value.valueDomain.options[0].ids = ['u1', 'u2', 'u3']
    api.handleEntityRowPickerUpdate(0, ['u1', 'u2'])
    expect(tplForm.value.valueDomain.options[0].ids).toEqual(['u1', 'u2'])

    expect(base).toHaveLength(3)
  })

  it('草稿行的哨兵变更同样走三态协议', async () => {
    const { api } = setup('person')
    await api.ensureEntityOptions()
    api.entityDraft.value = { type: 'specified', ids: [] }
    api.handleEntityDraftPickerUpdate([SELECT_ALL])
    expect(api.entityDraft.value.ids).toEqual(['u1', 'u2', 'u3'])
    api.handleEntityDraftPickerUpdate(['u1', 'u2', 'u3'])
    expect(api.entityDraft.value.ids).toEqual([])
  })

  it('isSelectAllValue / withSelectAllOption / isAllSelected 直接透出', () => {
    const { api } = setup('person')
    expect(api.isSelectAllValue(SELECT_ALL)).toBe(true)
    expect(api.isSelectAllValue('u1')).toBe(false)
    const opts = [{ label: '张三', value: 'u1' }, { label: '李四', value: 'u2' }]
    expect(api.withSelectAllOption(opts, ['u1'])[0].value).toBe(SELECT_ALL)
    expect(api.withSelectAllOption(opts, ['u1', 'u2'])[1].label).toBe('张三')
    expect(api.isAllSelected(opts, ['u1', 'u2'])).toBe(true)
    expect(api.isAllSelected([], [])).toBe(false)
    expect(api.applySelectAll([SELECT_ALL], opts, false)).toEqual(['u1', 'u2'])
  })
})

describe('候选增删改', () => {
  it('新增候选：ids 去重；label 按原始 ids 顺序拼接（重复项不折叠，历史行为）', async () => {
    const { tplForm, api } = setup('person')
    await api.ensureEntityOptions()
    api.entityDraft.value = { type: 'specified', ids: ['u1', 'u1', 'u2'] }
    expect(api.addEntityOption()).toBe('')
    const opt = tplForm.value.valueDomain.options[0]
    expect(opt.ids).toEqual(['u1', 'u2'])
    // label 走的是未去重的 ids 映射后 join，重复 id 会被展示两次（重构不改动此行为）
    expect(opt.label).toBe('张三、张三、李四')
    expect(tplForm.value.valueDomain.kind).toBe('person')
  })

  it('校验顺序：未选方式 → 未选方式报错；重复方式 → 重复报错', async () => {
    const { tplForm, api } = setup('person')
    await api.ensureEntityOptions()

    api.entityDraft.value = { type: '', ids: ['u1'] }
    expect(api.addEntityOption()).not.toBe('')

    tplForm.value.valueDomain.options = [{ type: 'specified', ids: ['u1'], label: '张三' }]
    api.entityDraft.value = { type: 'specified', ids: ['u2'] }
    expect(api.addEntityOption()).not.toBe('')
  })

  it('指定类未选对象 → 报错且不写入', async () => {
    const { tplForm, api } = setup('person')
    await api.ensureEntityOptions()
    api.entityDraft.value = { type: 'specified', ids: [] }
    expect(api.addEntityOption()).not.toBe('')
    expect(tplForm.value.valueDomain.options).toHaveLength(0)
  })

  it('当前登录人类无需选对象即可新增', async () => {
    const { tplForm, api } = setup('person')
    await api.ensureEntityOptions()
    api.entityDraft.value = { type: 'current_user', ids: [] }
    expect(api.addEntityOption()).toBe('')
    expect(tplForm.value.valueDomain.options[0].ids).toEqual([])
    expect(tplForm.value.valueDomain.options[0].label).not.toBe('')
  })

  it('identity 类未选对象走身份专用文案', async () => {
    const { api } = setup('person')
    await api.ensureEntityOptions()
    api.entityDraft.value = { type: 'identity', ids: [] }
    expect(api.addEntityOption()).toBe(api.entityPickerRequiredText('identity'))

    const dept = setup('department')
    expect(dept.api.entityPickerRequiredText('specified')).not.toBe(
      dept.api.entityPickerRequiredText('current_user_dept'),
    )
  })

  it('entityDuplicateTypeText 带上方式名', () => {
    const { api } = setup('person')
    expect(api.entityDuplicateTypeText('specified')).toContain('指定人员')
  })

  it('删除候选按下标移除', async () => {
    const { tplForm, api } = setup('person')
    await api.ensureEntityOptions()
    tplForm.value.valueDomain.options = [
      { type: 'specified', ids: ['u1'], label: '张三' },
      { type: 'identity', ids: ['r1'], label: '技术面试官' },
    ]
    api.removeEntityOption(0)
    expect(tplForm.value.valueDomain.options).toHaveLength(1)
    expect(tplForm.value.valueDomain.options[0].type).toBe('identity')
  })

  it('🔴 改人后 label 快照同步刷新（对象改名仍可读）', async () => {
    const { tplForm, api } = setup('person')
    await api.ensureEntityOptions()
    tplForm.value.valueDomain.options = [{ type: 'specified', ids: ['u1'], label: '张三' }]
    api.updateEntityOptionIds(0, ['u2', 'u3'])
    expect(tplForm.value.valueDomain.options[0].ids).toEqual(['u2', 'u3'])
    expect(tplForm.value.valueDomain.options[0].label).toBe('李四、王五')

    api.updateEntityOptionIds(9, ['u1']) // 下标越界安全忽略
    expect(tplForm.value.valueDomain.options[0].ids).toEqual(['u2', 'u3'])
  })

  it('entityCandidateOptions：value 为可解析 JSON，保留取值方式与 ids', async () => {
    const { tplForm, api } = setup('person')
    tplForm.value.valueDomain.options = [
      { type: 'specified', ids: ['u1'], label: '张三' },
      { type: 'identity', ids: ['r1'], label: '' },
    ]
    const opts = api.entityCandidateOptions.value
    expect(opts[0].value).toBe(JSON.stringify({ t: 'specified', i: 0, ids: ['u1'] }))
    expect(opts[1].label).toBe('指定身份')
  })
})

describe('草稿行交互', () => {
  it('showEntityDraft 默认选中第一个未用方式并展开', async () => {
    const { api } = setup('person')
    api.showEntityDraft()
    expect(api.entityDraftVisible.value).toBe(true)
    expect(api.entityDraft.value.type).toBe('specified')
  })

  it('方式配齐 → 添加入口隐藏，showEntityDraft 不展开', async () => {
    const { tplForm, api } = setup('person')
    tplForm.value.valueDomain.options = [
      { type: 'specified', ids: ['u1'], label: '张三' },
      { type: 'identity', ids: ['r1'], label: '技术面试官' },
      { type: 'current_user', ids: [], label: '当前登录人' },
    ]
    expect(api.entityTypesExhausted.value).toBe(true)
    api.showEntityDraft()
    expect(api.entityDraftVisible.value).toBe(false)
  })

  it('cancelEntityDraft 复位并收起', () => {
    const { api } = setup('person')
    api.entityDraft.value = { type: 'specified', ids: ['u1'] }
    api.entityDraftVisible.value = true
    api.cancelEntityDraft()
    expect(api.entityDraft.value).toEqual({ type: '', ids: [] })
    expect(api.entityDraftVisible.value).toBe(false)
  })

  it('confirmEntityDraft：成功则复位并收起，失败则把错误挂到草稿行', async () => {
    const { api } = setup('person')
    await api.ensureEntityOptions()

    api.entityDraft.value = { type: 'specified', ids: [] }
    api.confirmEntityDraft()
    expect(api.entityDraftError.value).not.toBe('')
    expect(api.entityDraftVisible.value).toBe(false)

    api.entityDraft.value = { type: 'specified', ids: ['u1'] }
    api.confirmEntityDraft()
    expect(api.entityDraftError.value).toBe('')
    expect(api.entityDraft.value).toEqual({ type: '', ids: [] })
  })

  it('草稿内容一变就清错误', async () => {
    const { api } = setup('person')
    api.entityDraftError.value = 'E'
    api.entityDraft.value = { type: 'specified', ids: ['u1'] }
    await nextTick()
    expect(api.entityDraftError.value).toBe('')
  })

  it('entityUsedTypes / entityUnusedSelectorOptions 反映已配方式', () => {
    const { tplForm, api } = setup('person')
    tplForm.value.valueDomain.options = [{ type: 'specified', ids: [], label: '' }]
    expect(api.entityUsedTypes.value).toEqual(['specified'])
    expect(api.entityUnusedSelectorOptions.value.map((o) => o.value)).toEqual(['identity', 'current_user'])
  })

  it('entityTypeLabel 未知类型回落原值', () => {
    const { api } = setup('person')
    expect(api.entityTypeLabel('specified')).toBe('指定人员')
    expect(api.entityTypeLabel('unknown')).toBe('unknown')
  })
})
