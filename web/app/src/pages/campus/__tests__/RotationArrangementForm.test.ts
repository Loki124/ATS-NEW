/**
 * 轮岗安排弹窗 · 表单分组与级联回归测试（2026-10-21 三期）。
 *
 * 锁产品约定：
 * 1. 弹窗表单按「基本信息 / 批次&班级 / 轮岗信息 / 其他信息」四组排布；
 * 2. 每组的字段清单（基本信息：姓名·工号·教育经历·预计入职日期·入职日期；
 *    批次&班级：批次·班级·班主任·班长；轮岗信息：意向部门·轮岗资源·
 *    轮岗部门·带教导师·轮岗起止日期）；
 * 3. ⚠️ 2026-10-22 兵哥指令：直播间 + 客服部门整合为「轮岗资源」→
 *    原「轮岗位置」单选 + 「具体位置」级联下拉，合并为**单个**资源下拉（按类型分组）；
 *    选资源后「轮岗部门」自动填充为该资源的归属部门；
 *    选班级时「批次」自动回填。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { naivePlugin } from '../../../plugins/naive'

const apiGet = vi.fn()
vi.mock('../../../utils/request', () => ({
  api: {
    get: (...args: any[]) => apiGet(...args),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const DEPTS = [
  { id: 'd1', name: '集团总部', parentId: null, isActive: true },
  { id: 'd2', name: '技术事业群', parentId: 'd1', isActive: true },
  { id: 'd3', name: '技术BU', parentId: 'd2', isActive: true },
  { id: 'd4', name: '技术中心', parentId: 'd3', isActive: true },
]
/** 轮岗资源（直播间 + 客服部门 + 其他 合一；2026-10-22 兵哥指令） */
const RESOURCES = [
  { id: 'LR01', name: '视频号直播-上海-01', resourceNo: 'LR0001', resourceType: 'LIVE_ROOM', department: 'd4', bu: 'd3' },
  { id: 'LR02', name: '腾讯会议-北京-面试间', resourceNo: 'LR0002', resourceType: 'LIVE_ROOM', department: 'd4', bu: 'd3' },
  { id: 'SD01', name: '上海客服一组', resourceNo: 'SD0001', resourceType: 'SERVICE_DEPT', department: 'd4', bu: 'd3' },
]
const CLASS_ROOMS = [
  { id: 'CR01', code: 'CL100001', name: '2026校招-上海-01班', batch: '2026秋招', headTeacher: '林曼', hrbp: '刘婷' },
]

import RotationArrangement from '../RotationArrangement.vue'

function mountPage() {
  // 页面用 department store（pinia）+ naive-ui 全局组件，两个都要装上
  const wrapper = mount(RotationArrangement, {
    global: { plugins: [createPinia(), naivePlugin], stubs: { teleport: true } },
  })
  return wrapper
}

/** 打开「新建轮岗安排」弹窗（n-modal 内容在 show 时才渲染） */
async function mountAndOpen() {
  const w = mountPage()
  await flushPromises()
  ;(w.vm as any).openCreate()
  await flushPromises()
  return w
}

/** 取某分组下的表单项标签（去掉 naive-ui 的必填星号） */
function labelsIn(wrapper: ReturnType<typeof mountPage>, title: string): string[] {
  const section = wrapper.findAll('.form-section').find((s) => s.find('.form-section-title').text() === title)
  if (!section) return []
  return section.findAll('.n-form-item-label').map((l) => l.text().replace(/\*/g, '').trim())
}

describe('轮岗安排弹窗 · 表单分组', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/departments/')) return Promise.resolve({ data: { data: DEPTS } })
      if (url.includes('/campus-rotation/resources/')) return Promise.resolve({ data: { data: RESOURCES } })
      if (url.includes('/class-rooms/')) return Promise.resolve({ data: { data: CLASS_ROOMS } })
      return Promise.resolve({ data: { data: [] } })
    })
  })

  it('① 四个分组齐备且顺序正确', async () => {
    const w = await mountAndOpen()
    const titles = w.findAll('.form-section-title').map((t) => t.text())
    expect(titles).toEqual(['基本信息', '批次&班级', '轮岗信息', '其他信息'])
  }, 20000)

  it('② 基本信息组：姓名 / 工号 / 教育经历 / 预计入职日期 / 入职日期', async () => {
    const w = await mountAndOpen()
    expect(labelsIn(w, '基本信息')).toEqual(['姓名', '工号', '教育经历', '预计入职日期', '入职日期'])
  }, 20000)

  it('③ 批次&班级组：批次 / 班级 / 班主任 / 班长', async () => {
    const w = await mountAndOpen()
    expect(labelsIn(w, '批次&班级')).toEqual(['批次', '班级', '班主任', '班长'])
  }, 20000)

  it('④ 轮岗信息组：意向部门 / 轮岗资源 / 轮岗部门 / 带教导师 / 轮岗起止日期', async () => {
    const w = await mountAndOpen()
    expect(labelsIn(w, '轮岗信息')).toEqual([
      '意向部门', '轮岗资源', '轮岗部门', '带教导师', '轮岗起止日期',
    ])
    // ⚠️ 原「轮岗位置」单选 + 「具体位置」级联下拉已合并为「轮岗资源」
    const labels = labelsIn(w, '轮岗信息')
    expect(labels).not.toContain('轮岗位置')
    expect(labels).not.toContain('具体位置')
  }, 20000)

  it('⑤ 资源下拉按类型分组（直播间 / 客服部门）', async () => {
    const w = mountPage()
    await flushPromises()
    const vm = w.vm as any
    const groups = vm.resourceOptions
    expect(groups.map((g: any) => g.label)).toEqual(['直播间', '客服部门'])
    expect(groups[0].children.map((c: any) => c.value)).toEqual(['LR01', 'LR02'])
    expect(groups[1].children.map((c: any) => c.value)).toEqual(['SD01'])
  }, 20000)

  it('⑥ 选轮岗资源 → 轮岗部门自动填充为该资源的归属部门', async () => {
    const w = mountPage()
    await flushPromises()
    const vm = w.vm as any
    vm.formState.resource = 'SD01'
    vm.onResourceChange('SD01')
    await flushPromises()
    expect(vm.formState.currentDept).toBe('d4')
    expect(vm.formState.resource).toBe('SD01')
  }, 20000)

  it('⑦ 换资源即换位置（原直播间 → 客服部门），不再有两侧并存', async () => {
    const w = mountPage()
    await flushPromises()
    const vm = w.vm as any
    vm.formState.resource = 'LR01'
    expect(vm.formState.resource).toBe('LR01')
    vm.formState.resource = 'SD01'
    await flushPromises()
    expect(vm.formState.resource).toBe('SD01')
    // 旧的两个独立字段已下线
    expect(vm.formState.liveRoom).toBeUndefined()
    expect(vm.formState.serviceDept).toBeUndefined()
    expect(vm.formState.locationType).toBeUndefined()
  }, 20000)

  it('⑧ 选班级 → 批次自动回填；清空班级 → 批次清空', async () => {
    const w = mountPage()
    await flushPromises()
    const vm = w.vm as any
    vm.formState.classRoom = 'CR01'
    vm.onClassRoomChange('CR01')
    expect(vm.formState.batch).toBe('2026秋招')
    vm.onClassRoomChange(null)
    expect(vm.formState.batch).toBe('')
  }, 20000)

  it('⑨ 选校招生 → 基本信息自动回填（工号/教育经历/入职日期）', async () => {
    const w = mountPage()
    await flushPromises()
    const vm = w.vm as any
    vm.personOptions = [
      {
        label: '周砚（C99000001）',
        value: 'p1',
        person: {
          id: 'p1', name: '周砚', employeeId: 'CS99000001', education: '本科',
          expectedEntryDate: '2026-08-15', actualEntryDate: '',
        },
      },
    ]
    vm.onPersonChange('p1')
    expect(vm.formState.personEmployeeId).toBe('CS99000001')
    expect(vm.formState.personEducation).toBe('本科')
    expect(vm.formState.personExpectedEntryDate).toBe('2026-08-15')
    expect(vm.formState.personActualEntryDate).toBe('')
  }, 20000)
})
