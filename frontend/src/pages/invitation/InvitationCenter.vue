<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">邀约中心</h1>
      <n-space>
        <n-button @click="handleRefresh" :loading="loading">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
        <n-button type="warning" @click="handleProcessExpired">
          <template #icon><n-icon :component="FlashOutline" /></template>
          处理超时
        </n-button>
      </n-space>
    </div>

    <!-- 状态统计 -->
    <n-grid x-gap="12" y-gap="12" cols="8" responsive="screen" :item-responsive="true" class="stats-row">
      <n-gi v-for="stat in statusStats" :key="stat.key" :span="1">
        <n-card size="small" :bordered="false" class="stat-card" hoverable>
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-value" :style="{ color: stat.color }">{{ stat.count }}</div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 抢单池 -->
    <n-card v-if="claimPool.length > 0" title="🔥 抢单池" :bordered="false" class="rounded-xl claim-pool">
      <n-space>
        <n-tag
          v-for="item in claimPool"
          :key="item.id"
          type="warning"
          size="large"
          :bordered="false"
          closable
          @close="handleRefresh"
          @click="handleClaim(item)"
          style="cursor: pointer;"
        >
          <template #icon><n-icon :component="FlashOutline" /></template>
          {{ item.ownerName }} · 剩 {{ formatCountdown(item.timeoutAt) }}
        </n-tag>
      </n-space>
    </n-card>

    <!-- 筛选 + 表格 -->
    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">
        <n-select
          v-model:value="filterStatus"
          placeholder="邀约状态"
          style="width: 140px"
          clearable
          :options="statusOptions"
          @update:value="handleFilter"
        />
        <n-button @click="handleRefresh" :loading="loading">查询</n-button>
      </n-space>

      <n-data-table
        :columns="columns"
        :data="dataSource"
        :loading="loading"
        :row-key="(row: Invitation) => row.id"
        :pagination="pagination"
        @update:page="(p: number) => { pagination.page = p; loadList() }"
        @update:page-size="(s: number) => { pagination.pageSize = s; pagination.page = 1; loadList() }"
      />
    </n-card>

    <!-- 标记结果 Modal -->
    <n-modal v-model:show="resultModal.show" preset="dialog" :title="resultModal.title" style="width: 480px">
      <n-form ref="resultFormRef" :model="resultModal.form" label-placement="left" :label-width="80">
        <n-form-item label="结果">
          <n-tag :type="resultModal.form.success ? 'success' : 'error'">
            {{ resultModal.form.success ? '成功' : '失败' }}
          </n-tag>
        </n-form-item>
        <n-form-item label="原因" path="reason">
          <n-input v-model:value="resultModal.form.reason" type="textarea" :rows="3" placeholder="请说明结果原因" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="resultModal.show = false">取消</n-button>
          <n-button type="primary" @click="handleResultSubmit" :loading="resultModal.loading">确认</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 干预/终止 Modal -->
    <n-modal v-model:show="actionModal.show" preset="dialog" :title="actionModal.title" style="width: 480px">
      <n-form :model="actionModal.form" label-placement="left" :label-width="80">
        <n-form-item label="原因">
          <n-input v-model:value="actionModal.form.reason" type="textarea" :rows="3" :placeholder="actionModal.placeholder" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="actionModal.show = false">取消</n-button>
          <n-button :type="actionModal.type" @click="handleActionSubmit" :loading="actionModal.loading">确认</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, onBeforeUnmount, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, useMessage, useDialog } from 'naive-ui'
import { RefreshOutline, FlashOutline } from '@vicons/ionicons5'
import {
  listInvitations, getClaimPool, enterPool, claim, markContacted,
  markResult, intervene, terminate, processExpired,
  INVITATION_STATUS_LABEL, INVITATION_STATUS_COLOR,
  type Invitation,
} from '../../api/invitation'

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const dataSource = ref<Invitation[]>([])
const claimPool = ref<Invitation[]>([])
const filterStatus = ref<string | null>(null)
const pagination = ref({ page: 1, pageSize: 20, itemCount: 0, pageCount: 0 })

const statusOptions = Object.entries(INVITATION_STATUS_LABEL).map(([value, label]) => ({ value, label }))

const statusStats = computed(() => {
  const counts: Record<string, number> = {}
  for (const it of dataSource.value) {
    counts[it.invitationStatus] = (counts[it.invitationStatus] || 0) + 1
  }
  return Object.entries(INVITATION_STATUS_LABEL).map(([key, label]) => ({
    key, label, count: counts[key] || 0,
    color: statusColor(key),
  }))
})

function statusColor(s: string): string {
  const map: Record<string, string> = {
    PENDING_CLAIM: '#fa8c16', PENDING_INVITE: '#1890ff', INVITING: '#722ed1',
    SUCCESS: '#52c41a', FAILED: '#f5222d', INTERVENED: '#fa8c16',
  }
  return map[s] || '#8c8c8c'
}

function formatCountdown(timeoutAt?: string): string {
  if (!timeoutAt) return '—'
  const ms = new Date(timeoutAt).getTime() - Date.now()
  if (ms <= 0) return '已超时'
  const hours = Math.floor(ms / 3600000)
  const mins = Math.floor((ms % 3600000) / 60000)
  return `${hours}h ${mins}m`
}

// 操作弹窗
const resultModal = ref({
  show: false, loading: false, title: '',
  form: { id: '', success: true, reason: '' },
})

const actionModal = ref({
  show: false, loading: false, title: '', type: 'warning' as 'warning' | 'error',
  placeholder: '',
  action: '' as 'enterPool' | 'intervene' | 'terminate' | '',
  id: '',
  reason: '',
  form: { reason: '' } as { reason: string },
})

const resultFormRef = ref()

const columns = computed(() => [
  { title: '候选人', key: 'ownerName', width: 100 },
  { title: '职位', key: 'positionId', width: 120, render: (row: Invitation) => row.positionId?.slice(0, 8) + '...' },
  {
    title: '状态', key: 'invitationStatus', width: 100,
    render: (row: Invitation) => h(NTag, { type: INVITATION_STATUS_COLOR[row.invitationStatus], size: 'small' }, { default: () => INVITATION_STATUS_LABEL[row.invitationStatus] }),
  },
  { title: '邀约人', key: 'inviterName', width: 100, render: (row: Invitation) => row.inviterName || '—' },
  { title: '抢单人', key: 'claimedByName', width: 100, render: (row: Invitation) => row.claimedByName || '—' },
  {
    title: '联系次数', key: 'contactAttempts', width: 80,
    render: (row: Invitation) => row.contactAttempts,
  },
  {
    title: '超时', key: 'timeoutAt', width: 100,
    render: (row: Invitation) => formatCountdown(row.timeoutAt),
  },
  { title: '创建时间', key: 'createdAt', width: 140, render: (row: Invitation) => row.createdAt?.slice(0, 16) },
  {
    title: '操作', key: 'actions', width: 280, fixed: 'right' as const,
    render: (row: Invitation) => {
      const buttons: any[] = []
      if (row.invitationStatus === 'PENDING_ASSIGN') {
        buttons.push(h(NButton, { size: 'tiny', type: 'warning', onClick: () => openEnterPool(row) }, { default: () => '入池' }))
      }
      if (row.invitationStatus === 'PENDING_CLAIM') {
        buttons.push(h(NButton, { size: 'tiny', type: 'primary', onClick: () => handleClaim(row) }, { default: () => '抢单' }))
      }
      if (['PENDING_INVITE', 'INVITING', 'INTERVENED'].includes(row.invitationStatus)) {
        if (row.invitationStatus === 'PENDING_INVITE' || row.invitationStatus === 'INTERVENED') {
          buttons.push(h(NButton, { size: 'tiny', onClick: () => handleContact(row) }, { default: () => '已联系' }))
        }
        buttons.push(h(NButton, { size: 'tiny', type: 'success', onClick: () => openResult(row, true) }, { default: () => '成功' }))
        buttons.push(h(NButton, { size: 'tiny', type: 'error', onClick: () => openResult(row, false) }, { default: () => '失败' }))
        buttons.push(h(NButton, { size: 'tiny', type: 'warning', onClick: () => openAction(row, 'intervene') }, { default: () => '干预' }))
      }
      if (!['SUCCESS', 'FAILED', 'TERMINATED'].includes(row.invitationStatus)) {
        buttons.push(h(NButton, { size: 'tiny', quaternary: true, onClick: () => openAction(row, 'terminate') }, { default: () => '终止' }))
      }
      return h(NSpace, { size: 4 }, { default: () => buttons })
    },
  },
])

async function loadList() {
  loading.value = true
  try {
    const res = await listInvitations({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...(filterStatus.value && { status: filterStatus.value }),
    })
    dataSource.value = res.data.list
    pagination.value.itemCount = res.data.pagination.total
    pagination.value.pageCount = res.data.pagination.totalPages
  } catch (e: any) {
    message.error(`加载失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

async function loadClaimPool() {
  try {
    const res = await getClaimPool()
    claimPool.value = res.data
  } catch (e) { /* 静默 */ }
}

function handleRefresh() {
  pagination.value.page = 1
  loadList()
  loadClaimPool()
}

function handleFilter() {
  handleRefresh()
}

// 入池
function openEnterPool(row: Invitation) {
  actionModal.value = {
    show: true, loading: false, title: '入抢单池', type: 'warning',
    placeholder: '可填入池原因', action: 'enterPool', id: row.id, reason: '',
    form: { reason: '' },
  }
}

// 抢单
async function handleClaim(row: Invitation) {
  dialog.warning({
    title: '确认抢单',
    content: `确定抢单「${row.ownerName}」的邀约任务? 抢单后 24h 内未联系会自动升级。`,
    positiveText: '抢单',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await claim(row.id)
        message.success('抢单成功')
        handleRefresh()
      } catch (e: any) {
        message.error(`抢单失败: ${e.message}`)
      }
    },
  })
}

// 已联系
async function handleContact(row: Invitation) {
  try {
    await markContacted(row.id, '已电话联系候选人')
    message.success('已标记联系')
    handleRefresh()
  } catch (e: any) {
    message.error(`操作失败: ${e.message}`)
  }
}

// 标记结果
function openResult(row: Invitation, success: boolean) {
  resultModal.value = {
    show: true, loading: false,
    title: success ? '标记成功' : '标记失败',
    form: { id: row.id, success, reason: '' },
  }
}

async function handleResultSubmit() {
  if (!resultModal.value.form.reason.trim()) {
    message.warning('请填写结果原因')
    return
  }
  resultModal.value.loading = true
  try {
    await markResult(resultModal.value.form.id, resultModal.value.form.success, resultModal.value.form.reason)
    message.success('已记录结果')
    resultModal.value.show = false
    handleRefresh()
  } catch (e: any) {
    message.error(`操作失败: ${e.message}`)
  } finally {
    resultModal.value.loading = false
  }
}

// 干预 / 终止
function openAction(row: Invitation, action: 'enterPool' | 'intervene' | 'terminate') {
  if (action === 'enterPool') return openEnterPool(row)
  const isTerminate = action === 'terminate'
  actionModal.value = {
    show: true, loading: false,
    title: isTerminate ? '终止邀约' : '干预 (上级接手)',
    type: isTerminate ? 'error' : 'warning',
    placeholder: isTerminate ? '请说明终止原因' : '请说明干预原因',
    action,
    id: row.id,
    reason: '',
    form: { reason: '' },
  }
}

async function handleActionSubmit() {
  actionModal.value.loading = true
  try {
    if (actionModal.value.action === 'enterPool') {
      await enterPool(actionModal.value.id, actionModal.value.reason)
      message.success('已入抢单池')
    } else if (actionModal.value.action === 'intervene') {
      await intervene(actionModal.value.id, actionModal.value.reason)
      message.success('已记录干预')
    } else if (actionModal.value.action === 'terminate') {
      await terminate(actionModal.value.id, actionModal.value.reason)
      message.success('已终止')
    }
    actionModal.value.show = false
    handleRefresh()
  } catch (e: any) {
    message.error(`操作失败: ${e.message}`)
  } finally {
    actionModal.value.loading = false
  }
}

// 处理超时
async function handleProcessExpired() {
  try {
    const res = await processExpired()
    const s = res.data
    message.success(`处理完成: 处理 ${s.processed} 条, 重入池 ${s.requeued}, 升级 ${s.escalated}, 终止 ${s.terminated}`)
    handleRefresh()
  } catch (e: any) {
    message.error(`处理失败: ${e.message}`)
  }
}

let refreshTimer: number | null = null
onMounted(() => {
  handleRefresh()
  // 每 30 秒刷新倒计时
  refreshTimer = window.setInterval(() => {
    loadClaimPool()
  }, 30000)
})
onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-label { font-size: 12px; color: #8c8c8c; }
.stat-value { font-size: 22px; font-weight: 600; margin-top: 4px; }
.claim-pool { margin-bottom: 16px; border-left: 4px solid #fa8c16; }
.filter-row { margin-bottom: 12px; }
</style>
