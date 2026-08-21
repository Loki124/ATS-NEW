import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

/**
 * Theme Store — v2 液态玻璃运行时换肤（DESIGN.md §2 可自定义机制）
 *
 * 单一输入：--brand（CSS 变量）
 * 派生（自动）：--brand-hover / --brand-pressed / --brand-dark
 *              （由 color-mix 在 tokens.css 完成）
 *
 * Naive UI themeOverrides 需要 hex 字面量（不接受 CSS 变量），
 * 因此 store 同时暴露 brandHex 给 App.vue 派生 primaryColor 等。
 *
 * 持久化：localStorage 'ats-theme' = { brand, mode }
 *   mode: 'light' | 'dark' | 'auto'（auto = 跟随 prefers-color-scheme）
 */

export type ThemeMode = 'light' | 'dark' | 'auto'

interface ThemePrefs {
  /** HEX 字符串（如 '#6366F1'）；不合法时回退默认 #6366F1 */
  brand: string
  mode: ThemeMode
}

const STORAGE_KEY = 'ats-theme'
const DEFAULT_PREFS: ThemePrefs = {
  brand: '#6366F1',
  mode: 'light',
}

// === 工具函数 ===

/** 校验 hex 颜色（#RGB / #RRGGBB） */
function isValidHex(hex: string): boolean {
  return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(hex)
}

/** hex → {r, g, b}（0-255） */
function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const m = hex.replace('#', '')
  const v = m.length === 3
    ? m.split('').map(c => parseInt(c + c, 16))
    : [parseInt(m.slice(0, 2), 16), parseInt(m.slice(2, 4), 16), parseInt(m.slice(4, 6), 16)]
  return { r: v[0], g: v[1], b: v[2] }
}

/** {r, g, b} → hex */
function rgbToHex(r: number, g: number, b: number): string {
  const c = (n: number) => Math.round(n).toString(16).padStart(2, '0')
  return `#${c(r)}${c(g)}${c(b)}`
}

/** RGB → HSL（h: 0-360, s/l: 0-100） */
function rgbToHsl(r: number, g: number, b: number): { h: number; s: number; l: number } {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  const l = (max + min) / 2
  let h = 0, s = 0
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break
      case g: h = (b - r) / d + 2; break
      case b: h = (r - g) / d + 4; break
    }
    h *= 60
  }
  return { h, s: s * 100, l: l * 100 }
}

/** HSL → RGB */
function hslToRgb(h: number, s: number, l: number): { r: number; g: number; b: number } {
  s /= 100; l /= 100
  const k = (n: number) => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = (n: number) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))
  return {
    r: Math.round(f(0) * 255),
    g: Math.round(f(8) * 255),
    b: Math.round(f(4) * 255),
  }
}

/** Naive UI hover 派生色：HSL 提亮 ~8%（与 Naive 内部算法近似） */
export function deriveHover(brandHex: string): string {
  if (!isValidHex(brandHex)) return brandHex
  const { r, g, b } = hexToRgb(brandHex)
  const { h, s, l } = rgbToHsl(r, g, b)
  const nl = Math.min(100, l + 8)
  const nr = hslToRgb(h, s, nl)
  return rgbToHex(nr.r, nr.g, nr.b)
}

/** Naive UI pressed 派生色：HSL 压暗 ~8% */
export function derivePressed(brandHex: string): string {
  if (!isValidHex(brandHex)) return brandHex
  const { r, g, b } = hexToRgb(brandHex)
  const { h, s, l } = rgbToHsl(r, g, b)
  const nl = Math.max(0, l - 8)
  const nr = hslToRgb(h, s, nl)
  return rgbToHex(nr.r, nr.g, nr.b)
}

// === Store ===

export const useThemeStore = defineStore('theme', () => {
  // === State ===
  const brandHex = ref<string>(DEFAULT_PREFS.brand)
  const mode = ref<ThemeMode>(DEFAULT_PREFS.mode)

  // === 派生（Naive UI themeOverrides 用） ===
  const brandHoverHex = computed(() => deriveHover(brandHex.value))
  const brandPressedHex = computed(() => derivePressed(brandHex.value))

  // === 内部：把状态写到 DOM / localStorage ===

  function applyBrandToDom(hex: string) {
    if (!isValidHex(hex)) return
    const root = document.documentElement
    root.style.setProperty('--brand', hex)
    // color-mix 自动派生 hover/pressed/dark；无需手动计算
  }

  function applyModeToDom(m: ThemeMode) {
    const body = document.body
    const apply = (dark: boolean) => body.classList.toggle('dark', dark)

    if (m === 'auto') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)')
      apply(mq.matches)
      // 监听系统主题变化
      const listener = (e: MediaQueryListEvent) => apply(e.matches)
      mq.addEventListener('change', listener)
      // 不清理——store 生命周期 = 应用生命周期
    } else {
      apply(m === 'dark')
    }
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        brand: brandHex.value,
        mode: mode.value,
      }))
    } catch (e) {
      console.warn('[theme] persist failed', e)
    }
  }

  function loadFromStorage(): ThemePrefs {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return DEFAULT_PREFS
      const parsed = JSON.parse(raw)
      return {
        brand: isValidHex(parsed.brand) ? parsed.brand : DEFAULT_PREFS.brand,
        mode: ['light', 'dark', 'auto'].includes(parsed.mode) ? parsed.mode : DEFAULT_PREFS.mode,
      }
    } catch {
      return DEFAULT_PREFS
    }
  }

  // === Actions（公开 API） ===

  function setBrand(hex: string) {
    if (!isValidHex(hex)) {
      console.warn('[theme] invalid hex:', hex)
      return
    }
    brandHex.value = hex
    applyBrandToDom(hex)
    persist()
  }

  function setMode(m: ThemeMode) {
    mode.value = m
    applyModeToDom(m)
    persist()
  }

  function reset() {
    setBrand(DEFAULT_PREFS.brand)
    setMode(DEFAULT_PREFS.mode)
  }

  /** Boot 时调用：从 localStorage 恢复 + 应用到 DOM */
  function init() {
    const prefs = loadFromStorage()
    brandHex.value = prefs.brand
    mode.value = prefs.mode
    applyBrandToDom(prefs.brand)
    applyModeToDom(prefs.mode)
  }

  // 响应式监听：state 变时自动同步 DOM
  watch(brandHex, applyBrandToDom)
  watch(mode, applyModeToDom)

  return {
    // state
    brandHex,
    mode,
    // 派生
    brandHoverHex,
    brandPressedHex,
    // actions
    setBrand,
    setMode,
    reset,
    init,
  }
})
