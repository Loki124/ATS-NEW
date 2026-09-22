import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * RecruitSystem Store — 社会招聘 / 校园招聘 双系统切换（G-2026-09-23 立项）
 *
 * 当前阶段（Phase 1）：仅前端上下文切换 —— 两套系统共用同一组页面与路由，
 * 数据隔离（后端 recruit_type 维度）尚未落地，切换暂不影响接口请求。
 * 后续 Phase 3 后端就绪后，此处 current 会被注入到全局 axios 拦截器
 * （header: X-Recruit-Type），并在 router 守卫中做系统级路由域隔离。
 */

export type RecruitSystemKey = 'social' | 'campus'

export interface RecruitSystemMeta {
  key: RecruitSystemKey
  label: string
  /** 侧栏折叠态的单字标识（drawer/浮层展开前的兜底显示） */
  short: string
}

export const RECRUIT_SYSTEMS: RecruitSystemMeta[] = [
  { key: 'social', label: '社会招聘', short: '社' },
  { key: 'campus', label: '校园招聘', short: '校' },
]

const STORAGE_KEY = 'recruit-system'

function readInitial(): RecruitSystemKey {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'social' || saved === 'campus') return saved
  } catch {
    /* SSR / 隐私模式兜底 */
  }
  return 'social'
}

export const useSystemStore = defineStore('recruitSystem', () => {
  const current = ref<RecruitSystemKey>(readInitial())

  const meta = computed<RecruitSystemMeta>(
    () => RECRUIT_SYSTEMS.find((s) => s.key === current.value) ?? RECRUIT_SYSTEMS[0],
  )

  /** 当前是否为校园招聘系统（后续功能显隐的统一判定口） */
  const isCampus = computed(() => current.value === 'campus')

  /** 系统显示名（品牌名之外的系统域标识，供面包屑/标题拼接） */
  const label = computed(() => meta.value.label)

  function switchTo(key: RecruitSystemKey) {
    if (key === current.value) return
    current.value = key
    try {
      localStorage.setItem(STORAGE_KEY, key)
    } catch {
      /* ignore */
    }
  }

  return { current, meta, label, isCampus, switchTo }
})
