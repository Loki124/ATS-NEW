import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

export function useShortcuts() {
  const router = useRouter()
  let lastG = 0  // 上次按 G 的时间戳

  function onKey(e: KeyboardEvent) {
    const target = e.target as HTMLElement
    const tag = target.tagName
    // 输入框内不响应（避免误触发）
    if (['INPUT', 'TEXTAREA'].includes(tag) && !(e.metaKey || e.ctrlKey)) return
    // 中文输入法期间不响应
    if ((e as any).isComposing) return

    // `/` 聚焦搜索
    if (e.key === '/' && !e.metaKey && !e.ctrlKey) {
      e.preventDefault()
      document.querySelector<HTMLElement>('.layout-header__search-trigger')?.click()
      return
    }
    // `?` 打开帮助（任意面板）
    if (e.key === '?' && !e.metaKey && !e.ctrlKey) {
      e.preventDefault()
      document.dispatchEvent(new CustomEvent('open-shortcut-help'))
      return
    }
    // `G D` 跳工作台（1.5s 内按 D）
    if (e.key.toLowerCase() === 'g' && Date.now() - lastG < 1500) {
      lastG = 0
      router.replace('/dashboard')
      return
    }
    if (e.key.toLowerCase() === 'g') lastG = Date.now()
  }

  onMounted(() => window.addEventListener('keydown', onKey))
  onUnmounted(() => window.removeEventListener('keydown', onKey))
}