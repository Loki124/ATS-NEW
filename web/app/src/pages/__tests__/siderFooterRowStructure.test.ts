/**
 * 侧栏底部行 · DOM 嵌套结构护栏（2026-10-21 兵哥指令）
 *
 * 为什么要用 **AST** 而不是正则：正则只能看「出现顺序」，看不出**嵌套关系** ——
 * 若 `.sider-footer`（设置）被写到了 `.sider-footer-row` 之外（标签闭合错位），
 * 正则全绿、页面却把「设置」和「固定/折叠」按钮排成上下两行（兵哥截图就是这个现象）。
 * 这里直接用 @vue/compiler-sfc 解析模板 AST，断言两者的**父子关系**。
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { parse } from '@vue/compiler-sfc'

const SRC = fs.readFileSync(path.resolve(__dirname, '../Layout.vue'), 'utf8')
const { descriptor, errors } = parse(SRC, { filename: 'Layout.vue' })

type Node = any

/** 在 AST 里找 class 含指定名的元素节点 */
function findByClass(nodes: Node[], className: string): Node | undefined {
  for (const n of nodes) {
    if (n.type === 1) {
      const cls = n.props?.find?.((p: any) => p.type === 6 && p.name === 'class')?.value?.content
      const staticCls = typeof cls === 'string' ? cls : ''
      if (staticCls.split(/\s+/).includes(className)) return n
      const hit = findByClass(n.children ?? [], className)
      if (hit) return hit
    }
  }
  return undefined
}

/** 取元素的祖先链（从外到内） */
function ancestorsOf(node: Node, nodes: Node[], chain: Node[] = []): Node[] {
  for (const n of nodes) {
    if (n.type !== 1) continue
    if (n === node) return chain
    const next = [...chain, n]
    if ((n.children ?? []).includes(node)) return ancestorsOf(node, n.children ?? [], next)
    const hit = ancestorsOf(node, n.children ?? [], next)
    if (hit.length) return hit
  }
  return []
}

const template = descriptor.template
const astChildren = template?.ast?.children ?? []

describe('侧栏底部行 DOM 嵌套', () => {
  it('模板可被编译（无标签闭合错位）', () => {
    // parse() 把模板/脚本的编译错误收在 errors 里（不是 onError 回调 —— 那是 compiler 的选项）
    expect(descriptor.template?.ast).toBeTruthy()
    expect(errors).toEqual([])
  })

  it('「设置」是 .sider-footer-row 的直接子元素（同一行）', () => {
    const row = findByClass(astChildren, 'sider-footer-row')
    const footer = findByClass(astChildren, 'sider-footer')
    expect(row).toBeTruthy()
    expect(footer).toBeTruthy()
    // 设置必须在 row 里
    expect((row.children ?? []).includes(footer)).toBe(true)
    // 且不能是 row 的孙级（说明中间多套了一层）
    const chain = ancestorsOf(footer, astChildren)
    expect(chain[chain.length - 1]).toBe(row)
  })

  it('「固定/折叠」切换按钮与「设置」同为 row 的直接子元素（同一行）', () => {
    const row = findByClass(astChildren, 'sider-footer-row')
    const toggle = findByClass(astChildren, 'sider-toggle')
    expect(row).toBeTruthy()
    expect(toggle).toBeTruthy()
    expect((row.children ?? []).includes(toggle)).toBe(true)
  })

  it('切换按钮内只有图标，没有文字标签节点', () => {
    const toggle = findByClass(astChildren, 'sider-toggle')
    const hasText = (toggle.children ?? []).some((c: Node) => c.type === 2 && String(c.content ?? '').trim())
    expect(hasText).toBe(false)
  })
})
