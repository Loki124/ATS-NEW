<template>
  <div class="page-container ca-page">
    <!-- 社招环境：显性差异 —— 此配置为校招专属，不呈现 -->
    <EmptyState
      v-if="!systemStore.isCampus"
      :title="t('pages.settings.CampusAmbassador.s2')"
      :description="t('pages.settings.CampusAmbassador.s3')"
    />

    <!-- 校招环境：校园大使配置（Phase 4 真实后端接线） -->
    <template v-else>
      <header class="ca-header">
        <div>
          <h1 class="page-title">{{ systemStore.label }} · {{ t('pages.settings.CampusAmbassador.s14') }}</h1>
          <p class="page-subtitle">{{ t('pages.settings.CampusAmbassador.s1') }}</p>
        </div>
        <n-switch
          :value="enabled"
          :loading="savingEnabled"
          @update:value="onToggleEnabled"
        >
          <template #checked>{{ t('pages.settings.CampusAmbassador.s15') }}</template>
          <template #unchecked>{{ t('pages.settings.CampusAmbassador.s16') }}</template>
        </n-switch>
      </header>

      <n-card class="ca-card" :bordered="false">
        <div class="ca-card__toolbar">
          <n-input
            v-model:value="keyword"
            :placeholder="t('pages.settings.CampusAmbassador.s4')"
            clearable
            class="ca-search"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-button type="primary" :disabled="!enabled" @click="openCreate">
            <template #icon><n-icon :component="PersonAddOutline" /></template>
            {{ t('pages.settings.CampusAmbassador.s5') }}
          </n-button>
        </div>

        <n-data-table
          :columns="columns"
          :data="filteredRows"
          :row-key="(row: any) => row.id"
          :loading="loading"
          :pagination="tablePagination"
          flex-height
          class="ca-table"
        />

        <n-empty
          v-if="!loading && filteredRows.length === 0"
          :description="keyword ? t('pages.settings.CampusAmbassador.s30', '无匹配结果') : t('pages.settings.CampusAmbassador.s6')"
          class="ca-empty"
        />
      </n-card>
    </template>

    <!-- 新增 / 编辑 弹窗 -->
    <n-modal
      :show="showModal"
      :mask-closable="false"
      :on-mask-click="requestClose"
      @update:show="(v: boolean) => !v && requestClose()"
      preset="card"
      :title="editingId ? t('pages.settings.CampusAmbassador.s31', '编辑校园大使') : t('pages.settings.CampusAmbassador.s32', '添加校园大使')"
      class="ca-modal"
      :auto-focus="false"
    >
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
        <n-form-item :label="t('pages.settings.CampusAmbassador.s33', '高校')" path="school">
          <n-input v-model:value="form.school" :placeholder="t('pages.settings.CampusAmbassador.s34', '如：上海交通大学')" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusAmbassador.s35', '大使姓名')" path="name">
          <n-input v-model:value="form.name" :placeholder="t('pages.settings.CampusAmbassador.s36', '学生大使姓名')" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusAmbassador.s9', '区域')" path="region">
          <n-input v-model:value="form.region" :placeholder="t('pages.settings.CampusAmbassador.s37', '如：华东')" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusAmbassador.s10', '状态')" path="status">
          <n-select v-model:value="form.status" :options="statusOptions" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusAmbassador.s38', '联系电话')" path="phone">
          <n-input v-model:value="form.phone" :placeholder="t('pages.settings.CampusAmbassador.s39', '选填')" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusAmbassador.s40', '备注')" path="note">
          <n-input
            v-model:value="form.note"
            type="textarea"
            :placeholder="t('pages.settings.CampusAmbassador.s39', '选填')"
            :autosize="{ minRows: 2, maxRows: 4 }"
            :disabled="saving"
          />
        </n-form-item>
      </n-form>

      <template #footer>
        <div class="ca-modal__footer">
          <n-button :disabled="saving" @click="requestClose">{{ t('pages.settings.CampusAmbassador.s41', '取消') }}</n-button>
          <n-button type="primary" :loading="saving" :disabled="saving" @click="submitForm">
            {{ editingId ? t('pages.settings.CampusAmbassador.s42', '保存') : t('pages.settings.CampusAmbassador.s43', '创建') }}
          </n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { localPagination } from '@/composables/useTablePagination'
import { computed, h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NEmpty,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NModal,
  NSelect,
  NSwitch,
  useMessage,
  useNotification,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { SearchOutline, PersonAddOutline } from '@vicons/ionicons5'
import { useCloseGuard } from '@/composables/useCloseGuard'
import EmptyState from '../../components/common/EmptyState.vue'
import { useSystemStore } from '../../stores/system'
import {
  AMBASSADOR_STATUS_LABELS,
  createAmbassador,
  deleteAmbassador,
  getAmbassadorConfig,
  listAmbassadors,
  putAmbassadorConfig,
  restoreAmbassador,
  updateAmbassador,
  type AmbassadorStatus,
  type CampusAmbassador,
} from '../../api/campusRecruit'

const { t } = useI18n()

/**
 * CampusAmbassador — 校园招聘专属配置（Phase 4 接真实后端）
 *
 * 体现「显性配置差异」范式：
 * - 整页用 v-if="systemStore.isCampus" 包裹，社招环境直接展示 EmptyState 说明；
 * - 菜单入口也仅在 isCampus 时由 Layout.menuOptions 追加，双重保证。
 *
 * 所有/api 调用经 main.ts 全局拦截器自动注入 X-Recruit-Type: campus，
 * 后端 ScopeQuerysetMixin 据此按 recruit_type='campus' 硬分区。
 *
 * 国际化：t() 第二个参数为兜底中文（locale 暂未补对应 key 时仍可显示），
 * 后续 i18n 会话收敛后可去除兜底参数。
 */
const systemStore = useSystemStore()
const message = useMessage()
const notification = useNotification()

const enabled = ref(false)
const savingEnabled = ref(false)
const loading = ref(false)
const keyword = ref('')
const rows = ref<CampusAmbassador[]>([])

const showModal = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)

// 弹窗关闭守卫：保存中拦截；有未保存修改时二次确认（防点遮罩/ESC/X 静默丢草稿）
const { requestClose } = useCloseGuard({
  isSaving: () => saving.value,
  isDirty: () => true,
  onClose: () => { showModal.value = false },
})
const formRef = ref<FormInst | null>(null)
const form = ref({
  school: '',
  name: '',
  region: '',
  status: 'pending' as AmbassadorStatus,
  phone: '',
  note: '',
})

const statusOptions = Object.entries(AMBASSADOR_STATUS_LABELS).map(([value, label]) => ({ value, label }))

const rules: FormRules = {
  school: { required: true, message: t('pages.settings.CampusAmbassador.s44', '请填写高校'), trigger: ['input', 'blur'] },
  name: { required: true, message: t('pages.settings.CampusAmbassador.s45', '请填写大使姓名'), trigger: ['input', 'blur'] },
}

const tablePagination = localPagination()

const filteredRows = computed(() => {
  const k = keyword.value.trim()
  if (!k) return rows.value
  return rows.value.filter((r) => (r.school ?? '').includes(k) || (r.name ?? '').includes(k))
})

function statusTag(status: AmbassadorStatus) {
  const cls =
    status === 'active'
      ? 'ca-tag ca-tag--on'
      : status === 'pending'
        ? 'ca-tag ca-tag--off'
        : 'ca-tag ca-tag--muted'
  return h('span', { class: cls }, AMBASSADOR_STATUS_LABELS[status] ?? status)
}

const columns = [
  { title: t('pages.settings.CampusAmbassador.s7', '高校'), key: 'school' },
  { title: t('pages.settings.CampusAmbassador.s8', '大使姓名'), key: 'name' },
  { title: t('pages.settings.CampusAmbassador.s9', '区域'), key: 'region', render: (row: CampusAmbassador) => row.region || '—' },
  {
    title: t('pages.settings.CampusAmbassador.s10', '状态'),
    key: 'status',
    render: (row: CampusAmbassador) => statusTag(row.status),
  },
  {
    title: t('pages.settings.CampusAmbassador.s11', '操作'),
    key: 'actions',
    render: (row: CampusAmbassador) =>
      h('div', { style: 'display:flex; gap:8px' }, [
        h(NButton, { size: 'small', quaternary: true, onClick: () => openEdit(row) }, { default: () => t('pages.settings.CampusAmbassador.s46', '编辑') }),
        h(
          NButton,
          { size: 'small', quaternary: true, type: 'error', onClick: () => remove(row) },
          { default: () => t('pages.settings.CampusAmbassador.s19', '移除') },
        ),
      ]),
  },
]

/* ============================ 数据加载 ============================ */
async function reload() {
  loading.value = true
  try {
    const res = await listAmbassadors()
    rows.value = res.rows
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t('pages.settings.CampusAmbassador.s47', '加载校园大使失败'))
  } finally {
    loading.value = false
  }
}

async function loadConfig() {
  try {
    const cfg = await getAmbassadorConfig()
    enabled.value = Boolean(cfg?.enabled)
  } catch {
    enabled.value = false
  }
}

/* ============================ 启用开关 ============================ */
async function onToggleEnabled(val: boolean) {
  savingEnabled.value = true
  try {
    await putAmbassadorConfig({ enabled: val })
    enabled.value = val
    message.success(val ? t('pages.settings.CampusAmbassador.s20') : t('pages.settings.CampusAmbassador.s21'))
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t('pages.settings.CampusAmbassador.s48', '保存启用状态失败'))
  } finally {
    savingEnabled.value = false
  }
}

/* ============================ 新增 / 编辑 ============================ */
function resetForm() {
  form.value = { school: '', name: '', region: '', status: 'pending', phone: '', note: '' }
  editingId.value = null
}

function openCreate() {
  resetForm()
  showModal.value = true
}

function openEdit(row: CampusAmbassador) {
  editingId.value = row.id
  form.value = {
    school: row.school,
    name: row.name,
    region: row.region,
    status: row.status,
    phone: row.phone,
    note: row.note,
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  resetForm()
}

async function submitForm() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  const payload = {
    school: form.value.school,
    name: form.value.name,
    region: form.value.region,
    status: form.value.status,
    phone: form.value.phone,
    note: form.value.note,
  }
  try {
    if (editingId.value) {
      await updateAmbassador(editingId.value, payload)
      message.success(t('pages.settings.CampusAmbassador.s49', '已保存'))
    } else {
      await createAmbassador(payload)
      message.success(t('pages.settings.CampusAmbassador.s50', '已添加校园大使'))
    }
    closeModal()
    await reload()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t('pages.settings.CampusAmbassador.s51', '保存失败'))
  } finally {
    saving.value = false
  }
}

/* ============================ 删除（R-106 撤销） ============================ */
function remove(row: CampusAmbassador) {
  const id = row.id
  rows.value = rows.value.filter((r) => r.id !== id)
  notification.success({
    title: t('pages.settings.CampusAmbassador.s52', '已移除该大使'),
    duration: 8000,
    action: () =>
      h(
        NButton,
        {
          size: 'small',
          onClick: async () => {
            try {
              await restoreAmbassador(id)
              await reload()
              message.success(t('pages.settings.CampusAmbassador.s53', '已恢复'))
            } catch {
              message.error(t('pages.settings.CampusAmbassador.s54', '恢复失败，请联系管理员'))
            }
          },
        },
        { default: () => t('pages.settings.CampusAmbassador.s55', '撤销') },
      ),
  })
  deleteAmbassador(id).catch(() => reload())
}

onMounted(() => {
  if (systemStore.isCampus) {
    loadConfig()
    reload()
  }
})
</script>

<style scoped>
.ca-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
.ca-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.ca-card {
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
}
.ca-card__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.ca-search {
  max-width: 280px;
}
.ca-table {
  min-height: 240px;
}
.ca-empty {
  padding: var(--space-10) 0;
}
.ca-modal {
  width: 520px;
  max-width: 92vw;
}
.ca-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}
.ca-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: var(--fs-12);
  line-height: 1.4;
}
.ca-tag--on {
  background: color-mix(in oklch, var(--color-success) 16%, transparent);
  color: var(--color-success);
}
.ca-tag--off {
  background: color-mix(in oklch, var(--color-warning) 16%, transparent);
  color: var(--color-warning);
}
.ca-tag--muted {
  background: color-mix(in oklch, var(--color-text-tertiary) 16%, transparent);
  color: var(--color-text-secondary);
}
</style>