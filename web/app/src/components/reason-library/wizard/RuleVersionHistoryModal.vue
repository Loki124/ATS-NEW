<template>
  <n-modal
    :show="show"
    preset="card"
    :title="t('reasonLibrary.wizard.historyTitle')"
    style="max-width: 640px"
    :mask-closable="false"
    :bordered="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <n-spin :show="loading" :description="t('reasonLibrary.common.loading')">
      <div v-if="!loading && versions.length === 0" class="ver-empty">
        {{ t('reasonLibrary.wizard.history.empty') }}
      </div>
      <div v-else class="ver-list">
        <div
          v-for="v in versions"
          :key="v.id"
          class="ver-item"
          :class="{ current: currentVersion != null && v.version === currentVersion }"
        >
          <div class="ver-head">
            <span class="ver-no">v{{ v.version }}</span>
            <n-tag size="tiny" :type="kindTagType(v.changeKind)" :bordered="false">
              {{ kindLabel(v.changeKind) }}
            </n-tag>
            <span v-if="currentVersion != null && v.version === currentVersion" class="ver-current-badge">
              {{ t('reasonLibrary.wizard.history.current') }}
            </span>
            <span class="ver-time">{{ formatTime(v.createdAt) }}</span>
            <n-button
              v-if="currentVersion == null || v.version !== currentVersion"
              size="tiny"
              type="primary"
              ghost
              class="ver-rollback-btn"
              :loading="rollingBack === v.version"
              @click="onRollback(v)"
            >
              {{ t('reasonLibrary.wizard.history.rollback') }}
            </n-button>
          </div>
          <div v-if="v.changeNote" class="ver-note">{{ v.changeNote }}</div>
          <div v-if="v.changedFields && v.changedFields.length" class="ver-fields">
            <span class="ver-fields-label">{{ t('reasonLibrary.wizard.history.changedFields') }}</span>
            <n-tag
              v-for="f in v.changedFields"
              :key="f"
              size="tiny"
              :bordered="false"
              type="default"
              class="ver-field-tag"
            >
              {{ f }}
            </n-tag>
          </div>
          <div v-if="v.createdBy" class="ver-by">#{{ v.createdBy }}</div>
        </div>
      </div>
    </n-spin>
    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('update:show', false)">{{ t('reasonLibrary.common.close') }}</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * RuleVersionHistoryModal (2026-09 — 历史版本号 Task)
 * 浏览某条规则的版本快照列表, 支持回滚到任意历史版本。
 * - 列表按版本号降序 (后端 ordering=['-version'])
 * - 当前版本 (currentVersion) 高亮且不可回滚自身
 * - 回滚经 useDialog 二次确认, 调用 rollbackRuleVersion; 成功后 emit('rollbacked', rule)
 *   由父组件 (ReasonRuleWizard) 原地重建向导草稿。
 */
import { ref, watch } from 'vue'
import { NModal, NButton, NTag, NSpin, NSpace, useMessage, useDialog } from 'naive-ui'
import { listRuleVersions, rollbackRuleVersion, extractReasonApiError } from '../../../api/reason-library'
import type { SceneRule, SceneRuleVersion } from '../../../types/reason-library'
import { BIZ_CODE } from '../../../types/reason-library'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  show: boolean
  ruleId: string
  /** 当前版本号 — 用于高亮并禁止回滚自身 */
  currentVersion?: number
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'rollbacked', rule: SceneRule): void
}>()

const message = useMessage()
const dialog = useDialog()

const versions = ref<SceneRuleVersion[]>([])
const loading = ref(false)
const rollingBack = ref<number | null>(null)

watch(
  () => [props.show, props.ruleId] as const,
  async ([show, ruleId]) => {
    if (!show || !ruleId) return
    loading.value = true
    versions.value = []
    try {
      versions.value = await listRuleVersions(ruleId)
    } catch (e: any) {
      message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

function kindLabel(kind: SceneRuleVersion['changeKind']): string {
  switch (kind) {
    case 'create': return t('reasonLibrary.wizard.history.changeKind.create')
    case 'update': return t('reasonLibrary.wizard.history.changeKind.update')
    case 'rollback': return t('reasonLibrary.wizard.history.changeKind.rollback')
    case 'import': return t('reasonLibrary.wizard.history.changeKind.import')
    default: return kind
  }
}

function kindTagType(kind: SceneRuleVersion['changeKind']): 'success' | 'info' | 'warning' | 'primary' | 'default' {
  switch (kind) {
    case 'create': return 'success'
    case 'update': return 'info'
    case 'rollback': return 'warning'
    case 'import': return 'primary'
    default: return 'default'
  }
}

function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function onRollback(v: SceneRuleVersion) {
  if (!props.ruleId) return
  dialog.warning({
    title: t('reasonLibrary.wizard.history.rollbackConfirmTitle'),
    content: t('reasonLibrary.wizard.history.rollbackConfirm', { version: v.version }),
    positiveText: t('reasonLibrary.common.confirm'),
    negativeText: t('reasonLibrary.common.cancel'),
    onPositiveClick: async () => {
      rollingBack.value = v.version
      try {
        const result = await rollbackRuleVersion(props.ruleId, v.version)
        message.success(t('reasonLibrary.wizard.history.rollbackSuccess', { version: v.version }))
        emit('rollbacked', result)
        emit('update:show', false)
      } catch (e: any) {
        if (e?.code === BIZ_CODE.RULE_SCENE_CONFLICT) {
          message.error(t('reasonLibrary.errors.RULE_SCENE_CONFLICT'))
        } else {
          message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
        }
      } finally {
        rollingBack.value = null
      }
    },
  })
}
</script>

<style scoped>
.ver-empty {
  padding: var(--space-6) 0;
  text-align: center;
  font-size: var(--fs-13);
  color: var(--ink-faint);
}
.ver-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-height: 60vh;
  overflow-y: auto;
}
.ver-item {
  padding: var(--space-3);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.ver-item.current {
  border-color: var(--brand);
  background: var(--brand-soft, rgba(32, 128, 240, 0.08));
}
.ver-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.ver-no {
  font-size: var(--fs-13);
  font-weight: 700;
  color: var(--ink);
}
.ver-current-badge {
  font-size: var(--fs-11);
  font-weight: 600;
  color: var(--brand);
  background: var(--brand-soft, rgba(32, 128, 240, 0.12));
  border-radius: 999px;
  padding: 1px 8px;
}
.ver-time {
  font-size: var(--fs-11);
  color: var(--ink-faint);
  margin-left: auto;
}
.ver-rollback-btn {
  margin-left: var(--space-2);
}
.ver-note {
  margin-top: var(--space-2);
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1.5;
}
.ver-fields {
  margin-top: var(--space-2);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.ver-fields-label {
  font-size: var(--fs-11);
  color: var(--ink-faint);
}
.ver-field-tag { font-family: var(--font-mono, monospace); }
.ver-by {
  margin-top: var(--space-1);
  font-size: var(--fs-11);
  color: var(--ink-faint);
}
</style>
