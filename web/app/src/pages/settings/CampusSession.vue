<template>
  <div class="page-container cs-page">
    <!-- 社招环境：显性差异 —— 此配置为校招专属，不呈现 -->
    <EmptyState
      v-if="!systemStore.isCampus"
      :title="t('pages.settings.CampusSession.s1')"
      :description="t('pages.settings.CampusSession.s2')"
    />

    <!-- 校招环境：宣讲会配置（Phase 4 真实后端接线） -->
    <template v-else>
      <header class="cs-header">
        <div>
          <h1 class="page-title">{{ systemStore.label }} · {{ t('pages.settings.CampusSession.s38') }}</h1>
          <p class="page-subtitle">{{ t('pages.settings.CampusSession.s1') }}</p>
        </div>
        <n-switch
          :value="enabled"
          :loading="savingEnabled"
          @update:value="onToggleEnabled"
        >
          <template #checked>{{ t('pages.settings.CampusSession.s39') }}</template>
          <template #unchecked>{{ t('pages.settings.CampusSession.s40') }}</template>
        </n-switch>
      </header>

      <n-card class="cs-card" :bordered="false">
        <div class="cs-card__toolbar">
          <n-input
            v-model:value="keyword"
            :placeholder="t('pages.settings.CampusSession.s3')"
            clearable
            class="cs-search"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-button type="primary" :disabled="!enabled" @click="openCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            {{ t('pages.settings.CampusSession.s4') }}
          </n-button>
        </div>

        <n-data-table
          :columns="columns"
          :data="filteredRows"
          :row-key="(row: any) => row.id"
          :loading="loading"
          :pagination="tablePagination"
          flex-height
          class="cs-table"
        />

        <n-empty v-if="!loading && filteredRows.length === 0" :description="keyword ? t('pages.settings.CampusSession.s41') : t('pages.settings.CampusSession.s42')" class="cs-empty" />
      </n-card>
    </template>

    <!-- 新增 / 编辑 弹窗 -->
    <n-modal
      v-model:show="showModal"
      preset="card"
      :title="editingId ? t('pages.settings.CampusSession.s36') : t('pages.settings.CampusSession.s37')"
      class="cs-modal"
      :auto-focus="false"
      @close="closeModal"
    >
      <n-form ref="formRef" :model="form" :rules="rules" label-placement="top">
        <n-form-item :label="t('pages.settings.CampusSession.s6')" path="title">
          <n-input v-model:value="form.title" :placeholder="t('pages.settings.CampusSession.s7')" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusSession.s8')" path="school">
          <n-input v-model:value="form.school" :placeholder="t('pages.settings.CampusSession.s9')" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusSession.s10')" path="sessionType">
          <n-select v-model:value="form.sessionType" :options="typeOptions" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusSession.s11')" path="status">
          <n-select v-model:value="form.status" :options="statusOptions" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusSession.s12')" path="startTime">
          <n-date-picker
            v-model:value="form.startTime"
            type="datetime"
            clearable
            :placeholder="t('pages.settings.CampusSession.s13')"
            class="cs-date"
            :disabled="saving"
          />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusSession.s14')" path="endTime">
          <n-date-picker
            v-model:value="form.endTime"
            type="datetime"
            clearable
            :placeholder="t('pages.settings.CampusSession.s15')"
            class="cs-date"
            :disabled="saving"
          />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusSession.s16')" path="venue">
          <n-input v-model:value="form.venue" :placeholder="t('pages.settings.CampusSession.s17')" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusSession.s18')" path="onlineLink">
          <n-input v-model:value="form.onlineLink" :placeholder="t('pages.settings.CampusSession.s19')" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusSession.s20')" path="capacity">
          <n-input-number v-model:value="form.capacity" :min="0" :placeholder="t('pages.settings.CampusSession.s21')" :disabled="saving" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.CampusSession.s22')" path="note">
          <n-input
            v-model:value="form.note"
            type="textarea"
            :placeholder="t('pages.settings.CampusSession.s23')"
            :autosize="{ minRows: 2, maxRows: 4 }"
            :disabled="saving"
          />
        </n-form-item>
      </n-form>

      <template #footer>
        <div class="cs-modal__footer">
          <n-button :disabled="saving" @click="closeModal">{{ t('pages.settings.CampusSession.s24') }}</n-button>
          <n-button type="primary" :loading="saving" :disabled="saving" @click="submitForm">
            {{ editingId ? t('pages.settings.CampusSession.s43') : t('pages.settings.CampusSession.s44') }}
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
  NDatePicker,
  NEmpty,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSwitch,
  useMessage,
  useNotification,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { SearchOutline, AddOutline } from '@vicons/ionicons5'
import EmptyState from '../../components/common/EmptyState.vue'
import { useSystemStore } from '../../stores/system'
import {
  SESSION_STATUS_LABELS,
  SESSION_TYPE_LABELS,
  createSession,
  deleteSession,
  getSessionConfig,
  listSessions,
  putSessionConfig,
  restoreSession,
  updateSession,
  type CampusSession,
  type SessionInput,
  type SessionStatus,
  type SessionType,
} from '../../api/campusRecruit'
const { t } = useI18n()

/**
 * CampusSession — 校园招聘专属配置（Phase 4 接真实后端 campus_session 模块）
 *
 * 体现「显性配置差异」范式：
 * - 整页用 v-if="systemStore.isCampus" 包裹，社招环境直接展示 EmptyState 说明；
 * - 菜单入口也仅在 isCampus 时由 Layout.menuOptions 追加，双重保证。
 *
 * 所有/api 调用经 main.ts 全局拦截器自动注入 X-Recruit-Type: campus，
 * 后端 ScopeQuerysetMixin 据此按 recruit_type='campus' 硬分区（读侧过滤 + 写侧权威注入）。
 */
const systemStore = useSystemStore()
const message = useMessage()
const notification = useNotification()

const enabled = ref(false)
const savingEnabled = ref(false)
const loading = ref(false)
const keyword = ref('')
const rows = ref<CampusSession[]>([])

const showModal = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)
const formRef = ref<FormInst | null>(null)
const form = ref({
  title: '',
  school: '',
  sessionType: 'offline' as SessionType,
  status: 'planned' as SessionStatus,
  startTime: null as number | null,
  endTime: null as number | null,
  venue: '',
  onlineLink: '',
  capacity: null as number | null,
  note: '',
})

const typeOptions = Object.entries(SESSION_TYPE_LABELS).map(([value, label]) => ({ value, label }))
const statusOptions = Object.entries(SESSION_STATUS_LABELS).map(([value, label]) => ({ value, label }))

const rules: FormRules = {
  title: { required: true, message: t('pages.settings.CampusSession.s45'), trigger: ['input', 'blur'] },
}

const tablePagination = localPagination()

/** ISO 字符串 → 时间戳数字（日期选择器值）。 */
function isoToTs(iso: string | null): number | null {
  if (!iso) return null
  const t = Date.parse(iso)
  return Number.isNaN(t) ? null : t
}

/** 时间戳数字 → ISO 字符串（提交后端）。 */
function tsToIso(ts: number | null): string | null {
  return ts ? new Date(ts).toISOString() : null
}

function fmtTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const filteredRows = computed(() => {
  const k = keyword.value.trim()
  if (!k) return rows.value
  return rows.value.filter((r) => (r.title ?? '').includes(k) || (r.school ?? '').includes(k))
})

function statusTag(status: SessionStatus) {
  const map: Record<SessionStatus, string> = {
    planned: 'cs-tag cs-tag--planned',
    ongoing: 'cs-tag cs-tag--ongoing',
    ended: 'cs-tag cs-tag--ended',
    cancelled: 'cs-tag cs-tag--cancelled',
  }
  return h('span', { class: map[status] }, SESSION_STATUS_LABELS[status] ?? status)
}

const columns = [
  { title: t('pages.settings.CampusSession.s25'), key: 'title' },
  { title: t('pages.settings.CampusSession.s26'), key: 'school', render: (row: CampusSession) => row.school || '—' },
  {
    title: t('pages.settings.CampusSession.s27'),
    key: 'sessionType',
    render: (row: CampusSession) => SESSION_TYPE_LABELS[row.sessionType] ?? row.sessionType,
  },
  { title: t('pages.settings.CampusSession.s28'), key: 'status', render: (row: CampusSession) => statusTag(row.status) },
  { title: t('pages.settings.CampusSession.s29'), key: 'startTime', render: (row: CampusSession) => fmtTime(row.startTime) },
  {
    title: t('pages.settings.CampusSession.s30'),
    key: 'actions',
    render: (row: CampusSession) =>
      h('div', { style: 'display:flex; gap:8px' }, [
        h(NButton, { size: 'small', quaternary: true, onClick: () => openEdit(row) }, { default: () => t('pages.settings.CampusSession.s52') }),
        h(
          NButton,
          { size: 'small', quaternary: true, type: 'error', onClick: () => remove(row) },
          { default: () => t('pages.settings.CampusSession.s53') },
        ),
      ]),
  },
]

/* ============================ 数据加载 ============================ */
async function reload() {
  loading.value = true
  try {
    const res = await listSessions()
    rows.value = res.rows
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t('pages.settings.CampusSession.s46'))
  } finally {
    loading.value = false
  }
}

async function loadConfig() {
  try {
    const cfg = await getSessionConfig()
    enabled.value = Boolean(cfg?.enabled)
  } catch {
    enabled.value = false
  }
}

/* ============================ 启用开关 ============================ */
async function onToggleEnabled(val: boolean) {
  savingEnabled.value = true
  try {
    await putSessionConfig({ enabled: val })
    enabled.value = val
    message.success(val ? t('pages.settings.CampusSession.s47') : t('pages.settings.CampusSession.s48'))
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t('pages.settings.CampusSession.s49'))
  } finally {
    savingEnabled.value = false
  }
}

/* ============================ 新增 / 编辑 ============================ */
function resetForm() {
  form.value = {
    title: '', school: '', sessionType: 'offline', status: 'planned',
    startTime: null, endTime: null, venue: '', onlineLink: '', capacity: null, note: '',
  }
  editingId.value = null
}

function openCreate() {
  resetForm()
  showModal.value = true
}

function openEdit(row: CampusSession) {
  editingId.value = row.id
  form.value = {
    title: row.title,
    school: row.school,
    sessionType: row.sessionType,
    status: row.status,
    startTime: isoToTs(row.startTime),
    endTime: isoToTs(row.endTime),
    venue: row.venue,
    onlineLink: row.onlineLink,
    capacity: row.capacity,
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
  const payload: SessionInput = {
    title: form.value.title,
    school: form.value.school,
    sessionType: form.value.sessionType,
    status: form.value.status,
    startTime: tsToIso(form.value.startTime),
    endTime: tsToIso(form.value.endTime),
    venue: form.value.venue,
    onlineLink: form.value.onlineLink,
    capacity: form.value.capacity,
    note: form.value.note,
  }
  try {
    if (editingId.value) {
      await updateSession(editingId.value, payload)
      message.success(t('pages.settings.CampusSession.s31'))
    } else {
      await createSession(payload)
      message.success(t('pages.settings.CampusSession.s32'))
    }
    closeModal()
    await reload()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || t('pages.settings.CampusSession.s50'))
  } finally {
    saving.value = false
  }
}

/* ============================ 删除（R-106 撤销） ============================ */
function remove(row: CampusSession) {
  const id = row.id
  rows.value = rows.value.filter((r) => r.id !== id)
  notification.success({
    title: t('pages.settings.CampusSession.s33'),
    duration: 8000,
    action: () =>
      h(
        NButton,
        {
          size: 'small',
          onClick: async () => {
            try {
              await restoreSession(id)
              await reload()
              message.success(t('pages.settings.CampusSession.s34'))
            } catch {
              message.error(t('pages.settings.CampusSession.s35'))
            }
          },
        },
        { default: () => t('pages.settings.CampusSession.s51') },
      ),
  })
  deleteSession(id).catch(() => reload())
}

onMounted(() => {
  if (systemStore.isCampus) {
    loadConfig()
    reload()
  }
})
</script>

<style scoped>
.cs-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
.cs-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.cs-card {
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
}
.cs-card__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.cs-search {
  max-width: 280px;
}
.cs-date {
  width: 100%;
}
.cs-table {
  min-height: 240px;
}
.cs-empty {
  padding: var(--space-10) 0;
}
.cs-modal {
  width: 560px;
  max-width: 92vw;
}
.cs-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}
.cs-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: var(--fs-12);
  line-height: 1.4;
}
.cs-tag--planned { background: color-mix(in oklch, var(--color-info) 16%, transparent); color: var(--color-info); }
.cs-tag--ongoing { background: color-mix(in oklch, var(--color-success) 16%, transparent); color: var(--color-success); }
.cs-tag--ended { background: color-mix(in oklch, var(--color-text-tertiary) 16%, transparent); color: var(--color-text-secondary); }
.cs-tag--cancelled { background: color-mix(in oklch, var(--color-error) 16%, transparent); color: var(--color-error); }
</style>
