// E6 守卫：扫描「双滚动」设置页 —— 滚动容器是 .page-body(整体滚)，
// 同时页面内又有 flex-height 表格(表体自滚) → 外层与内层同时可滚 (R-215 违规)。
//
// 为什么要有这个守卫：SettingsLayout 的滚动契约是**两条轨道**（见该文件注释）——
//   ① 表单/详情页 → .page-body 由布局层统一滚动；
//   ② 数据列表页 → .data-body 区域滚动（只有表格体滚，工具条/分页器固定）。
// 表格页若误用 .page-body 就会出现双滚动条，而这类回归**没有编译期信号**（lint/typecheck
// 都发现不了），只能靠静态约定 + 本扫描器兜住。
//
// 判据：页面用 .page-body 作滚动容器 + 页面内有 flex-height 表格 → 报出来。
// 退出码：0 无违规；1 有违规（供 CI 硬门禁用）。
import fs from 'node:fs'
import path from 'node:path'

const SKIP = new Set(['node_modules', 'dist', '.git'])

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (SKIP.has(e.name)) continue
      walk(path.join(dir, e.name), out)
    } else if (e.name.endsWith('.vue')) {
      out.push(path.join(dir, e.name))
    }
  }
  return out
}

const root = process.argv[2] || 'src/pages/settings'
const bad = []
for (const file of walk(root)) {
  const src = fs.readFileSync(file, 'utf8')
  const usesPageBody = /class="[^"]*\bpage-body\b/.test(src)
  const hasFlexHeight = /flex-height/.test(src)
  if (usesPageBody && hasFlexHeight) bad.push(file)
}

console.log(`=== 双滚动候选（.page-body + flex-height 表格）：${bad.length} 处 ===`)
for (const f of bad) console.log('  ' + f)
if (bad.length === 0) {
  console.log('  ✓ 无 —— 数据列表页均已走 .data-body 区域滚动链 (R-215)')
}
process.exit(bad.length > 0 ? 1 : 0)
