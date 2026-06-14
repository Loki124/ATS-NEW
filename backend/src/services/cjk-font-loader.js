/**
 * CJK 字体加载器 - 在常见系统路径查找中文字体
 * 用于 PDF 中文字体嵌入 (Todo #6)
 *
 * 不抛错: 未找到时返回 null, 由调用方决定 fallback 策略
 */

import { promises as fs, existsSync } from 'fs'

// 常见中文字体路径 (按优先级)
const CJK_FONT_PATHS = {
  darwin: [
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/STHeiti Light.ttc',
    '/Library/Fonts/Songti.ttc',
    '/System/Library/Fonts/PingFang.ttc',
  ],
  linux: [
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/arphic/uming.ttc',
  ],
  win32: [
    'C:\\Windows\\Fonts\\msyh.ttc',
    'C:\\Windows\\Fonts\\msyh.ttf',
    'C:\\Windows\\Fonts\\simsun.ttc',
  ],
}

/**
 * 在系统中查找可用的 CJK 字体 (异步)
 * @returns {Promise<string|null>} 字体文件路径, 或 null (未找到)
 */
export async function findCjkFont() {
  const platform = process.platform
  const candidates = CJK_FONT_PATHS[platform] || CJK_FONT_PATHS.linux

  for (const p of candidates) {
    try {
      await fs.access(p)
      return p
    } catch {
      // not found, try next
    }
  }
  return null
}

/**
 * 同步版本: 在缓存路径中查找
 * @returns {string|null}
 */
export function findCjkFontSync() {
  const platform = process.platform
  const candidates = CJK_FONT_PATHS[platform] || CJK_FONT_PATHS.linux

  for (const p of candidates) {
    if (existsSync(p)) return p
  }
  return null
}
