/**
 * check-h-render-scope.mjs — 扫出「样式写在 scoped 块、但元素由 h() 动态渲染 → 规则不命中」的失效样式。
 *
 * ## 背景（2026-10-22 实测）
 *   Vue 的 scoped 样式依赖**编译期给模板里的元素**注入 `data-v-xxx`；
 *   而 `render` 里用 `h()` 造的 VNode **不带该属性** → scoped 规则对它**完全不命中**。
 *   症状：源码里规则写得完全正确、lint/编译/单测全绿，**渲染却是裸的**
 *   （实测：两行日期被排成两列、图标越出高亮块、日期在「/」处折行 —— 连续三轮改 CSS 都没生效，
 *     根因就是规则压根没命中）。
 *
 * ## 实测证据（2026-10-22，Chrome channel:'chrome'）
 *   规则选择器 = `.saturation-cell[data-v-ba9f44de]`
 *   元素属性  = **无任何 data-v-\* 属性**（h(NTag, {...}) 渲染的组件根元素也不带）
 *   → 选择器不匹配 → 规则不命中。
 *   ⚠️ 判据必须用**非继承属性**：`.saturation-cell` 声明的 `font-variant-numeric: tabular-nums`
 *      在 computed 里看着"生效了"，其实是父级 `.n-data-table-table` 继承来的 —— 假阳性。
 *      所以本扫描器只做**静态结构判定**（谁在 scoped 块、谁只由 h() 渲染），
 *      实际是否可见差异需浏览器实测。
 *
 * ## 用法
 *   node scripts/check-h-render-scope.mjs            # 报告（退出码 0）
 *   node scripts/check-h-render-scope.mjs --strict   # 有失效即 exit 1（可挂 CI）
 *   node scripts/check-h-render-scope.mjs --baseline # 把当前结果写入基线文件（存量登记）
 *
 * ## 基线机制（只许减少、不许新增）
 *   与仓库既有门禁同源思路（见 apps/django/scripts_scan_todo.py、ruff 门禁注释）：
 *   存量失效样式**登记进基线**放行，CI 只拦**新增**。
 *   → 今天就能挂 CI 且不阻塞并行会话；存量清完后把基线清空即自动变严格门禁。
 *   基线文件：scripts/render-scope-baseline.txt（每行 `文件路径 类名`）
 *
 * ## 修法
 *   把这类样式从 `<style scoped>` 挪到**非 scoped** 的 `<style>` 块（类名要够独特），
 *   或改用 naive 组件自带的 class（自带样式，不依赖 scope）。
 */
import { parse } from '@vue/compiler-sfc'
import { readFileSync, readdirSync, statSync, writeFileSync, existsSync } from 'node:fs'
import path from 'node:path'

const BASELINE_FILE = path.join('scripts', 'render-scope-baseline.txt')

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (p.endsWith('.vue')) out.push(p)
  }
  return out
}

/**
 * 收集该 SFC 里所有「由 h() 渲染」的元素类名。
 * 覆盖两种形态（实测两种都不命中 scoped）：
 *   ① h('div',  { class: 'foo' })      —— 原生标签
 *   ② h(NTag,  { class: 'foo' })      —— 组件（组件根元素同样不带 data-v）
 * 另外 class 也可能是数组：class: ['foo', { cond: 'bar' }]。
 */
function collectHRenderedClasses(src) {
  const classes = new Set()
  // 匹配 h( 后的第一个参数（'小写标签' 或 大写组件名），再抓它的 class 属性
  const re = /h\(\s*(?:'[a-z][a-z0-9-]*'|[A-Z][A-Za-z0-9_]*)\s*,\s*\{/g
  let m
  while ((m = re.exec(src)) !== null) {
    // 从 h( 的 '{' 起做括号配平，截出该对象的完整文本
    let i = m.index + m[0].length - 1 // 指向 '{'
    let depth = 0
    let end = -1
    for (let k = i; k < src.length; k++) {
      const ch = src[k]
      if (ch === '{') depth++
      else if (ch === '}') {
        depth--
        if (depth === 0) { end = k; break }
      }
    }
    if (end < 0) continue
    const objText = src.slice(i, end + 1)
    // class: 'foo'
    for (const cm of objText.matchAll(/class:\s*'([a-zA-Z0-9_-]+)'/g)) classes.add(cm[1])
    // class: ['foo', { cond: 'bar' }] —— 只取字符串字面量项
    for (const cm of objText.matchAll(/class:\s*\[([^\]]*)\]/g)) {
      for (const sm of cm[1].matchAll(/'([a-zA-Z0-9_-]+)'/g)) classes.add(sm[1])
    }
  }
  return classes
}

const files = walk('src')
const broken = []
for (const f of files) {
  const src = readFileSync(f, 'utf8')
  const { descriptor } = parse(src)
  const scopedBlocks = descriptor.styles.filter((s) => s.scoped)
  const globalBlocks = descriptor.styles.filter((s) => !s.scoped)
  if (!scopedBlocks.length) continue

  const classes = collectHRenderedClasses(src)
  const tpl = descriptor.template?.content || ''
  for (const c of classes) {
    // 类名若也出现在**模板**里 → 模板那处的 scoped 规则是生效的；
    // 但 h() 渲染的那处实例仍然不命中 → 仍是失效（模板与 h() 可能是两套元素）
    const sel = `.${c}`
    const inScoped = scopedBlocks.some((b) => b.content.includes(sel))
    const inGlobal = globalBlocks.some((b) => b.content.includes(sel))
    // 全局样式文件里若已定义该类 → h() 那处也能命中（非 scoped 选择器不依赖 data-v）
    const inGlobalCss = readdirSync('src/styles')
      .filter((n) => n.endsWith('.css'))
      .some((n) => readFileSync(path.join('src/styles', n), 'utf8').includes(sel))
    if (inScoped && !inGlobal && !inGlobalCss) {
      broken.push({ file: f, cls: c, alsoInTemplate: tpl.includes(c) })
    }
  }
}

console.log('=== 样式写在 scoped 块、但元素由 h() 动态渲染 → 规则不命中（失效）===')

// 基线：存量登记项（"文件路径 类名"），用于「只许减少、不许新增」
const baseline = new Set()
if (existsSync(BASELINE_FILE)) {
  for (const line of readFileSync(BASELINE_FILE, 'utf8').split('\n')) {
    const t = line.trim()
    if (!t || t.startsWith('#')) continue
    baseline.add(t)
  }
}

const key = (b) => `${b.file} ${b.cls}`
const isNew = (b) => !baseline.has(key(b))

if (process.argv.includes('--baseline')) {
  writeFileSync(BASELINE_FILE, [...broken].map(key).sort().join('\n') + '\n')
  console.log(`\n✔ 已写入基线 ${BASELINE_FILE}（${broken.length} 条）`)
  process.exit(0)
}

for (const b of broken) {
  const mark = isNew(b) ? '🆕' : '  '
  console.log(
    `${mark} ${b.file}  .${b.cls}${b.alsoInTemplate ? '   ← 类名也出现在模板里（h() 那处仍裸奔）' : ''}`,
  )
}
console.log(`总计 ${broken.length}（其中新增 ${broken.filter(isNew).length}，存量 ${broken.length - broken.filter(isNew).length}）`)

if (process.argv.includes('--strict')) {
  const news = broken.filter(isNew)
  if (news.length > 0) {
    console.error(`\n❌ 发现 ${news.length} 处**新增** scoped→h() 失效样式（--strict 模式阻断）`)
    for (const b of news) console.error(`   ${b.file}  .${b.cls}`)
    console.error('   修法：把该类样式挪到非 scoped <style> 块，或改用组件自带 class。')
    console.error(`   （若确认是既有存量，需登记进基线：node scripts/check-h-render-scope.mjs --baseline）`)
    process.exit(1)
  }
  console.log(`\n✓ 无新增 scoped→h() 失效样式（存量 ${broken.length} 处已在基线内，待逐步清理）`)
}
