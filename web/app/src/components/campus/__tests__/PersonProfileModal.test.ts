/**
 * 个人档案详情弹窗 —— 组件级渲染契约测试（二期）。
 *
 * 锁住设计稿要求的版式与状态机：
 *  1. 成功态：名片（姓名 / 副标题 / 状态·性别·批次标签）+ 四项统计 + 六个区块
 *     + 底部「关闭 / 编辑基础信息」操作区（R-223 #footer 承载）。
 *  2. 空态：四个尚未建模的业务域各自渲染设计稿对应的空态文案。
 *  3. 失败态：走 R-203 错误三段式（人话描述 + 数据安全说明 + 可点击恢复动作）。
 *  4. 无数据时统计项显示「—」而不是 0（不把「无数据」表达成「0 分」）。
 *  5. 「编辑基础信息」把档案抛给父页面（父页面复用既有编辑弹窗）。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PersonProfileModal from '../PersonProfileModal.vue'

const getPersonProfile = vi.fn()
vi.mock('../../../api/campusControl', () => ({
  getPersonProfile: (...args: any[]) => getPersonProfile(...args),
}))

const profile = {
  person: {
    id: 'p1',
    code: 'C00000001',
    name: '陆翔宇',
    employeeId: 'E001',
    status: '待入职',
    sex: '男',
    bu: '三到BG',
    position: '技术研发',
    level: 'L1',
    school: '211',
    schoolName: '武汉理工大学',
    major: '生物技术',
    education: '本科',
    phone: '15800009278',
    month: '8月',
    expectedEntryDate: '2026-10-08',
    actualEntryDate: '',
    counted: true,
    classRoomId: 'cr1',
    classRoomName: '2610 班',
    headTeacherId: 'u1',
    headTeacherName: '张老师',
    mentorId: 'u2',
    mentorName: '李导师',
    batch: '261002',
  },
  classRoom: {
    id: 'cr1',
    code: 'CL000001',
    name: '2610 班',
    batch: '261002',
    headTeacher: '张老师',
    hrbp: '王HRBP',
    studentCount: 12,
  },
  rotation: null,
  stats: {
    rotationAvgScore: null,
    monthlyAvgScore: null,
    overallScore: null,
    rank: null,
    rating: null,
  },
  stages: [],
  monthlyAssessments: [],
  dailyReports: [],
  recommendations: [],
  feedbacks: [],
}

describe('PersonProfileModal 二期版式契约', () => {
  beforeEach(() => {
    getPersonProfile.mockReset()
    getPersonProfile.mockResolvedValue(JSON.parse(JSON.stringify(profile)))
  })

  const mountModal = async (props: Record<string, any> = {}) => {
    const wrapper = mount(PersonProfileModal, {
      props: { show: true, personId: 'p1', personName: '陆翔宇', ...props },
      global: { stubs: { teleport: true } },
    })
    await flushPromises()
    return wrapper
  }

  it('成功态：名片 + 四项统计 + 六个区块 + 底部操作区', async () => {
    const wrapper = await mountModal()
    const html = wrapper.html()

    // 名片区
    expect(wrapper.find('.pp-name').text()).toBe('陆翔宇')
    expect(wrapper.find('.pp-subtitle').text()).toContain('武汉理工大学')
    expect(wrapper.find('.pp-subtitle').text()).toContain('生物技术')
    expect(wrapper.find('.pp-subtitle').text()).toContain('本科')
    // 状态 / 性别 / 批次 三个标签
    const chips = wrapper.findAll('.pp-chip').map((c) => c.text())
    expect(chips).toContain('待入职')
    expect(chips).toContain('男')
    expect(chips.join(' ')).toContain('批次 261002')

    // 四项统计
    const statLabels = wrapper.findAll('.pp-stat-label').map((n) => n.text())
    expect(statLabels).toEqual(['轮岗均分', '月度综合均分', '综合排名', '综合评级'])

    // 六个区块标题
    const titles = wrapper.findAll('.pp-section-title').map((n) => n.text())
    expect(titles.join('|')).toContain('基本信息')
    expect(titles.join('|')).toContain('轮岗期考核结果')
    expect(titles.join('|')).toContain('轮岗期月度考核明细')
    expect(titles.join('|')).toContain('日报及评价')
    expect(titles.join('|')).toContain('推介意见')
    expect(titles.join('|')).toContain('反馈记录')

    // 基本信息九宫格：含班主任 / HRBP（班长已按 D-02 从模型移除）
    const fieldLabels = wrapper.findAll('.pp-field-label').map((n) => n.text())
    expect(fieldLabels).toContain('院校名称')
    expect(fieldLabels).toContain('联系电话')
    expect(fieldLabels).toContain('班主任')
    expect(fieldLabels).toContain('HRBP')
    expect(fieldLabels).not.toContain('班长')

    // 底部操作区
    expect(html).toContain('关闭')
    expect(html).toContain('编辑基础信息')
    expect(getPersonProfile).toHaveBeenCalledWith('p1')
  })

  it('空态：四个未建模业务域各渲染对应空态文案', async () => {
    const wrapper = await mountModal()
    const text = wrapper.text()
    expect(text).toContain('暂无日报记录')
    expect(text).toContain('暂无推介意见')
    expect(text).toContain('暂无反馈')
  })

  it('无评分时显示「—」而不是 0', async () => {
    const wrapper = await mountModal()
    const scoreCircle = wrapper.find('.pp-score-circle').text()
    expect(scoreCircle).toBe('—')
    const values = wrapper.findAll('.pp-stat-value').map((n) => n.text())
    expect(values.every((v) => v === '—')).toBe(true)
  })

  it('失败态：错误三段式 + 可点击恢复动作', async () => {
    getPersonProfile.mockRejectedValueOnce({ response: { data: { detail: '服务不可用' } } })
    const wrapper = await mountModal()
    const text = wrapper.text()
    expect(text).toContain('没取到这份档案')
    expect(text).toContain('未受影响')
    expect(text).toContain('重新加载档案')
  })

  it('「编辑基础信息」把档案抛给父页面', async () => {
    const wrapper = await mountModal()
    const editBtn = wrapper.findAll('button').find((b) => b.text().includes('编辑基础信息'))
    expect(editBtn).toBeTruthy()
    await editBtn!.trigger('click')
    expect(wrapper.emitted('edit')).toBeTruthy()
    expect((wrapper.emitted('edit') as any)[0][0].person.name).toBe('陆翔宇')
  })

  it('尺寸契约：宽 80vw / 高 90vh 由卡片固定，内容区不设 max-height（R-223）', async () => {
    const wrapper = await mountModal()
    // 弹窗根节点带尺寸类（非 scoped 全局样式：.pp-profile-modal.n-modal）
    expect(wrapper.find('.pp-profile-modal').exists()).toBe(true)
    // 内容区：只有滚动与内边距，高度由卡片 90vh 决定 ⇒ 不用 max-height
    const vm = wrapper.vm as any
    expect(vm.contentStyle.overflowY).toBe('auto')
    expect(vm.contentStyle.maxHeight).toBeUndefined()
    expect(vm.contentStyle.height).toBeUndefined()
  })

  it('示例数据模式：传 preloaded 时不发请求，直接渲染本地载荷', async () => {
    getPersonProfile.mockClear()
    const preloaded = JSON.parse(JSON.stringify(profile))
    preloaded.person.name = '张一鸣'
    const wrapper = mount(PersonProfileModal, {
      props: {
        show: true,
        personId: 'MOCK_PS_01',
        personName: '张一鸣',
        preloaded,
        readonly: true,
      },
      global: { stubs: { teleport: true } },
    })
    await flushPromises()

    // 关键：mock id 在后端不存在，绝不能发请求（否则必然 404）
    expect(getPersonProfile).not.toHaveBeenCalled()
    expect(wrapper.find('.pp-name').text()).toBe('张一鸣')
    // 只读模式：不显示「编辑基础信息」出口（示例数据不落库）
    expect(wrapper.text()).not.toContain('编辑基础信息')
  })
})
