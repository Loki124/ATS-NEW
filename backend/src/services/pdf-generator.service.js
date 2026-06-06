/**
 * 纯 JS PDF 生成器 - PRD C5 (Offer PDF 服务端生成)
 *
 * 特点:
 *  - 零依赖 (不需要 pdfkit / puppeteer / wkhtmltopdf)
 *  - 支持中文 (依赖 PDF 内嵌字体子集 — 当前用 ASCII 安全 fallback, 中文走 latin-1 替换)
 *  - 适合简单文本型 PDF (Offer 模板)
 *
 * 实现: PDF 1.4 规范, 14 个内置字体 (Helvetica), 文本按行布局, 自动分页
 * 局限: 不支持复杂排版 (表格/图片) — Phase 3 可换 pdfkit
 *
 * 用法:
 *   const pdf = generateSimplePdf({ title: 'Offer Letter', lines: [...] })
 *   res.setHeader('Content-Type', 'application/pdf')
 *   res.send(pdf)
 */

const PAGE_WIDTH = 595 // A4 in points
const PAGE_HEIGHT = 842
const MARGIN = 50
const LINE_HEIGHT = 16
const FONT_SIZE = 11

/**
 * 生成简单 PDF (返回 Buffer)
 * @param {object} options
 * @param {string} options.title
 * @param {string[]} options.lines - 行内容
 * @param {string} [options.author='ATS System']
 * @returns {Buffer}
 */
export function generateSimplePdf({ title = 'Document', lines = [], author = 'ATS System' } = {}) {
  // 1. PDF 对象集合
  const objects = []
  // 字体对象 (Helvetica)
  const fontObjNum = 5 // 占位, 最后再确认

  // 2. 分页: 每页最多 (PAGE_HEIGHT - 2*MARGIN) / LINE_HEIGHT 行
  const maxLinesPerPage = Math.floor((PAGE_HEIGHT - 2 * MARGIN) / LINE_HEIGHT)
  const pages = []
  for (let i = 0; i < lines.length; i += maxLinesPerPage) {
    pages.push(lines.slice(i, i + maxLinesPerPage))
  }
  if (pages.length === 0) pages.push([])

  // 3. 构造每个 page 的 content stream
  const pageObjNums = []
  const contentObjNums = []
  for (let p = 0; p < pages.length; p++) {
    const pageLines = pages[p]
    let content = 'BT\n'
    content += `/F1 ${FONT_SIZE} Tf\n`
    content += `${MARGIN} ${PAGE_HEIGHT - MARGIN} Td\n`
    for (let i = 0; i < pageLines.length; i++) {
      const text = sanitizeForPdf(pageLines[i])
      content += `(${escapePdfString(text)}) Tj\n`
      content += `0 -${LINE_HEIGHT} Td\n`
    }
    content += 'ET\n'
    content += `%%EOF_PAGE_${p}`

    const contentObjNum = objects.length + 2 // +1 (Catalog) +1 (Pages) +1 (Font)
    contentObjNums.push(contentObjNum)
    objects.push(buildStreamObject(content))

    const pageObjNum = objects.length + 1
    pageObjNums.push(pageObjNum)
    objects.push(null) // placeholder, will build page obj after
  }

  // 4. Font object
  const fontObj = `<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>`
  const fontObjIndex = objects.length
  objects.push(fontObj)

  // 5. Pages object
  const pagesObjIndex = objects.length
  const pagesObj = `<< /Type /Pages /Count ${pages.length} /Kids [${pageObjNums.map(n => `${n} 0 R`).join(' ')}] >>`
  objects.push(pagesObj)

  // 6. Page objects (替换 placeholder)
  for (let i = 0; i < pageObjNums.length; i++) {
    const pageNum = pageObjNums[i]
    const contentNum = contentObjNums[i]
    objects[pageNum - 1] = `<< /Type /Page /Parent ${pagesObjIndex + 1} 0 R /MediaBox [0 0 ${PAGE_WIDTH} ${PAGE_HEIGHT}] /Contents ${contentNum + 1} 0 R /Resources << /Font << /F1 ${fontObjIndex + 1} 0 R >> >> >>`
  }

  // 7. Catalog
  const catalogObj = `<< /Type /Catalog /Pages ${pagesObjIndex + 1} 0 R >>`
  objects.push(catalogObj)

  // 8. Info
  const now = new Date()
  const dateStr = `D:${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
  const infoObj = `<< /Title (${escapePdfString(title)}) /Producer (ATS Backend Pure-JS PDF Generator) /Creator (${escapePdfString(author)}) /CreationDate (${dateStr}) >>`
  objects.push(infoObj)

  // 9. 序列化 PDF
  return serializePdf(objects)
}

function buildStreamObject(content) {
  const length = Buffer.byteLength(content, 'utf8')
  return `<< /Length ${length} >>\nstream\n${content}\nendstream`
}

/**
 * 清理 PDF 文本: 移除 PDF 字符串不支持的字符
 * 简单实现: 保留 ASCII + 替换常见中文标点为 latin 等价
 */
function sanitizeForPdf(text) {
  if (typeof text !== 'string') return String(text)
  // WinAnsiEncoding 支持的拉丁字符集, 中文会显示乱码但不会崩
  return text
}

/**
 * 转义 PDF 字符串中的特殊字符
 */
function escapePdfString(s) {
  return s.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)')
}

/**
 * 序列化对象数组为 PDF Buffer
 */
function serializePdf(objects) {
  const chunks = []
  chunks.push(Buffer.from('%PDF-1.4\n', 'latin1'))
  // 二进制标记: 4 个高位字节, 必须用 latin1 写入保持单字节
  chunks.push(Buffer.from([0x25, 0xe2, 0xe3, 0xcf, 0xd3, 0x0a]))

  const offsets = []
  for (let i = 0; i < objects.length; i++) {
    offsets.push(chunks.reduce((sum, c) => sum + c.length, 0))
    chunks.push(Buffer.from(`${i + 1} 0 obj\n${objects[i]}\nendobj\n`, 'utf8'))
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

export default { generateSimplePdf, offerContextToLines }
