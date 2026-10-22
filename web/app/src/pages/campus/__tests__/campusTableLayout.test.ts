/**
 * 校招生管理 · 表格版式护栏（2026-10-21 样式优化）
 *
 * 修的问题（见用户截图）：档案页 14 列列宽合计 1630px 超出容器，naive-ui 未给
 * `scroll-x` 就不横向滚动 ⇒ 末尾列被裁、「专业」列被 fixed:'right' 的操作列盖住，
 * 且 140px 的操作列装不下「编辑 + 删除」两个带图标按钮，「删除」被截掉半截。
 *
 * 锁四条（静态断言，不依赖运行时渲染）：
 * 1. 每列都有显式 width（否则 naive 按内容分配，宽度随数据漂移）；
 * 2. `scroll-x` 恒等于各列 width 之和（两者漂移就等于没设）；
 * 3. 操作列宽度 ≥ 该页实际按钮数所需（两按钮 ≈148px + 单元格内边距 24px；
 *    ⚠️ 2026-10-22 班级管理下线「删除」按钮 → 只剩「编辑」，所需宽度按页取 minActionWidth）；
 * 4. 操作列 fixed:'right'（窄屏横向滚动时不被内容列顶掉）。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import CampusPerson from '../../../pages/campus/CampusPerson.vue'
import ClassRoom from '../../../pages/campus/ClassRoom.vue'
import RotationResourcePanel from '../../../pages/campus/RotationResourcePanel.vue'
import RotationArrangement from '../../../pages/campus/RotationArrangement.vue'

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

const PAGES = [
  { name: '校招生档案', comp: CampusPerson, minActionWidth: 160 },
  // 2026-10-22：班级删除按钮下线 → 操作列只剩「编辑」，所需宽度按实际按钮数取
  { name: '班级管理', comp: ClassRoom, minActionWidth: 80 },
  // 2026-10-22：轮岗资源（直播间 + 客服部门合并）操作列含「启用/停用」按钮
  //   → 三按钮（编辑/启停/删除），宽度下限 160 → 268
  { name: '轮岗资源', comp: RotationResourcePanel, minActionWidth: 268 },
  { name: '轮岗安排', comp: RotationArrangement, minActionWidth: 160 },
] as const

const mountPage = async (comp: any) => {
  const wrapper = mount(comp, {
    global: { stubs: { teleport: true }, plugins: [createPinia()] },
  })
  await flushPromises()
  return wrapper
}

describe.each(PAGES)('$name 表格版式', ({ comp, minActionWidth }) => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { data: [] } })
  })

  it('① 每列都有显式 width', async () => {
    const w = await mountPage(comp)
    const cols = (w.vm as any).columns
    expect(cols.length).toBeGreaterThan(3)
    cols.forEach((c: any) => {
      expect(typeof c.width).toBe('number')
      expect(c.width).toBeGreaterThan(0)
    })
  }, 20000)

  it('② scroll-x 等于各列 width 之和（防止两者漂移）', async () => {
    const w = await mountPage(comp)
    const vm = w.vm as any
    const sum = vm.columns.reduce((s: number, c: any) => s + (c.width ?? 0), 0)
    expect(vm.TABLE_SCROLL_X).toBe(sum)
  }, 20000)

  it('③ 操作列宽度足够（按钮不被裁）且固定在右侧', async () => {
    const w = await mountPage(comp)
    const cols = (w.vm as any).columns
    const actions = cols.find((c: any) => c.key === 'actions')
    expect(actions).toBeTruthy()
    expect(actions.width).toBeGreaterThanOrEqual(minActionWidth)
    expect(actions.fixed).toBe('right')
  }, 20000)
})

describe('校招生档案表格版式（专项）', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { data: [] } })
  })

  it('① 列宽合计 ≤ 1400px（14 列一屏放得下，不触发横向滚动）', async () => {
    const w = await mountPage(CampusPerson)
    const vm = w.vm as any
    const sum = vm.columns.reduce((s: number, c: any) => s + (c.width ?? 0), 0)
    expect(sum).toBeLessThanOrEqual(1400)
  }, 20000)

  it('② 数字类列（工号 / 日期 / 职级）用等宽数字，刷新不抖动', async () => {
    // scoped 样式不进渲染 HTML，只能扫源码（与设置中心 DataListStandard 护栏同一手法）
    // ⚠️ vitest 的 import.meta.url 不是 file:// scheme，走 process.cwd()（= web/app）
    const src = readFileSync(
      join(process.cwd(), 'src/pages/campus/CampusPerson.vue'),
      'utf8',
    )
    expect(src).toContain('font-variant-numeric: tabular-nums')
  }, 20000)
})

/**
 * 班级管理 · 工具条筛选行版式护栏（2026-10-22 兵哥指令「筛选项搜索框按钮放到同一行里」）
 *
 * 修的问题：班长筛选用了 `class="filter-select"` —— 该类**在班级管理页无定义**
 * （`CampusPerson.vue` 有自己的 scoped 副本，本页没有；全局标准类是 `.rule-filter-select`）。
 * 类不存在 ⇒ n-select 回落到 naive-ui 自带的 `width: 100%` ⇒ 撑满整行、
 * 把搜索框挤到上一行 —— 正是截图里的样子（搜索框一行、全部班长又一行）。
 *
 * 锁两条：
 * 1. 班级管理页的工具条控件用**全局标准类**（.rule-filter-search 240px /
 *    .rule-filter-select 136px，均带 flex-shrink:0）—— 两者同处一行且不被压缩；
 * 2. 全局工具类本身确有宽度与 flex-shrink 声明（防全局样式被改坏）。
 */
describe('班级管理工具条（筛选项与搜索框同一行）', () => {
  const readSrc = (rel: string) =>
    readFileSync(join(process.cwd(), rel), 'utf8')

  it('① 搜索框用 .rule-filter-search、班长筛选用 .rule-filter-select（全局标准类）', () => {
    const src = readSrc('src/pages/campus/ClassRoom.vue')
    expect(src).toContain('class="rule-filter-search"')
    expect(src).toContain('class="rule-filter-select"')
    // 旧的不存在的类不得再出现（它就是「独占整行」的病根）
    expect(src).not.toMatch(/class="filter-select"/)
  }, 20000)

  it('② 全局工具类有固定宽度 + flex-shrink:0（保证同排且不被压扁）', () => {
    const glass = readSrc('src/styles/glass.css')
    expect(glass).toMatch(/\.rule-filter-search\s*\{[^}]*width:\s*240px[^}]*flex-shrink:\s*0/)
    expect(glass).toMatch(/\.rule-filter-select\s*\{[^}]*width:\s*136px[^}]*flex-shrink:\s*0/)
  }, 20000)

  it('③ 工具条容器允许换行但不强制（宽度够时同排，不够时兜底换行）', () => {
    const glass = readSrc('src/styles/glass.css')
    expect(glass).toMatch(/\.toolbar\s*\{[^}]*flex-wrap:\s*wrap/)
  }, 20000)
})

/**
 * 表格居中护栏（2026-10-22：用户截图「这两个字段没有居中对齐」）
 *
 * 病根：n-data-table 的 td 居中靠行内 `text-align:center`，而 text-align **只对行内级内容生效**。
 *       列定义里 `h(NSpace, ...)` 渲染出的是**块级** flex（display:flex），其子项按
 *       justify-content 排列（naive 默认 start）→ 整组内容贴左，text-align 失效。
 *       症状 = 表头居中、正文不居中（操作列的「编辑」贴着单元格左边）。
 *       n-switch / n-button / n-tag 的根元素都是 inline-flex（行内级）→ 居中本就正常，
 *       故只需给 n-space 补一次居中，一次性修好全仓 43 处操作/控件列。
 *
 * 锁三条：
 * 1. glass.css 存在「居中档 td 内的 n-space 居中」规则；
 * 2. 班级管理「阶段分布」用 NTag 呈现（inline-flex → 居中生效），不再用无底色按钮；
 * 3. 阶段分布仍保留下钻（真实 <button> 承载，键盘可达 R-109）。
 */
describe('表格居中（表头居中 → 内容也居中）', () => {
  const readSrc = (rel: string) => readFileSync(join(process.cwd(), rel), 'utf8')

  const stageColumnBlock = (src: string) =>
    src.slice(src.indexOf("title: '阶段分布'"), src.indexOf("title: '操作'"))

  it('① glass.css 给居中档 td 内的 n-space 补居中', () => {
    const glass = readSrc('src/styles/glass.css')
    expect(glass).toMatch(
      /\.n-data-table-td--center-align\s*>\s*\.n-space\s*\{[^}]*justify-content:\s*center\s*!important/,
    )
  }, 20000)

  it('② 班级管理「阶段分布」用标签（NTag）呈现，而非无底色文字按钮', () => {
    const block = stageColumnBlock(readSrc('src/pages/campus/ClassRoom.vue'))
    expect(block).toContain('NTag')
    expect((block.match(/NButton/g) ?? []).length).toBe(0)
  }, 20000)

  it('③ 阶段分布仍可下钻（真实 button 承载，键盘可达）', () => {
    const block = stageColumnBlock(readSrc('src/pages/campus/ClassRoom.vue'))
    expect(block).toContain("'button'")
    expect(block).toContain('openStageMembers')
    // 可点标签的 button 外观必须复位（否则会看到浏览器默认按钮边框）
    const src = readSrc('src/pages/campus/ClassRoom.vue')
    expect(src).toMatch(/\.stage-chip\s*\{[^}]*border:\s*none[^}]*\}/)
  }, 20000)
})
