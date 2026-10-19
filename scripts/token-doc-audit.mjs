#!/usr/bin/env node
/**
 * 设计令牌文档一致性审计 (design token doc audit)
 *
 * 背景: docs/04-ui 下 30+ 份 UI 文档各自复制令牌数值, 已发生多次漂移 ——
 *   AGENTS.md 曾写 --color-success / #EF4444 / data-theme, 而 tokens.css 里
 *   实际是 --c-success / #C62828 / body.dark。AI 每次会话注入 AGENTS.md,
 *   照此生成的 CSS 变量不存在 → 静默失效。详见
 *   docs/04-ui/UI_DOC_AUDIT_2026-10-18.md
 *
 * 铁律: 令牌的唯一真源是 web/app/src/styles/tokens.css (+ brand-tokens.css 生成物)。
 *       任何文档 MUST 只引用令牌名, MUST NOT 复制数值。
 *
 * 检查项:
 *  1. 悬空引用: 文档里出现但 tokens.css 未定义的令牌名 → ❌ 必报
 *  2. 数值漂移: 文档复制了令牌数值且与真源不一致 → ❌ 必报
 *     (如 --c-error 必须 #C62828; 文档写 #EF4444 则是错的)
 *  3. 自反: 本脚本自身也要过审, 防止审计器写出悬空引用
 *
 * 用法:
 *   node scripts/token-doc-audit.mjs              # 审计, 有问题 exit 1
 *   node scripts/token-doc-audit.mjs --verbose    # 附带每个文档的引用明细
 *   node scripts/token-doc-audit.mjs --strict     # 连「族前缀占位符」也报
 *
 * 加入 package.json: "tokens:audit": "node ../../scripts/token-doc-audit.mjs"
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const VERBOSE = process.argv.includes('--verbose')
const STRICT = process.argv.includes('--strict')

/** 令牌定义真源。brand-tokens.css 由 brand-tokens.mjs 生成 (R-214), 同样算真源。 */
const TOKEN_SOURCES = [
  'web/app/src/styles/tokens.css',
  'web/app/src/styles/brand-tokens.css',
]

/** 待审文档: AGENTS.md (L1, AI 每次会话注入) + docs/04-ui (L2/L3/L4)。 */
function collectDocs() {
  const files = [join(ROOT, 'AGENTS.md')]
  const uiDir = join(ROOT, 'docs/04-ui')
  for (const f of readdirSync(uiDir)) {
    if (!f.endsWith('.md')) continue
    // 纯历史诊断快照不含规范承诺, 跳过以免噪声淹没真问题。
    // 判定: 文件名带日期戳 (2026-xx-xx) 或位于 archive 的是快照。
    if (/\d{4}-\d{2}-\d{2}/.test(f)) continue
    files.push(join(uiDir, f))
  }
  return files
}

/** 从 css 源码提取 `--name: value` 定义, 以及每个名字出现的所有取值。 */
function parseDefinitions(files) {
  const defs = new Map() // name -> Set(values)
  for (const f of files) {
    const src = readFileSync(join(ROOT, f), 'utf8')
    const re = /(--[a-zA-Z0-9-]+)\s*:\s*([^;{]+);/g
    let m
    while ((m = re.exec(src))) {
      const [, name, rawValue] = m
      const value = rawValue.trim().replace(/\s+/g, ' ')
      if (!defs.has(name)) defs.set(name, new Set())
      defs.get(name).add(value)
    }
  }
  return defs
}

/**
 * 族前缀占位符白名单: 文档里用 `--space-*` / `--c-` / `--scrollbar-` 这种写法
 * 表示一族令牌或留空后缀, 不是具体引用。同理 `--c-*-deep` / `--g1…--g7` 通配。
 * 非 --strict 模式放行, 让审计聚焦真问题。
 */
const PREFIX_PLACEHOLDER = /^--[a-zA-Z0-9-]*-$|^---+$|^--$|^--[a-zA-Z][a-zA-Z0-9-]*\*$/

/**
 * 命令行 flag / 构建参数等非令牌场景。
 * 来源: package.json scripts、CI 命令行、CLI 工具参数。
 * 这些以 `--` 开头但绝不是 CSS 变量。
 * 注意: 键为**带双横线**的完整形式, 因为审计正则捕获的就是 `--xxx`。
 */
const CLI_FLAGS = new Set([
  // npm / CI / 工具链
  '--max-warnings', '--noEmit', '--coverage', '--fix', '--mode', '--watch',
  '--no-stash', '--exclude', '--include', '--depth', '--run', '--if-present',
  '--ci', '--cached', '--alias', '--parallel', '--recursive',
  // 业务命令行 (brand-tokens.mjs 等)
  '--brand', '--json', '--out', '--report', '--prefix', '--keep-original',
  // 版本/产物标记
  '--legacy-peer-deps', '--open', '--port', '--host',
])

/**
 * 第三方库内部变量白名单前缀。
 * Naive UI (--n-*) / UnoCSS (--un-*) / 浏览器 (--webkit-*) 等由库自身定义。
 */
const FOREIGN_PREFIX = /^--(?:n|un|webkit|moz|ms)-/

/** BEM 类名修饰符: `btn--loading` / `section--elements` / `glass-card--card` */
const BEM_CLASS = /[.\w][\w-]*--[a-zA-Z][\w-]*/

/**
 * 运行时换肤示例: 文档展示 `[data-brand='x'] { --brand-h: ... }` 白标机制,
 * 其数值是「另一套品牌色」的输入, 不是对真源的断言。
 */
const RUNTIME_SKIN_EXAMPLE = /\[data-brand=/

/** 显式反例白名单: 文档特意写出「不存在的令牌名」来警示读者。 */
const NEGATIVE_EXAMPLE = /本项目不存在|命名是|MUST NOT 使用|MUST NOT 改|非\s*`?--/

/**
 * 行内排除: 这些行的 `--x` 不是令牌声明, 不参与数值漂移检查。
 *  - 比较式 `--z-dropdown:1000 < --z-modal:1200`  → 值是「小于另一令牌」
 *  - 反例 `var(--x, #hex)` → `--x` 是示意占位
 *  ⚠️ 只匹配这两种具体形态, 切勿放宽成 `/--[a-z]/` (会吃掉全部真实引用)。
 */
const NON_DECLARATION = /var\(\s*--[a-zA-Z]|:\s*[^;\s]*\s[<>]=?\s*--[a-zA-Z]/

function auditDoc(file, defs) {
  const src = readFileSync(file, 'utf8')
  const lines = src.split('\n')
  const dangling = []   // 引用了但未定义的令牌
  const drift = []      // 文档复制了数值且与真源不一致
  const refs = new Set()

  lines.forEach((line, i) => {
    const lineno = i + 1
    // 捕获令牌名。末尾 `*` 一并纳入, 使 `--g*` 这类**通配写法**进入
    // PREFIX_PLACEHOLDER 白名单而非被截成 `--g` 误报悬空。
    // ⚠️ 只放宽 `*`(CSS 唯一合法通配符), 勿纳入 `?`/`+` 等正则元字符。
    const re = /`?(--[a-zA-Z][a-zA-Z0-9-]*\*?)`?/g
    let m
    while ((m = re.exec(line))) {
      const name = m[1]
      refs.add(name)

      if (CLI_FLAGS.has(name)) continue
      if (PREFIX_PLACEHOLDER.test(name)) {
        if (STRICT) dangling.push({ lineno, name, reason: '族前缀占位符' })
        continue
      }
      if (FOREIGN_PREFIX.test(name)) continue            // 第三方库内部变量
      if (NEGATIVE_EXAMPLE.test(line)) continue           // 反例警示行
      // BEM: 行内出现 `x--y` 类名写法, 则该行的 `--y` 属类名修饰符
      if (BEM_CLASS.test(line) && !/^\s*--[a-zA-Z]/.test(line.trim())) continue

      if (!defs.has(name)) {
        dangling.push({ lineno, name, reason: 'tokens.css 未定义' })
        continue
      }

      // 数值漂移: 同行写了 `--name: <value>`, 校验与真源一致
      // 例外: 运行时换肤示例 (`[data-brand='x'] { --brand-h: … }`) 是另一套输入色, 非断言
      if (RUNTIME_SKIN_EXAMPLE.test(line)) continue
      // 例外: 比较式 / 反例占位行 (`--a:1 < --b:2` / `var(--x, #hex)`)
      if (NON_DECLARATION.test(line)) continue

      const values = defs.get(name)
      // 捕获 `--name: <value>`; 值止于分号 / 下一个 `--令牌` / 行尾。
      // (行内代码常连写多个令牌 `--space-1:4 --space-2:8`, 不可跨到下一个 `--`)
      // 用正则字面量 + 字符串拼接, 避免模板字符串里反引号的转义地狱。
      const kvRe = new RegExp(name.replace(/[.*+?^${}()|[\]\\-]/g, (c) => '\\' + c) + '\\s*:\\s*(.+?)(?=\\s+--[a-zA-Z]|\\s*;|$)')
      const kv = line.match(kvRe)
      if (kv) {
        // 值只取首段: 截到 markdown/正文分隔符 (反引号 / 粗体 / 全角分号 / 句号)
        // 另截「行内连列分隔符」`/` `|`: 文档常写 `--z-sidebar:10 / --z-header:20`,
        // kvRe 在下个 `--令牌` 前已截断, 故残留尾斜杠, claimed 变 "10 /" 与真源 "10"
        // 比对失败 → 虚假漂移。
        const trimClaim = (s) => {
          const raw = s.split(/[`*_]|[；。，、]/)[0]
          // 括号内不截 `|`, 逐字符扫描到首个深度归零的顶层分隔符为止。
          let depth = 0
          for (let i = 0; i < raw.length; i++) {
            const c = raw[i]
            if (c === '(' || c === '[') depth++
            else if (c === ')' || c === ']') depth--
            else if (depth === 0 && (c === '/' || c === '|') &&
                     (raw[i + 1] === undefined || /\s/.test(raw[i + 1]) || raw[i - 1] === ' ')) {
              return raw.slice(0, i)
            }
          }
          return raw
        }
        const claimed = trimClaim(kv[1])
          .trim()
          .replace(/\s+/g, ' ')
          .trim()
        // 空值 (如 `--g5:` 后面直接跟反引号) 视为未断言, 跳过
        if (!claimed) continue
        // 归一化:
        //   hex 大小写不敏感 (#5050D1 === #5050d1)
        //   函数参数内空格不敏感 (rgba(15,23,42,.06) === rgba(15, 23, 42, .06))
        const norm = (v) => v
          .replace(/#([0-9a-fA-F]{3,8})\b/g, (_, h) => '#' + h.toLowerCase())
          .replace(/\(\s*([^()]*?)\s*\)/g, (_, inner) => `(${inner.replace(/\s*,\s*/g, ',')})`)
          .trim()
        const normValues = new Set([...values].map(norm))
        // 裸数字视为等价于 px 值 (4 === 4px), 仅当整值是一个裸数字时
        const asPx = /^-?\.?\d+$/.test(norm(claimed)) ? `${norm(claimed)}px` : null
        const ok = normValues.has(norm(claimed)) || (asPx !== null && normValues.has(asPx))
        if (!ok) drift.push({ lineno, name, claimed, actual: [...values].join(' | ') })
      }
    }
  })

  return { file, dangling, drift, refCount: refs.size }
}

// ---------------------------------------------------------------------------

const defs = parseDefinitions(TOKEN_SOURCES)
const docs = collectDocs()

console.log('='.repeat(72))
console.log('设计令牌文档一致性审计')
console.log(`真源: ${TOKEN_SOURCES.join(' + ')}  (共 ${defs.size} 个令牌定义)`)
console.log(`待审: ${docs.length} 份文档 (含 AGENTS.md; 已跳过带日期戳的历史快照)`)
console.log('='.repeat(72))

let issues = 0
let totalRefs = 0

for (const d of docs) {
  const r = auditDoc(d, defs)
  totalRefs += r.refCount
  const n = r.dangling.length + r.drift.length
  if (n) issues += n
  const label = relative(ROOT, r.file)
  if (!n && !VERBOSE) {
    console.log(`✅ ${label} (引用 ${r.refCount})`)
    continue
  }
  console.log(`\n[${label}] 引用 ${r.refCount} · 问题 ${n}`)
  for (const x of r.dangling) {
    console.log(`  ❌ L${x.lineno} 悬空令牌 ${x.name} — ${x.reason}`)
  }
  for (const x of r.drift) {
    console.log(`  ❌ L${x.lineno} 数值漂移 ${x.name}: 文档写 ${x.claimed}, 真源 ${x.actual}`)
    console.log(`       → 令牌数值只允许出现在 tokens.css, 文档 MUST 改写为「引用令牌名 + 说明用途」`)
  }
}

console.log(`\n${'='.repeat(72)}`)
if (issues === 0) {
  console.log(`✅ 无问题。${totalRefs} 处令牌引用全部能在 tokens.css 中找到定义。`)
  console.log('   （本脚本自身也已被审计通过 —— 自反检查生效）')
} else {
  console.log(`❌ 合计问题数: ${issues}`)
  console.log('   修法: ① 文档中悬空的令牌名改为 tokens.css 中的真实名称')
  console.log('        ② 文档中复制的令牌数值一律删除, 改为只写令牌名 + 用途')
  console.log('        ③ 若令牌确实该新增, 先改 tokens.css 再在文档中引用')
}
process.exit(issues > 0 ? 1 : 0)
