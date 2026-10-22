/**
 * 校招生管理 · 示例数据开关
 *
 * 三个模式：
 * - `auto`（开发环境默认）：**真实优先** —— 真实数据有就展示真实数据，真实为空（或接口失败）
 *   才用示例数据兜底。生产环境默认 `off`，绝不自动兜底。
 * - `on`：强制用示例数据（演示 / 评审看版式）。
 * - `off`：强制用真实数据（示例数据也不兜底）。
 *
 * 优先级：URL `?campusMock=on|off|auto`（仅开发环境）> localStorage `campus-mock-mode` > 默认值。
 * 模式是**跨页共享**的（模块级单例）：在一个页面切到示例数据，切换到别的菜单依然生效。
 *
 * ⚠️ 示例数据只读：展示示例数据时页面必须禁用新建/编辑/删除，
 *    避免把 `MOCK_` 前缀的假 id 写进后端（「能点但数据假」）。
 */
import { computed, ref } from 'vue'

export type CampusMockMode = 'auto' | 'on' | 'off'

const STORAGE_KEY = 'campus-mock-mode'
const QUERY_KEY = 'campusMock'

/** 开发环境默认 auto（空数据兜底示例），生产环境默认 off（永不兜底）。 */
const DEFAULT_MODE: CampusMockMode = import.meta.env.DEV ? 'auto' : 'off'

function isMode(v: any): v is CampusMockMode {
  return v === 'auto' || v === 'on' || v === 'off'
}

function readInitialMode(): CampusMockMode {
  // 1) URL 参数（仅开发环境，便于分享演示链接）
  if (import.meta.env.DEV) {
    try {
      const q = new URLSearchParams(window.location.search).get(QUERY_KEY)
      if (isMode(q)) return q
    } catch {
      /* 非浏览器环境忽略 */
    }
  }
  // 2) localStorage（用户在自己机器上的显式选择）
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (isMode(v)) return v
  } catch {
    /* 隐私模式等场景忽略 */
  }
  return DEFAULT_MODE
}

/** 跨页共享的模式（模块级单例）。 */
const sharedMode = ref<CampusMockMode>(readInitialMode())

export function useCampusMock() {
  /**
   * 「本页当前展示的是不是示例数据」—— 由 mode 与取数结果**派生**，不是可写状态。
   *
   * 🔴 2026-10-21 修复：原先 isMock 是个普通 ref，只在 pick()/pickBy() 内部赋值。
   * 但页面在「强制示例」分支（isMockOnly）里**从不调用 pick()** —— 它直接
   * `list.value = mockRows.value; return`。于是：
   *   - 模式切到 'on'（或从 localStorage 持久化读到 'on'）→ isMock 恒为 false，
   *     而页面渲染的却是示例数据；
   *   - 页面上的「新建/编辑/删除/成员穿透」disabled 守卫随之全部失效，
   *     拿 MOCK_ 前缀的假 id 打真接口 → 404（班级管理页「校招人数」穿透即如此）。
   *
   * 另外 setMode() 所在实例与页面实例**不是同一个**（只有 mode 是模块级共享单例），
   * 故在 setMode 里改 isMock 也修不到页面 —— 必须改成派生。
   *
   * 派生规则：
   *   'on'  → 恒为示例（页面跳过接口直接渲染示例）；
   *   'off' → 恒为真实（示例也不兜底）；
   *   'auto'→ 以本页最后一次取数结果为准（真实有数据用真实，为空才兜底示例）。
   */
  /** auto 模式下：最近一次取数是否兜底到了示例数据（每个页面独立）。 */
  const dataIsMock = ref(false)

  const mode = sharedMode

  const isMock = computed(() => {
    if (mode.value === 'on') return true
    if (mode.value === 'off') return false
    return dataIsMock.value
  })

  function setMode(m: CampusMockMode) {
    mode.value = m
    try {
      localStorage.setItem(STORAGE_KEY, m)
    } catch {
      /* 忽略存储失败 */
    }
  }

  /**
   * 真实列表 → 最终展示列表。
   * @param real 接口返回的真实数据
   * @param mock 示例数据
   */
  function pick<T>(real: T[], mock: T[]): T[] {
    if (mode.value === 'on') {
      dataIsMock.value = true
      return mock
    }
    if (mode.value === 'off') {
      dataIsMock.value = false
      return real
    }
    // auto：真实优先，为空才用示例兜底
    if (real && real.length) {
      dataIsMock.value = false
      return real
    }
    dataIsMock.value = true
    return mock
  }

  /**
   * 聚合类接口（返回结构而非列表，如 BU 汇总）的版本：
   * 由调用方判定「真实数据是否存在」，避免「空结构」被误判成有数据。
   */
  function pickBy<T>(hasReal: boolean, real: T, mock: T): T {
    if (mode.value === 'on') {
      dataIsMock.value = true
      return mock
    }
    if (mode.value === 'off') {
      dataIsMock.value = false
      return real
    }
    if (hasReal) {
      dataIsMock.value = false
      return real
    }
    dataIsMock.value = true
    return mock
  }

  return {
    mode,
    isMock,
    /** 强制示例数据模式：页面应**跳过接口**，直接渲染示例数据。 */
    isMockOnly: computed(() => mode.value === 'on'),
    pick,
    pickBy,
    setMode,
    showMock: () => setMode('on'),
    showReal: () => setMode('off'),
  }
}
