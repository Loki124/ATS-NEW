<template>
  <div class="page-container">
    <div class="page-body">
      <div class="page-header">
        <div>
          <h1 class="page-title">注册审核</h1>
          <p class="page-subtitle">审核自助注册申请：通过则激活账号，拒绝则保持未激活</p>
        </div>
        <div class="page-header-actions">
          <n-segmented
            v-model:value="statusFilter"
            :options="statusOptions"
            @update:value="onFilterChange"
          />
          <n-button :loading="loading" @click="loadList">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
        </div>
      </div>

      <n-card>
        <n-data-table
          :data="list"
          :columns="columns"
          :row-key="(row: RegApp) => row.id"
          :loading="loading"
          :pagination="{ pageSize: 10, showSizePicker: true, pageSizes: [10, 20, 50] }"
        />
        <n-empty
          v-if="!loading && list.length === 0"
          description="暂无符合条件的注册申请"
          style="padding: 40px 0"
        />
      </n-card>

      <!-- 拒绝理由弹窗 -->
      <n-modal
        v-model:show="rejectModalVisible"
        preset="card"
        title="拒绝注册申请"
        :style="{ width: '520px' }"
        :mask-closable="false"
      >
        <n-alert type="warning" :show-icon="true" style="margin-bottom: 16px">
          账号 <strong>{{ rejectingApp?.email }}</strong> 将保持未激活状态，申请人登录时会看到「申请已被拒绝」。
        </n-alert>
        <n-input
          v-model:value="rejectReason"
          type="textarea"
          placeholder="请填写拒绝理由（可选，将反馈给申请人）"
          :autosize="{ minRows: 3, maxRows: 6 }"
        />
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
            <n-button @click="rejectModalVisible = false">取消</n-button>
            <n-button type="error" :loading="rejecting" @click="confirmReject">确认拒绝</n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { useMessage, type DataTableColumns, NTag, NButton, NSpace, NIcon } from 'naive-ui'
import { RefreshOutline, CheckmarkOutline, CloseOutline } from '@vicons/ionicons5'
import { listRegistrations, approveRegistration, rejectRegistration } from '../../api/auth'

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
  { label: '待审核', value: 'PENDING' },
  { label: '已通过', value: 'APPROVED' },
  { label: '已拒绝', value: 'REJECTED' },
  { label: '全部', value: 'ALL' },
]

const statusMeta: Record<RegApp['status'], { text: string; type: 'warning' | 'success' | 'error' }> = {
  PENDING: { text: '待审核', type: 'warning' },
  APPROVED: { text: '已通过', type: 'success' },
  REJECTED: { text: '已拒绝', type: 'error' },
}

const columns: DataTableColumns<RegApp> = [
  { title: '邮箱 / 账号', key: 'email', minWidth: 200, render: (row) => h('div', [
    h('div', { style: 'font-weight: 600; color: var(--ink);' }, row.email),
    h('div', { style: 'font-size: 12px; color: var(--ink-faint);' }, row.username),
  ]) },
  { title: '姓名', key: 'full_name', minWidth: 110,
    render: (row) => row.full_name || h('span', { style: 'color: var(--ink-faint);' }, '—') },
  { title: '状态', key: 'status', width: 100,
    render: (row) => h(NTag, { type: statusMeta[row.status].type, size: 'small', round: true },
      { default: () => statusMeta[row.status].text }) },
  { title: '邮箱验证', key: 'email_verified', width: 100,
    render: (row) => row.email_verified
      ? h(NTag, { type: 'success', size: 'small', round: true }, { default: () => '已验证' })
      : h(NTag, { type: 'default', size: 'small', round: true }, { default: () => '未验证' }) },
  { title: '申请时间', key: 'createdAt', width: 170,
    render: (row) => new Date(row.createdAt).toLocaleString('zh-CN', { hour12: false }) },
  { title: '审核人', key: 'reviewedByName', width: 110,
    render: (row) => row.reviewedByName || h('span', { style: 'color: var(--ink-faint);' }, '—') },
  { title: '拒绝理由', key: 'rejectReason', minWidth: 160,
    render: (row) => row.rejectReason || h('span', { style: 'color: var(--ink-faint);' }, '—') },
  {
    title: '操作', key: 'actions', width: 150, fixed: 'right',
    render: (row) => {
      if (row.status !== 'PENDING') {
        return h('span', { style: 'color: var(--ink-faint); font-size: 13px;' }, '已处理')
      }
      return h(NSpace, { size: 8 }, {
        default: () => [
          h(NButton, {
            size: 'small', type: 'primary',
            onClick: () => onApprove(row),
          }, { default: () => '通过', icon: () => h(NIcon, null, { default: () => h(CheckmarkOutline) }) }),
          h(NButton, {
            size: 'small', type: 'error',
            onClick: () => openReject(row),
          }, { default: () => '拒绝', icon: () => h(NIcon, null, { default: () => h(CloseOutline) }) }),
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
    message.error(err?.response?.data?.message || '加载注册申请失败')
  } finally {
    loading.value = false
  }
}

const onFilterChange = () => loadList()

// ===== 通过 =====
const onApprove = async (row: RegApp) => {
  if (!row.email_verified) {
    message.warning('该申请尚未完成邮箱验证，请先让申请人完成验证码校验')
    return
  }
  try {
    const { data } = await approveRegistration(String(row.id))
    if (data.success) {
      message.success(`已通过并激活账号 ${row.email}`)
      await loadList()
    } else {
      message.error(data.message || '操作失败')
    }
  } catch (err: any) {
    const d = err?.response?.data
    message.error(d?.message || '操作失败，请重试')
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
      message.success(`已拒绝申请 ${rejectingApp.value.email}`)
      rejectModalVisible.value = false
      await loadList()
    } else {
      message.error(data.message || '操作失败')
    }
  } catch (err: any) {
    message.error(err?.response?.data?.message || '操作失败，请重试')
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
