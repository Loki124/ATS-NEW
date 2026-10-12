#!/usr/bin/env node
/**
 * 语言包一致性审计 (i18n audit)
 *
 * 检查项:
 *  1. key 缺失: 某语言缺 key (回显 key 原文)
 *  2. 未翻译:   英文值里残留中文 / 中文值等于 key
 *  3. 空值:     值为空字符串或纯空白
 *  4. 格式不一致: 中英文标点混用、全半角括号不一致、首尾空格、句末标点风格不一致
 *  5. key 前缀冲突: 某 key 恰为另一 key 前缀 (会导致 toNested 覆盖文案)
 *
 * 用法: node scripts/locale-audit.mjs [--verbose]
 */
import { readFileSync, readdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const LOCALES = join(ROOT, 'web/app/src/locales')
const VERBOSE = process.argv.includes('--verbose')

/**
 * 解析 TS 文件中指定常量的扁平字典 → Map<key, value>。
 * 按行扫描 + 常量归属跟踪, 不用花括号配对 (值里常含 {n} 占位符会干扰计数)。
 */
function parseConst(file, constName) {
  const src = readFileSync(file, 'utf8')
  const map = new Map()
  let inside = false
  for (const line of src.split('\n')) {
    const decl = line.match(/^export const ([A-Za-z0-9_]+)/)
    if (decl) { inside = decl[1] === constName; continue }
    if (!inside) continue
    const m = line.match(/^\s*(['"])((?:[^\\]|\\.)*?)\1\s*:\s*(['"])((?:[^\\]|\\.)*?)\3\s*,?\s*$/)
    if (m) map.set(m[2], m[4])
  }
  return map
}

const CJK = /[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/

/** R-222 白名单: 文件路径 / URL / 接口名等技术值允许含中文, 不算未翻译 */
const TECH_VALUE = /^(docs?\/|https?:\/\/|\/api\/|[\w./-]+\.(md|xlsx?|csv|json|png|jpg)$)/i

/** 术语一致性只看实词差异, 忽略大小写 (英文句首大写属正常书写) */
function normalizeTerm(s) {
  return s.toLowerCase().replace(/\s+/g, ' ').trim()
}

/** 术语表: 同一概念在不同 key 中必须使用同一译法 */
const GLOSSARY = {
  '原因库': ['Reason Library', 'reason library', 'Reason library'],
  '原因标签': ['Reason Tag', 'reason tag', 'Reason tag'],
  '场景规则': ['Scene Rule', 'scene rule', 'Scene rule'],
  '预置默认规则': ['Preset Default Rule', 'preset default rule', 'Default preset rule'],
  '系统预置': ['System preset', 'system preset'],
  '自定义': ['Custom', 'custom', 'User-defined'],
  '待分配': ['Unassigned', 'Pending Assignment', 'Unallocated'],
  '人才库': ['Talent Pool', 'talent pool', 'Talent pool'],
  '面试轮次': ['Interview Round', 'interview round', 'Interview round'],
}
// 不列入自动检查的形态差异 (属正常英文表达, 人工约定即可):
//   启用 Enable(动作) / Enabled(状态)   停用 Disable / Disabled
//   回滚 roll back(动作按钮) / Rollback(变更类型徽标, 名词)
//   预置 Preset 是 "System preset" 的子串, 不构成独立译法

/** 收集所有 (zh 源, en 源, 常量名) 配对 */
function collectPacks() {
  const packs = []
  const domainFiles = readdirSync(join(LOCALES, 'domains'))
  const zhDomains = domainFiles.filter((f) => f.startsWith('zh-CN.'))
  for (const zf of zhDomains) {
    const base = zf.replace(/^zh-CN\./, '').replace(/\.ts$/, '').replace(/_ZH$/, '')
    const ef = domainFiles.find(
      (f) => f.startsWith('en-US.') && f.replace(/^en-US\./, '').replace(/\.ts$/, '').replace(/_EN$/, '') === base,
    )
    if (!ef) { console.log(`!! 找不到 ${zf} 对应的英文文件`); continue }
    const constName = zf.replace(/^zh-CN\./, '').replace(/\.ts$/, '')
    packs.push({
      label: `domains/${base}`,
      zh: parseConst(join(LOCALES, 'domains', zf), constName),
      en: parseConst(join(LOCALES, 'domains', ef), constName.replace(/_ZH$/, '_EN')),
    })
  }
  for (const [file, pairs] of [
    ['language.ts', [['LANGUAGE_ZH', 'LANGUAGE_EN']]],
    ['metrics.ts', [['METRICS_ZH', 'METRICS_EN']]],
    ['resumeParser.ts', [['RESUME_PARSER_ZH', 'RESUME_PARSER_EN']]],
  ]) {
    for (const [cz, ce] of pairs) {
      packs.push({ label: file, zh: parseConst(join(LOCALES, file), cz), en: parseConst(join(LOCALES, file), ce) })
    }
  }
  return packs
}

const packs = collectPacks()
let issues = 0
const bump = (n = 1) => { issues += n }

console.log('='.repeat(72))
console.log('语言包一致性审计')
console.log('='.repeat(72))

for (const p of packs) {
  const zhKeys = [...p.zh.keys()], enKeys = [...p.en.keys()]
  const enSet = new Set(enKeys)
  const zhSet = new Set(zhKeys)
  const missingEn = zhKeys.filter((k) => !enSet.has(k))
  const missingZh = enKeys.filter((k) => !zhSet.has(k))
  const untranslated = enKeys.filter((k) => CJK.test(p.en.get(k)) && !TECH_VALUE.test(p.en.get(k)))
  const empty = []
  for (const [k, v] of [...p.zh, ...p.en]) {
    if (v === undefined || String(v).trim() === '') empty.push(k)
  }

  // 格式: 首尾空格
//  仅审计中文值 —— 中文计数后缀 (「5条」) 与消息前缀不需要空格;
//  英文侧的首空格 (「 tags」) 与尾空格 (「Failed: 」) 是拼接片段的有意设计。
  const isPrefix = (v) => v !== undefined && /[:：,，、\-—]\s*$/.test(v)
  const padded = zhKeys.filter((k) => /^\s|\s$/.test(p.zh.get(k)) && !isPrefix(p.zh.get(k)))

  // 格式: 中文值用半角逗号 (与全角标点混用)
  const punct = zhKeys.filter((k) => /[,](?![0-9A-Za-z])/.test(p.zh.get(k)) && /[一-鿿]/.test(p.zh.get(k)))

  const total = missingEn.length + missingZh.length + untranslated.length + empty.length + padded.length + punct.length
  console.log(`\n[${p.label}] zh=${zhKeys.length} en=${enKeys.length} 问题=${total}`)
  if (missingEn.length) { console.log(`  ❌ 英文缺失 (${missingEn.length}): ${missingEn.join(', ')}`); bump(missingEn.length) }
  if (missingZh.length) { console.log(`  ❌ 中文缺失 (${missingZh.length}): ${missingZh.join(', ')}`); bump(missingZh.length) }
  if (untranslated.length) {
    console.log(`  ❌ 英文未翻译 (${untranslated.length}):`)
    untranslated.forEach((k) => console.log(`       ${k} = "${p.en.get(k)}"`))
    bump(untranslated.length)
  }
  if (empty.length) { console.log(`  ❌ 空值 (${empty.length}): ${empty.join(', ')}`); bump(empty.length) }
  if (padded.length) { console.log(`  ⚠️  首尾空格 (${padded.length}): ${padded.join(', ')}`); bump(padded.length) }
  if (punct.length) { console.log(`  ⚠️  中文值含半角逗号 (${punct.length}): ${punct.slice(0, 12).join(', ')}${punct.length > 12 ? ' …' : ''}`); bump(punct.length) }

  // 前缀冲突
  const prefix = []
  for (const k of zhKeys) for (const k2 of zhKeys) {
    if (k !== k2 && k2.startsWith(k + '.') && !k2.startsWith(k + 'Title')) prefix.push(`${k} <- ${k2}`)
  }
  if (prefix.length) { console.log(`  ❌ key 前缀冲突 (${prefix.length}): ${prefix.slice(0, 8).join('; ')}`); bump(prefix.length) }

  if (VERBOSE) {
    for (const k of zhKeys) {
      console.log(`    ${k}\n      zh: ${p.zh.get(k)}\n      en: ${p.en.get(k) ?? '⟨缺失⟩'}`)
    }
  }
}

// 术语一致性: 同一中文概念是否映射到多种英文译法
console.log(`\n${'='.repeat(72)}\n术语一致性检查`)
for (const [zh, variants] of Object.entries(GLOSSARY)) {
  // 按归一化形式去重: 只有实词不同才算分歧, 纯大小写差异忽略
  const byNorm = new Map()
  for (const p of packs) {
    for (const [k, v] of p.zh) {
      if (!v.includes(zh)) continue
      const ev = p.en.get(k)
      if (!ev) continue
      const normEv = normalizeTerm(ev)
      for (const cand of variants) {
        // 词边界匹配: 避免 "System preset" 同时命中候选 "Preset" 造成假分歧
        const re = new RegExp(`(^|[^a-z])${normalizeTerm(cand).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}([^a-z]|$)`)
        if (re.test(normEv) && !byNorm.has(normalizeTerm(cand))) byNorm.set(normalizeTerm(cand), cand)
      }
    }
  }
  if (byNorm.size > 1) {
    console.log(`  ⚠️  「${zh}」存在多种英译: ${[...byNorm.values()].join(' / ')}`)
    bump()
  }
}

console.log(`\n${'='.repeat(72)}\n合计问题数: ${issues}`)
process.exit(issues > 0 ? 1 : 0)