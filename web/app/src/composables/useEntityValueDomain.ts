/**
 * useEntityValueDomain.ts — 实体引用型值域（人员 / 部门 / 身份）域。
 *
 * 从 useMetricsWorkspace.ts 拆出（原 694–969 一段）。本域独占 3 个组织架构接口：
 *   listUsers / listRoles / listManagementUnits
 *
 * 拆出原因：
 *   1. 这三个接口只被本域使用（已在 import 侧收口），与模板 CRUD / 值域分段 / 预览无关；
 *   2. 实体值域的「候选清单 + 取值方式 + 全选哨兵」自成一套交互闭环（27 个函数），
 *      独立成文件后其边界与主 composable 一眼可见。
 *
 * 与主 composable 的耦合仅 3 个只读量：tplForm（值域容器）、entityKind、isDeptOutput。
 * 三个接口用 Promise.allSettled 且 fail-soft：单个失败不影响其余（下游为空即可，不阻断配置）。
 *
 * 行为零变化：函数体与调用顺序与拆分前逐字一致。
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listUsers } from '@/api/users'
import { listRoles } from '@/api/role-v2'
import { listManagementUnits } from '@/api/management-unit'
import * as ED from '@/utils/metricsEntityDomain'

export interface EntityValueDomainDeps {
  /** 模板表单（只读 valueDomain；本域仅在取值方式不匹配时由主 composable 负责重置）。 */
  tplForm: { value: any }
  /** 当前选中定义的实体出参类型：person / department / ''。 */
  entityKind: { value: 'person' | 'department' | '' }
  /** 是否为部门型出参（决定取值方式清单与对象下拉数据源）。 */
  isDeptOutput: { value: boolean }
}

export function useEntityValueDomain(deps: EntityValueDomainDeps) {
  const { t } = useI18n()
  const { tplForm, entityKind, isDeptOutput } = deps

  // 纯函数侧不接 i18n 的 t，文案在这里集中翻译后以函数形式注入。
  const ED_LABELS: ED.EntityDomainLabels = {
    selectAll: () => t('metrics.tpl.selectAll'),
    selectAllOff: () => t('metrics.tpl.selectAllOff'),
    currentUser: () => t('metrics.tpl.entityCurrentUser'),
    currentUserDept: () => t('metrics.tpl.entityCurrentUserDept'),
  }

  // ================================================================
  // 🔴 实体引用型值域（2026-10-13）：人员 / 部门
  //   数据结构 {kind, selector, <id 字段>: [], multiple}，
  //   与既有 segments 分段体系**并列互不影响**（kind 存在才走本分支）。
  //   下拉数据源复用现成接口：用户 / 身份(RoleV2) / 管理单元。
  // ================================================================
  const entityUsers = ref<{ id: string; name: string; label: string }[]>([])
  const entityIdentities = ref<{ id: string; name: string; label: string }[]>([])
  const entityUnits = ref<{ id: string; name: string; label: string }[]>([])
  const entityOptionsLoading = ref(false)
  /** 懒加载标记：切换到实体型指标时才拉取，避免每次进模板弹窗都请求三份列表 */
  const entityOptionsLoaded = ref(false)

  function toEntityOptions(rows: any[], nameKeys: string[]): { id: string; name: string; label: string }[] {
    return ED.toEntityOptions(rows, nameKeys)
  }

  async function ensureEntityOptions() {
    if (entityOptionsLoaded.value || entityOptionsLoading.value) return
    entityOptionsLoading.value = true
    try {
      // 三者相互独立，单个失败不影响其余（fail-soft：下拉空即可，不阻断配置）
      const [u, r, m] = await Promise.allSettled([
        listUsers(),
        listRoles(),
        listManagementUnits(),
      ])
      if (u.status === 'fulfilled') entityUsers.value = toEntityOptions(u.value as any[], ['fullName', 'realName', 'name', 'username', 'employeeId'])
      if (r.status === 'fulfilled') {
        const data: any = (r as any).value
        const rows = Array.isArray(data) ? data : (data?.items || data?.results || [])
        entityIdentities.value = toEntityOptions(rows, ['roleName', 'name'])
      }
      if (m.status === 'fulfilled') {
        const data: any = (m as any).value
        const rows = Array.isArray(data) ? data : (data?.items || data?.results || [])
        entityUnits.value = toEntityOptions(rows, ['unitName', 'name', 'fullName'])
      }
      entityOptionsLoaded.value = true
    } finally {
      entityOptionsLoading.value = false
    }
  }

  /** 当前实体值域（保证 kind/selector 键存在） */
  const entityDomain = computed<any>(() => {
    const vd = tplForm.value.valueDomain
    if (!vd || typeof vd !== 'object') return { kind: entityKind.value, selector: '', multiple: true }
    return vd
  })

  /** 可选的选取方式（人员 / 部门各自不同）—— 每个取值方式就是一个「候选类型」 */
  const entitySelectorOptions = computed<{ label: string; value: string }[]>(() => {
    if (isDeptOutput.value) {
      return [
        { label: t('metrics.tpl.entitySpecifiedDept'), value: 'specified' },
        { label: t('metrics.tpl.entityCurrentUserDept'), value: 'current_user_dept' },
      ]
    }
    return [
      { label: t('metrics.tpl.entitySpecifiedUser'), value: 'specified' },
      { label: t('metrics.tpl.entitySpecifiedIdentity'), value: 'identity' },
      { label: t('metrics.tpl.entityCurrentUser'), value: 'current_user' },
    ]
  })

  const entityDefaultSelector = computed<string>(
    () => entitySelectorOptions.value[0]?.value || 'specified',
  )

  /**
   * 🔴 该候选类型是否需要额外的对象选择下拉（当前登录人 → 运行时才知值，无需选）。
   * 与「锁定一种方式」的旧设计不同：这里只影响**新增候选**时是否要弹选择器。
   */
  function entityTypeNeedsPicker(type: string): boolean {
    return ED.entityTypeNeedsPicker(type)
  }

  /** 按候选类型给出正确的对象下拉（人员 / 身份 / 部门） */
  function entityOptionsForType(type: string): { label: string; value: string }[] {
    const src =
      type === 'identity'
        ? entityIdentities.value
        : isDeptOutput.value
          ? entityUnits.value
          : entityUsers.value
    return src.map((x) => ({ label: x.label, value: x.id }))
  }

  /** 候选清单（对应数值型的segments → domainItems：模板层只限定可选范围，应用方选具体值） */
  const entityOptions = computed<any[]>(() => {
    const v = (entityDomain.value as any).options
    return Array.isArray(v) ? v : []
  })

  /** 已配置过候选的取值方式（同一种方式只允许一条，配多了没有意义） */
  const entityUsedTypes = computed<string[]>(() =>
    entityOptions.value.map((o: any) => String(o?.type || '')).filter(Boolean),
  )
  /** 草稿里还能选的取值方式：已配过的不再出现 */
  const entityUnusedSelectorOptions = computed<{ label: string; value: string }[]>(() =>
    entitySelectorOptions.value.filter((o) => !entityUsedTypes.value.includes(o.value)),
  )
  /** 三种方式全部配齐 → 隐藏添加入口 */
  const entityTypesExhausted = computed<boolean>(() => entityUnusedSelectorOptions.value.length === 0)

  /** 新增一条候选；当前登录人类型无需选择对象，其余类型挂在「正在配置」态由 UI 收集 */
  const entityDraft = ref<{ type: string; ids: string[] }>({ type: '', ids: [] })
  // 🔴 草稿行默认收起（兵哥 2026-10-14 交互修正）：常驻空草稿行既占地又像没填完，
  //   改为点「+ 添加候选」才展开，确认/取消后收起并复位。
  const entityDraftVisible = ref(false)
  const entityDraftError = ref('')
  function showEntityDraft() {
    const unused = entityUnusedSelectorOptions.value
    if (!unused.length) return
    entityDraft.value.type = unused[0].value
    entityDraftError.value = ''
    entityDraftVisible.value = true
  }
  function resetEntityDraft() {
    entityDraft.value = { type: '', ids: [] }
    entityDraftError.value = ''
    entityDraftVisible.value = false
  }
  // 草稿内容一变就清错误（保留"点确认才校验"的节奏）
  watch(entityDraft, () => { entityDraftError.value = '' }, { deep: true })
  function cancelEntityDraft() {
    resetEntityDraft()
  }
  function confirmEntityDraft() {
    const err = addEntityOption()
    entityDraftError.value = err
    if (!err) resetEntityDraft()
  }

  function entityDraftPickerOptions(): { label: string; value: string }[] {
    return entityOptionsForType(entityDraft.value.type)
  }

  /** 已配置候选行的对象下拉（含顶部「全选」哨兵项） */
  function entityRowPickerOptions(idx: number): { label: string; value: string }[] {
    const opt = entityOptions.value[idx]
    if (!opt) return []
    return withSelectAllOption(entityOptionsForType(opt.type), opt.ids || [])
  }
  /** 已配置候选行的选中值：全选时把哨兵项一起给出去（让「全选」呈选中态） */
  function entityRowPickerValue(idx: number): string[] {
    const opt = entityOptions.value[idx]
    if (!opt) return []
    const ids = opt.ids || []
    const base = entityOptionsForType(opt.type)
    return isAllSelected(base, ids) ? [SELECT_ALL, ...ids] : ids
  }
  function handleEntityRowPickerUpdate(idx: number, raw: string[]) {
    const opt = entityOptions.value[idx]
    if (!opt) return
    const base = entityOptionsForType(opt.type)
    const wasAll = isAllSelected(base, opt.ids || [])
    updateEntityOptionIds(idx, applySelectAll(raw, base, wasAll))
  }
  /** 草稿行的对象下拉 / 选中值（同款全选） */
  const entityDraftPickerOptionsAll = computed<{ label: string; value: string }[]>(() =>
    withSelectAllOption(entityDraftPickerOptions(), entityDraft.value.ids),
  )
  const entityDraftPickerValue = computed<string[]>(() => {
    const base = entityDraftPickerOptions()
    const ids = entityDraft.value.ids
    return isAllSelected(base, ids) ? [SELECT_ALL, ...ids] : ids
  })
  function handleEntityDraftPickerUpdate(raw: string[]) {
    const base = entityDraftPickerOptions()
    const wasAll = isAllSelected(base, entityDraft.value.ids)
    entityDraft.value.ids = applySelectAll(raw, base, wasAll)
  }
  /** 三处多选框的「是否全选」判定（标签区据此把全量折叠成单个「全部」chip） */
  function entityRowIsAll(idx: number): boolean {
    const opt = entityOptions.value[idx]
    if (!opt) return false
    return isAllSelected(entityOptionsForType(opt.type), opt.ids || [])
  }
  const entityDraftIsAll = computed<boolean>(() =>
    isAllSelected(entityDraftPickerOptions(), entityDraft.value.ids),
  )

  /** 新增候选：type 必选且未配过；指定类必须至少选一个对象 */
  function addEntityOption(): string {
    const type = entityDraft.value.type
    if (!type) return t('metrics.tpl.entitySelectorRequired')
    if (entityUsedTypes.value.includes(type)) return entityDuplicateTypeText(type)
    if (entityTypeNeedsPicker(type) && !entityDraft.value.ids.filter(Boolean).length) {
      return entityPickerRequiredText(type)
    }
    const vd = tplForm.value.valueDomain
    vd.kind = entityKind.value
    if (!Array.isArray(vd.options)) vd.options = []
    vd.options.push(makeEntityOption(type, entityDraft.value.ids))
    entityDraft.value = { type: '', ids: [] }
    return ''
  }

  function entityPickerRequiredText(type: string): string {
    if (type === 'identity') return t('metrics.tpl.entityIdentityRequired')
    if (type === 'specified' && isDeptOutput.value) return t('metrics.tpl.entityDeptRequired')
    return t('metrics.tpl.entityUserRequired')
  }

  function entityDuplicateTypeText(type: string): string {
    return t('metrics.tpl.entityTypeDuplicate', { type: entityTypeLabel(type) })
  }

  // ── 多选对象的「全部」支持（Naive UI 无内置项，用顶部哨兵项实现）──
  // 文案按兵哥要求叫「全部」；全选后标签区只回显一个「全部」，不铺开所有选项（见 AllChipTag）
  const SELECT_ALL = ED.SELECT_ALL
  function isSelectAllValue(v: string): boolean {
    return ED.isSelectAllValue(v)
  }
  /** 顶部插入「全部 / 取消全部」；已全选时该项本身也呈选中态 */
  function withSelectAllOption(opts: { label: string; value: string }[], current: string[]) {
    return ED.withSelectAllOption(opts, current, ED_LABELS)
  }
  /** 当前值是否已覆盖全部候选（用于把哨兵项渲染成选中态） */
  function isAllSelected(opts: { label: string; value: string }[], current: string[]): boolean {
    return ED.isAllSelected(opts, current)
  }
  /**
   * 全选哨兵项的值变化 → 真实 id 列表。
   * 三种情形要分清（Naive UI 不可区分"取消勾选全选项"与"逐个勾满"）：
   *   1. 勾上哨兵 → 全选；
   *   2. 原本全选、只取消哨兵（其余 id 仍在）→ 清空；
   *   3. 原本全选、取消某个具体项 → 保留剩余。
   */
  function applySelectAll(raw: string[], opts: { label: string; value: string }[], wasAll: boolean): string[] {
    return ED.applySelectAll(raw, opts, wasAll)
  }

  /** 生成一条候选（存id + label 快照：id 用于精确匹配，label 用于展示与改名后仍可读） */
  function makeEntityOption(type: string, ids: string[]) {
    return ED.makeEntityOption(type, ids, entityOptionsForType(type), ED_LABELS)
  }

  function entityAutoLabelKey(type: string): string {
    return ED.entityAutoLabelKey(type)
  }

  function removeEntityOption(idx: number) {
    const vd = tplForm.value.valueDomain
    if (Array.isArray(vd.options)) vd.options.splice(idx, 1)
  }

  /** 修改某条候选的对象选择（换人/换身份后要同步刷新 label 快照） */
  function updateEntityOptionIds(idx: number, ids: string[]) {
    const vd = tplForm.value.valueDomain
    const opt = Array.isArray(vd.options) ? vd.options[idx] : null
    if (!opt) return
    const merged = makeEntityOption(opt.type, ids)
    vd.options[idx] = { ...opt, ids: merged.ids, label: merged.label }
  }

  /** 候选类型的中文标签（列表展示用） */
  function entityTypeLabel(type: string): string {
    return entitySelectorOptions.value.find((o) => o.value === type)?.label || type
  }

  /**
   * 候选清单 → 候选下拉项。
   * value 用可解析的 JSON 串（type + ids），既保留"选哪种方式"的信息，
   * 又能直接喂给枚举型复用的 previewNeedsEnumPicker 路径 —— 与枚举型行为完全一致。
   */
  const entityCandidateOptions = computed<{ label: string; value: string }[]>(() =>
    entityOptions.value.map((o, i) => ({
      label: o.label || entityTypeLabel(o.type),
      value: JSON.stringify({ t: o.type, i: i, ids: o.ids || [] }),
    })),
  )


  return {
    SELECT_ALL,
    addEntityOption,
    applySelectAll,
    cancelEntityDraft,
    confirmEntityDraft,
    ensureEntityOptions,
    entityAutoLabelKey,
    entityCandidateOptions,
    entityDefaultSelector,
    entityDomain,
    entityDraft,
    entityDraftError,
    entityDraftIsAll,
    entityDraftPickerOptions,
    entityDraftPickerOptionsAll,
    entityDraftPickerValue,
    entityDraftVisible,
    entityDuplicateTypeText,
    entityIdentities,
    entityOptions,
    entityOptionsForType,
    entityOptionsLoaded,
    entityOptionsLoading,
    entityPickerRequiredText,
    entityRowIsAll,
    entityRowPickerOptions,
    entityRowPickerValue,
    entitySelectorOptions,
    entityTypeLabel,
    entityTypeNeedsPicker,
    entityTypesExhausted,
    entityUnits,
    entityUnusedSelectorOptions,
    entityUsedTypes,
    entityUsers,
    handleEntityDraftPickerUpdate,
    handleEntityRowPickerUpdate,
    isAllSelected,
    isSelectAllValue,
    makeEntityOption,
    removeEntityOption,
    resetEntityDraft,
    showEntityDraft,
    toEntityOptions,
    updateEntityOptionIds,
    withSelectAllOption,
  }
}
