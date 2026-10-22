/**
 * 轮岗资源页 · 字段回归测试（2026-10-22 兵哥指令：直播间 + 客服部门整合为「轮岗资源」）。
 *
 * 兵哥指令（合并后）：
 * 1. 直播间编号 / 客服部门编号 → **资源编号**；
 * 2. 直播间名称 / 部门名称 → **资源名称**；
 * 3. 直播间导师 / 客服主管 → **导师**；
 * 4. 客服部门去掉品牌、客服类型、工位类型 → 品牌也一并去掉；
 * 5. 新增 **资源类型** 字段（直播间 / 客服部门 / 其他）。
 *
 * 锁的业务约定：
 * 1. 列表列名：资源编号 / 资源名称 / 资源类型 / 导师；
 * 2. 列表无「品牌」「客服类型」「工位类型」「校招占用」列；有「校招占用」「饱和度」；
 * 3. 表单有「资源类型」必填项，无品牌 / 客服类型 / 工位类型 / 备注，补只读「校招人数」；
 * 4. 工具栏筛选项：归属部门 / 资源类型 / 平台 / 状态，状态默认「启用」；
 * 5. 请求带 department / resource_type / platform / is_active（默认 'true'）；
 * 6. 行内操作列有「启用 / 停用」按钮，点击走 PATCH /resources/{id}/；
 * 7. 工具栏有「导入 Excel」「导出 Excel」入口；
 * 8. 饱和度 = round((社招+校招)/容量×100)，>70% 危险 / >40% 警告 / 其余正常；
 * 9. 编号占位文案随资源类型变化（LR+4 / SD+4 / OT+4）。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { naivePlugin } from '../../../plugins/naive'

const apiGet = vi.fn()
const apiPatch = vi.fn()
vi.mock('../../../utils/request', () => ({
  api: {
    get: (...args: any[]) => apiGet(...args),
    post: vi.fn(),
    put: vi.fn(),
    patch: (...args: any[]) => apiPatch(...args),
    delete: vi.fn(),
  },
}))

import RotationResourcePanel from '../RotationResourcePanel.vue'

const RESOURCES = [
  {
    id: 'rs1', resourceNo: 'LR0001', name: '视频号直播-上海-01', resourceType: 'LIVE_ROOM',
    department: 'd1', bu: 'b1', mentor: 'u1', mentorName: '王建国', platform: 'VIDEO_ACCOUNT',
    location: '上海', capacity: 20, socialCount: 3, campusCount: 12, isActive: true,
  },
  {
    id: 'rs2', resourceNo: 'SD0001', name: '上海在线客服一部', resourceType: 'SERVICE_DEPT',
    department: 'd2', bu: 'b1', mentor: 'u2', mentorName: '林曼', platform: '',
    location: '上海', capacity: 40, socialCount: 8, campusCount: 22, isActive: true,
  },
]

/** 只有轮岗资源列表接口返回真实数据；部门 / 字典接口返回空（避免污染部门 store 与下拉选项） */
const mockApi = () => {
  apiGet.mockImplementation((url: string) => {
    if (String(url).includes('/campus-rotation/resources/')) {
      return Promise.resolve({ data: { data: RESOURCES } })
    }
    return Promise.resolve({ data: { data: [] } })
  })
}

const mountPage = async () => {
  const w = mount(RotationResourcePanel, {
    global: { plugins: [createPinia(), naivePlugin], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

/** 取**最后一次**轮岗资源列表请求（挂载时已请求过一次，取最后一次才是筛选后的那次） */
const resourceCall = () => {
  const calls = apiGet.mock.calls.filter((c: any[]) =>
    String(c[0]).includes('/campus-rotation/resources/'),
  )
  return calls[calls.length - 1]
}

describe('轮岗资源页 · 字段（合并后）', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPatch.mockReset()
    apiPatch.mockResolvedValue({ data: { success: true, data: {} } })
    mockApi()
  })

  it('① 列表列名：资源编号 / 资源名称 / 资源类型 / 导师', async () => {
    const w = await mountPage()
    const heads = w.findAll('.n-data-table-thead th').map((th) => th.text())
    expect(heads).toContain('资源编号')
    expect(heads).toContain('资源名称')
    expect(heads).toContain('资源类型')
    expect(heads).toContain('导师')
    expect(heads).not.toContain('直播间编号')
    expect(heads).not.toContain('客服主管')
    expect(heads).not.toContain('直播间导师')
  }, 20000)

  it('② 列表列：无 品牌·客服类型·工位类型；有 校招占用·饱和度', async () => {
    const w = await mountPage()
    const heads = w.findAll('.n-data-table-thead th').map((th) => th.text())
    expect(heads).toContain('归属部门')
    expect(heads).toContain('归属BU')
    expect(heads).toContain('平台')
    expect(heads).toContain('地点')
    expect(heads).toContain('容量')
    expect(heads).toContain('社招人数')
    expect(heads).toContain('校招占用')
    expect(heads).toContain('饱和度')
    expect(heads).toContain('操作')
    expect(heads).not.toContain('品牌')
    expect(heads).not.toContain('客服类型')
    expect(heads).not.toContain('工位类型')
    expect(heads).not.toContain('校招人数')
  }, 20000)

  it('③ 资源类型列渲染中文名（直播间 / 客服部门）', async () => {
    const w = await mountPage()
    const rows = w.findAll('.n-data-table-tbody tr').map((tr) => tr.text())
    expect(rows[0]).toContain('直播间')
    expect(rows[1]).toContain('客服部门')
  }, 20000)

  it('④ 表单：资源类型必填；无 品牌 / 客服类型 / 工位类型 / 备注；补只读 校招人数', async () => {
    const w = await mountPage()
    ;(w.vm as any).openCreate()
    await flushPromises()
    const labels = w.findAll('.n-form-item-label').map((l) => l.text().replace(/\*/g, '').trim())
    expect(labels).toContain('资源类型')
    expect(labels).toContain('资源名称')
    expect(labels).toContain('导师')
    expect(labels).toContain('校招人数')
    expect(labels).toContain('社招人数')
    expect(labels).not.toContain('品牌')
    expect(labels).not.toContain('客服类型')
    expect(labels).not.toContain('工位类型')
    expect(labels).not.toContain('备注')
    expect(labels).not.toContain('直播间导师')
    expect(labels).not.toContain('客服主管')
    // 表单内已无任何 n-switch（启用开关下线）
    const modal = w.findAll('.n-modal').at(-1)!
    expect(modal.findAll('.n-switch').length).toBe(0)
  }, 20000)

  it('⑤ 工具栏：无「是否启用」开关，有 归属部门 / 资源类型 / 平台 / 状态 四个筛选项，状态默认「启用」', async () => {
    const w = await mountPage()
    expect(w.findAll('.n-switch').length).toBe(0)
    // 归属部门筛选是部门树多选组件（DeptTreeFilter），占位文案在它的触发按钮上
    const deptTrigger = w.find('.dept-filter__trigger')
    expect(deptTrigger.exists()).toBe(true)
    expect(deptTrigger.text()).toContain('全部归属部门')
    // 其余三个是普通 n-select，占位文案在 .n-base-selection-placeholder 上
    const placeholders = w.findAll('.n-base-selection-placeholder').map((p) => p.text())
    expect(placeholders).toContain('全部资源类型')
    expect(placeholders).toContain('全部平台')
    // 状态筛选项默认选中「启用」→ 显示选中值而非占位文案
    expect((w.vm as any).filterStatus).toBe('active')
    expect(w.text()).toContain('启用')
  }, 20000)

  it('⑥ 筛选请求：带 department / resource_type / platform / is_active（默认启用 = true）', async () => {
    const w = await mountPage()
    const vm = w.vm as any
    // 归属部门是部门树**多选**（ids 列表）→ 请求参数为逗号分隔
    vm.filterDepartment = ['d1', 'd2']
    vm.filterResourceType = 'LIVE_ROOM'
    vm.filterPlatform = 'VIDEO_ACCOUNT'
    await vm.loadList()
    const call = resourceCall()
    expect(call?.[1]?.params?.department).toBe('d1,d2')
    expect(call?.[1]?.params?.resource_type).toBe('LIVE_ROOM')
    expect(call?.[1]?.params?.platform).toBe('VIDEO_ACCOUNT')
    expect(call?.[1]?.params?.is_active).toBe('true')

    // 切到「停用」→ is_active=false；清空（全部状态）→ 不传该参数
    vm.filterStatus = 'inactive'
    await vm.loadList()
    expect(resourceCall()?.[1]?.params?.is_active).toBe('false')
    vm.filterStatus = null
    await vm.loadList()
    expect(resourceCall()?.[1]?.params?.is_active).toBeUndefined()
  }, 20000)

  it('⑦ 操作列有「启用 / 停用」按钮：启用行显示「停用」，点击走 PATCH /resources/{id}/', async () => {
    const w = await mountPage()
    const row = w.findAll('.n-data-table-tbody tr')[0]
    const labels = row.findAll('button').map((b) => b.text())
    expect(labels).toContain('编辑')
    expect(labels).toContain('停用')
    expect(labels).toContain('删除')

    await row.findAll('button').find((b) => b.text() === '停用')!.trigger('click')
    await flushPromises()
    expect(apiPatch).toHaveBeenCalled()
    expect(apiPatch.mock.calls[0][0]).toContain('/campus-rotation/resources/rs1/')
    expect(apiPatch.mock.calls[0][1]).toEqual({ isActive: false })
  }, 20000)

  it('⑧ 工具栏有「导入 Excel」「导出 Excel」入口，导入弹窗可打开并含模板下载', async () => {
    const w = await mountPage()
    const texts = w.findAll('button').map((b) => b.text())
    expect(texts.join('|')).toContain('导入 Excel')
    expect(texts.join('|')).toContain('导出 Excel')

    ;(w.vm as any).openImport()
    await flushPromises()
    const modal = w.findAll('.n-modal').at(-1)!
    expect(modal.text()).toContain('下载导入模板')
    expect(modal.text()).toContain('选择 Excel 文件')
  }, 20000)

  it('⑨ 饱和度口径：round((社招+校招)/容量×100)，>70% 危险 / >40% 警告 / 其余正常', async () => {
    const w = await mountPage()
    const vm = w.vm as any
    expect(vm.saturationOf({ capacity: 20, socialCount: 3, campusCount: 12 })).toBe(75)
    expect(vm.saturationOf({ capacity: 10, socialCount: 1, campusCount: 5 })).toBe(60)
    expect(vm.saturationLevel(71)).toBe('error')
    expect(vm.saturationLevel(70)).toBe('warning')
    expect(vm.saturationLevel(41)).toBe('warning')
    expect(vm.saturationLevel(40)).toBe('success')
    // 行内渲染：75% / 75%（40 容量 / (8+22) = 75%）
    const rows = w.findAll('.n-data-table-tbody tr').map((tr) => tr.text())
    expect(rows[0]).toContain('75%')
    expect(rows[1]).toContain('75%')
  }, 20000)

  it('⑩ 容量上限为空 / 0 → 饱和度显示「—」（不静默当成 0%）', async () => {
    const w = await mountPage()
    const vm = w.vm as any
    expect(vm.saturationOf({ capacity: 0, socialCount: 1, campusCount: 1 })).toBeNull()
    expect(vm.saturationOf({ capacity: null, socialCount: 1, campusCount: 1 })).toBeNull()
  }, 20000)

  it('⑪ 编号占位文案随资源类型变化（LR+4 / SD+4 / OT+4）', async () => {
    const w = await mountPage()
    const vm = w.vm as any
    vm.openCreate()
    await flushPromises()
    expect(vm.formState.resourceType).toBe('LIVE_ROOM')
    expect(vm.noHint).toContain('LR+4')
    vm.formState.resourceType = 'SERVICE_DEPT'
    await flushPromises()
    expect(vm.noHint).toContain('SD+4')
    vm.formState.resourceType = 'OTHER'
    await flushPromises()
    expect(vm.noHint).toContain('OT+4')
  }, 20000)

  it('⑫ 切换资源类型为非直播间 → 平台被清空（后端会拒绝非直播间的平台值）', async () => {
    const w = await mountPage()
    const vm = w.vm as any
    vm.openCreate()
    await flushPromises()
    vm.formState.platform = 'VIDEO_ACCOUNT'
    vm.onResourceTypeChange('SERVICE_DEPT')
    expect(vm.formState.platform).toBe(null)
    expect(vm.formState.resourceType).toBe('SERVICE_DEPT')
  }, 20000)
})
