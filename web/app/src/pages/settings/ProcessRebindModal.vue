<!--
  流程「改绑引用需求」弹窗 — 方案 A（2026-10-16）

  为什么存在：流程被需求引用时不能删除，而后端 perform_destroy 只报一句
  「被 N 个需求引用，不可删除」，用户既看不到是哪 N 条需求，也没有「换流程」的
  出路（此前全仓不存在任何解绑/改绑能力，Demand.process 又是 NOT NULL + PROTECT，
  结果就是流程被永久钉死）。本弹窗把出路摆出来：列出引用需求 → 选目标流程 → 改绑。

  三条硬约束（与后端 DemandService.rebind_demand_process 一一对应，改动须同步）：
  1. 目标流程只列 **ENABLED + is_latest + 未软删** 的行 —— 后端对这三条各有一道
     StateTransitionError，前端先过滤不是优化，是避免用户白提交一次。
  2. 当前流程自己要从候选里排除（后端允许同流程幂等，但让人选自己是荒谬的）。
  3. 改绑只动需求与其名下 live 职位，**在跑候选人不受影响**（BR-102）；
     若需求下有在跑申请，后端返 409，文案已在 s40 之前由 message 直出。

  提交语义：rebound=false 表示幂等成功（本来就挂着目标流程），不是失败。
-->
<template>
  <n-modal
    :show="show"
    preset="card"
    class="process-rebind-modal"
    style="width: 760px; max-width: 95vw"
    :mask-closable="!submitting"
    :title="t('pages.settings.RecruitmentProcess.s27', { name: props.processName ?? '' })"
    :bordered="false"
    :segmented="{ content: true, footer: true }"
    @update:show="onUpdateShow"
  >
    <n-alert v-if="blockedHint" type="warning" :show-icon="true" class="rb-alert">
      {{ blockedHint }}
    </n-alert>

    <n-spin :show="loading">
      <div class="rb-body">
        <n-empty
          v-if="!loading && demands.length === 0"
          size="small"
          :description="t('pages.settings.RecruitmentProcess.s30')"
        />

        <n-data-table
          v-else
          :columns="columns"
          :data="demands"
          :row-key="(r: any) => r.id"
          :pagination="false"
          size="small"
          flex-height
          :style="{ height: '320px' }"
        />
      </div>
    </n-spin>

    <template #footer>
      <div class="rb-footer">
        <n-button :disabled="submitting" @click="onUpdateShow(false)">
          {{ t('common.cancel') }}
        </n-button>
        <n-button type="primary" :loading="submitting" @click="handleRebindAll">
          <template #icon><n-icon :component="SwapHorizontalOutline" /></template>
          {{ t('pages.settings.RecruitmentProcess.s36') }}
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * 流程引用改绑弹窗。
 *
 * 交互：表格列出引用本流程的需求，每行一个「改绑到」下拉；底部「确认改绑」把所有
 * **已选择**的行一次性提交（逐条 await，串行而非 Promise.all —— 后端每条都要
 * 409 判定在跑申请，并发改绑同一批职位，并发会互相踩）。
 */
import { computed, h, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage, NAlert, NButton, NDataTable, NEmpty, NIcon, NModal, NSelect, NSpin, useDialog } from 'naive-ui'
import { SwapHorizontalOutline } from '@vicons/ionicons5'

import { listDemands, rebindDemandProcess } from '@/api/demand'
import { listProcesses } from '@/api/recruitment-process'
import { column } from '@/composables/useTableColumns'

const { t } = useI18n()
const message = useMessage()
const dialog = useDialog()

const show = defineModel<boolean>('show', { type: Boolean, default: false })
const props = defineProps<{ processId: string; processName?: string }>()
const emit = defineEmits<{ rebound: []; close: [] }>()

const loading = ref(false)
const submitting = ref(false)
const demands = ref<any[]>([])
/** 可选目标流程：ENABLED + is_latest + 未软删，且排除当前流程自己。 */
const targetOptions = ref<{ label: string; value: string }[]>([])
/** demandId → 选中的目标流程 id（只存「选了的」，没选的行不提交）。 */
const picked = ref<Record<string, string>>({})

const blockedHint = computed(() => {
  const n = demands.value.length
  if (!n) return ''
  return t('pages.settings.RecruitmentProcess.s28', { count: n })
})

async function load() {
  if (!props.processId) return
  loading.value = true
  try {
    const [dList, pList] = await Promise.all([
      listDemands({ process: props.processId } as any),
      listProcesses({ status: 'ENABLED' }),
    ])
    demands.value = Array.isArray(dList) ? dList : []
    // 后端 filterset 已保证只回本流程的需求；前端再按 id 兜一道，
    // 防止后端加/改 filter 时静默回全量（那会让用户改绑到不相干的流程上）。
    demands.value = demands.value.filter((d: any) => d.process === props.processId)
    targetOptions.value = (Array.isArray(pList) ? pList : [])
      .filter((p: any) => p.id !== props.processId && p.status === 'ENABLED' && p.isLatest !== false)
      .map((p: any) => ({ label: `${p.code} ${p.name}`, value: p.id }))
    picked.value = {}
  } catch (e: any) {
    message.error(t('pages.settings.RecruitmentProcess.s42'))
  } finally {
    loading.value = false
  }
}

const columns = computed(() => [
  column({ title: t('pages.settings.RecruitmentProcess.s31'), key: 'code', width: 130 }, 'short'),
  column({ title: t('pages.settings.RecruitmentProcess.s32'), key: 'title', ellipsis: true }),
  column({ title: t('pages.settings.RecruitmentProcess.s33'), key: 'state', width: 90 }, 'short'),
  column({
    title: t('pages.settings.RecruitmentProcess.s34'),
    key: 'target',
    width: 300,
    render: (row: any) => h(NSelect, {
      size: 'small',
      filterable: true,
      clearable: true,
      options: targetOptions.value,
      placeholder: t('pages.settings.RecruitmentProcess.s35'),
      value: picked.value[row.id] ?? null,
      'onUpdate:value': (v: string | null) => {
        const next = { ...picked.value }
        if (v === null) delete next[row.id]
        else next[row.id] = v
        picked.value = next
      },
    }),
  }, 'control'),
])

async function handleRebindAll() {
  const ids = Object.keys(picked.value)
  if (ids.length === 0) {
    message.warning(t('pages.settings.RecruitmentProcess.s41'))
    return
  }
  const targets = new Set(Object.values(picked.value))
  if (targets.size > 1) {
    dialog.warning({
      title: t('pages.settings.RecruitmentProcess.s34'),
      content: t('pages.settings.RecruitmentProcess.s37', {
        count: ids.length,
        process: targets.size,
      }),
      positiveText: t('common.confirm'),
      negativeText: t('common.cancel'),
      onPositiveClick: () => doRebind(ids),
    })
    return
  }
  await doRebind(ids)
}

async function doRebind(ids: string[]) {
  submitting.value = true
  let ok = 0
  let movedTotal = 0
  const failures: string[] = []
  // 串行：并发改绑同一批职位会互相覆盖，且后端逐条判定在跑申请需要串行快照。
  for (const id of ids) {
    const target = picked.value[id]
    if (!target) continue
    try {
      const res = await rebindDemandProcess(id, target)
      ok += 1
      movedTotal += res?.moved_position_ids?.length ?? 0
    } catch (e: any) {
      const body = e?.response?.data
      failures.push(`${demands.value.find((d: any) => d.id === id)?.code ?? id}: ${body?.message ?? ''}`)
    }
  }
  submitting.value = false

  if (ok > 0) {
    message.success(
      movedTotal > 0
        ? `${t('pages.settings.RecruitmentProcess.s38')}（${t('pages.settings.RecruitmentProcess.s39', { count: movedTotal })}）`
        : t('pages.settings.RecruitmentProcess.s38'),
    )
  }
  if (failures.length > 0) {
    // 409 的文案（"还有 N 个在跑的候选人申请…"）必须透出，否则用户不知道为什么失败。
    dialog.error({
      title: t('pages.settings.RecruitmentProcess.s40'),
      content: failures.join('\n'),
      positiveText: t('common.confirm'),
    })
  }
  if (ok > 0) {
    emit('rebound')
    await load()
  }
}

function onUpdateShow(v: boolean) {
  if (submitting.value) return
  show.value = v
  if (v) load()
  else emit('close')
}

watch(() => props.processId, () => {
  if (show.value) load()
})
</script>

<style scoped>
.rb-alert { margin-bottom: 12px; }
.rb-body { min-height: 160px; }
.rb-footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
