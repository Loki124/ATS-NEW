/**
 * 主表单 state + 加载 / 保存 / 校验编排
 * - 并发加载：listStageRules + listEntryConditionRules（Promise.all，全部 resolve 才解除 loading）
 * - 保存：StageRule 主链路（含 skip_rules/archive_rules JSON）+ 进入条件规则逐条 create/update/delete
 * - R6 根治：不再有 activeTab 概念，保存时遍历所有 card 数据全量提交
 */
import { reactive, ref } from 'vue'
import {
  listStageRules,
  listEntryConditionRules,
  listEntryConditionFields,
  upsertStageRule,
  createEntryConditionRule,
  updateEntryConditionRule,
  deleteEntryConditionRule,
  reorderEntryConditionRules,
} from '../../../../api/recruitment-process'
import type { EntryConditionRule, SkipRule, ArchiveRule, StageRuleFormState, ConditionItem, SourceKey, OperatorKey } from '../types'

function defaultForm(): StageRuleFormState {
  return {
    defaultHandlerType: 'FROM_DEMAND',
    defaultHandlerFields: [],
    defaultHandlerUserIds: [],
    interviewRoundIds: [],
    interviewFormat: [],
    autoEvalN2: false,
    autoEvalPrevAa: false,
    autoAdvanceType: 'NONE',
    autoAdvanceTiming: 'IMMEDIATE',
    autoAdvanceDays: null,
    skipEnabled: false,
    archiveEnabled: false,
  }
}

/** 将前端 ConditionItem 规整为后端 payload（仅传后端识别字段） */
function serializeItem(it: ConditionItem) {
  const out: Record<string, any> = {
    item_seq: it.item_seq,
    condition_type: it.condition_type,
    field: it.field,
    operator: it.operator,
  }
  if (it.condition_type === 'STAGE_STATUS') {
    if (it.field === 'stage_name') out.stage_name = it.stage_name ?? null
    if (it.field === 'stage_statuses') out.stage_statuses = it.stage_statuses ?? []
  }
  out.auto_filter_inactive_users = it.auto_filter_inactive_users ?? false
  const noValue = it.operator === 'IS_EMPTY' || it.operator === 'IS_NOT_EMPTY'
  out.value = noValue ? null : it.value ?? null
  return out
}

function serializeEntry(r: EntryConditionRule) {
  return {
    rule_name: r.rule_name,
    rule_seq: r.rule_seq,
    status: r.status,
    expression: r.expression,
    reject_message: r.reject_message,
    items: r.items.map(serializeItem),
  }
}

/** 规范化后端枚举值，兼容历史/遗留数据（避免 round-trip 时因非法 choices 触发 400）。
 * 仅在值非法时映射/兜底，合法值原样透传；合法化后下次保存即固化，不再需要兜底。 */
const VALID_STATUS = ['ENABLED', 'DISABLED']
const VALID_CONDITION_TYPE = ['STAGE_STATUS', 'CANDIDATE', 'DEMAND']
const VALID_OPERATOR = ['EQ', 'NEQ', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN', 'IN', 'NOT_IN', 'IS_EMPTY', 'IS_NOT_EMPTY']
const STATUS_LEGACY: Record<string, string> = { ACTIVE: 'ENABLED', INACTIVE: 'DISABLED', ON: 'ENABLED', OFF: 'DISABLED' }
const CONDITION_TYPE_LEGACY: Record<string, string> = { STAGE: 'STAGE_STATUS', PERSON: 'CANDIDATE', REQUIREMENT: 'DEMAND' }
const OPERATOR_LEGACY: Record<string, string> = {
  EQUALS: 'EQ', EQUAL: 'EQ', '=': 'EQ', '==': 'EQ',
  NOT_EQUALS: 'NEQ', NOT_EQUAL: 'NEQ', '<>': 'NEQ', '!=': 'NEQ',
  GREATER_THAN: 'GT', '>': 'GT', GT: 'GT',
  GREATER_THAN_OR_EQUAL: 'GTE', '>=': 'GTE',
  LESS_THAN: 'LT', '<': 'LT',
  LESS_THAN_OR_EQUAL: 'LTE', '<=': 'LTE',
}
function normStatus(v: any): 'ENABLED' | 'DISABLED' {
  if (VALID_STATUS.includes(v)) return v
  return (STATUS_LEGACY[String(v ?? '').toUpperCase()] as 'ENABLED' | 'DISABLED') || 'ENABLED'
}
function normConditionType(v: any): SourceKey {
  if (VALID_CONDITION_TYPE.includes(v)) return v
  return (CONDITION_TYPE_LEGACY[String(v ?? '').toUpperCase()] as SourceKey) || 'DEMAND'
}
function normOperator(v: any): OperatorKey {
  if (VALID_OPERATOR.includes(v)) return v
  return (OPERATOR_LEGACY[String(v ?? '').toUpperCase()] as OperatorKey) || 'EQ'
}

export function useStageRuleForm() {
  const form = reactive<StageRuleFormState>(defaultForm())
  const entryRules = ref<EntryConditionRule[]>([])
  const skipRules = ref<SkipRule[]>([])
  const archiveRules = ref<ArchiveRule[]>([])
  const catalog = ref<any>(null)
  const loading = ref(false)
  const saving = ref(false)
  const loadError = ref('')

  /** 加载时已存在的 entry rule id，用于保存时 diff 删除 */
  const loadedEntryIds = ref<string[]>([])

  function applyStageRule(sr: any) {
    if (!sr) return
    form.defaultHandlerType = sr.defaultHandlerType || 'FROM_DEMAND'
    form.defaultHandlerFields = sr.defaultHandlerFields || []
    form.defaultHandlerUserIds = sr.defaultHandlerUserIds || []
    form.interviewRoundIds = sr.interviewRoundIds || []
    form.interviewFormat = sr.interviewFormat ? String(sr.interviewFormat).split(',').filter(Boolean) : []
    form.autoEvalN2 = !!sr.autoSkipNPlusTwo
    form.autoEvalPrevAa = !!sr.inheritPriorConsensus
    form.autoAdvanceType = sr.autoAdvanceType || 'NONE'
    form.autoAdvanceTiming = sr.autoAdvanceTiming || 'IMMEDIATE'
    form.autoAdvanceDays = sr.autoAdvanceDays ?? null
    // skip / archive 规则（后端 StageRule JSONField，前端先写库）
    const sk = Array.isArray(sr.skip_rules) ? sr.skip_rules : []
    const ar = Array.isArray(sr.archive_rules) ? sr.archive_rules : []
    skipRules.value = sk.map((x: any) => ({
      id: x.id,
      name: x.name || '',
      enabled: x.enabled !== false,
      scope: x.scope || 'NEW_ONLY',
      expression: x.expression || '',
      items: (x.items || []).map((it: any) => ({ ...it })),
      action: x.action || 'SKIP',
    }))
    archiveRules.value = ar.map((x: any) => ({
      id: x.id,
      name: x.name || '',
      enabled: x.enabled !== false,
      scope: x.scope || 'NEW_ONLY',
      expression: x.expression || '',
      items: (x.items || []).map((it: any) => ({ ...it })),
      lock_days: x.lock_days ?? 0,
      extend_days: x.extend_days ?? 0,
      effective_scope: x.effective_scope || 'ALL',
    }))
    form.skipEnabled = skipRules.value.length > 0
    form.archiveEnabled = archiveRules.value.length > 0
  }

async function loadFields() {
  try {
    catalog.value = await listEntryConditionFields()
  } catch {
    catalog.value = null
  }
}

  async function load(linkId: string) {
    if (!linkId) return
    loading.value = true
    loadError.value = ''
    try {
      const [stageRules, entryList] = await Promise.all([
        listStageRules({ linkId }).catch(() => []),
        listEntryConditionRules({ linkId }).catch(() => [] as any[]),
      ])
      const sr = Array.isArray(stageRules) ? stageRules[0] : null
      applyStageRule(sr)
      entryRules.value = (entryList || [])
        .slice()
        .sort((a: any, b: any) => (a.rule_seq || 0) - (b.rule_seq || 0))
        .map((r: any) => ({
          id: r.id,
          rule_name: r.rule_name || '',
          rule_seq: r.rule_seq || 0,
          // 规范化遗留枚举（status / condition_type / operator），避免 round-trip 400
          status: normStatus(r.status),
          expression: r.expression || '',
          reject_message: r.reject_message || '',
          items: (r.items || []).map((it: any) => ({
            ...it,
            condition_type: normConditionType(it.condition_type),
            operator: normOperator(it.operator),
          })),
        }))
      loadedEntryIds.value = entryRules.value.filter((r) => r.id).map((r) => r.id as string)
      // 字段字典非阻塞加载（P0-1：不再注入 demo 脏数据，空配置即真实空配置）
      loadFields()
    } catch (e: any) {
      loadError.value = e?.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function save(linkId: string): Promise<boolean> {
    if (!linkId) return false
    saving.value = true
    try {
      await upsertStageRule(linkId, {
        autoAdvanceType: form.autoAdvanceType,
        autoAdvanceTiming: form.autoAdvanceTiming,
        autoAdvanceDays: form.autoAdvanceTiming === 'DELAYED' ? (form.autoAdvanceDays ?? undefined) : undefined,
        defaultHandlerType: form.defaultHandlerType === 'NONE' ? undefined : form.defaultHandlerType,
        defaultHandlerFields: form.defaultHandlerFields,
        defaultHandlerUserIds: form.defaultHandlerUserIds,
        timeLimit: undefined,
        timeLimitScope: 'NEW_ONLY',
        interviewRoundIds: form.interviewRoundIds,
        inheritPriorConsensus: form.autoEvalPrevAa,
        isGrabMode: form.autoEvalN2,
        grabThreshold: 30,
        interviewFormat: form.interviewFormat.join(','),
        skip_rules: skipRules.value,
        archive_rules: archiveRules.value,
      })
      // 进入条件规则：逐条 create / update + 删除移除项
      const currentIds = entryRules.value.filter((r) => r.id).map((r) => r.id as string)
      const toDelete = loadedEntryIds.value.filter((id) => !currentIds.includes(id))
      entryRules.value.forEach((r, i) => (r.rule_seq = i + 1))
      for (const r of entryRules.value) {
        const payload = serializeEntry(r)
        if (r.id) {
          await updateEntryConditionRule(r.id, payload)
        } else {
          const created = await createEntryConditionRule({ link_id: linkId, ...payload })
          r.id = created?.id ?? r.id
        }
      }
      for (const id of toDelete) {
        await deleteEntryConditionRule(id).catch(() => {})
      }
      // 重排（seq 已按索引；reorder 兜底，失败不阻断）
      const ordered = entryRules.value.filter((r) => r.id).map((r, i) => ({ rule_id: r.id as string, rule_seq: i + 1 }))
      if (ordered.length) await reorderEntryConditionRules(ordered).catch(() => {})
      loadedEntryIds.value = entryRules.value.filter((r) => r.id).map((r) => r.id as string)
      return true
    } finally {
      saving.value = false
    }
  }

  function reset() {
    Object.assign(form, defaultForm())
    entryRules.value = []
    skipRules.value = []
    archiveRules.value = []
    catalog.value = null
    loadError.value = ''
  }

  return {
    form,
    entryRules,
    skipRules,
    archiveRules,
    catalog,
    loading,
    saving,
    loadError,
    load,
    save,
    reset,
  }
}

export type { SourceKey, OperatorKey }
