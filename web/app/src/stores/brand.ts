import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchBrandInfo, type BrandInfo } from '../api/brand'
import { useThemeStore } from './theme'

// 未填写品牌名称时的系统默认名（兵哥 2026-09-14: 未填→「招聘管理系统」；已填→完全以填写为准，不再拼后缀）
const DEFAULT_SYSTEM_NAME = '招聘管理系统'

/** 校验 hex 颜色（#RGB / #RRGGBB） */
function isValidHex(hex: string): boolean {
  return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(hex)
}

/**
 * Brand Store — G43 品牌信息全局消费
 *
 * 负责：
 * 1. 从 /api/v1/brand/ 拉取单例品牌配置；
 * 2. 把 primaryColor 同步到 theme store（全站 Naive UI + CSS 变量联动）；
 * 3. 把 companyName/logoUrl 同步到 document.title / favicon / Layout 系统名称与 Logo。
 *
 * 注意：brand 端点需要鉴权，未登录（无 token）时 init() 直接返回，不请求接口。
 */
export const useBrandStore = defineStore('brand', () => {
  const info = ref<BrandInfo | null>(null)
  const loaded = ref(false)

  // === 派生（供 Layout / 标题 / favicon 使用）===
  const systemName = computed(() => info.value?.companyName || DEFAULT_SYSTEM_NAME)
  const logoUrl = computed(() => info.value?.logoUrl || '')
  const portalTitle = computed(() => info.value?.portalTitle || '')
  const primaryColor = computed(() => info.value?.primaryColor || '')

  /** 获取或创建 <link rel="icon"> */
  function getOrCreateFaviconLink(): HTMLLinkElement | null {
    if (typeof document === 'undefined') return null
    let link = document.querySelector<HTMLLinkElement>('link[rel*="icon"]')
    if (!link) {
      link = document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)
    }
    return link
  }

  /** 把当前品牌信息写入 document.title + favicon（title 完全以品牌名称为准，不拼后缀） */
  function applyToDocument() {
    if (typeof document === 'undefined') return
    document.title = systemName.value

    const link = getOrCreateFaviconLink()
    if (!link) return
    const url = logoUrl.value
    if (url) {
      link.href = url
      // 强制浏览器重载 favicon：先切 alternate 再切回 icon
      link.rel = 'alternate icon'
      link.rel = 'icon'
    } else {
      link.href = '/static/vite.svg'
    }
  }

  /** 设置品牌信息并同步主题色/文档元信息 */
  function setInfo(data: BrandInfo) {
    info.value = data
    loaded.value = true

    const themeStore = useThemeStore()
    if (isValidHex(data.primaryColor)) {
      themeStore.setBrand(data.primaryColor)
    }
    applyToDocument()
  }

  /** Boot / 进入管理后台时调用：拉取品牌配置并同步到全局 */
  async function init() {
    const token = localStorage.getItem('accessToken') || localStorage.getItem('token')
    if (!token) return
    try {
      const data = await fetchBrandInfo()
      setInfo(data)
    } catch (e) {
      console.warn('[brand] init failed', e)
    }
  }

  return {
    info,
    loaded,
    systemName,
    logoUrl,
    portalTitle,
    primaryColor,
    setInfo,
    init,
    applyToDocument,
  }
})
