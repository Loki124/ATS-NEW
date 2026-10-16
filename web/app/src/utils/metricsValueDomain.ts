/**
 * metricsValueDomain.ts — 值域分段的候选枚举与校验（数值型 / 日期型）纯逻辑。
 *
 * 从 composables/useMetricsWorkspace.ts 抽出的部分：
 *   - computeDateDomain / buildDomainItems：分段 → 候选值枚举
 *   - dateSegmentIssues：日期型分段的逐条校验 + 区间重叠检测
 *   - numericSegmentIssues：数值型分段的逐条校验 + 区间重叠检测
 *   - domainErrorText：校验结果聚合为可读的一行文案
 *
 * 约定（重构铁律）：
 *   - 全部为纯函数；**不接受 i18n 的 t**：校验文案由调用方把「已解析好的文案函数」
 *     注入（labels），单测传 identity mock 即可，无需真实字典。
 *   - 行为与拆分前逐字一致，重构不改判定规则与文案键。
 */
import * as MF from './metricsFormat'

/** 分段校验与候选摘要用到的文案函数集合（由 composable 用 `t('...')` 的薄包装注入）。 */
export interface ValueDomainLabels {
  /** 「共 N 个值」摘要，支持 {n} 插值。 */
  domainCount: (n: number) => string
  /** 「共 {total} 个值，已展示 {shown} 个」摘要。 */
  domainCountTruncated: (total: number, shown: number) => string
  domainStepRequired: () => string
  domainStepPositiveInt: () => string
  domainBoundRequired: () => string
  domainRelativeRequired: () => string
  domainFromBeforeTo: () => string
  domainOverlap: () => string
  domainMaxGtMin: () => string
  domainStepPositive: () => string
  domainStepInteger: () => string
  domainSegmentOverlap: () => string
}

/** 日期型候选枚举的展示条数上限（防一次展开几万个日期把弹窗撑爆）。 */
export const DATE_ENUM_LIMIT = 40

/** 日期型枚举的硬上限：超过即停止枚举，UI 走「共 N 个值」摘要。 */
export const DATE_ENUM_HARD_LIMIT = 5000

/** 显示单位 → 计算参数单位枚举值（仅「月/年」这类需要换算的粒度才写 calcParams.unit）。 */
export const UNIT_TO_CALC: Record<string, string> = { 月: 'month', 年: 'year' }

export interface DomainItem {
  text: string
  value: string
}

/**
 * 分隔单位落库值（供 buildDomainItems / submitTemplate 判断是否换算）。
 * 非日期型时对无单位指标应返回空串，由调用方兜底。
 */
export function calcUnitFor(displayUnit: string): string {
  return UNIT_TO_CALC[displayUnit] || ''
}

/**
 * 日期型值域：按分段枚举出候选日期。
 *   - 单边区间（只有 from 或只有 to）→ 产出「起 / 及以前」两种边界项，各计 1 个总数；
 *   - 双边区间 → 从 from 步进到 to（含），step <= 0 时兜底为 1；
 *   - from > to 的段跳过；total 统计真实总数，items 受 DATE_ENUM_LIMIT 截断；
 *   - total 触达 DATE_ENUM_HARD_LIMIT 即停止枚举。
 */
export function computeDateDomain(params: {
  segments: any[]
  granularity: string
}): { items: DomainItem[]; total: number } {
  const { segments, granularity: g } = params
  const items: DomainItem[] = []
  let total = 0
  for (const seg of segments || []) {
    const from = MF.resolveDateBound(seg.from)
    const to = MF.resolveDateBound(seg.to)
    if (!from && !to) continue
    let st = Number(seg.step)
    if (!st || st < 1) st = 1
    const su = seg.stepUnit || g
    if (!from || !to) {
      const edge = (from || to) as Date
      total += 1
      if (items.length < DATE_ENUM_LIMIT) {
        items.push({
          text: from ? `${MF.fmtDate(edge, g)}起` : `${MF.fmtDate(edge, g)}及以前`,
          value: MF.fmtDate(edge, '日'),
        })
      }
      continue
    }
    if (from.getTime() > to.getTime()) continue
    for (let d = from; d.getTime() <= to.getTime(); d = MF.advanceDate(d, st, su)) {
      total += 1
      if (items.length < DATE_ENUM_LIMIT) {
        items.push({ text: MF.fmtDate(d, g), value: MF.fmtDate(d, '日') })
      }
      if (total >= DATE_ENUM_HARD_LIMIT) break
    }
  }
  return { items, total }
}

/**
 * 数值型值域：按分段枚举候选值。
 *   - max 为空 → 产出「N 单位以上」开放项；
 *   - max <= min 的段跳过（视为无效区间）；
 *   - step <= 0 时按参数类型兜底：离散 1 / 连续 0.5；
 *   - 用 1e-9 容差累积，避免浮点误差漏掉上界值。
 */
export function buildDomainItems(params: {
  segments: any[]
  unit: string
  isDiscrete: boolean
}): DomainItem[] {
  const { segments, unit: u, isDiscrete } = params
  const out: DomainItem[] = []
  for (const seg of segments || []) {
    const mn = Number(seg.min)
    const mxRaw =
      seg.max === null || seg.max === undefined || seg.max === '' ? null : Number(seg.max)
    let st = Number(seg.step)
    if (!st || st <= 0) st = isDiscrete ? 1 : 0.5
    if (!Number.isFinite(mn) || !(st > 0)) continue
    if (mxRaw === null || !Number.isFinite(mxRaw)) {
      out.push({ text: `${MF.fmtNum(mn)}${u}以上`, value: `${MF.fmtNum(mn)}+` })
      continue
    }
    if (mxRaw <= mn) continue
    for (let v = mn; v <= mxRaw + 1e-9; v += st) {
      out.push({ text: `${MF.fmtNum(v)}${u}`, value: MF.fmtNum(v) })
    }
  }
  return out
}

/**
 * 日期型分段逐条校验 + 区间重叠检测。
 * 校验顺序：step 必填 → step 为正整数 → 边界至少一侧存在 → 相对边界 n 必填 → from < to。
 * 最后把所有双边区间按 from 升序排序，相邻重叠则标记后一段（首条重叠错误优先）。
 */
export function dateSegmentIssues(
  segments: any[],
  labels: Pick<ValueDomainLabels, 'domainStepRequired' | 'domainStepPositiveInt' | 'domainBoundRequired' | 'domainRelativeRequired' | 'domainFromBeforeTo' | 'domainOverlap'>,
): (string | null)[] {
  const segs = segments || []
  const issues: (string | null)[] = segs.map(() => null)
  segs.forEach((s: any, i: number) => {
    if (s.step === null || s.step === undefined || s.step === '') {
      issues[i] = labels.domainStepRequired()
      return
    }
    const st = Number(s.step)
    if (!Number.isFinite(st) || !Number.isInteger(st) || st <= 0) {
      issues[i] = labels.domainStepPositiveInt()
      return
    }
    const from = MF.resolveDateBound(s.from)
    const to = MF.resolveDateBound(s.to)
    if (!from && !to) {
      issues[i] = labels.domainBoundRequired()
      return
    }
    for (const b of [s.from, s.to]) {
      if (b?.type === 'relative' && (b.n === null || b.n === undefined || b.n === '')) {
        issues[i] = labels.domainRelativeRequired()
        return
      }
    }
    if (from && to && from.getTime() >= to.getTime()) {
      issues[i] = labels.domainFromBeforeTo()
      return
    }
  })
  const ranged = segs
    .map((s: any, i: number) => ({ i, from: MF.resolveDateBound(s.from), to: MF.resolveDateBound(s.to) }))
    .filter((b) => b.from && b.to)
    .sort((a, b) => (a.from as Date).getTime() - (b.from as Date).getTime())
  for (let k = 1; k < ranged.length; k++) {
    if (
      (ranged[k].from as Date).getTime() <= (ranged[k - 1].to as Date).getTime() &&
      !issues[ranged[k].i]
    ) {
      issues[ranged[k].i] = labels.domainOverlap()
    }
  }
  return issues
}

/**
 * 数值型分段逐条校验 + 区间重叠检测。
 * 校验顺序：max > min（双侧都有值时）→ step 必填 → step 为正 → 离散型 step 必须为整数。
 * 重叠判定：按 min 升序，相邻区间的 min <= 前一段 max 则标记后一段。
 */
export function numericSegmentIssues(
  segments: any[],
  isDiscrete: boolean,
  labels: Pick<ValueDomainLabels, 'domainMaxGtMin' | 'domainStepRequired' | 'domainStepPositive' | 'domainStepInteger' | 'domainSegmentOverlap'>,
): (string | null)[] {
  const segs = segments || []
  const issues: (string | null)[] = segs.map(() => null)
  segs.forEach((s: any, i: number) => {
    const mn = MF.segBound(s.min)
    const mx = MF.segBound(s.max)
    if (mn !== null && mx !== null && mx <= mn) {
      issues[i] = labels.domainMaxGtMin()
      return
    }
    const raw = s.step
    if (raw === null || raw === undefined || raw === '') {
      issues[i] = labels.domainStepRequired()
      return
    }
    const st = Number(raw)
    if (!Number.isFinite(st) || st <= 0) {
      issues[i] = labels.domainStepPositive()
      return
    }
    if (isDiscrete && !Number.isInteger(st)) {
      issues[i] = labels.domainStepInteger()
    }
  })
  const ranged = segs
    .map((s: any, i: number) => ({ i, mn: MF.segBound(s.min), mx: MF.segBound(s.max) }))
    .filter((b) => b.mn !== null && b.mx !== null)
    .sort((a, b) => (a.mn as number) - (b.mn as number))
  for (let k = 1; k < ranged.length; k++) {
    if (
      (ranged[k].mn as number) <= (ranged[k - 1].mx as number) &&
      !issues[ranged[k].i]
    ) {
      issues[ranged[k].i] = labels.domainSegmentOverlap()
    }
  }
  return issues
}

/** 逐条校验结果聚合为「段1：xxx；段2：yyy」形式的单行文案；无错返回空串。 */
export function domainErrorText(issues: (string | null)[]): string {
  return issues
    .map((m, i) => (m ? `段${i + 1}：${m}` : ''))
    .filter(Boolean)
    .join('；')
}

/** 「共 N 个值 / 已截断」摘要：非日期型直接用候选数，日期型可能展示被截断的真实总数。 */
export function domainSummaryTagText(
  isDateOutput: boolean,
  shownCount: number,
  dateTotal: number,
  labels: Pick<ValueDomainLabels, 'domainCount' | 'domainCountTruncated'>,
): string {
  if (!isDateOutput) return labels.domainCount(shownCount)
  return dateTotal > shownCount
    ? labels.domainCountTruncated(dateTotal, shownCount)
    : labels.domainCount(dateTotal)
}
