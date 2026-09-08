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

/**
 * demo 种子数据（对齐 HTML 原型 DOMContentLoaded 初始化块）
 * 后端无数据时注入，让主弹窗呈现原型演示态（有规则行 + 开关开启 + N+2 勾选）。
 * 有真实数据时不注入，避免覆盖用户已保存的配置。
 */
function seedDemoIfEmpty() {
  if (entryRules.value.length === 0) {
    entryRules.value = [
      {
        rule_name: 'HRBP阶段',
        rule_seq: 1,
        status: 'ENABLED',
        expression: '1 and 2',
        reject_message: '需HRBP全部已反馈',
        items: [
          {
            item_seq: 1,
            condition_type: 'STAGE_STATUS',
            field: 'stage_statuses',
            operator: 'IN',
            value: ['全部通过', '全部不通过', '部分通过'],
          },
          {
            item_seq: 2,
            condition_type: 'DEMAND',
            field: 'DEMAND_LEVEL',
            operator: 'IN',
            value: ['助理'],
          },
        ],
      },
    ]
  }
  if (skipRules.value.length === 0) {
    skipRules.value = [
      {
        id: 'demo-skip-1',
        name: '跳过1',
        enabled: true,
        scope: 'NEW_ONLY',
        expression: '1',
        items: [
          {
            item_seq: 1,
            condition_type: 'STAGE_STATUS',
            field: 'stage_statuses',
            operator: 'IN',
            value: ['已接受其他offer'],
          },
        ],
        action: 'SKIP',
      },
    ]
  }
  if (archiveRules.value.length === 0) {
    archiveRules.value = [
      {
        id: 'demo-archive-1',
        name: '30',
        enabled: true,
        scope: 'NEW_ONLY',
        expression: '1 and 2',
        items: [
          { item_seq: 1, condition_type: 'CANDIDATE', field: 'GENDER', operator: 'IS_EMPTY', value: null },
          { item_seq: 2, condition_type: 'CANDIDATE', field: 'GENDER', operator: 'IS_NOT_EMPTY', value: null },
        ],
        lock_days: 30,
        extend_days: 0,
        effective_scope: 'ALL',
      },
      {
        id: 'demo-archive-2',
        name: '阿萨德',
        enabled: true,
        scope: 'NEW_ONLY',
        expression: '1',
        items: [
          {
            item_seq: 1,
            condition_type: 'DEMAND',
            field: 'DEPARTMENT',
            operator: 'IN',
            value: ['能效BG_共89项', '数据智能中心_共32项', '智能制造BG_共58项', '国内营销_共17项', '海外营销_共23项'],
          },
        ],
        lock_days: 23,
        extend_days: 23,
        effective_scope: 'ALL',
      },
    ]
  }
  // 原型演示态：跳过 / 归档模块开启，N+2 推荐免筛选默认勾选
  form.skipEnabled = true
  form.archiveEnabled = true
  form.autoEvalN2 = true
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
          status: r.status || 'ENABLED',
          expression: r.expression || '',
          reject_message: r.reject_message || '',
          items: (r.items || []).map((it: any) => ({ ...it })),
        }))
      loadedEntryIds.value = entryRules.value.filter((r) => r.id).map((r) => r.id as string)
      // 无真实数据时注入原型 demo（呈现演示态，不覆盖已有配置）
      seedDemoIfEmpty()
      // 字段字典非阻塞加载
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
        autoAdvanceDays: form.autoAdvanceTiming === 'DELAYED' ? form.autoAdvanceDays : null,
        defaultHandlerType: form.defaultHandlerType,
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
      const ordered = entryRules.value.filter((r) => r.id).map((r, i) => ({ id: r.id as string, rule_seq: i + 1 }))
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
