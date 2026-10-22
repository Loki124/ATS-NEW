/**
 * 人员管理页 · 筛选区重排（2026-10-22 兵哥指令）。
 *
 * 需求原文：「部门、轮岗状态、导师、班主任作为常驻筛选项，去掉在职状态筛选，
 *            其他筛选项放入高级筛选中」
 *
 * 最终口径（与并行会话的实现对齐）：
 *  - 常驻筛选项 = 部门 / 轮岗状态 / 导师 / 班主任；
 *  - 性别 / 班级 移入「高级筛选」弹窗；
 *  - **在职状态由页面状态页签唯一控制**，弹窗里不再重复一份
 *    （避免「页签选在职、弹窗选待入职」这种自相矛盾）。
 *
 * 常驻区那四项由并行会话的 CampusPerson.test.ts 锁；本文件锁「移入」与「页签唯一入口」：
 *  1. 高级筛选弹窗里有 性别 / 班级，且**没有** 在职状态；
 *  2. 在职状态唯一来源 = 状态页签 → 映射到后端 status 参数；
 *  3. 高级筛选的 性别 / 班级 → 映射到后端查询参数；
 *  4. 高级筛选内容区是**固定高度**（R-223：切条件不跳变），且仅内容区滚动（R-215）。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusPerson from '../CampusPerson.vue'

const apiGet = vi.fn()
vi.mock('../../../utils/request', () => ({
  api: {
    get: (...args: any[]) => apiGet(...args),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const searchUsers = vi.fn(async () => [{ label: '林曼（班主任）', value: 'u1' }])
const searchClassRooms = vi.fn(async () => [{ label: '2026校招-上海-01班', value: 'cr1' }])
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
  name: '王明远',
  employeeId: '25080001',
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

const lastParams = () => {
  const call = apiGet.mock.calls[apiGet.mock.calls.length - 1]
  return call[1]?.params ?? {}
}

describe('人员管理页 · 筛选区重排', () => {
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

  /** 打开「高级筛选」弹窗（n-modal 内容在 show 时才渲染） */
  const openAdvanced = async () => {
    const wrapper = await mountPage()
    const btn = wrapper.findAll('button').find((b) => b.text() === '高级筛选')
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    await flushPromises()
    return wrapper
  }

  it('① 高级筛选弹窗里有 性别 / 班级，且不再有 在职状态（在职状态由页签唯一控制）', async () => {
    const wrapper = await openAdvanced()
    const labels = wrapper.findAll('.n-form-item-label').map((l) => l.text().replace(/\*/g, '').trim())
    expect(labels).toContain('性别')
    expect(labels).toContain('班级')
    expect(labels).not.toContain('在职状态')
  })

  it('② 在职状态唯一来源 = 状态页签 → 映射到后端 status 参数', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab')
    const pending = tabs.find((t) => t.text() === '待入职')!
    await pending.trigger('click')
    await flushPromises()
    expect(lastParams().status).toBe('待入职')

    const resigned = tabs.find((t) => t.text() === '离职')!
    await resigned.trigger('click')
    await flushPromises()
    expect(lastParams().status).toBe('离职')
  })

  it('③ 高级筛选的 性别 / 班级 → 映射到后端查询参数', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.advancedForm.sex = '男'
    vm.advancedForm.classRoom = 'cr1'
    await vm.reload()
    await flushPromises()

    const params = lastParams()
    expect(params.sex).toBe('男')
    expect(params.class_room).toBe('cr1')
  })

  it('④ 高级筛选内容区是固定高度（不是 max-height），且仅内容区滚动', async () => {
    const wrapper = await openAdvanced()
    // ⚠️ 用组件 prop 断言而非渲染后的 style：jsdom 的 CSS 解析器不支持
    //    `min(300px, calc(88vh - 140px))` 这类函数值，会把 height 声明**静默丢弃**，
    //    渲染层断言会假失败（真实浏览器支持 min()，无此问题）。
    const modal = wrapper
      .findAllComponents({ name: 'Modal' })
      .find((m) => m.props('title') === '高级筛选')
    expect(modal).toBeTruthy()
    const contentStyle = (modal!.props('contentStyle') ?? {}) as Record<string, any>
    // R-223：固定 height（非 max-height）→ 切条件/出校验提示时容器高度不跳变
    expect(String(contentStyle.height)).toMatch(/^min\(/)
    expect(contentStyle.maxHeight).toBeUndefined()
    // R-215：滚动只发生在内容区
    expect(String(contentStyle.overflowY)).toBe('auto')

    // 渲染层：内容区确实拿到了 overflow（证明 content-style 已透传到 DOM）
    const cardContent = wrapper.findAll('.n-card-content')
    expect(cardContent.length).toBeGreaterThan(0)
    expect(cardContent.some((el) => (el.attributes('style') || '').includes('overflow-y: auto'))).toBe(true)
  })

  it('⑤ 清空全部筛选 → 状态页签回到「全部」', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.onTabChange('在职')
    await flushPromises()
    vm.clearFilters()
    expect(vm.activeTab).toBe('')
    expect(vm.advancedForm.sex).toBeNull()
    expect(vm.advancedForm.classRoom).toBeNull()
  })
})
