<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">{{ t('pages.settings.RegistrationApproval.s1') }}</h1>
          <p class="page-subtitle">{{ t('pages.settings.RegistrationApproval.s2') }}</p>
        </div>
        <div class="page-header-actions">
          <!-- 状态筛选：本项目的 naive-ui 2.44.1 安装包不含 NSegmented
               （dist 包与 volar.d.ts 中均无该导出），用单选按钮组替代，交互等价 -->
          <n-radio-group
            v-model:value="statusFilter"
            size="small"
            @update:value="onFilterChange"
          >
            <n-radio-button
              v-for="opt in statusOptions"
              :key="opt.value"
              :value="opt.value"
              :label="opt.label"
            />
          </n-radio-group>
          <n-button :loading="loading" @click="loadList">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            {{ t('pages.settings.RegistrationApproval.s3') }}
          </n-button>
        </div>
      </div>

      <n-card>
        <n-data-table
          :data="list"
          :columns="columns"
          :row-key="(row: RegApp) => row.id"
          :loading="loading"
          :pagination="localPagination()"
        />
        <n-empty
          v-if="!loading && list.length === 0"
          :description="t('pages.settings.RegistrationApproval.s4')"
          style="padding: 40px 0"
        />
      </n-card>

      <!-- 拒绝理由弹窗 -->
      <n-modal
        v-model:show="rejectModalVisible"
        preset="card"
        :title="t('pages.settings.RegistrationApproval.s5')"
        :style="{ width: '520px' }"
        :mask-closable="false"
      >
        <n-alert type="warning" :show-icon="true" style="margin-bottom: 16px">
          {{ t('pages.settings.RegistrationApproval.s9', { email: rejectingApp?.email }) }}
        </n-alert>
        <n-input
          v-model:value="rejectReason"
          type="textarea"
          :placeholder="t('pages.settings.RegistrationApproval.s6')"
          :autosize="{ minRows: 3, maxRows: 6 }"
        />
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
            <n-button @click="rejectModalVisible = false">{{ t('pages.settings.RegistrationApproval.s7') }}</n-button>
            <n-button type="error" :loading="rejecting" @click="confirmReject">{{ t('pages.settings.RegistrationApproval.s8') }}</n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { localPagination } from '@/composables/useTablePagination'
import { ref, h, onMounted } from 'vue'
import { useMessage, type DataTableColumns, NTag, NButton, NSpace, NIcon } from 'naive-ui'
import { RefreshOutline, CheckmarkOutline, CloseOutline } from '@vicons/ionicons5'
import { listRegistrations, approveRegistration, rejectRegistration } from '../../api/auth'
const { t } = useI18n()

// 注意: 后端全局启用 djangorestframework-camel-case, 响应字段为 camelCase
// (fullName / emailVerified / createdAt / reviewedAt / reviewedByName / rejectReason),
// 与内存里序列化器的 snake_case 字段名不同 —— 前端必须消费 camelCase。
interface RegApp {
  id: number
  username: string
  email: string
  fullName: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED'
  emailVerified: boolean
  createdAt: string
  reviewedAt: string | null
  reviewedByName: string | null
  rejectReason: string
}

const message = useMessage()
const loading = ref(false)
const list = ref<RegApp[]>([])
const statusFilter = ref('PENDING')

const statusOptions = [
  { label: t('pages.settings.RegistrationApproval.s10'), value: 'PENDING' },
  { label: t('pages.settings.RegistrationApproval.s11'), value: 'APPROVED' },
  { label: t('pages.settings.RegistrationApproval.s12'), value: 'REJECTED' },
  { label: t('pages.settings.RegistrationApproval.s13'), value: 'ALL' },
]

const statusMeta: Record<RegApp['status'], { text: string; type: 'warning' | 'success' | 'error' }> = {
  PENDING: { text: t('pages.settings.RegistrationApproval.s10'), type: 'warning' },
  APPROVED: { text: t('pages.settings.RegistrationApproval.s11'), type: 'success' },
  REJECTED: { text: t('pages.settings.RegistrationApproval.s12'), type: 'error' },
}

const columns: DataTableColumns<RegApp> = [
  { title: t('pages.settings.RegistrationApproval.s14'), key: 'email', minWidth: 200, render: (row) => h('div', [
    h('div', { style: 'font-weight: 600; color: var(--ink);' }, row.email),
    h('div', { style: 'font-size: 12px; color: var(--ink-faint);' }, row.username),
  ]) },
  // 后端 camelCase：字段名是 fullName / emailVerified，写成 full_name 会永远取不到值
  { title: t('pages.settings.RegistrationApproval.s15'), key: 'fullName', minWidth: 110,
    render: (row) => row.fullName || h('span', { style: 'color: var(--ink-faint);' }, '—') },
  { title: t('pages.settings.RegistrationApproval.s16'), key: 'status', width: 100,
    render: (row) => h(NTag, { type: statusMeta[row.status].type, size: 'small', round: true },
      { default: () => statusMeta[row.status].text }) },
  { title: t('pages.settings.RegistrationApproval.s17'), key: 'emailVerified', width: 100,
    render: (row) => row.emailVerified
      ? h(NTag, { type: 'success', size: 'small', round: true }, { default: () => t('pages.settings.RegistrationApproval.s18') })
      : h(NTag, { type: 'default', size: 'small', round: true }, { default: () => t('pages.settings.RegistrationApproval.s19') }) },
  { title: t('pages.settings.RegistrationApproval.s20'), key: 'createdAt', width: 170,
    render: (row) => new Date(row.createdAt).toLocaleString('zh-CN', { hour12: false }) },
  { title: t('pages.settings.RegistrationApproval.s21'), key: 'reviewedByName', width: 110,
    render: (row) => row.reviewedByName || h('span', { style: 'color: var(--ink-faint);' }, '—') },
  { title: t('pages.settings.RegistrationApproval.s22'), key: 'rejectReason', minWidth: 160,
    render: (row) => row.rejectReason || h('span', { style: 'color: var(--ink-faint);' }, '—') },
  {
    title: t('pages.settings.RegistrationApproval.s23'), key: 'actions', width: 150, fixed: 'right',
    render: (row) => {
      if (row.status !== 'PENDING') {
        return h('span', { style: 'color: var(--ink-faint); font-size: 13px;' }, t('pages.settings.RegistrationApproval.s24'))
      }
      return h(NSpace, { size: 8 }, {
        default: () => [
          h(NButton, {
            size: 'small', type: 'primary',
            onClick: () => onApprove(row),
          }, { default: () => t('pages.settings.RegistrationApproval.s25'), icon: () => h(NIcon, null, { default: () => h(CheckmarkOutline) }) }),
          h(NButton, {
            size: 'small', type: 'error',
            onClick: () => openReject(row),
          }, { default: () => t('pages.settings.RegistrationApproval.s26'), icon: () => h(NIcon, null, { default: () => h(CloseOutline) }) }),
        ],
      })
    },
  },
]

const loadList = async () => {
  loading.value = true
  try {
    const { data } = await listRegistrations(statusFilter.value === 'ALL' ? '' : statusFilter.value)
    list.value = (data.data || []) as RegApp[]
  } catch (err: any) {
    message.error(err?.response?.data?.message || t('pages.settings.RegistrationApproval.s27'))
  } finally {
    loading.value = false
  }
}

const onFilterChange = () => loadList()

// ===== 通过 =====
const onApprove = async (row: RegApp) => {
  if (!row.emailVerified) {
    message.warning(t('pages.settings.RegistrationApproval.s28'))
    return
  }
  try {
    const { data } = await approveRegistration(String(row.id))
    if (data.success) {
      message.success(t('pages.settings.RegistrationApproval.s29', { email: row.email }))
      await loadList()
    } else {
      message.error(data.message || t('pages.settings.RegistrationApproval.s30'))
    }
  } catch (err: any) {
    const d = err?.response?.data
    message.error(d?.message || t('pages.settings.RegistrationApproval.s30b'))
  }
}

// ===== 拒绝 =====
const rejectModalVisible = ref(false)
const rejecting = ref(false)
const rejectingApp = ref<RegApp | null>(null)
const rejectReason = ref('')

const openReject = (row: RegApp) => {
  rejectingApp.value = row
  rejectReason.value = ''
  rejectModalVisible.value = true
}

const confirmReject = async () => {
  if (!rejectingApp.value) return
  rejecting.value = true
  try {
    const { data } = await rejectRegistration(String(rejectingApp.value.id), rejectReason.value)
    if (data.success) {
      message.success(t('pages.settings.RegistrationApproval.s31', { email: rejectingApp.value.email }))
      rejectModalVisible.value = false
      await loadList()
    } else {
      message.error(data.message || t('pages.settings.RegistrationApproval.s30'))
    }
  } catch (err: any) {
    message.error(err?.response?.data?.message || t('pages.settings.RegistrationApproval.s30b'))
  } finally {
    rejecting.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.page-header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
