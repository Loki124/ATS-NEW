<template>
  <n-modal
    :show="show"
    preset="card"
    class="am-modal"
    :title="t('dataperm.actions.title')"
    :style="{ width: '860px' }"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <n-alert type="info" :bordered="false" class="am-desc">
      {{ t('dataperm.actions.desc') }}
    </n-alert>

    <!-- 动作字典 -->
    <n-data-table
      :columns="actionColumns"
      :data="actions"
      :bordered="false"
      size="small"
      :row-key="(r: any) => r.key"
    />

    <!-- 预设包 -->
    <div class="preset-block">
      <div class="preset-head">
        <span class="preset-title">{{ t('dataperm.actions.presetsTitle') }}</span>
        <n-button size="small" secondary type="primary" @click="openPresetForm()">
          {{ t('dataperm.actions.addPreset') }}
        </n-button>
      </div>
      <div class="preset-list">
        <n-tag
          v-for="p in presets"
          :key="p.key"
          size="large"
          :bordered="p.is_system !== true"
          class="preset-tag"
        >
          {{ p.label }}（{{ (p.actionKeys || []).length }}）
          <n-button
            v-if="!p.is_system"
            text
            size="tiny"
            class="preset-edit"
            @click="openPresetForm(p)"
          >
            {{ t('dataperm.actions.edit') }}
          </n-button>
        </n-tag>
      </div>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('update:show', false)">{{ t('dataperm.actions.cancel') }}</n-button>
      </n-space>
    </template>

    <!-- 动作/预设编辑表单 -->
    <n-modal
      :show="formShow"
      preset="card"
      :style="{ width: '520px' }"
      :title="formTitle"
      @update:show="(v: boolean) => (formShow = v)"
    >
      <n-form label-placement="top">
        <n-form-item v-if="!editingKey" :label="t('dataperm.actions.formKey')">
          <n-input v-model:value="form.key" :placeholder="t('dataperm.actions.formKey')" />
        </n-form-item>
        <n-form-item :label="t('dataperm.actions.formLabel')">
          <n-input v-model:value="form.label" />
        </n-form-item>
        <template v-if="formKind === 'action'">
          <n-form-item :label="t('dataperm.actions.formCategory')">
            <n-select v-model:value="form.category" :options="categoryOptions" />
          </n-form-item>
        </template>
        <n-form-item v-if="formKind === 'preset'" :label="t('dataperm.actions.formActions')">
          <n-select
            v-model:value="form.actionKeys"
            multiple
            :options="actionSelectOptions"
          />
        </n-form-item>
        <n-form-item v-if="formKind === 'action' && editingKey">
          <n-checkbox v-model:checked="form.enabled">{{ t('dataperm.actions.enabled') }}</n-checkbox>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="formShow = false">{{ t('dataperm.actions.cancel') }}</n-button>
          <n-button type="primary" :loading="formSaving" @click="submitForm">
            {{ t('dataperm.actions.save') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * ActionManageModal.vue — 动作字典 / 预设包管理（权限 v2，仅超管）。
 *
 * 数据源是后端可配置字典（/data-permissions/actions/ 等），本组件只做 CRUD 壳：
 * 业务护栏（custom_ 前缀 / 系统动作锁定 / 被引用不可删）全部由后端裁决，
 * 前端只透出错误信息 —— 权限系统的规则单源在后端，UI 不重复实现（避免双源漂移）。
 */
import { computed, h, ref, watch } from 'vue'
import {
  NModal, NAlert, NDataTable, NButton, NTag, NSpace, NForm, NFormItem,
  NInput, NSelect, NCheckbox, NSwitch, useMessage,
} from 'naive-ui'
import { useI18n } from 'vue-i18n'
import {
  listActions, createAction, updateAction, deleteAction,
  listActionPresets, createActionPreset, updateActionPreset, deleteActionPreset,
  type ActionDictItem, type ActionPreset,
} from '@/api/data-permission'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void }>()
const { t } = useI18n()
const message = useMessage()

const actions = ref<ActionDictItem[]>([])
const presets = ref<ActionPreset[]>([])
const loadingActions = ref(false)

async function reload() {
  loadingActions.value = true
  try {
    const [a, p] = await Promise.all([listActions(), listActionPresets()])
    actions.value = a
    presets.value = p
  } catch (e: any) {
    message.error(e?.message || String(e))
  } finally {
    loadingActions.value = false
  }
}

watch(() => props.show, (v) => { if (v) reload() })

// ===== 动作表格 =====

function renderSwitch(row: ActionDictItem) {
  return h(NSwitch, {
    value: row.enabled,
    size: 'small',
    onUpdateValue: async (v: boolean) => {
      try {
        await updateAction(row.key, { enabled: v })
        row.enabled = v
        invalidateAfterChange()
      } catch (e: any) {
        message.error(e?.response?.data?.message || String(e))
      }
    },
  })
}

function renderOps(row: ActionDictItem) {
  const ops = [
    h(NButton, {
      text: true, type: 'primary', size: 'small', class: 'op-btn',
      onClick: () => openActionForm(row),
    }, { default: () => t('dataperm.actions.edit') }),
  ]
  if (!row.is_system) {
    ops.push(h(NButton, {
      text: true, type: 'error', size: 'small', class: 'op-btn',
      onClick: () => removeAction(row),
    }, { default: () => t('dataperm.actions.delete') }))
  }
  return ops
}

const actionColumns = computed(() => [
  { title: t('dataperm.actions.colKey'), key: 'key', width: 200 },
  { title: t('dataperm.actions.colLabel'), key: 'label', width: 140 },
  { title: t('dataperm.actions.colCategory'), key: 'category', width: 100 },
  {
    title: t('dataperm.actions.colSystem'), key: 'is_system', width: 90,
    render: (row: ActionDictItem) => h(NTag, {
      size: 'small', bordered: false, type: row.is_system ? 'default' : 'info',
    }, { default: () => (row.is_system ? t('dataperm.actions.system') : t('dataperm.actions.custom')) }),
  },
  { title: t('dataperm.actions.colEnabled'), key: 'enabled', width: 90, render: renderSwitch },
  { title: '', key: 'ops', width: 120, render: renderOps },
])

async function removeAction(row: ActionDictItem) {
  try {
    await deleteAction(row.key)
    message.success(row.key)
    invalidateAfterChange()
  } catch (e: any) {
    // 后端护栏（被引用不可删等）的 message 原样透出 —— 权限语义单源在后端
    message.error(e?.response?.data?.message || String(e))
  }
}

function invalidateAfterChange() {
  // 字典变更后刷新本组件数据；写守卫侧的 TTL 缓存由后端 invalidate_cache 处理
  reload()
}

// ===== 表单（动作 / 预设包共用）=====

const formShow = ref(false)
const formSaving = ref(false)
const formKind = ref<'action' | 'preset'>('action')
const editingKey = ref('')
const form = ref({
  key: '', label: '', category: 'write', enabled: true, actionKeys: [] as string[],
})

const categoryOptions = [
  { label: 'write', value: 'write' },
  { label: 'read', value: 'read' },
  { label: 'destructive', value: 'destructive' },
]

const actionSelectOptions = computed(() =>
  actions.value
    .filter((a) => a.enabled && (a.category === 'write' || a.category === 'destructive'))
    .map((a) => ({ label: `${a.label} (${a.key})`, value: a.key })),
)

const formTitle = computed(() =>
  formKind.value === 'action'
    ? (editingKey.value ? `${t('dataperm.actions.edit')} · ${editingKey.value}` : t('dataperm.actions.add'))
    : (editingKey.value ? `${t('dataperm.actions.edit')} · ${editingKey.value}` : t('dataperm.actions.addPreset')),
)

function openActionForm(row?: ActionDictItem) {
  formKind.value = 'action'
  editingKey.value = row?.key || ''
  form.value = {
    key: row?.key || '',
    label: row?.label || '',
    category: row?.category || 'write',
    enabled: row?.enabled ?? true,
    actionKeys: [],
  }
  formShow.value = true
}

function openPresetForm(row?: ActionPreset) {
  formKind.value = 'preset'
  editingKey.value = row?.key || ''
  form.value = {
    key: row?.key || '',
    label: row?.label || '',
    category: 'write',
    enabled: true,
    actionKeys: [...(row?.actionKeys || [])],
  }
  formShow.value = true
}

async function submitForm() {
  formSaving.value = true
  try {
    if (formKind.value === 'action') {
      if (editingKey.value) {
        const body: Record<string, unknown> = { label: form.value.label, enabled: form.value.enabled }
        if (!actions.value.find((a) => a.key === editingKey.value)?.is_system) {
          // 自定义动作可改 label/enabled；category 变更影响预设包语义，暂不开放（后端也未允许）
        }
        await updateAction(editingKey.value, body)
      } else {
        await createAction({
          key: form.value.key, label: form.value.label, category: form.value.category,
        })
      }
    } else if (editingKey.value) {
      await updateActionPreset(editingKey.value, {
        label: form.value.label, actionKeys: form.value.actionKeys,
      })
    } else {
      await createActionPreset({
        key: form.value.key, label: form.value.label, actionKeys: form.value.actionKeys,
      })
    }
    formShow.value = false
    invalidateAfterChange()
  } catch (e: any) {
    message.error(e?.response?.data?.message || String(e))
  } finally {
    formSaving.value = false
  }
}
</script>

<style scoped>
.am-modal { max-width: 92vw; }
.am-desc { margin-bottom: 12px; }
.preset-block { margin-top: 16px; }
.preset-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.preset-title { font-size: 13px; font-weight: 700; color: var(--ink, #1e293b); }
.preset-list { display: flex; flex-wrap: wrap; gap: 8px; }
.preset-tag { padding-right: 4px; }
.preset-edit { margin-left: 6px; }
.op-btn { margin-right: 10px; }
</style>
