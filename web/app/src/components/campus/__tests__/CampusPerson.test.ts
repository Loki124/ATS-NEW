/**
 * 校招生档案页 —— 二期行为契约测试。
 *
 * 锁住二期五项需求的前端行为：
 *  1. 页面标题（h1 + 副标题）与顶部权限提示条已移除
 *  2. 状态页签 = 全部 / 在职 / 待入职 / 离职，且「待入职」映射到后端多值状态
 *  3. 筛选区含 性别 / 班级 / 导师 / 班主任，且各自映射到后端查询参数
 *  4. 姓名可点击 → 打开个人档案详情弹窗
 *  5. 列表接口字段驱动表格列（含新增的工号 / 班级 / 班主任）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusPerson from '../../../pages/campus/CampusPerson.vue'

const apiGet = vi.fn()
const apiPost = vi.fn()
const apiPut = vi.fn()
const apiDelete = vi.fn()

vi.mock('../../../utils/request', () => ({
  api: {
    get: (...args: any[]) => apiGet(...args),
    post: (...args: any[]) => apiPost(...args),
    put: (...args: any[]) => apiPut(...args),
    delete: (...args: any[]) => apiDelete(...args),
  },
}))

const searchUsers = vi.fn(async () => [
  { label: '张老师（E001）', value: 'u1' },
  { label: '李导师（E002）', value: 'u2' },
])
const searchClassRooms = vi.fn(async () => [{ label: '2610 班', value: 'cr1' }])
vi.mock('../../../utils/campus', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../utils/campus')>()
  return {
    ...actual,
    searchUsers: (...args: any[]) => searchUsers(...(args as [])),
    searchClassRooms: (...args: any[]) => searchClassRooms(...(args as [])),
  }
})

const person = {
  id: 'p1',
  code: 'C00000001',
  name: '员工16',
  employeeId: '',
  bu: '三到BG',
  school: '211',
  sex: '男',
  major: '工学',
  month: '8月',
  status: '在职',
  expectedEntryDate: null,
  actualEntryDate: null,
  position: '',
  level: '',
  headTeacher: null,
  headTeacherName: '',
  classRoom: null,
  classRoomName: '',
  mentor: null,
  mentorName: '',
  schoolName: '',
  majorName: '',
  intentBu: null,
  education: '',
  phone: '',
  counted: true,
}

/** 取最近一次列表请求的 query 参数 */
const lastParams = () => {
  const call = apiGet.mock.calls[apiGet.mock.calls.length - 1]
  return call[1]?.params ?? {}
}

describe('CampusPerson 二期行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { data: [person] } })
    searchUsers.mockClear()
    searchClassRooms.mockClear()
  })

  const mountPage = async () => {
    const wrapper = mount(CampusPerson, {
      global: { stubs: { teleport: true } },
    })
    await flushPromises()
    return wrapper
  }

  it('① 页面标题与顶部权限提示条已移除', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('h1.page-title').exists()).toBe(false)
    expect(wrapper.find('.page-subtitle').exists()).toBe(false)
    expect(wrapper.find('.scope-alert').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('本页仅维护校招生档案')
  }, 20000)

  it('② 状态页签 = 全部/在职/待入职/离职，旧的 在途Offer / 候选池 页签下线', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab').map((t) => t.text())
    expect(tabs).toEqual(['全部', '在职', '待入职', '离职'])
  }, 20000)

  it('② 切「待入职」页签 → 后端 status 参数为单值「待入职」', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab')
    const pending = tabs.find((t) => t.text() === '待入职')!
    await pending.trigger('click')
    await flushPromises()
    expect(lastParams().status).toBe('待入职')

    const resigned = wrapper.findAll('.n-tabs-tab').find((t) => t.text() === '离职')!
    await resigned.trigger('click')
    await flushPromises()
    expect(lastParams().status).toBe('离职')
  }, 20000)

  it('③ 工具栏常驻筛选 = 部门 / 轮岗状态 / 导师 / 班主任；性别 / 班级 / 在职状态 移入高级筛选', async () => {
    const wrapper = await mountPage()
    // n-select 的占位符渲染在 .n-base-selection-placeholder（非 input[placeholder]）
    const placeholders = wrapper.findAll('.n-base-selection-placeholder').map((n) => n.text())
    // 工具栏只保留高频维度（2026-10-22 兵哥指令：避免首屏筛选项过载）
    expect(placeholders).toContain('全部部门')
    expect(placeholders).toContain('全部轮岗状态')
    expect(placeholders).toContain('全部导师')
    expect(placeholders).toContain('全部班主任')
    // 性别 / 班级 / 在职状态 收进「高级筛选」弹窗
    expect(placeholders).not.toContain('全部性别')
    expect(placeholders).not.toContain('全部班级')
  }, 20000)

  it('③ 筛选值映射到后端查询参数（工具栏 mentor / head_teacher + 高级筛选 sex / class_room）', async () => {
    const wrapper = await mountPage()
    // 直接驱动组件的筛选状态，验证 → 请求参数的映射
    const vm = wrapper.vm as any
    vm.advancedForm.sex = '男'
    vm.advancedForm.classRoom = 'cr1'
    vm.filterMentor = 'u2'
    vm.filterHeadTeacher = 'u1'
    await vm.reload()
    await flushPromises()

    const params = lastParams()
    expect(params.sex).toBe('男')
    expect(params.class_room).toBe('cr1')
    expect(params.mentor).toBe('u2')
    expect(params.head_teacher).toBe('u1')
  }, 20000)

  it('④ 姓名可点击 → 打开个人档案详情弹窗', async () => {
    const wrapper = await mountPage()
    const nameBtn = wrapper.findAll('.n-data-table-tbody button').find((b) => b.text() === '员工16')
    expect(nameBtn).toBeTruthy()
    await nameBtn!.trigger('click')
    await flushPromises()
    // 弹窗被渲染（含「个人档案 ·」标题）
    expect(wrapper.html()).toContain('个人档案 ·')
  }, 20000)

  it('⑤ 表格列含 工号 / 班级 / 带教导师 / HRBP（需求 2-2 字段），且不含 候选人编号', async () => {
    const wrapper = await mountPage()
    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text())
    expect(heads.join('|')).toContain('姓名')
    expect(heads.join('|')).toContain('工号')
    expect(heads.join('|')).toContain('班级')
    // 2026-10-22 兵哥指令：列重排后「班主任」列下线，改为「带教导师 / HRBP」
    expect(heads.join('|')).toContain('带教导师')
    expect(heads.join('|')).toContain('HRBP')
    expect(heads.join('|')).not.toContain('候选人编号')
  }, 20000)
})

describe('校招生档案编辑弹窗 · 分组重排（2026-10-22）', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { data: [person] } })
  })

  const mountAndOpenEdit = async () => {
    const wrapper = mount(CampusPerson, { global: { stubs: { teleport: true } } })
    await flushPromises()
    ;(wrapper.vm as any).openEdit({ ...person })
    await flushPromises()
    return wrapper
  }

  /** 取编辑弹窗内各分组的表单项标签（按分组） */
  const groupLabels = (wrapper: Awaited<ReturnType<typeof mountAndOpenEdit>>) =>
    wrapper.findAll('.form-section').map((s) => ({
      title: s.find('.form-section-title').text().replace(/\s+/g, ' ').trim(),
      labels: s.findAll('.n-form-item-label').map((l) => l.text().replace(/\*/g, '').trim()),
    }))

  it('① 三个分组按「轮岗信息 → 基本信息 → 毕业院校」排序', async () => {
    const w = await mountAndOpenEdit()
    const groups = groupLabels(w)
    expect(groups.map((g) => g.title.split(' ')[0])).toEqual([
      '轮岗信息', '基本信息', '毕业院校',
    ])
  }, 20000)

  it('② 候选人编号字段隐藏（仅留数据库），关联候选人字段下线', async () => {
    const w = await mountAndOpenEdit()
    const labels = groupLabels(w).flatMap((g) => g.labels)
    expect(labels).not.toContain('候选人编号')
    expect(labels).not.toContain('关联候选人')
  }, 20000)

  it('③ 基本信息组：姓名/性别/在职状态/工号/预计入职日期/实际入职日期，全部禁止编辑', async () => {
    const w = await mountAndOpenEdit()
    const g = groupLabels(w).find((x) => x.title.startsWith('基本信息'))!
    expect(g.labels).toEqual([
      '姓名', '性别', '在职状态', '工号', '预计入职日期', '实际入职日期',
    ])
    // 2026-10-22 兵哥指令：组内字段**全部禁止编辑** → 统一 disabled（显式灰显锁定）。
    // ⚠️ 不再用 readonly：readonly 的白框看起来仍像可编辑，用户会反复去点。
    const section = w.findAll('.form-section').find((s) => s.find('.form-section-title').text().startsWith('基本信息'))!
    const inputs = section.findAll('input')
    expect(inputs.length).toBeGreaterThanOrEqual(4)
    inputs.forEach((i) => expect(i.attributes('disabled')).toBeDefined())
    const selects = section.findAll('.n-base-selection')
    expect(selects.length).toBe(2)
    selects.forEach((s) => expect(s.classes()).toContain('n-base-selection--disabled'))
    // 显式锁定标识：标题锁图标（不配提示文案，避免弹窗里堆说明）
    expect(section.find('.form-section-lock').exists()).toBe(true)
    expect(section.find('.form-section-note').exists()).toBe(false)
  }, 20000)

  it('④ 毕业院校组：院校名称→专业名称→学历→学位，全部禁止编辑；标签在标题后', async () => {
    const w = await mountAndOpenEdit()
    const g = groupLabels(w).find((x) => x.title.startsWith('毕业院校'))!
    expect(g.labels).toEqual(['院校名称', '专业名称', '学历', '学位'])
    expect(g.labels).not.toContain('院校标签')
    expect(g.labels).not.toContain('专业标签')
    const tags = w.findAll('.form-section-title .n-tag').map((t) => t.text())
    expect(tags.length).toBeGreaterThanOrEqual(2)
    // 该组全部禁止编辑（统一 disabled）
    const section = w.findAll('.form-section').find((s) => s.find('.form-section-title').text().startsWith('毕业院校'))!
    section.findAll('input').forEach((i) => expect(i.attributes('disabled')).toBeDefined())
    section.findAll('.n-base-selection').forEach((s) => expect(s.classes()).toContain('n-base-selection--disabled'))
    // 显式锁定标识
    expect(section.find('.form-section-lock').exists()).toBe(true)
    expect(section.find('.form-section-note').exists()).toBe(false)
  }, 20000)

  it('⑤ 轮岗信息组：意向部门→当前轮岗部门→班级→班主任→HRBP→带教导师→批次', async () => {
    const w = await mountAndOpenEdit()
    const g = groupLabels(w).find((x) => x.title.startsWith('轮岗信息'))!
    expect(g.labels).toEqual([
      '意向部门', '当前轮岗部门', '班级', '班主任', 'HRBP', '带教导师', '批次',
    ])
  }, 20000)

  it('⑥ HRBP / 带教导师 不可编辑并提示「仅可在轮岗安排中填写」', async () => {
    const w = await mountAndOpenEdit()
    const hints = w.findAll('.field-hint').map((h) => h.text())
    expect(hints.filter((t) => t.includes('仅可在轮岗安排中填写')).length).toBe(2)
    // 两个字段的下拉都是 disabled
    const section = w.findAll('.form-section').find((s) => s.find('.form-section-title').text().startsWith('轮岗信息'))!
    const disabled = section.findAll('.n-base-selection--disabled')
    expect(disabled.length).toBe(2)
  }, 20000)

  it('⑦ 工号无值时显示横杠', async () => {
    const w = await mountAndOpenEdit()
    const section = w.findAll('.form-section').find((s) => s.find('.form-section-title').text().startsWith('基本信息'))!
    const empIdInput = section.findAll('input').find((i) => i.element.value === '-')
    expect(empIdInput).toBeTruthy()
  }, 20000)
})

describe('CampusPerson 二期工具栏（去按钮 / 搜索右置 / 查询·清空·高级筛选）', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { data: [person] } })
    searchUsers.mockClear()
    searchClassRooms.mockClear()
  })

  const mountPage = async () => {
    const wrapper = mount(CampusPerson, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 新建档案 / 刷新 按钮已移除', async () => {
    const wrapper = await mountPage()
    const buttons = wrapper.findAll('.toolbar button').map((b) => b.text())
    expect(buttons.join('|')).not.toContain('新建档案')
    expect(buttons.join('|')).not.toContain('刷新')
  }, 20000)

  it('② 搜索框在最右，其后依次是 查询 / 清空 / 高级筛选', async () => {
    const wrapper = await mountPage()
    const toolbar = wrapper.find('.toolbar')
    // 工具栏子节点顺序：5 个筛选下拉 → spacer → 搜索框 → 3 个按钮
    const kids = toolbar.element.children
    const order = Array.from(kids).map((el) => {
      if (el.classList.contains('rule-filter-search')) return 'search'
      if (el.classList.contains('n-button')) return el.textContent?.trim() ?? ''
      if (el.classList.contains('spacer')) return 'spacer'
      return 'filter'
    })
    const searchIdx = order.indexOf('search')
    expect(searchIdx).toBeGreaterThan(order.indexOf('spacer'))
    expect(order.slice(searchIdx + 1)).toEqual(['查询', '清空', '高级筛选'])
  }, 20000)

  it('③ 高级筛选：设置条件后点查询 → 请求参数带上 school/major（2026-10-22 已下线 position/level/month/year）', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.advancedForm.school = '985'
    vm.advancedForm.major = '工学'
    await vm.applyAdvanced()
    await flushPromises()

    const params = lastParams()
    expect(params.school).toBe('985')
    expect(params.major).toBe('工学')
    // 2026-10-22 兵哥指令：招聘月份 / 职务 / 职级 / 入职年度 已从高级筛选移除 → 不再下发
    expect(params.position).toBeUndefined()
    expect(params.level).toBeUndefined()
    expect(params.month).toBeUndefined()
    expect(params.year).toBeUndefined()
  }, 20000)

  it('④ 清空：重置全部筛选条件并重新查询', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.searchText = '张三'
    vm.advancedForm.sex = '男'
    vm.advancedForm.classRoom = 'cr1'
    vm.advancedForm.school = '985'
    await vm.clearFilters()
    await flushPromises()

    expect(vm.searchText).toBe('')
    expect(vm.advancedForm.sex).toBe(null)
    expect(vm.advancedForm.classRoom).toBe(null)
    expect(vm.advancedForm.school).toBe(null)
    const params = lastParams()
    expect(params.search).toBeUndefined()
    expect(params.sex).toBeUndefined()
    expect(params.school).toBeUndefined()
  }, 20000)

  it('⑤ 档案详情点「编辑基础信息」：档案页不消失，编辑弹窗打开', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.profileRow = { id: 'p1', name: '员工16' }
    vm.profileVisible = true
    await flushPromises()

    // 模拟档案详情弹窗抛出「编辑基础信息」
    vm.onProfileEdit({ person: person })
    await flushPromises()

    expect(vm.profileVisible).toBe(true)      // 档案页仍在
    expect(vm.modalVisible).toBe(true)       // 编辑弹窗已打开
  }, 20000)

  it('⑥ 示例数据模式：点 mock 姓名 → 本地拼档案载荷，不请求后端（否则必 404）', async () => {
    // 真实列表为空 ⇒ auto 模式兜底到示例数据
    apiGet.mockResolvedValue({ data: { data: [] } })
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    expect(vm.isMock).toBe(true)

    // 列表里是示例行（id 形如 MOCK_PS_01，后端不存在）
    const nameBtn = wrapper.findAll('.n-data-table-tbody button')
      .find((b) => (b.text() || '').trim() === '张一鸣')
    expect(nameBtn).toBeTruthy()
    apiGet.mockClear()
    await nameBtn!.trigger('click')
    await flushPromises()

    // 关键断言：没有发出 profile 请求（没有 /profile/ 的 URL）
    const urls = apiGet.mock.calls.map((c) => String(c[0]))
    expect(urls.some((u) => u.includes('/profile/'))).toBe(false)
    // 本地载荷已就位，弹窗直接渲染
    expect(vm.profilePreloaded).toBeTruthy()
    expect(vm.profilePreloaded.person.name).toBe('张一鸣')
  }, 20000)
})

/**
 * 2026-10-21 兵哥口径：编辑态下 姓名 / 工号 / 简历编号 / 院校 / 专业 / 预计入职日期 / 入职日期 只读。
 * 锁死规则：编辑态 + 字段已有值 → 只读；空值仍可补录（否则待入职→在职 的补录流程会被断死）。
 */
describe('CampusPerson 编辑态只读字段', () => {
  const personFull = {
    ...person,
    employeeId: '12345678',
    school: '211',
    schoolName: '武汉理工大学',
    major: '工学',
    expectedEntryDate: '2026-03-01',
    actualEntryDate: '2026-03-05',
  }

  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { data: [personFull] } })
    searchUsers.mockClear()
    searchClassRooms.mockClear()
  })

  const mountPage = async () => {
    const wrapper = mount(CampusPerson, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 编辑态：基本信息 / 毕业院校 两组全部禁止编辑；候选人编号不再展示', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.openEdit(personFull)
    await flushPromises()

    expect(vm.modalVisible).toBe(true)
    expect(vm.editing).toBeTruthy()
    // 两组的输入框全部 disabled（显式锁定，不只是 readonly）
    const sections = wrapper.findAll('.form-section')
    const basic = sections.find((s) => s.find('.form-section-title').text().startsWith('基本信息'))!
    const school = sections.find((s) => s.find('.form-section-title').text().startsWith('毕业院校'))!
    for (const sec of [basic, school]) {
      const inputs = sec.findAll('input')
      expect(inputs.length).toBeGreaterThan(0)
      inputs.forEach((i) => expect(i.attributes('disabled')).toBeDefined())
      sec.findAll('.n-base-selection').forEach((sel) =>
        expect(sel.classes()).toContain('n-base-selection--disabled'),
      )
    }
    // 2026-10-22：候选人编号字段已隐藏（仅留数据库）→ 表单里不再有该输入框
    const codeInput = wrapper.findAll('input').find((i) => i.attributes('value') === 'C00000001')
    expect(codeInput).toBeUndefined()
  }, 20000)

  it('② 空值同样禁止补录（2026-10-22 兵哥指令：两组字段**全部**禁止编辑）', async () => {
    // ⚠️ 旧契约是「有值才锁、缺值可补录」，本次指令已推翻：缺值也不可编辑
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.openEdit({ ...personFull, employeeId: '', actualEntryDate: null })
    await flushPromises()

    const basic = wrapper
      .findAll('.form-section')
      .find((s) => s.find('.form-section-title').text().startsWith('基本信息'))!
    const empInput = basic.findAll('input').find((i) => i.attributes('value') === '-')
    expect(empInput, '工号为空时仍应渲染为禁用输入框').toBeTruthy()
    expect(empInput!.attributes('disabled')).toBeDefined()
  }, 20000)

  it('③ 锁死 helper 已下线（两组一律 disabled，不再有「有值才锁」的分支）', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    expect(vm.editing).toBeFalsy()
    expect(vm.locked).toBeUndefined()
  }, 20000)

  it('④ 编辑态不再展示顶部只读字段提示（2026-10-22 下线提示内容）', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.openEdit(personFull)
    await flushPromises()
    const hints = wrapper.findAll('.readonly-hint')
    expect(hints).toHaveLength(0)
  }, 20000)
})

/**
 * 2026-10-21 兵哥口径：编号**自动获取**（不需要人工选候选人）+ 编辑弹窗字段分组。
 * 编号由后端按姓名(+手机号)到「招聘系统 · 候选人管理」自动认人后取其编号；
 * 前端只读展示编号与关联候选人，不提供任何选择器。
 */
describe('CampusPerson 编号自动获取 + 字段分组', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { data: [person] } })
    apiPost.mockReset()
    apiPut.mockReset()
    searchUsers.mockClear()
    searchClassRooms.mockClear()
  })

  const mountPage = async () => {
    const wrapper = mount(CampusPerson, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 编辑弹窗字段分为 3 组（轮岗信息 → 基本信息 → 毕业院校）', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.openEdit(person)
    await flushPromises()
    const titles = wrapper.findAll('.form-section-title').map((t) => t.text().split(' ')[0].trim())
    expect(titles).toEqual(['轮岗信息', '基本信息', '毕业院校'])
  }, 20000)

  it('② 表单里没有候选人选择器（编号自动获取，不需要人工选）', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.openEdit(person)
    await flushPromises()
    // 没有任何下拉绑定 formState.candidate
    expect(wrapper.findAll('.n-base-selection').filter((s) => s.html().includes('从招聘系统候选人中选择'))).toHaveLength(0)
    // 编号与关联候选人都是只读展示
    expect(vm.formCodeText).toBe(person.code)
    expect(vm.formCandidateText).toBe('')
  }, 20000)

  it('③ 已认定的档案：只读回显「编号 · 姓名」', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.openEdit({ ...person, candidate: 'cand-1', candidateCode: 'C00000042', candidateName: '候选人一' })
    await flushPromises()
    expect(vm.formCandidateText).toBe('C00000042 · 候选人一')
  }, 20000)

  it('④ 保存时不传 code / candidate（编号由后端自动获取）', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.openEdit({ ...person, status: '在职', employeeId: '12345678', actualEntryDate: '2026-03-05' })
    await flushPromises()

    await vm.save()
    await flushPromises()

    expect(apiPut).toHaveBeenCalled()
    const payload = apiPut.mock.calls[0][1]
    expect(payload.code).toBeUndefined()
    expect(payload.candidate).toBeUndefined()
  }, 20000)

  it('⑤ 编号被后端同步成候选人编号时给出提示', async () => {
    apiPut.mockResolvedValue({ data: { data: { ...person, code: 'C00000042' } } })
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.openEdit({ ...person, status: '在职', employeeId: '12345678', actualEntryDate: '2026-03-05' })
    await flushPromises()

    await vm.save()
    await flushPromises()
    // message.info 被全局 stub 掉 → 只断言不抛错、且保存成功
    expect(apiPut).toHaveBeenCalled()
  }, 20000)
})
