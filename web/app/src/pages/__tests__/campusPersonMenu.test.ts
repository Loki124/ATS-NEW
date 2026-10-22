/**
 * 校招「人员管理」菜单命名 —— 回归护栏（2026-10-21 兵哥更名）。
 *
 * 背景：原菜单项「校招生档案」更名为「人员管理」。菜单标签写在
 * `pages/Layout.vue` 的静态数组里、面包屑/文档标题取自路由 `meta.title`，
 * 二者都是**字面量**，极易被后人「顺手改回」或改一处漏一处（面包屑与菜单不一致）。
 *
 * 本测试按仓库既有先例（`styles/__tests__/table-alignment-rules.test.ts`
 * 的源码扫描式护栏）把两处字面量钉死。
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

const LAYOUT_SRC = fs.readFileSync(path.resolve(__dirname, '../Layout.vue'), 'utf8')
const ROUTER_SRC = fs.readFileSync(path.resolve(__dirname, '../../router/index.ts'), 'utf8')

describe('校招人员菜单命名', () => {
  it('菜单项 /campus/person 的标签是「人员管理」', () => {
    expect(LAYOUT_SRC).toMatch(/key:\s*'\/campus\/person',\s*label:\s*'人员管理'/)
    // 旧名不得再出现在菜单项上
    expect(LAYOUT_SRC).not.toMatch(/key:\s*'\/campus\/person',\s*label:\s*'校招生档案'/)
  })

  it('路由 campus/person 的 meta.title 是「人员管理」（面包屑/文档标题与菜单一致）', () => {
    const block = ROUTER_SRC.match(/path:\s*'campus\/person'[\s\S]*?\n\s*\},/)
    expect(block).toBeTruthy()
    expect(block![0]).toContain("title: '人员管理'")
  })

  it('路由路径与 name 不变（更名只动显示文案，不影响路由与授权）', () => {
    expect(ROUTER_SRC).toMatch(/path:\s*'campus\/person'/)
    expect(ROUTER_SRC).toMatch(/name:\s*'CampusPersonManagement'/)
  })
})
