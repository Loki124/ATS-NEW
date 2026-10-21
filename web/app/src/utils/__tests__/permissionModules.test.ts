/**
 * permissionModules.test.ts — 前端模块映射表与 seed 一致性断言（S6-04）。
 *
 * 背景：RESOURCE_MODULE_LABELS 是「模块代码 → 中文名」的前端唯一数据源。
 * 若有人新增一个模块到后端 seed（apps/core/management/commands/seed_v2_init.py
 * 的 RESOURCES 四元组第 4 段）却忘了同步本表，该模块下所有资源在「资源管理」
 * 页的模块列会被渲染成「—」（误判为「没有模块」）—— 这正是 2026-10-19 复盘
 * 暴露的漂移问题（此前漏收 campus/channel/notification/user_app_data_scope 四模块）。
 *
 * 本测试在 CI 拦截此类回归：断言 seed 实际用到的全部 module 都被
 * RESOURCE_MODULE_LABELS 收录，且映射值非空。
 *
 * 真源：直接读取 seed_v2_init.py 解析 RESOURCES（不手搓常量，避免二次漂移）。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import {
  RESOURCE_MODULE_LABELS,
  GROUP_PATH_LABELS,
  buildSubModuleIndex,
  resourceModuleLabel,
  buildPermissionTree,
  collectNodeCodes,
} from '../permissionModules'

// 跨前后端的真源路径：从本测试文件（web/app/src/utils/__tests__）上溯到仓库根，
// 再进入 Django 种子文件。
const here = dirname(fileURLToPath(import.meta.url))
const SEED_PATH = resolve(
  here,
  '../../../../../apps/django/apps/core/management/commands/seed_v2_init.py',
)

/** 解析 seed_v2_init.py 的 RESOURCES 列表，提取每条资源的 module（四元组第 4 段）。 */
function seedModules(): string[] {
  const content = readFileSync(SEED_PATH, 'utf-8')
  const marker = 'RESOURCES = ['
  const start = content.indexOf(marker)
  expect(start, `在 ${SEED_PATH} 中未找到 RESOURCES 定义`).toBeGreaterThan(-1)
  const rest = content.slice(start)
  // 资源列表以单独成行的 ] 收尾
  const end = rest.indexOf('\n]')
  expect(end, '未能定位 RESOURCES 列表的结束 ]').toBeGreaterThan(-1)
  const block = rest.slice(0, end)

  // RESOURCES 为 (code, 中文名, type, module) 四元组，module 是第 4 段
  const tupleRe =
    /\((['"][^'"]+['"]),\s*(['"][^'"]+['"]),\s*(['"][^'"]+['"]),\s*(['"][^'"]+['"])\)/g
  const modules: string[] = []
  let m: RegExpExecArray | null
  while ((m = tupleRe.exec(block)) !== null) {
    modules.push(m[4].slice(1, -1)) // 去掉首尾引号
  }
  return modules
}

describe('RESOURCE_MODULE_LABELS 覆盖 seed 全部 module（S6-04）', () => {
  const modules = seedModules()

  it('应解析到足量资源四元组（防止解析逻辑静默为空）', () => {
    expect(
      modules.length,
      '解析到的 module 数量过少，可能解析逻辑失效或 seed 路径变化',
    ).toBeGreaterThan(50)
  })

  it('seed 用到的每个 module 都必须被前端映射表收录（否则显示「—」）', () => {
    const seedModuleSet = [...new Set(modules)]
    const missing = seedModuleSet.filter((mod) => !(mod in RESOURCE_MODULE_LABELS))
    expect(
      missing,
      `以下 seed module 未收录进 RESOURCE_MODULE_LABELS（会在资源管理页显示「—」）: ${missing.join(', ')}`,
    ).toEqual([])
  })

  it('映射表收录的模块必须有非空中文名（避免空 label）', () => {
    const empty = Object.entries(RESOURCE_MODULE_LABELS)
      .filter(([, label]) => !label || !label.trim())
      .map(([k]) => k)
    expect(empty, `以下模块的中文名为空: ${empty.join(', ')}`).toEqual([])
  })
})

/**
 * 管理单元归属断言（2026-10-20，core.0042）。
 *
 * 背景：管理单元原为一级模块 mgmt_unit，与侧边栏「设置中心 → 权限管理 → 管理单元」
 * 的归属不符。现码族迁入 `recruit:settings:mgmt_unit:*`，资源管理页应把它显示成
 * 「系统设置」模块下的「管理单元」子模块 —— 本测试锁定这一结果，防止再漂回去。
 */
describe('管理单元归入系统设置模块（0042）', () => {
  const resources = [
    { resourceCode: 'recruit:settings:mgmt_unit:menu:view', resourceName: '管理单元菜单' },
    { resourceCode: 'recruit:settings:mgmt_unit:list', resourceName: '管理单元列表' },
  ]

  it('模块列显示「系统设置」', () => {
    expect(resourceModuleLabel('settings')).toBe('系统设置')
  })

  it('子模块列由数据推导为「管理单元」', () => {
    const index = buildSubModuleIndex(resources)
    // 子模块索引按第 4 段为 menu 判定，故只有 menu:view 参与建索引
    expect(index.settings?.mgmt_unit).toBe('管理单元')
  })
})

/**
 * 功能权限树按显式 sub_module 分组（2026-10-21 兵哥）。
 *
 * 背景：资源管理页已给候选人管理 10 条资源登记子模块（6 基础功能 + 4 offer管理，
 * 存于 permission_resources.sub_module）。功能权限页签必须以该分类为准分组展示，
 * 而不是按编码结构把 candidate:offer:* 推导成裸「offer」码段分组。
 * 本测试锁定：显式分类优先、分组名即分类值、资源分类调整后树自动同步（数据驱动）。
 */
describe('功能权限树：显式 sub_module 分组优先（2026-10-21）', () => {
  // 与 seed_v2_init.RESOURCE_SUB_MODULES 同构的样例（10 条候选人资源）
  const resources = [
    { resourceCode: 'recruit:candidate:create', resourceName: '新增候选人', subModule: '基础功能' },
    { resourceCode: 'recruit:candidate:delete', resourceName: '删除候选人', subModule: '基础功能' },
    { resourceCode: 'recruit:candidate:edit', resourceName: '编辑候选人', subModule: '基础功能' },
    { resourceCode: 'recruit:candidate:export', resourceName: '导出候选人', subModule: '基础功能' },
    { resourceCode: 'recruit:candidate:list', resourceName: '候选人列表', subModule: '基础功能' },
    { resourceCode: 'recruit:candidate:menu:view', resourceName: '候选人菜单', subModule: '基础功能' },
    { resourceCode: 'recruit:candidate:offer:approve', resourceName: '发起offer审批', subModule: 'offer管理' },
    { resourceCode: 'recruit:candidate:offer:create', resourceName: '创建offer', subModule: 'offer管理' },
    { resourceCode: 'recruit:candidate:offer:edit', resourceName: '编辑offer', subModule: 'offer管理' },
    { resourceCode: 'recruit:candidate:offer:list', resourceName: '查看offer', subModule: 'offer管理' },
  ]

  const candidateOf = () => {
    const tree = buildPermissionTree(resources)
    const candidate = tree.find((n) => n.segment === 'candidate')
    expect(candidate, '候选人模块节点应存在').toBeDefined()
    return candidate!
  }

  it('按显式子模块分成两组，组名即分类值，按清单首现序排（基础功能在前）', () => {
    expect(candidateOf().children.map((c) => c.label)).toEqual(['基础功能', 'offer管理'])
  })

  it('编码推导的裸「offer」码段分组不再出现（显式分类覆盖编码结构）', () => {
    const candidate = candidateOf()
    expect(candidate.children.some((c) => c.segment === 'offer')).toBe(false)
    const offer = candidate.children.find((c) => c.label === 'offer管理')!
    expect(offer.children.map((c) => c.label).sort()).toEqual(
      ['发起offer审批', '创建offer', '编辑offer', '查看offer'].sort(),
    )
  })

  it('基础功能 6 条叶子齐全（含菜单项），分组全选口径（collectNodeCodes）不受影响', () => {
    const basic = candidateOf().children[0]
    expect(basic.children).toHaveLength(6)
    const codes = collectNodeCodes(basic)
    expect(codes).toHaveLength(6)
    expect(codes).toContain('recruit:candidate:menu:view')
  })

  it('未带 sub_module 的资源保持编码结构分组（回归：settings 菜单族不受影响）', () => {
    const tree = buildPermissionTree([
      { resourceCode: 'recruit:settings:account:menu:view', resourceName: '个人信息管理菜单' },
      { resourceCode: 'recruit:settings:account:create', resourceName: '新增个人信息' },
    ])
    const settings = tree.find((n) => n.segment === 'settings')!
    const account = settings.children.find((c) => c.segment === 'account')!
    expect(account.label).toBe('个人信息管理')
    expect(account.children).toHaveLength(2)
  })
})

/**
 * 功能权限树分组名兜底映射（2026-10-21 兵哥截图：metrics/users/role_grant 裸英文）。
 *
 * 根因：这些分组没有「启用的 MENU 资源」做名字锚点（metrics/role_grant 只有
 * BUTTON；users 唯一菜单已随 0026 停用，前端默认只拉启用资源）。
 * GROUP_PATH_LABELS 是展示兜底，锁定三类行为：兜底生效、菜单回填优先、值非空。
 */
describe('功能权限树：无菜单锚点分组的中文兜底（GROUP_PATH_LABELS）', () => {
  it('映射表每条值必须非空（防手滑登记空串）', () => {
    const empty = Object.entries(GROUP_PATH_LABELS)
      .filter(([, label]) => !label || !label.trim())
      .map(([k]) => k)
    expect(empty).toEqual([])
  })

  it('metrics / users / role_grant 分组显示中文而非裸码段', () => {
    const tree = buildPermissionTree([
      { resourceCode: 'recruit:settings:metrics:list', resourceName: '指标管理' },
      { resourceCode: 'recruit:settings:metrics:edit', resourceName: '指标维护' },
      { resourceCode: 'recruit:settings:users:all:menu:view', resourceName: '全部用户菜单' },
      { resourceCode: 'recruit:settings:users:all:list', resourceName: '全部用户列表' },
      { resourceCode: 'recruit:settings:users:role_grant:create', resourceName: '新增身份配置' },
    ])
    const settings = tree.find((n) => n.segment === 'settings')!
    const bySegment = (seg: string) => settings.children.find((c) => c.segment === seg)
    expect(bySegment('metrics')!.label).toBe('指标管理')
    expect(bySegment('users')!.label).toBe('用户管理')
    const users = bySegment('users')!
    // 子层：全部用户（菜单回填）与 role_grant（兜底映射）
    expect(users.children.find((c) => c.segment === 'all')!.label).toBe('全部用户')
    expect(users.children.find((c) => c.segment === 'role_grant')!.label).toBe('用户身份配置')
  })

  it('菜单名回填优先于兜底映射（menu 锚点启用后自动接管）', () => {
    // settings/users 已登记兜底「用户管理」；若该路径直接挂启用菜单，
    // 菜单名必须覆盖兜底值（数据真源优先）
    const tree = buildPermissionTree([
      { resourceCode: 'recruit:settings:metrics:menu:view', resourceName: '指标中心菜单' },
      { resourceCode: 'recruit:settings:metrics:list', resourceName: '指标管理' },
    ])
    const settings = tree.find((n) => n.segment === 'settings')!
    expect(settings.children.find((c) => c.segment === 'metrics')!.label).toBe('指标中心')
  })
})
