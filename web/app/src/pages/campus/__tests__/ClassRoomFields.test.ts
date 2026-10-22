/**
 * 班级管理页 · 字段调整回归测试（2026-10-22）。
 *
 * 锁三条业务约定：
 * 1. 列表下线「班主任 / HRBP / 批次」三列，改挂「班长」；
 * 2. 表单同步下线这三个字段，只留 班级编号 / 班级名称 / 班长 / 启用 / 备注；
 * 3. 班级名称 = 从 1 开始的流水号 → 输入框只读，新建时提示下一个序号。
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

import ClassRoom from '../ClassRoom.vue'

const CLASS_ROOMS = [
  { id: 'cr1', code: 'CL100001', name: '1', classMonitor: 'u9', classMonitorName: '周小舟（班长）', studentCount: 32, isActive: true },
  { id: 'cr2', code: 'CL100002', name: '2', classMonitor: null, classMonitorName: '', studentCount: 28, isActive: true },
]

async function mountAndOpen() {
  apiGet.mockResolvedValue({ data: { data: CLASS_ROOMS } })
  const wrapper = mount(ClassRoom, {
    global: { plugins: [createPinia(), naivePlugin], stubs: { teleport: true } },
  })
  await flushPromises()
  ;(wrapper.vm as any).openCreate()
  await flushPromises()
  return wrapper
}

describe('班级管理页 · 字段调整', () => {
  beforeEach(() => {
    apiGet.mockReset()
  })

  it('① 列表列：编号/班级名称/班长/校招人数/阶段分布/操作（无 班主任·HRBP·批次·启用）', async () => {
    apiGet.mockResolvedValue({ data: { data: CLASS_ROOMS } })
    const w = mount(ClassRoom, { global: { plugins: [createPinia(), naivePlugin], stubs: { teleport: true } } })
    await flushPromises()
    const heads = w.findAll('.n-data-table-thead th').map((th) => th.text())
    expect(heads).toContain('编号')
    expect(heads).toContain('班级名称')
    expect(heads).toContain('班长')
    expect(heads).toContain('校招人数')
    expect(heads).toContain('阶段分布')
    expect(heads).not.toContain('班主任')
    expect(heads).not.toContain('HRBP')
    expect(heads).not.toContain('批次')
    expect(heads).not.toContain('启用')
  })

  it('①b 操作列不再有「删除」按钮（班级编号是流水号，删除会占坑）', async () => {
    apiGet.mockResolvedValue({ data: { data: CLASS_ROOMS } })
    const w = mount(ClassRoom, { global: { plugins: [createPinia(), naivePlugin], stubs: { teleport: true } } })
    await flushPromises()
    const actions = w.findAll('.n-data-table-tbody tr')[0].findAll('button').map((b) => b.text())
    expect(actions.join('|')).not.toContain('删除')
  })

  it('①c 阶段分布列展示三态计数（待分配 / 轮岗中 / 已完成）', async () => {
    apiGet.mockResolvedValue({ data: { data: CLASS_ROOMS } })
    const w = mount(ClassRoom, { global: { plugins: [createPinia(), naivePlugin], stubs: { teleport: true } } })
    await flushPromises()
    const cell = w.findAll('.n-data-table-tbody tr')[0].text()
    expect(cell).toContain('待分配')
    expect(cell).toContain('轮岗中')
    expect(cell).toContain('已完成')
  })

  it('①d 班长筛选下拉存在，且请求带 class_monitor 参数', async () => {
    apiGet.mockResolvedValue({ data: { data: CLASS_ROOMS } })
    const w = mount(ClassRoom, { global: { plugins: [createPinia(), naivePlugin], stubs: { teleport: true } } })
    await flushPromises()
    expect(w.findAll('.n-base-selection-placeholder').some((p) => p.text() === '全部班长')).toBe(true)

    const vm = w.vm as any
    vm.filterMonitor = 'u9'
    await vm.loadList()
    const last = apiGet.mock.calls[apiGet.mock.calls.length - 1]
    expect(last[1]?.params?.class_monitor).toBe('u9')
  })

  it('② 表单：只剩 班级编号/班级名称/班长/备注（启用开关已下线）', async () => {
    const w = await mountAndOpen()
    const labels = w.findAll('.n-form-item-label').map((l) => l.text().replace(/\*/g, '').trim())
    expect(labels).toEqual(['班级编号', '班级名称', '班长', '备注'])
    expect(labels).not.toContain('班主任')
    expect(labels).not.toContain('HRBP')
    expect(labels).not.toContain('批次')
    expect(labels).not.toContain('启用')
  })

  it('③ 班级名称只读；新建时提示下一个序号（现存最大号 + 1）', async () => {
    const w = await mountAndOpen()
    const nameInput = w.findAll('.n-form-item')
      .find((f) => f.find('.n-form-item-label').text().includes('班级名称'))!
      .find('input')
    expect(nameInput.attributes('readonly')).toBeDefined()
    // 现存班名 1、2 → 下一个是 3
    expect((w.vm as any).nextNameHint).toBe('3')
  })
})
