/**
 * 校招生「人员管理」列表列口径护栏（2026-10-22 兵哥指令）
 *
 * 兵哥原话：「人员管理列表页字段排序调整为：姓名、工号、性别、在职状态、
 * 入职日期(在同一列下展示预计入职日期、实际入职日期，例：预：2026/12/02 实：2026/12/31)、
 * 带教导师、HRBP、当前轮岗部门、批次、班级、学校、专业、综合评分；
 * 筛选项增加：轮岗状态、在职状态」
 *
 * 锁四条：
 *  ① 列**顺序**逐项等于兵哥清单（顺序错位 = 需求未落地，列名对但排错了同样算错）；
 *  ② 「入职日期」是**一列**内含预 / 实两个日期，不再有独立的「入职时间」「预计入职日期」两列；
 *  ③ 兵哥清单外的旧列（班主任 / 职务 / 职级）已下线；
 *  ④ 工具栏新增「轮岗状态」「在职状态」两个筛选项。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { parse } from '@vue/compiler-sfc'
import { join } from 'node:path'
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

vi.mock('../../../utils/campus', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../utils/campus')>()
  return {
    ...actual,
    searchUsers: async () => [],
    searchClassRooms: async () => [],
  }
})

/** 列工厂把 title 包成了函数（返回 VNode），这里取回原始标题文本 */
function titleText(col: any): string {
  const t = col.title
  if (typeof t === 'string') return t
  const vnode = t()
  const children = vnode?.children
  if (children && typeof children === 'object' && typeof children.default === 'function') {
    return String(children.default())
  }
  return String(children ?? '')
}

async function mountPage() {
  const wrapper = mount(CampusPerson, {
    global: { stubs: { teleport: true }, plugins: [createPinia()] },
  })
  await flushPromises()
  return wrapper
}

const EXPECTED_ORDER = [
  '姓名', '工号', '性别', '在职状态', '入职日期',
  '带教导师', 'HRBP', '当前轮岗部门', '批次', '班级', '学校', '专业', '综合评分',
  '操作',
]

describe('人员管理列口径（2026-10-22 兵哥指令）', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { data: [] } })
  })

  it('① 列顺序逐项等于兵哥清单', async () => {
    const w = await mountPage()
    const titles = (w.vm as any).columns.map((c: any) => titleText(c))
    expect(titles).toEqual(EXPECTED_ORDER)
  }, 20000)

  it('② 入职日期是合并列（预 / 实 上下两行，日期用 YYYY/MM/DD，标签用 icon）', async () => {
    const w = await mountPage()
    const cols = (w.vm as any).columns
    const entry = cols.find((c: any) => c.key === 'entryDate')
    expect(entry, '应存在合并后的「入职日期」列').toBeTruthy()

    const vnode = entry.render({
      expectedEntryDate: '2026-12-02',
      actualEntryDate: '2026-12-31',
    })
    const text = JSON.stringify(vnode.children)
    expect(text).toContain('2026/12/02')
    expect(text).toContain('2026/12/31')
    // 2026-10-22 二次调整：「预」「实」两个文字改用 icon → 单元格里不再有这两个字面量
    expect(text).not.toContain('预：')
    expect(text).not.toContain('实：')
    // icon 单独出现会失去语义 → 必须带 title（悬停提示）与 aria-label（R-217）
    expect(text).toContain('预计入职日期')
    expect(text).toContain('实际入职日期')
    expect(text).toContain('aria-label')
    // 两行（预 / 实 换行）→ 单元格里两个 row
    const rows = (vnode.children as any[]).filter((c) => c?.props?.class === 'entry-date-cell__row')
    expect(rows.length).toBe(2)
    // 旧的独立两列必须已下线
    expect(cols.find((c: any) => c.key === 'actualEntryDate')).toBeFalsy()
    expect(cols.find((c: any) => c.key === 'expectedEntryDate')).toBeFalsy()
  }, 20000)

  it('③ 清单外的旧列（班主任 / 职务 / 职级）已下线', async () => {
    const w = await mountPage()
    const keys = (w.vm as any).columns.map((c: any) => c.key)
    expect(keys).not.toContain('headTeacherName')
    expect(keys).not.toContain('position')
    expect(keys).not.toContain('level')
    // 新增列必须到位
    expect(keys).toContain('mentorName')
    expect(keys).toContain('hrbpName')
    expect(keys).toContain('rotationDept')
    expect(keys).toContain('batch')
    expect(keys).toContain('overallScore')
  }, 20000)

  it('④ 筛选项：工具栏含「轮岗状态」；高级筛选只剩 性别 / 班级 / 院校标签 / 专业标签', async () => {
    const w = await mountPage()
    const vm = w.vm as any
    const placeholders = w.findAll('.n-base-selection-placeholder').map((el) => el.text())
    // 工具栏常驻：部门 / 轮岗状态 / 导师 / 班主任
    expect(placeholders).toContain('全部轮岗状态')
    // 2026-10-22（兵哥指令）：高级筛选去掉 招聘月份 / 职务 / 职级 / 入职年度 / 在职状态
    vm.advancedVisible = true
    await flushPromises()
    // 注：本测试把 teleport 打了桩，弹窗内容渲染在组件内 → 用 wrapper 查（不是 document.body）
    const advancedPlaceholders = w
      .findAll('.n-base-selection-placeholder')
      .map((el) => el.text())
    expect(advancedPlaceholders).toEqual(
      expect.arrayContaining(['全部性别', '全部班级', '全部院校', '全部专业']),
    )
    for (const gone of ['全部月份', '全部职务', '全部职级', '全部在职状态']) {
      expect(advancedPlaceholders).not.toContain(gone)
    }
    // 入职年度是数字输入（无 placeholder 文案）→ 直接断言表单里没有该字段
    const advancedLabels = w.findAll('.n-form-item-label').map((l) => l.text())
    expect(advancedLabels).not.toContain('入职年度')
    expect(advancedLabels).not.toContain('招聘月份')
    expect(advancedLabels).not.toContain('职务')
    expect(advancedLabels).not.toContain('职级')
    expect(advancedLabels).not.toContain('在职状态')
  }, 20000)

  it('④b 在职状态由状态页签唯一控制（高级筛选里不再重复一份）', async () => {
    const w = await mountPage()
    const vm = w.vm as any
    vm.onTabChange('在职')
    await flushPromises()
    expect(vm.activeTab).toBe('在职')
    // 高级筛选状态里不再有 status 这一项（在职状态只有一个来源）
    expect(vm.advancedForm.status).toBeUndefined()
    // 请求参数里的 status 来自页签
    const lastCall = apiGet.mock.calls[apiGet.mock.calls.length - 1] as any[]
    expect(lastCall[1].params.status).toBe('在职')
  }, 20000)

  it('⑤ 列宽合计仍 ≤ 1400px（一屏放下，不触发横向滚动）', async () => {
    const w = await mountPage()
    const vm = w.vm as any
    const sum = vm.columns.reduce((s: number, c: any) => s + (c.width ?? 0), 0)
    expect(sum).toBeLessThanOrEqual(1400)
    expect(vm.TABLE_SCROLL_X).toBe(sum)
  }, 20000)

  it('⑥ 页签与数据列表容器之间无「人为留白带」（间距唯一来源 = 容器 gap）', async () => {
    // 2026-10-22 兵哥反馈「页签分栏和数据列表容器的间距太大」——同款病根
    //   （元素 margin + 容器 gap + naive 空 pane 内边距 三重叠加）
    //   仓库在 2026-09-18 已治过一次（glass.css「双重间距根治」：间距唯一来源 = 容器 gap）。
    const src = readFileSync(
      join(process.cwd(), 'src/pages/campus/CampusPerson.vue'),
      'utf8',
    )
    // ① 页签行不得自带下外边距（会与 .page-body 的 flex gap 叠加）
    const tabsRule = src.match(/\.status-tabs \{([\s\S]*?)\n\}/)
    expect(tabsRule, '应存在 .status-tabs 样式').toBeTruthy()
    expect(tabsRule![1]).not.toMatch(/margin[^:]*:\s*[^;]*\bvar\(--space-/)
    // ② 空 tab-pane 的内建上内边距必须清零（数据列表是 tabs 的兄弟节点，不在 pane 内）
    expect(src).toMatch(/\.status-tabs :deep\(\.n-tab-pane\) \{\s*padding: 0;/)
  })
}, 20000)

/**
 * ② 回归护栏：入职日期单元格的样式**必须**放在非 scoped 块。
 *
 * 根因（2026-10-22 实测）：Vue 的 scoped 依赖**编译期给模板元素**注入 `data-v-xxx`，
 * 而表格列 render 里用 `h()` 造的 VNode **不带该属性** → scoped 规则对它们**完全不命中**。
 * 症状极具迷惑性：源码规则完全正确、lint/编译/单测全绿，**渲染却是裸的**
 * （实测连续三轮改 CSS 都没生效：两行日期被排成两列、日期在「/」处折行）。
 * 判据用 @vue/compiler-sfc 解析 SFC 的 style 块归属，比正则可靠。
 */
describe('入职日期单元格样式的作用域（2026-10-22 真机回归）', () => {
  it('样式必须在非 scoped 块（scoped 对 h() 动态渲染的元素不命中）', () => {
    const src = readFileSync(
      join(process.cwd(), 'src/pages/campus/CampusPerson.vue'),
      'utf8',
    )
    const { descriptor } = parse(src)
    const scoped = descriptor.styles.filter((s: any) => s.scoped)
    const global = descriptor.styles.filter((s: any) => !s.scoped)
    // scoped 块里不得再出现 .entry-date-cell* 规则
    for (const block of scoped) {
      expect(block.content).not.toMatch(/\.entry-date-cell/)
    }
    // 非 scoped 块里必须有（否则样式彻底丢失）
    expect(global.some((b: any) => b.content.includes('.entry-date-cell'))).toBe(true)
    // 关键：三段结构齐全（图标槽 / 文字 / 勾）
    const css = global.map((b: any) => b.content).join('\n')
    expect(css).toMatch(/\.entry-date-cell__row/)
    expect(css).toMatch(/\.entry-date-cell__icon/)
    expect(css).toMatch(/\.entry-date-cell__val/)
    // 日期不允许断行（否则在「/」处折行把图标甩到上一行）
    expect(css).toMatch(/white-space:\s*nowrap/)
  }, 20000)
})
