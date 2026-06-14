/**
 * CJK 字体子集嵌入 - 配合 pdf-generator.service 使用 (Todo #6)
 *
 * 工作流程:
 *  1. 加载系统 CJK 字体 (fontkit)
 *  2. 收集文本中所有 Unicode codepoints
 *  3. 子集化字体 (保留这些 codepoints 的 glyph)
 *  4. 构造 Type0 PDF 字体对象 (UniGB-UTF16-H 编码)
 *  5. 构造 CIDToGIDMap 流 (CID → 子集 GID)
 *  6. 编码文本为 2 字节 CID hex 字符串
 *
 * PDF 规范 (Type0 复合字体):
 *  - /Type /Font /Subtype /Type0 /BaseFont /<name>
 *  - /Encoding /UniGB-UTF16-H  (Adobe 标准 2-byte CMap)
 *  - /DescendantFonts [<CIDFont ref>]
 *
 *  CIDFont (CIDFontType2 = TrueType):
 *  - /Subtype /CIDFontType2 /BaseFont /<name>
 *  - /CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 2 >>
 *  - /FontDescriptor <ref> /DW <default width>
 *  - /CIDToGIDMap <stream ref>  (CID → GID 映射表)
 *
 *  FontDescriptor:
 *  - /Type /FontDescriptor /FontName /<name>
 *  - /Flags 4 /FontBBox [...] /ItalicAngle 0
 *  - /Ascent /Descent /CapHeight /StemV
 *  - /FontFile2 <ref>  (TTF 字体二进制流)
 */

import { readFileSync } from 'fs'
import * as fontkit from 'fontkit'
import iconv from 'iconv-lite'
import { findCjkFontSync } from './cjk-font-loader.js'

/** 全局缓存: 字体加载开销大, 复用 */
let cachedFont = null
let cachedFontPath = null

/**
 * 从字体集合 (.ttc) 中挑选合适的单个字体
 * 优先 SC (简体中文) > TC > 默认
 */
function pickFont(collection) {
  if (!collection.fonts) return collection
  // 尝试按名称匹配
  const preferredNames = ['Heiti SC', 'STHeiti SC', 'HeitiSC', 'PingFang SC', 'Songti SC', 'NotoSansSC', 'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei']
  for (const name of preferredNames) {
    for (const f of collection.fonts) {
      if (f.postscriptName && f.postscriptName.includes(name.split(' ')[0]) && f.familyName === name.split(' ')[0]) {
        return f
      }
    }
  }
  // 按 postscriptName 包含 "SC" 的优先
  const sc = collection.fonts.find(f => f.postscriptName && f.postscriptName.includes('SC'))
  if (sc) return sc
  // 否则取第一个
  return collection.fonts[0]
}

/**
 * 加载 CJK 字体 (从系统路径)
 * @returns {object|null} fontkit 字体对象
 */
export function loadCjkFont() {
  if (cachedFont) return cachedFont

  const fontPath = findCjkFontSync()
  if (!fontPath) {
    return null
  }

  try {
    cachedFontPath = fontPath
    const buf = readFileSync(fontPath)
    const opened = fontkit.create(buf)
    cachedFont = pickFont(opened)
    return cachedFont
  } catch (err) {
    console.warn(`[pdf-cjk] failed to load CJK font at ${fontPath}: ${err.message}; falling back to Helvetica`)
    return null
  }
}

/**
 * 重置缓存 (用于测试)
 */
export function _resetFontCache() {
  cachedFont = null
  cachedFontPath = null
}

/**
 * 获取当前缓存的字体路径 (调试用)
 */
export function getLoadedFontPath() {
  return cachedFontPath
}

/**
 * 收集字符串中所有唯一 Unicode codepoints
 * @param {string} text
 * @returns {number[]}
 */
function uniqueCodePoints(text) {
  const set = new Set()
  for (const ch of text) {
    set.add(ch.codePointAt(0))
  }
  return [...set]
}

/**
 * 将 Unicode codepoint 转换为 GBK 编码
 * 返回 2-byte CID 值 (高字节=0 表示 ASCII 区)
 * @param {number} cp - Unicode codepoint
 * @returns {number|null} GBK 编码, 或 null (不可映射)
 */
function unicodeToGbk(cp) {
  if (cp < 0x80) {
    return cp // ASCII 0x00-0x7F
  }
  try {
    const buf = iconv.encode(String.fromCodePoint(cp), 'gbk')
    if (buf.length === 2) {
      return (buf[0] << 8) | buf[1]
    }
    return null
  } catch {
    return null
  }
}

/**
 * 构造 Type0 CJK 字体 PDF 对象
 * @param {object} font - fontkit 字体
 * @param {string} text - 字体要渲染的全部文本
 * @returns {object} { fontObjects: string[], fontStreams: Buffer[], placeholderMap: {...}, cjkFont: { name, type0Idx } }
 */
export function buildCjkFontObjects(font, text) {
  const codePoints = uniqueCodePoints(text)

  // 1. 子集化字体
  const subset = font.createSubset()
  for (const cp of codePoints) {
    if (font.hasGlyphForCodePoint(cp)) {
      const glyph = font.glyphForCodePoint(cp)
      subset.includeGlyph(glyph.id)
    }
  }

  // 2. 编码 TTF 子集
  let ttfBuffer = subset.encode()
  // 修补 sfnt version: fontkit 写 "true" (Apple AAT), PDF 偏好 0x00010000
  if (ttfBuffer[0] === 0x74 && ttfBuffer[1] === 0x72 && ttfBuffer[2] === 0x75 && ttfBuffer[3] === 0x65) {
    ttfBuffer = Buffer.from(ttfBuffer)
    ttfBuffer[0] = 0x00
    ttfBuffer[1] = 0x01
    ttfBuffer[2] = 0x00
    ttfBuffer[3] = 0x00
  }

  // 3. 构造 CID→GID 映射
  const cidToGid = new Map()
  for (const cp of codePoints) {
    if (!font.hasGlyphForCodePoint(cp)) continue
    const glyph = font.glyphForCodePoint(cp)
    const newGid = subset.mapping[glyph.id]
    const cid = unicodeToGbk(cp)
    if (cid !== null && newGid !== undefined) {
      cidToGid.set(cid, newGid)
    }
  }

  // 4. 构造 CIDToGIDMap 流
  let maxCid = 0
  for (const cid of cidToGid.keys()) {
    if (cid > maxCid) maxCid = cid
  }
  const cidToGidSize = (maxCid + 1) * 2
  const cidToGidBuffer = Buffer.alloc(cidToGidSize, 0)
  for (const [cid, gid] of cidToGid) {
    cidToGidBuffer.writeUInt16BE(gid, cid * 2)
  }

  // 5. 字体度量
  const fontName = 'CJKBeta'
  const ascent = Math.round(font.ascent || 800)
  const descent = Math.round(font.descent || -200)
  const capHeight = Math.round(font.capHeight || 700)
  let bbox
  if (font.bbox) {
    bbox = [
      Math.round(font.bbox.minX),
      Math.round(font.bbox.minY),
      Math.round(font.bbox.maxX),
      Math.round(font.bbox.maxY),
    ]
  } else {
    bbox = [0, descent, 1000, ascent]
  }
  const stemV = 80

  // 默认宽度: 取一个 ASCII 字符的 advance
  let defaultWidth = 500
  if (font.hasGlyphForCodePoint(0x0041)) {
    defaultWidth = font.glyphForCodePoint(0x0041).advanceWidth || 500
  }

  // 6. 构造 PDF 对象
  const objects = []
  const streams = []

  // [0] CIDToGIDMap stream
  const cidToGidIdx = objects.length
  objects.push(`<< /Length ${cidToGidBuffer.length} >>`)
  streams.push(cidToGidBuffer)

  // [1] CIDFont 字典
  const cidFontIdx = objects.length
  objects.push(
    `<< /Type /Font /Subtype /CIDFontType2 /BaseFont /${fontName} ` +
    `/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 2 >> ` +
    `/DW ${defaultWidth} ` +
    `/CIDToGIDMap __CIDTOGIDMAP_REF__ ` +
    `/FontDescriptor __FONTDESC_REF__ >>`
  )

  // [2] FontFile2 stream (TTF)
  const fontFileIdx = objects.length
  objects.push(
    `<< /Length ${ttfBuffer.length} /Length1 ${ttfBuffer.length} >>`
  )
  streams.push(ttfBuffer)

  // [3] FontDescriptor
  const fontDescIdx = objects.length
  objects.push(
    `<< /Type /FontDescriptor /FontName /${fontName} ` +
    `/Flags 4 /FontBBox [${bbox.join(' ')}] ` +
    `/ItalicAngle 0 /Ascent ${ascent} /Descent ${descent} ` +
    `/CapHeight ${capHeight} /StemV ${stemV} ` +
    `/FontFile2 __FONTFILE_REF__ >>`
  )

  // [4] Type0 字体 (composite)
  const type0Idx = objects.length
  objects.push(
    `<< /Type /Font /Subtype /Type0 /BaseFont /${fontName} ` +
    `/Encoding /UniGB-UTF16-H ` +
    `/DescendantFonts [__CIDFONT_REF__] >>`
  )

  return {
    fontObjects: objects,
    fontStreams: streams,
    placeholderMap: {
      cidToGid: cidToGidIdx,
      cidFont: cidFontIdx,
      fontFile: fontFileIdx,
      fontDesc: fontDescIdx,
      type0: type0Idx,
    },
    cjkFont: { name: fontName, type0Idx },
  }
}

/**
 * 编码一行文本为 Type0 UniGB-UTF16-H CID 序列 (hex string)
 * @param {string} text
 * @returns {string} 形如 "0041D6D0" 的 hex 字符串
 */
export function encodeTextAsCid(text) {
  let hex = ''
  for (const ch of text) {
    const cp = ch.codePointAt(0)
    const cid = unicodeToGbk(cp)
    if (cid !== null) {
      hex += cid.toString(16).padStart(4, '0')
    }
  }
  return hex
}
