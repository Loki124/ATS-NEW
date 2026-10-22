// E5 守卫：扫描 .vue **模板层**的 emoji（AGENTS.md X-02：禁止 emoji 当功能图标）。
//
// 为什么只扫模板层：注释里的 ⚠️/🔴 是给开发者的标记（"这里踩过坑"），不是用户可见的
// 功能图标，不属于 X-02 管辖范围；把它们一并报出来会让守卫变成噪音，最终被无视。
//
// 只扫顶层 <template>…</template> 之间、且不在 HTML 注释 <!-- --> 里的行。
// 跨平台写法（macOS/BSD 的 grep 没有 -P），纯 Node 实现。
//
// 用法：node scripts/scan_emoji.mjs [根目录，默认 src]
// 退出码：0 无违规；1 有违规（供 CI 硬门禁用）。
import fs from 'node:fs'
import path from 'node:path'

const RE = /\p{Extended_Pictographic}/u
const SKIP_DIRS = new Set(['node_modules', 'dist', '.git'])

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (SKIP_DIRS.has(e.name)) continue
      walk(path.join(dir, e.name), out)
    } else if (e.name.endsWith('.vue')) {
      out.push(path.join(dir, e.name))
    }
  }
  return out
}

/** 取顶层 <template> 的行区间 [start, end)，并剔除 HTML 注释行 */
function templateLines(lines) {
  let start = -1
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim().startsWith('<template>')) { start = i; break }
  }
  if (start === -1) return []
  let end = lines.length
  for (let i = start + 1; i < lines.length; i++) {
    if (lines[i].trim() === '</template>') { end = i; break }
  }
  const inComment = new Array(end - start).fill(false)
  let comment = false
  for (let i = start; i < end; i++) {
    const line = lines[i]
    if (!comment && line.includes('<!--')) {
      comment = true
      inComment[i - start] = true
      if (line.includes('-->')) { comment = false; inComment[i - start] = false }
      continue
    }
    if (comment) {
      inComment[i - start] = true
      if (line.includes('-->')) comment = false
    }
  }
  return lines.slice(start, end).map((l, i) => ({ line: l, no: start + i + 1, skip: inComment[i] }))
}

const root = process.argv[2] || 'src'
let total = 0
for (const file of walk(root)) {
  const lines = fs.readFileSync(file, 'utf8').split('\n')
  for (const { line, no, skip } of templateLines(lines)) {
    if (skip || !RE.test(line)) continue
    const chars = [...line].filter((c) => RE.test(c))
    console.log(`${file}:${no}  [${chars.join(' ')}]  ${line.trim().slice(0, 100)}`)
    total += 1
  }
}
console.log(`\n模板层 emoji 违规：${total} 处`)
process.exit(total > 0 ? 1 : 0)
