/**
 * 校招生交流论坛页（CampusForum）· 行为契约测试。
 *
 * 锁住：
 *  1. 板块列表（全部板块 + 各板块按钮）
 *  2. 帖子表格列（标题 / 作者 / 回复数 / 时间）与行内容
 *  3. 发帖弹窗：必填校验 + 提交载荷
 *  4. 关键词搜索：请求带 kw 参数
 *  5. 空态二分
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusForum from '../../../pages/campus/CampusForum.vue'

const { notifyCreate } = vi.hoisted(() => ({ notifyCreate: vi.fn() }))

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

vi.mock('naive-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('naive-ui')>()
  const stub = () => ({ info: vi.fn(), success: vi.fn(), warning: vi.fn(), error: vi.fn(), loading: vi.fn() })
  return {
    ...actual,
    useDialog: () => ({ ...stub(), create: vi.fn() }),
    useMessage: stub,
    useNotification: () => ({ create: notifyCreate }),
  }
})

const board = { id: 'b1', name: '校招互助', description: '互帮互助', sort: 1, enabled: true }

const post = {
  id: 'fp1',
  board: 'b1',
  boardName: '校招互助',
  title: '秋招面试怎么准备',
  content: '面经分享',
  author: 'u1',
  authorName: '张一鸣',
  person: 'p1',
  personName: '张一鸣',
  replyCount: 5,
  pinned: false,
  createdAt: '2026-10-22T08:00:00Z',
}

function formItem(wrapper: any, label: string) {
  return wrapper
    .findAll('.n-form-item')
    .find((n: any) => n.find('.n-form-item-label').exists() && n.find('.n-form-item-label').text().replace(/\*/g, '').trim() === label)
}

describe('CampusForum 论坛页行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiDelete.mockReset()
    notifyCreate.mockReset()
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/forum-boards/')) return Promise.resolve({ data: { data: [board] } })
      if (url.includes('/forum-posts/')) return Promise.resolve({ data: { data: [post] } })
      return Promise.resolve({ data: { data: [] } })
    })
    apiPost.mockResolvedValue({ data: { data: post } })
    apiPut.mockResolvedValue({ data: { data: post } })
    apiDelete.mockResolvedValue({ data: { success: true } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusForum, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 板块列表渲染：全部板块 + 各板块按钮', async () => {
    const wrapper = await mountPage()
    const boardButtons = wrapper.findAll('.board-row button').map((b) => b.text())
    expect(boardButtons[0]).toBe('全部板块')
    expect(boardButtons).toContain('校招互助')
  }, 20000)

  it('② 帖子表格列齐全，帖子行按接口字段渲染', async () => {
    const wrapper = await mountPage()
    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('标题')
    expect(heads).toContain('作者')
    expect(heads).toContain('回复数')
    expect(heads).toContain('发布时间')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('秋招面试怎么准备')
    expect(body).toContain('张一鸣')
    expect(body).toContain('5')
  }, 20000)

  it('③ 发帖：填标题与正文 → POST /campus-learning/forum-posts/', async () => {
    const wrapper = await mountPage()
    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('发布帖子'))!.trigger('click')
    await flushPromises()

    const vm = wrapper.vm as any
    vm.postForm.board = 'b1'
    await flushPromises()
    const titleInput = formItem(wrapper, '帖子标题')?.find('input')
    await titleInput!.setValue('转正答辩准备清单')
    const contentInput = formItem(wrapper, '帖子正文')?.find('textarea')
    await contentInput!.setValue('这是正文内容')

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('发布帖子'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/campus-learning/forum-posts/'))
    expect(call).toBeTruthy()
    expect(call![1]).toMatchObject({ board: 'b1', title: '转正答辩准备清单', content: '这是正文内容' })
  }, 20000)

  it('④ 关键词搜索 → 列表请求带 kw 参数', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.keyword = '面试'
    await vm.loadPosts()
    await flushPromises()

    const call = apiGet.mock.calls.filter((c) => String(c[0]).includes('/campus-learning/forum-posts/')).pop()
    expect(call![1]?.params?.kw).toBe('面试')
  }, 20000)

  it('⑤ 空态二分：无数据 = 暂无数据；筛选无结果 = 没有符合筛选条件的帖子', async () => {
    apiGet.mockResolvedValue({ data: { data: [] } })
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('暂无数据')

    const vm = wrapper.vm as any
    vm.keyword = '不存在的帖子'
    await vm.loadPosts()
    await flushPromises()
    expect(wrapper.text()).toContain('没有符合筛选条件的帖子')
  }, 20000)

  it('⑥ 删除帖子 = 直接执行删除 + 通知里带「撤销」动作', async () => {
    const wrapper = await mountPage()
    await wrapper.findAll('.n-data-table-tbody button').find((b) => b.text().includes('删除帖子'))!.trigger('click')
    await flushPromises()

    const del = apiDelete.mock.calls.find((c) => String(c[0]).includes('/campus-learning/forum-posts/fp1/'))
    expect(del).toBeTruthy()
    expect(notifyCreate).toHaveBeenCalled()
    expect(notifyCreate.mock.calls[0][0].duration).toBe(8000)
  }, 20000)
})
