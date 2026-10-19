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
import { RESOURCE_MODULE_LABELS } from '../permissionModules'

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
