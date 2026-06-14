/**
 * 纯 JS PDF 生成器 - PRD C5 (Offer PDF 服务端生成)
 *
 * 特点:
 *  - 零依赖 (不需要 pdfkit / puppeteer / wkhtmltopdf)
 *  - 自动中文字体嵌入 (Todo #6): 检测到非 ASCII 字符时, 从系统加载 CJK 字体并子集化嵌入
 *  - 适合简单文本型 PDF (Offer 模板)
 *
 * 实现: PDF 1.4 规范, 14 个内置字体 (Helvetica) 或 Type0 CID 字体 (CJK), 文本按行布局, 自动分页
 * 局限: 不支持复杂排版 (表格/图片) — Phase 3 可换 pdfkit
 *
 * 用法:
 *   const pdf = generateSimplePdf({ title: 'Offer Letter', lines: [...] })
 *   res.setHeader('Content-Type', 'application/pdf')
 *   res.send(pdf)
 */

import { loadCjkFont, buildCjkFontObjects, encodeTextAsCid } from './cjk-font-embed.js'

const PAGE_WIDTH = 595 // A4 in points
const PAGE_HEIGHT = 842
const MARGIN = 50
const LINE_HEIGHT = 16
const FONT_SIZE = 11

/**
 * 检测文本是否包含 CJK 字符
 */
function hasCjk(text) {
  return /[^\x00-\x7F]/.test(text)
}

/**
 * 生成简单 PDF (返回 Buffer)
 * @param {object} options
 * @param {string} options.title
 * @param {string[]} options.lines - 行内容
 * @param {string} [options.author='ATS System']
 * @returns {Buffer}
 */
export function generateSimplePdf({ title = 'Document', lines = [], author = 'ATS System' } = {}) {
  // 1. 决定字体策略: 含 CJK -> 尝试加载系统字体
  const allText = title + '\n' + (lines || []).join('\n')
  const useCjk = hasCjk(allText)
  const font = useCjk ? loadCjkFont() : null

  // 2. PDF 对象集合
  const objects = []

  // 3. 分页: 每页最多 (PAGE_HEIGHT - 2*MARGIN) / LINE_HEIGHT 行
  const maxLinesPerPage = Math.floor((PAGE_HEIGHT - 2 * MARGIN) / LINE_HEIGHT)
  const pages = []
  for (let i = 0; i < lines.length; i += maxLinesPerPage) {
    pages.push(lines.slice(i, i + maxLinesPerPage))
  }
  if (pages.length === 0) pages.push([])

  // 4. 准备 CJK 字体对象 (如有)
  let cjkFontInfo = null
  if (font) {
    try {
      cjkFontInfo = buildCjkFontObjects(font, allText)
    } catch (err) {
      console.warn(`[pdf-cjk] subsetting failed: ${err.message}; falling back to Helvetica`)
      cjkFontInfo = null
    }
  }

  // 5. 构造每个 page 的 content stream
  const pageObjNums = []
  const contentObjNums = []
  for (let p = 0; p < pages.length; p++) {
    const pageLines = pages[p]
    let content = 'BT\n'
    content += `/F1 ${FONT_SIZE} Tf\n`
    content += `${MARGIN} ${PAGE_HEIGHT - MARGIN} Td\n`
    for (let i = 0; i < pageLines.length; i++) {
      const text = sanitizeForPdf(pageLines[i])
      if (cjkFontInfo) {
        // Type0 字体: 用 hex string 编码 CID
        const hex = encodeTextAsCid(text)
        content += `<${hex}> Tj\n`
      } else {
        content += `(${escapePdfString(text)}) Tj\n`
      }
      content += `0 -${LINE_HEIGHT} Td\n`
    }
    content += 'ET\n'
    content += `%%EOF_PAGE_${p}`

    objects.push(buildStreamObject(content))
    contentObjNums.push(objects.length) // 1-based
    objects.push(null) // placeholder for page obj
    pageObjNums.push(objects.length)
  }

  // 6. 字体对象
  let fontRefObjNum
  // streamMap: 对象编号 (1-based) -> 二进制流 Buffer
  const streamMap = new Map()
  if (cjkFontInfo) {
    // 插入 CJK 字体对象 (5 个对象), 记下 Type0 对象的最终编号
    const baseOffset = objects.length // push 前的 objects 长度
    // 5 个对象按顺序 push, 最终 1-based 编号 = baseOffset + idx + 1
    // 我们需要把 __XXX_REF__ 占位符替换成真实引用
    const fontObjects = cjkFontInfo.fontObjects.map((s, idx) => {
      let result = s
      result = result.replace('__CIDTOGIDMAP_REF__', `${baseOffset + cjkFontInfo.placeholderMap.cidToGid + 1} 0 R`)
      result = result.replace('__CIDFONT_REF__', `${baseOffset + cjkFontInfo.placeholderMap.cidFont + 1} 0 R`)
      result = result.replace('__FONTFILE_REF__', `${baseOffset + cjkFontInfo.placeholderMap.fontFile + 1} 0 R`)
      result = result.replace('__FONTDESC_REF__', `${baseOffset + cjkFontInfo.placeholderMap.fontDesc + 1} 0 R`)
      return result
    })
    for (let i = 0; i < fontObjects.length; i++) {
      objects.push(fontObjects[i])
    }
    // stream 对象: cidToGid stream, fontFile2 stream
    const cidToGidObjNum = baseOffset + cjkFontInfo.placeholderMap.cidToGid + 1
    const fontFileObjNum = baseOffset + cjkFontInfo.placeholderMap.fontFile + 1
    streamMap.set(cidToGidObjNum, cjkFontInfo.fontStreams[0]) // CIDToGIDMap
    streamMap.set(fontFileObjNum, cjkFontInfo.fontStreams[1]) // FontFile2
    fontRefObjNum = baseOffset + cjkFontInfo.placeholderMap.type0 + 1
  } else {
    // Helvetica fallback
    objects.push(`<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>`)
    fontRefObjNum = objects.length
  }

  // 7. Pages object
  const pagesObjIndex = objects.length
  const pagesObj = `<< /Type /Pages /Count ${pages.length} /Kids [${pageObjNums.map(n => `${n} 0 R`).join(' ')}] >>`
  objects.push(pagesObj)

  // 8. Page objects (替换 placeholder)
  for (let i = 0; i < pageObjNums.length; i++) {
    const pageNum = pageObjNums[i] // 1-based
    const contentNum = contentObjNums[i] // 1-based
    objects[pageNum - 1] = `<< /Type /Page /Parent ${pagesObjIndex + 1} 0 R /MediaBox [0 0 ${PAGE_WIDTH} ${PAGE_HEIGHT}] /Contents ${contentNum} 0 R /Resources << /Font << /F1 ${fontRefObjNum} 0 R >> >> >>`
  }

  // 9. Catalog
  const catalogObj = `<< /Type /Catalog /Pages ${pagesObjIndex + 1} 0 R >>`
  objects.push(catalogObj)

  // 10. Info
  const now = new Date()
  const dateStr = `D:${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
  const infoObj = `<< /Title (${escapePdfString(title)}) /Producer (ATS Backend Pure-JS PDF Generator) /Creator (${escapePdfString(author)}) /CreationDate (${dateStr}) >>`
  objects.push(infoObj)

  // 11. 序列化 PDF (含二进制流)
  return serializePdfWithStreams(objects, streamMap)
}

function buildStreamObject(content) {
  const length = Buffer.byteLength(content, 'utf8')
  return `<< /Length ${length} >>`
}

/**
 * 清理 PDF 文本: 保留原文 (CJK 字体自己处理编码)
 */
function sanitizeForPdf(text) {
  if (typeof text !== 'string') return String(text)
  return text
}

/**
 * 转义 PDF literal string 中的特殊字符 ( ) \
 */
function escapePdfString(s) {
  return s.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)')
}

/**
 * 序列化对象数组为 PDF Buffer (支持二进制流)
 *
 * @param {string[]} objects - 对象字典字符串数组
 * @param {Map<number, Buffer>} streamMap - 对象编号 (1-based) → 二进制流 Buffer
 */
function serializePdfWithStreams(objects, streamMap = new Map()) {
  const chunks = []
  chunks.push(Buffer.from('%PDF-1.4\n', 'latin1'))
  // 二进制标记: 4 个高位字节
  chunks.push(Buffer.from([0x25, 0xe2, 0xe3, 0xcf, 0xd3, 0x0a]))

  const offsets = []
  for (let i = 0; i < objects.length; i++) {
    offsets.push(chunks.reduce((sum, c) => sum + c.length, 0))
    const objNum = i + 1
    const objStr = objects[i]
    const stream = streamMap.get(objNum)
    if (stream) {
      chunks.push(Buffer.from(`${objNum} 0 obj\n${objStr}\nstream\n`, 'utf8'))
      chunks.push(stream)
      chunks.push(Buffer.from(`\nendstream\nendobj\n`, 'utf8'))
    } else {
      chunks.push(Buffer.from(`${objNum} 0 obj\n${objStr}\nendobj\n`, 'utf8'))
    }
  }

  const xrefStart = chunks.reduce((sum, c) => sum + c.length, 0)
  let xref = `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  for (const offset of offsets) {
    xref += `${String(offset).padStart(10, '0')} 00000 n \n`
  }
  chunks.push(Buffer.from(xref, 'utf8'))

  const trailer = `trailer\n<< /Size ${objects.length + 1} /Root ${objects.length} 0 R /Info ${objects.length - 1} 0 R >>\nstartxref\n${xrefStart}\n%%EOF\n`
  chunks.push(Buffer.from(trailer, 'utf8'))

  return Buffer.concat(chunks)
}

/**
 * 从 Offer context (扁平对象) 生成 PDF lines
 * 适合 G24 模板的纯文本布局版本
 */
export function offerContextToLines(context) {
  const lines = []
  lines.push('录用意向书 / Offer Letter')
  lines.push('='.repeat(60))
  lines.push('')
  lines.push(`尊敬的 ${context.candidateName}:`)
  lines.push('')
  lines.push(`恭喜您通过 ${context.positionTitle} (${context.jobLevel}) 的招聘流程。`)
  lines.push('')
  lines.push('录用信息:')
  lines.push('-'.repeat(40))

  const fields = [
    ['入职岗位', `${context.positionTitle} (${context.jobLevel})`],
    ['所属部门', context.departmentName],
    ['直接汇报', context.directLeader],
    ['工作地点', context.workLocation],
    ['期望入职日期', context.expectedJoinDate],
    ['试用期月薪', `¥ ${context.baseSalaryTrial} 元`],
    ['转正月薪', `¥ ${context.baseSalaryFormal} 元`],
    ['试用期', `${context.trialMonths} 个月`],
    ['合同类型', context.contractType],
    ['法人公司', context.legalCompany],
  ]
  for (const [k, v] of fields) {
    lines.push(`${k.padEnd(12, ' ')}: ${v}`)
  }

  if (context.commissionTrial || context.commissionFormal) {
    lines.push('')
    lines.push('提成信息:')
    lines.push(`  试用期提成: ¥ ${context.commissionTrial || 0} 元/月`)
    lines.push(`  转正提成:   ¥ ${context.commissionFormal || 0} 元/月`)
  }

  lines.push('')
  lines.push('请收到本函后 7 个工作日内确认是否接受, 并联系 HR:')
  lines.push(`  ${context.hrContact}`)
  lines.push('')
  lines.push('='.repeat(60))
  lines.push(`${context.legalCompany}`)
  lines.push(`签发日期: ${context.issueDate}`)

  return lines
}

/**
 * G26 - 背调报告 PDF (内联实现, 避免与 background-check.service 互相 import)
 *
 * @param {object} options
 * @param {object} options.offer
 * @param {object} options.candidate
 * @param {object} options.record - BackgroundCheckRecord (含 level/score/risks/completedAt/checkType/supplier)
 * @param {string} [options.supplier]
 * @returns {Buffer} PDF Buffer
 */
export function renderBackgroundCheckReport({ offer, candidate, record, supplier } = {}) {
  const candidateName = candidate?.name || '未知候选人'
  const level = record?.level || '-'
  const score = record?.score ?? '-'
  const supplierName = supplier || record?.supplier || '内部'
  const completedAt = record?.completedAt
    ? new Date(record.completedAt).toISOString().slice(0, 19).replace('T', ' ')
    : '-'
  const risks = Array.isArray(record?.risks) ? record.risks : []

  const lines = []
  lines.push(`背调报告 - ${candidateName}`)
  lines.push('='.repeat(60))
  lines.push('')
  lines.push('一、基本信息')
  lines.push('-'.repeat(40))
  lines.push(`候选人      : ${candidate?.name || '-'}`)
  lines.push(`候选人电话  : ${candidate?.phone || '-'}`)
  lines.push(`Offer ID   : ${offer?.id || '-'}`)
  lines.push(`职位        : ${offer?.positionName || '-'}`)
  lines.push(`背调供应商  : ${supplierName}`)
  lines.push(`背调类型    : ${record?.checkType || '-'}`)
  lines.push('')
  lines.push('二、背调结论')
  lines.push('-'.repeat(40))
  lines.push(`等级        : ${level}`)
  lines.push(`评分        : ${score}`)
  lines.push(`完成时间    : ${completedAt}`)
  lines.push('')
  lines.push('三、风险项')
  lines.push('-'.repeat(40))
  if (risks.length === 0) {
    lines.push('(无)')
  } else {
    for (const r of risks) {
      const cat = r.category || r.type || '风险'
      const sev = r.severity || r.level || '-'
      const desc = r.description || r.detail || ''
      lines.push(`- [${cat} / ${sev}] ${desc}`)
    }
  }
  lines.push('')
  lines.push('='.repeat(60))
  lines.push('本报告由 ATS 招聘管理系统自动生成 - 内部使用')

  return generateSimplePdf({
    title: `背调报告 - ${candidateName}`,
    lines,
    author: 'ATS Background Check',
  })
}

export default { generateSimplePdf, offerContextToLines, renderBackgroundCheckReport }
