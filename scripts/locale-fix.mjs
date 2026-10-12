#!/usr/bin/env node
/**
 * 语言包修复 (幂等)
 *
 * 处理四类问题:
 *  1. 补齐缺失条目   —— 中英双向对齐
 *  2. 修正未翻译     —— 英文包中残留的中文
 *  3. 统一术语       —— 同一概念的多种英译归一
 *  4. 统一格式       —— 值首尾空格、中文语境下的半角标点
 *
 * 用法:
 *   node scripts/locale-fix.mjs --dry-run   # 只报告, 不写文件
 *   node scripts/locale-fix.mjs             # 执行修复
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const L = join(ROOT, 'web/app/src/locales')
const DRY = process.argv.includes('--dry-run')

const F = {
  rlZh: 'domains/zh-CN.REASON_LIBRARY_ZH.ts',
  rlEn: 'domains/en-US.REASON_LIBRARY_EN.ts',
  apZh: 'domains/zh-CN.APP_UI_ZH.ts',
  apEn: 'domains/en-US.APP_UI_EN.ts',
  dpZh: 'domains/zh-CN.DATA_PERM_ZH.ts',
  dpEn: 'domains/en-US.DATA_PERM_EN.ts',
  metrics: 'metrics.ts',
}

// ============ 1. 缺失条目补齐 ============
const ADD = [
  // ---- REASON_LIBRARY 英文缺失 ----
  [F.rlEn, 'reasonLibrary.common.retry', 'Retry'],
  [F.rlEn, 'reasonLibrary.tags.col.code', 'Reason Code'],
  [F.rlEn, 'reasonLibrary.tags.import.templateXlsx', 'Download Import Template (Excel)'],
  [F.rlEn, 'reasonLibrary.tags.import.templateCsv', 'Download CSV Template'],
  [F.rlEn, 'reasonLibrary.tags.import.templateHint', 'Download the template first, fill it in, then upload'],
  [F.rlEn, 'reasonLibrary.wizard.ruleSettings', 'Rule Settings'],
  [F.rlEn, 'reasonLibrary.wizard.configRule.entryWithType', 'Recruit Type (Campus / Social)'],
  [F.rlEn, 'reasonLibrary.wizard.configRule.entryWithTypeHint',
    'The two cards are independent: select every applicable scene inside the "Campus" and "Social" cards, and the two entry types never affect each other.'],
  [F.rlEn, 'reasonLibrary.wizard.configRule.pairBlockedToast',
    '"{type} · {scene}" is already used by "{rule}". Remove this combination from the other rule first.'],
  [F.rlEn, 'reasonLibrary.wizard.maxSelectableTags', 'Max Selectable Reasons'],
  [F.rlEn, 'reasonLibrary.wizard.maxSelectableTagsPlaceholder', 'Enter 0 for no limit'],
  [F.rlEn, 'reasonLibrary.wizard.maxSelectableTagsHint',
    '0 means no limit; users can select at most this many reason tags in the business dialog.'],
  [F.rlEn, 'reasonLibrary.wizard.configRule.typeOccupied', 'In Use'],
  [F.rlEn, 'reasonLibrary.wizard.configRule.scopeSummary', 'Applicable Scope'],
  [F.rlEn, 'reasonLibrary.wizard.configRule.scopeEmpty', 'Select at least one entry and type'],
  [F.rlEn, 'reasonLibrary.wizard.configRule.sceneBlockedToast',
    '"{type} · {scene}" is already used by "{rule}". Remove this type first or choose another scene.'],
  [F.rlEn, 'reasonLibrary.wizard.tagPicker.onlyAvailable', 'Available Only'],
  [F.rlEn, 'reasonLibrary.wizard.cat.moveUp', 'Move Up'],
  [F.rlEn, 'reasonLibrary.wizard.cat.moveDown', 'Move Down'],
  [F.rlEn, 'reasonLibrary.wizard.cat.addChild', 'Add Subcategory'],
  [F.rlEn, 'reasonLibrary.wizard.cat.remove', 'Delete Category'],
  [F.rlEn, 'reasonLibrary.wizard.cat.expand', 'Expand / Collapse Subcategories'],
  [F.rlEn, 'reasonLibrary.wizard.preview.colorModeInherit', 'Inherit'],

  // ---- APP_UI 英文缺失 (RecruitmentProcess) ----
  [F.apEn, 'pages.settings.RecruitmentProcess.s4', 'Create Process'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s5', 'Process Code'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s6', 'Process Name'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s7', 'Applicable Departments'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s8', 'Stage Count'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s9', 'Status'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s10', 'Enabled'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s11', 'Disabled'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s12', 'Last Modified By'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s13', 'Last Modified At'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s14', 'Actions'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s15', 'Edit'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s16', 'Delete'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s17', 'Preset template processes cannot be deleted'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s18', 'Referenced by {count} requisition(s) and cannot be deleted'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s19', 'Delete this process?'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s20', 'All'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s22', '+{count} more'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s23', 'Failed to load'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s24', 'Process "{name}" deleted'],
  [F.apEn, 'pages.settings.RecruitmentProcess.s25', 'Failed to delete'],

  // ---- DATA_PERM 英文缺失 ----
  [F.dpEn, 'pages.settings.stage-rule.cards.InterviewConfigCard.s5',
    'No interview rounds available. Configure and enable them in "Interview Round Management" first'],

  // ---- DATA_PERM 中文缺失 (英文包独有的角色/示例人名) ----
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s6', '用人经理'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s7', '用人经理的上级'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s8', '总裁'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s9', '用人经理'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s10', '用人经理的上级'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s11', '总裁'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s12', '刘星星'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s13', '张三'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s14', '李四'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s15', '王五'],
  [F.dpZh, 'pages.settings.stage-rule.cards.DefaultHandlerCard.s16', '赵六'],

  // ---- metrics 英文缺失 ----
  [F.metrics, 'metrics.tpl.paramConfigUnit', '参数配置单位', 'zh'],
  [F.metrics, 'metrics.tpl.paramConfigUnitPlaceholder', '沿用指标单位', 'zh'],
  [F.metrics, 'metrics.tpl.previewTitle', '配置预览', 'zh'],
  [F.metrics, 'metrics.tpl.previewHint', '以下为该模板在规则条件中的呈现效果', 'zh'],
  [F.metrics, 'metrics.tpl.previewCheckValue', '校验值', 'zh'],
  [F.metrics, 'metrics.tpl.previewMetricItem', '指标项', 'zh'],
  [F.metrics, 'metrics.tpl.unnamed', '（未命名模板）', 'zh'],
  [F.metrics, 'metrics.tpl.previewNoDomain', '请先添加值域分段', 'zh'],
  [F.metrics, 'metrics.tpl.paramConfigUnit', 'Parameter Unit', 'en'],
  [F.metrics, 'metrics.tpl.paramConfigUnitPlaceholder', 'Use the metric unit', 'en'],
  [F.metrics, 'metrics.tpl.previewTitle', 'Configuration Preview', 'en'],
  [F.metrics, 'metrics.tpl.previewHint', 'How this template appears in rule conditions', 'en'],
  [F.metrics, 'metrics.tpl.previewCheckValue', 'Validation Value', 'en'],
  [F.metrics, 'metrics.tpl.previewMetricItem', 'Metric Item', 'en'],
  [F.metrics, 'metrics.tpl.unnamed', '(Unnamed Template)', 'en'],
  [F.metrics, 'metrics.tpl.previewNoDomain', 'Add value ranges first', 'en'],
]

// ============ 2. 英文包中残留中文 → 修正 ============
const RETRANS = [
  // 空值修复: 原 en 为空字符串, 渲染成 "导入成功 5 " 缺宾语
  [F.rlEn, 'reasonLibrary.common.item', 'items'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s214', 'Module Settings'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s215', 'Group Settings'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s216', 'Interaction Rules'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s217', 'Create Field'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s218', 'Add Field'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s219', 'Create Module'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s220', 'Create Group'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s221', 'Create Rule'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s222', 'Add Condition'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s223', 'Add Action'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s224', 'Locked (Core)'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s225', 'System Built-in'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s226', 'Custom'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s227', 'Manage Permissions'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s228', 'Edit'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s229', 'Delete'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s230', 'Enabled'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s231', 'Disabled'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s232', 'Edit'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s233', 'Delete'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s234', 'Enabled'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s235', 'Disabled'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s236', 'Edit'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s237', 'Delete'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s238', 'Enabled'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s239', 'Disabled'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s240', 'Edit'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s241', 'Delete'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s266', '", please select a subtype to continue'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s273', 'Format must be YYYY-MM-DD or T/T±N (e.g. T+3, T-3)'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s285', 'Export JSON'],
  [F.dpEn, 'pages.settings.DynamicFieldManager.s286', 'Export CSV'],
  // 术语统一: 「待分配」全库统一译为 Unassigned
  [F.dpEn, 'pages.candidate.addCandidate.Step2Assign.s22',
    'There are {n} resumes already occupied; only "Unassigned" can be selected.'],
  [F.dpEn, 'pages.candidate.addCandidate.AsyncResult.s8',
    'Will appear under "Unassigned"; you can handle or reassign it manually.'],
  [F.dpEn, 'pages.resume.ResumeList.s1', 'Unassigned'], // 原 "Pending Assignment"
]

// ============ 3. 术语统一 ============
const TERMS = [
  ['Pending Assignment', 'Unassigned'],
]

// ============ 执行 ============
const stats = { added: 0, retrans: 0, terms: 0, padded: 0, punct: 0 }
const cache = new Map()

// 预加载所有待规范化的文件 (否则格式步骤只会处理到「恰好被改动过」的文件)
for (const rel of new Set([...Object.values(F)])) load(rel)

function load(rel) {
  if (!cache.has(rel)) cache.set(rel, readFileSync(join(L, rel), 'utf8'))
  return cache.get(rel)
}
function save() {
  for (const [rel, src] of cache) {
    if (!DRY) writeFileSync(join(L, rel), src)
  }
}

/** 在指定 key 行之后插入新条目 (沿用该文件的引号风格与缩进) */
function insertAfter(file, anchorKey, key, value, constHint) {
  const src = load(file)
  const lines = src.split('\n')
  // 双常量文件 (metrics.ts): 只在该常量声明之后定位, 避免命中另一个语言段落的同名 key
  let from = 0
  if (constHint) {
    const decl = lines.findIndex((l) => new RegExp(`^export const ${constHint}\\b`).test(l))
    if (decl < 0) { console.error(`  ⚠️  找不到常量 ${constHint} @ ${file}`); return false }
    from = decl
  }
  // 幂等检查同样限定在该常量块内
  for (let i = from; i < lines.length; i++) {
    if (lines[i].includes(`'${key}':`) || lines[i].includes(`"${key}":`)) return false
  }
  let anchorIdx = -1
  for (let i = from; i < lines.length; i++) {
    if (lines[i].includes(`'${anchorKey}':`) || lines[i].includes(`"${anchorKey}":`)) { anchorIdx = i; break }
  }
  if (anchorIdx < 0) { console.error(`  ⚠️  找不到锚点 ${anchorKey} @ ${file}`); return false }
  // 推断风格: 锚点行用双引号值 → 新条目也用双引号
  const dq = /:\s*"/.test(lines[anchorIdx])
  const indent = (lines[anchorIdx].match(/^\s*/) || [''])[0]
  const kq = dq ? `"${key}"` : `'${key}'`
  const vq = dq ? `"${escapeDq(value)}"` : `'${escapeSq(value)}'`
  lines.splice(anchorIdx + 1, 0, `${indent}${kq}: ${vq},`)
  cache.set(file, lines.join('\n'))
  return true
}

/** 替换指定 key 的值 */
function replaceValue(file, key, value) {
  const src = load(file)
  const lines = src.split('\n')
  let hit = false
  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].includes(`'${key}':`) && !lines[i].includes(`"${key}":`)) continue
    const dq = /:\s*"/.test(lines[i])
    const indent = (lines[i].match(/^\s*/) || [''])[0]
    const kq = /^\s*"/.test(lines[i]) ? `"${key}"` : `'${key}'`
    const vq = dq ? `"${escapeDq(value)}"` : `'${escapeSq(value)}'`
    lines[i] = `${indent}${kq}: ${vq},`
    hit = true
    break
  }
  if (hit) cache.set(file, lines.join('\n'))
  return hit
}

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const escapeSq = (s) => s.replace(/\\/g, '\\\\').replace(/'/g, "\\'")
const escapeDq = (s) => s.replace(/\\/g, '\\\\').replace(/"/g, '\\"')

console.log(DRY ? '【试运行】不写入文件\n' : '【执行中】\n')

// --- 补齐缺失 ---
const anchors = {
  [F.rlEn]: 'reasonLibrary.common.refresh',
  [F.apEn]: 'pages.settings.RecruitmentProcess.s3',
  [F.dpEn]: 'pages.settings.stage-rule.cards.InterviewConfigCard.s4',
  [F.dpZh]: 'pages.settings.stage-rule.cards.DefaultHandlerCard.s5',
}
for (const [file, key, value, lang] of ADD) {
  if (lang === 'zh' || lang === 'en') {
    // metrics.ts 单文件双常量: 缺失则插入到对应常量块内
    const constName = lang === 'zh' ? 'METRICS_ZH' : 'METRICS_EN'
    if (insertAfter(file, 'metrics.tpl.sectionDomain', key, value, constName)) stats.added++
    else if (load(file).includes(`'${key}':`) || load(file).includes(`"${key}":`)) stats.added++ // 幂等
    else console.error(`  ⚠️  metrics 插入失败: ${key}`)
    continue
  }
  if (insertAfter(file, anchors[file] || key, key, value)) stats.added++
  else if (!load(file).includes(`'${key}':`) && !load(file).includes(`"${key}":`)) {
    console.error(`  ⚠️  插入失败: ${file} ${key}`)
  } else stats.added++ // 已存在, 幂等
}
console.log(`① 补齐条目: ${stats.added} 条`)

// --- 修正未翻译 ---
for (const [file, key, value] of RETRANS) {
  if (replaceValue(file, key, value)) stats.retrans++
}
console.log(`② 修正未翻译: ${stats.retrans} 条`)

// --- 术语统一 ---
for (const [rel, src] of [...cache]) {
  let out = src
  for (const [from, to] of TERMS) {
    const re = new RegExp(`(:\\s*['"])([^'"]*?)\\b${escapeRe(from)}\\b([^'"]*?)(['"])`, 'g')
    out = out.replace(re, (m, a, pre, post, d) => {
      if (!new RegExp(`['"]${escapeRe(to)}\\b`).test(m)) stats.terms++
      return `${a}${pre}${to}${post}${d}`
    })
  }
  if (out !== src) cache.set(rel, out)
}
console.log(`③ 术语统一: ${stats.terms} 处`)

// --- 格式统一 ---
// 注意: 仅处理「值内含中文」的行。英文文案尾部的空格多为消息前缀片段
// (如 "Failed to load company: " 需拼接后续错误详情), 属有意为之, 不得裁剪。
const CJK = /[\u4e00-\u9fff]/
const isPrefixFragment = (v) => /[:：,，、\-—]\s*$/.test(v)
const ZH_FILES = new Set([F.rlZh, F.apZh, F.dpZh, F.dpEn, F.apEn, F.rlEn, F.metrics])
for (const [rel, src] of [...cache]) {
  if (!ZH_FILES.has(rel)) continue
  const out = src.split('\n').map((line) => {
    const m = line.match(/^(\s*(?:'[^']*'|"[^"]*"):\s*)(['"])(.*)\2(,?\s*)$/)
    if (!m) return line
    let v = m[3]
    if (!CJK.test(v)) return line          // 纯英文值不动
    const before = v
    const trimmed = v.trim()
    // 前缀型文案保留尾部空格 (供后续拼接), 其余去首尾空格
    v = isPrefixFragment(trimmed) ? trimmed : trimmed
    // 中文语境下的半角标点 → 全角
    // 逗号: 紧邻中文任一侧即转换 (覆盖 "值 (JSON), 类型" 这类右括号后接中文的情形)
    // 问号: 前一个字符是中文时转换。避免动到 T+3、a,b 这类纯英文语境
    v = v.replace(/([一-鿿]),\s*(?=[一-鿿])/g, '$1，')
    v = v.replace(/([)\]）]),\s*(?=[一-鿿])/g, '$1，')
    v = v.replace(/([一-鿿])\?/g, '$1？')
    if (v !== before) {
      if (before !== before.trim() && !isPrefixFragment(before.trim())) stats.padded++
      if (/[一-鿿][,?]/.test(before)) stats.punct++
      return `${m[1]}${m[2]}${v}${m[2]}${m[4]}`
    }
    return line
  }).join('\n')
  if (out !== src) cache.set(rel, out)
}
console.log(`④ 格式统一: 去首尾空格 ${stats.padded} 处, 半角标点转全角 ${stats.punct} 处`)

save()
console.log(DRY ? '\n试运行结束（未写文件）' : '\n修复完成')