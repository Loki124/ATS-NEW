/**
 * metricsEntityDomain.ts — 实体引用型值域（人员 / 部门 / 身份）的无状态纯逻辑。
 *
 * 从 composables/useMetricsWorkspace.ts 抽出的部分：
 *   - 候选清单与下拉选项的映射（toEntityOptions / makeEntityOption）
 *   - 多选框的「全部」哨兵项协议（isAllSelected / withSelectAllOption / applySelectAll）
 *   - 取值方式判定与文案键（entityTypeNeedsPicker / entityAutoLabelKey）
 *   - 值域结构的载入归一与保存归一（normalizeValueDomain / buildSaveEntityDomain）
 *
 * 约定：
 *   - 全部为纯函数，reactive 状态（tplForm）与接口数据由调用方注入；
 *   - 行为与拆分前逐字一致，重构不改判定规则。
 *   - **不接受 i18n 的 t**：需要文案的规则由调用方注入已解析好的文案函数，
 *     「自动生效」类取值方式（current_user / current_user_dept）的 label 也走注入。
 */

/** 需要文案的规则用到的文案函数集合（由 composable 用 `t('...')` 的薄包装注入）。 */
export interface EntityDomainLabels {
  /** 哨兵项文案：勾上=全选，已全选态=取消全选。 */
  selectAll: () => string
  selectAllOff: () => string
  /** 「自动生效」类取值方式的中文 label。 */
  currentUser: () => string
  currentUserDept: () => string
}

export interface EntityOption {
  id: string
  name: string
  label: string
}

export interface SelectOption {
  label: string
  value: string
}

export interface EntityCandidate {
  type: string
  ids: string[]
  label: string
}

/** Naive UI 无「全选」内置项，用顶部哨兵项实现；常量在此单点定义。 */
export const SELECT_ALL = '__select_all__'

/**
 * 接口行 → 下拉选项。按 nameKeys 顺序取第一个非空名字字段；
 * 无 id 或无名字的行丢弃，同 id 只保留首次出现（DRF 列表去重）。
 */
export function toEntityOptions(rows: any[], nameKeys: string[]): EntityOption[] {
  const seen = new Set<string>()
  const out: EntityOption[] = []
  for (const r of rows || []) {
    if (!r) continue
    const id = String(r.id ?? r.pk ?? r.value ?? '').trim()
    if (!id || seen.has(id)) continue
    let name = ''
    for (const k of nameKeys) {
      const v = r[k]
      if (v !== undefined && v !== null && String(v).trim()) {
        name = String(v).trim()
        break
      }
    }
    if (!name) continue
    seen.add(id)
    out.push({ id, name, label: name })
  }
  return out
}

/**
 * 🔴 该取值方式是否需要额外的对象选择下拉。
 * 「当前登录人 / 当前登录人部门」的值由运行时决定，无需选对象。
 */
export function entityTypeNeedsPicker(type: string): boolean {
  return type !== 'current_user' && type !== 'current_user_dept'
}

/** 自动生效类取值方式的 label 走 i18n 键，指定类则展示所选对象名拼接。 */
export function entityAutoLabelKey(type: string): string {
  return type === 'current_user_dept'
    ? 'metrics.tpl.entityCurrentUserDept'
    : 'metrics.tpl.entityCurrentUser'
}

export function isSelectAllValue(v: string): boolean {
  return v === SELECT_ALL
}

/** 当前值是否已覆盖全部候选（据此把哨兵项渲染成选中态）。 */
export function isAllSelected(opts: SelectOption[], current: string[]): boolean {
  const ids = opts.map((o) => o.value)
  return ids.length > 0 && ids.every((id) => current.includes(id))
}

/** 顶部插入「全部 / 取消全部」；已全选时该项本身也呈选中态。 */
export function withSelectAllOption(
  opts: SelectOption[],
  current: string[],
  labels: Pick<EntityDomainLabels, 'selectAll' | 'selectAllOff'>,
): SelectOption[] {
  const ids = opts.map((o) => o.value)
  const all = ids.length > 0 && ids.every((id) => current.includes(id))
  return [{ label: all ? labels.selectAllOff() : labels.selectAll(), value: SELECT_ALL }, ...opts]
}

/**
 * 全选哨兵项的值变化 → 真实 id 列表。三种情形要分清
 * （Naive UI 不可区分「取消勾选全选项」与「逐个勾满」）：
 *   1. 勾上哨兵 → 全选；
 *   2. 原本全选、只取消哨兵（其余 id 仍在）→ 清空；
 *   3. 原本全选、取消某个具体项 → 保留剩余。
 */
export function applySelectAll(raw: string[], opts: SelectOption[], wasAll: boolean): string[] {
  const ids = opts.map((o) => o.value)
  if (raw.includes(SELECT_ALL)) return [...ids]
  if (wasAll && raw.length >= ids.length) return []
  return raw.filter((x) => !isSelectAllValue(x))
}

/**
 * 生成一条候选（存 id + label 快照：id 用于精确匹配，
 * label 用于展示，以及对象改名后仍可读）。
 */
export function makeEntityOption(
  type: string,
  ids: string[],
  optsForType: SelectOption[],
  labels: Pick<EntityDomainLabels, 'currentUser' | 'currentUserDept'>,
): EntityCandidate {
  const map = new Map(optsForType.map((o) => [o.value, o.label]))
  const picked = (ids || []).filter(Boolean).map((id) => map.get(id) || id)
  const autoLabel = entityAutoLabelKey(type) === 'metrics.tpl.entityCurrentUserDept' ? labels.currentUserDept() : labels.currentUser()
  return {
    type,
    ids: entityTypeNeedsPicker(type) ? [...new Set((ids || []).filter(Boolean))] : [],
    label: entityTypeNeedsPicker(type) ? picked.join('、') : autoLabel,
  }
}

/**
 * 值域回填归一：
 *   - 带 kind → 实体引用型，保留 kind/options 与对应 id 数组，
 *     其余互斥字段补空数组（避免 UI 读到 undefined）；
 *   - 不带 kind → 历史值域，原样回填 segments（数值/日期两条逻辑零改动）。
 * 之所以在载入时就分流，是为避免「实体值域」里的 segments 残留干扰既有分支。
 */
export function normalizeValueDomain(domain: any): { kind: string; options: EntityCandidate[] } | { segments: any[] } {
  const d = domain && typeof domain === 'object' ? domain : {}
  const kind = d.kind === 'person' || d.kind === 'department' ? d.kind : ''
  if (kind) {
    return {
      kind,
      options: Array.isArray(d.options)
        ? d.options
            .filter((o: any) => o && o.type)
            .map((o: any) => ({
              type: String(o.type),
              ids: Array.isArray(o.ids) ? [...o.ids] : [],
              label: String(o.label || ''),
            }))
        : [],
    }
  }
  return { segments: (d.segments || []).map((s: any) => ({ ...s })) }
}

/**
 * 保存前的值域归一（仅实体引用型）：
 * 只落 kind 与 options（候选清单），每条候选 {type, ids, label}；
 * label 为展示快照，ids 为精确匹配依据。非实体型由调用方原样返回。
 */
export function buildSaveEntityDomain(valueDomain: any, kind: string): { kind: string; options: EntityCandidate[] } {
  const vd = valueDomain
  const options = Array.isArray(vd.options)
    ? vd.options
        .filter((o: any) => o && o.type)
        .map((o: any) => ({
          type: String(o.type),
          ids: Array.isArray(o.ids) ? o.ids.filter((x: unknown) => String(x ?? '').trim()) : [],
          label: String(o.label || '').trim(),
        }))
    : []
  return { kind, options }
}
