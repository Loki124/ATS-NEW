<template>
  <div class="referral-page">
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h1 class="page-title">内推中心</h1>
      <n-button type="primary" @click="addModalVisible = true">
        <template #icon><n-icon :component="PersonAddOutline" /></template>
        新增推荐
      </n-button>
    </div>

    <n-card :bordered="false" class="card-base">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- Tab 1: 我的内推码 -->
        <n-tab-pane name="code" tab="我的内推码">
          <n-grid :cols="2" :x-gap="24" :y-gap="24" responsive="screen" :item-responsive="true">
            <n-grid-item span="2 m:1">
              <n-card title="🎫 当前内推码" :bordered="false" :loading="codeLoading">
                <template v-if="myCode">
                  <div class="code-display">
                    <div class="code-text">{{ myCode.code }}</div>
                    <n-tag :type="myCode.status === 'ACTIVE' ? 'success' : 'error'">
                      {{ myCode.status === 'ACTIVE' ? '生效中' : '已失效' }}
                    </n-tag>
                  </div>
                  <n-text :depth="3" class="block mt-4">创建于 {{ formatDate(myCode.createdAt) }}</n-text>
                  <n-space class="mt-4">
                    <n-button type="primary" @click="copyCode">
                      <template #icon><n-icon :component="CopyOutline" /></template>
                      复制码
                    </n-button>
                    <n-button @click="copyShareLink">
                      <template #icon><n-icon :component="LinkOutline" /></template>
                      复制分享链接
                    </n-button>
                  </n-space>
                </template>
                <n-empty v-else description="暂无内推码，请联系管理员开通" />
              </n-card>
            </n-grid-item>

            <n-grid-item span="2 m:1">
              <n-card title="💡 怎么用" :bordered="false">
                <n-p>1. 把内推码发给候选人</n-p>
                <n-p>2. 候选人通过内推码投递简历</n-p>
                <n-p>3. 候选人入职后你将获得奖励</n-p>
                <n-text :depth="3">详细规则请查看"内推规则"标签页</n-text>
              </n-card>
            </n-grid-item>
          </n-grid>
        </n-tab-pane>

        <!-- Tab 2: 我的战绩 -->
        <n-tab-pane name="summary" tab="我的战绩">
          <n-grid v-if="summary" :cols="3" :x-gap="24" :y-gap="24" responsive="screen" :item-responsive="true">
            <n-grid-item v-for="item in summaryCards" :key="item.label" span="3 s:2 m:1">
              <n-card :bordered="false" class="rounded-lg text-center stat-card">
                <n-icon :component="item.icon" :size="32" :color="item.color" />
                <div class="stat-value" :style="{ color: item.color }">{{ item.value }}</div>
                <n-text :depth="3">{{ item.label }}</n-text>
              </n-card>
            </n-grid-item>
          </n-grid>
          <n-empty v-else-if="!summaryLoading" description="暂无战绩数据" />
        </n-tab-pane>

        <!-- Tab 3: 推荐记录 -->
        <n-tab-pane name="records" tab="推荐记录">
          <n-data-table
            :columns="recordColumns"
            :data="records"
            :loading="recordsLoading"
            :pagination="recordsPagination"
            @update:page="loadRecords"
            :row-key="(row: any) => row.id"
          />
          <n-empty v-if="!recordsLoading && records.length === 0" description="暂无推荐记录，去分享你的内推码吧 🎉" class="mt-6" />
        </n-tab-pane>

        <!-- Tab 4: 我的奖励 -->
        <n-tab-pane name="rewards" tab="我的奖励">
          <n-data-table
            :columns="rewardColumns"
            :data="rewards"
            :loading="rewardsLoading"
            :pagination="rewardsPagination"
            @update:page="loadRewards"
            :row-key="(row: any) => row.id"
          />
          <n-empty v-if="!rewardsLoading && rewards.length === 0" description="暂无奖励" class="mt-6" />
        </n-tab-pane>

        <!-- Tab 5: 内推规则 -->
        <n-tab-pane name="rules" tab="内推规则">
          <n-spin :show="rulesLoading">
            <n-empty v-if="!rulesLoading && rules.length === 0" description="暂未配置内推规则" />
            <n-grid v-else :cols="2" :x-gap="16" :y-gap="16" responsive="screen" :item-responsive="true">
              <n-grid-item v-for="rule in rules" :key="rule.id" span="2 m:1">
                <n-card :bordered="false" class="rounded-lg">
                  <template #header>
                    <n-space>
                      <span>{{ rule.name }}</span>
                      <n-tag :type="rule.ruleType === 'REWARD' ? 'warning' : 'warning'">
                        {{ rule.ruleType === 'REWARD' ? '奖励' : '限制' }}
                      </n-tag>
                    </n-space>
                  </template>
                  <n-descriptions :column="1" size="small">
                    <n-descriptions-item label="职级">{{ rule.positionLevel || '不限' }}</n-descriptions-item>
                    <n-descriptions-item label="触发阶段">{{ rule.triggerStage || '不限' }}</n-descriptions-item>
                    <n-descriptions-item v-if="rule.amount" label="奖励金额">
                      <span style="color: #FBCE5B; font-weight: 600">¥{{ rule.amount }}</span>
                    </n-descriptions-item>
                    <n-descriptions-item label="说明">
                      <n-text :depth="3">
                        {{ rule.description || formatConditions(rule.conditions) }}
                      </n-text>
                    </n-descriptions-item>
                  </n-descriptions>
                </n-card>
              </n-grid-item>
            </n-grid>
          </n-spin>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 新增推荐弹窗 -->
    <AddReferralModal v-model:show="addModalVisible" @success="onAddSuccess" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted, watch } from 'vue'
import { useMessage, NTag, NIcon, NText, NButton, NSpace } from 'naive-ui'
import {
  CopyOutline,
  LinkOutline,
  PersonOutline,
  CheckmarkCircleOutline,
  StarOutline,
  GiftOutline,
  TrendingUpOutline,
  CashOutline,
} from '@vicons/ionicons5'
import {
  getMyCode,
  getMyRecords,
  getMyRecordSummary,
  getMyRewards,
  getRules,
  confirmReward,
  issueReward,
  rejectReward,
  type ReferralCode,
  type ReferralRecord,
  type ReferralRecordSummary,
  type ReferralReward,
  type ReferralRule,
} from '../../api/referral'
import AddReferralModal from './AddReferralModal.vue'

const message = useMessage()

const activeTab = ref('code')
const addModalVisible = ref(false)

// ===== 数据状态 =====
const myCode = ref<ReferralCode | null>(null)
const codeLoading = ref(false)
const summary = ref<ReferralRecordSummary | null>(null)
const summaryLoading = ref(false)
const records = ref<ReferralRecord[]>([])
const recordsTotal = ref(0)
const recordsPage = ref(1)
const recordsLoading = ref(false)
const rewards = ref<ReferralReward[]>([])
const rewardsTotal = ref(0)
const rewardsPage = ref(1)
const rewardsLoading = ref(false)
const rules = ref<ReferralRule[]>([])
const rulesLoading = ref(false)

const recordsPagination = computed(() => ({
  page: recordsPage.value,
  pageSize: 20,
  itemCount: recordsTotal.value,
  showTotal: (t: number) => `共 ${t} 条`,
}))

const rewardsPagination = computed(() => ({
  page: rewardsPage.value,
  pageSize: 20,
  itemCount: rewardsTotal.value,
  showTotal: (t: number) => `共 ${t} 条`,
}))

// ===== 战绩卡片 =====
const summaryCards = computed(() => {
  if (!summary.value) return []
  return [
    { label: '有效推荐', value: summary.value.recommendValidCount, icon: PersonOutline, color: '#1890ff' },
    { label: '已入职', value: summary.value.onboardedCount, icon: CheckmarkCircleOutline, color: '#52c41a' },
    { label: '过试用期', value: summary.value.probationPassedCount, icon: StarOutline, color: '#722ed1' },
    { label: '待确认奖励', value: summary.value.rewardToConfirmTotal, icon: GiftOutline, color: '#fa8c16' },
    { label: '已确认奖励', value: summary.value.rewardConfirmedTotal, icon: TrendingUpOutline, color: '#13c2c2' },
    { label: '已发放奖励', value: summary.value.rewardIssuedTotal, icon: CashOutline, color: '#FBCE5B' },
  ]
})

// ===== 表格列定义（Naive 用 render 函数） =====
const recordColumns = [
  {
    title: '候选人',
    key: 'candidateName',
    render: (row: any) => row.candidate?.name || row.candidateName || '-',
  },
  {
    title: '职位',
    key: 'positionTitle',
    render: (row: any) => row.position?.name || row.positionTitle || '-',
  },
  {
    title: '当前阶段',
    key: 'currentStage',
    render: (row: any) => row.referralStatus || row.currentStage || '-',
  },
  {
    title: '状态',
    key: 'status',
    render: (row: any) =>
      h(NTag, { type: statusToTagType(row.referralStatus || row.status) as any }, {
        default: () => statusLabel(row.referralStatus || row.status),
      }),
  },
  {
    title: '推荐时间',
    key: 'createdAt',
    render: (row: any) => formatDate(row.createdAt || row.recommendedAt),
  },
]

const rewardColumns = [
  {
    title: '候选人',
    key: 'candidateName',
    render: (row: any) => row.candidate?.name || row.candidateName || '-',
  },
  {
    title: '金额',
    key: 'amount',
    render: (row: any) =>
      h('span', { style: { color: '#FBCE5B', fontWeight: 600 } }, `¥${row.amount}`),
  },
  {
    title: '状态',
    key: 'status',
    render: (row: any) =>
      h(NTag, { type: rewardStatusToTagType(row.status) as any }, { default: () => rewardStatusLabel(row.status) }),
  },
  { title: '触发时间', key: 'triggeredAt', render: (row: any) => formatDate(row.triggeredAt) },
  { title: '确认时间', key: 'confirmedAt', render: (row: any) => formatDate(row.confirmedAt) },
  { title: '发放时间', key: 'issuedAt', render: (row: any) => formatDate(row.issuedAt) },
  {
    title: '操作',
    key: 'action',
    width: 200,
    render: (row: any) => {
      // 仅 ADMIN / HRBP 可操作
      const role = JSON.parse(localStorage.getItem('user') || '{}').roleType
      if (!['SUPER_ADMIN', 'HRBP'].includes(role)) return null
      if (row.status === 'TO_CONFIRM') {
        return h(NSpace, { size: 'small' }, () => [
          h(NButton, { size: 'small', type: 'primary', onClick: () => handleRewardAction(row, 'confirm') }, { default: () => '确认' }),
          h(NButton, { size: 'small', onClick: () => handleRewardAction(row, 'reject') }, { default: () => '拒绝' }),
        ])
      }
      if (row.status === 'CONFIRMED') {
        return h(NButton, { size: 'small', type: 'primary', onClick: () => handleRewardAction(row, 'issue') }, { default: () => '发放' })
      }
      return null
    },
  },
]

// ===== 加载 =====
async function loadCode() {
  codeLoading.value = true
  try { myCode.value = await getMyCode() } catch { myCode.value = null } finally { codeLoading.value = false }
}
async function loadSummary() {
  summaryLoading.value = true
  try { summary.value = await getMyRecordSummary() } catch { summary.value = null } finally { summaryLoading.value = false }
}
async function loadRecords(page = 1) {
  recordsLoading.value = true
  try {
    const data = await getMyRecords(page, 20)
    records.value = data.list
    recordsTotal.value = data.total
    recordsPage.value = data.page
  } catch { records.value = []; recordsTotal.value = 0 }
  finally { recordsLoading.value = false }
}
async function loadRewards(page = 1) {
  rewardsLoading.value = true
  try {
    const data = await getMyRewards(page, 20)
    rewards.value = data.list
    rewardsTotal.value = data.total
    rewardsPage.value = data.page
  } catch { rewards.value = []; rewardsTotal.value = 0 }
  finally { rewardsLoading.value = false }
}
async function loadRules() {
  rulesLoading.value = true
  try { rules.value = await getRules() } catch (e: any) {
    if (e?.response?.status === 403) {
      rules.value = []
      message.info('仅管理员可查看规则配置')
    } else rules.value = []
  } finally { rulesLoading.value = false }
}

// ===== 交互 =====
async function copyCode() {
  if (!myCode.value) return
  try {
    await navigator.clipboard.writeText(myCode.value.code)
    message.success('内推码已复制')
  } catch { message.error('复制失败，请手动复制') }
}
async function copyShareLink() {
  if (!myCode.value) return
  const link = `${window.location.origin}/referral/apply?code=${myCode.value.code}`
  try {
    await navigator.clipboard.writeText(link)
    message.success('分享链接已复制')
  } catch { message.error('复制失败，请手动复制') }
}

// ===== 工具 =====
function formatDate(s?: string | null) {
  if (!s) return '-'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}
function statusToTagType(s: string) {
  return ({ NORMAL: 'info', PROTECTING: 'info', HIRED: 'success', REJECTED: 'error', EXPIRED: 'default' } as Record<string, string>)[s] || 'default'
}
function statusLabel(s: string) {
  return ({ NORMAL: '正常', PROTECTING: '保护期', HIRED: '已入职', REJECTED: '已拒绝', EXPIRED: '已过期' } as Record<string, string>)[s] || s
}
function rewardStatusToTagType(s: string) {
  return ({ TO_CONFIRM: 'warning', CONFIRMED: 'info', ISSUED: 'success', REJECTED: 'error' } as Record<string, string>)[s] || 'default'
}
function rewardStatusLabel(s: string) {
  return ({ TO_CONFIRM: '待确认', CONFIRMED: '已确认', ISSUED: '已发放', REJECTED: '已拒绝' } as Record<string, string>)[s] || s
}
function formatConditions(conditions: any) {
  if (!conditions?.conditions) return '-'
  return conditions.conditions.map((c: any) => `${c.key} ${c.op} ${c.value}`).join(' 且 ')
}

// 懒加载
watch(activeTab, (tab) => {
  if (tab === 'code' && !myCode.value) loadCode()
  if (tab === 'summary' && !summary.value) loadSummary()
  if (tab === 'records' && records.value.length === 0) loadRecords()
  if (tab === 'rewards' && rewards.value.length === 0) loadRewards()
  if (tab === 'rules' && rules.value.length === 0) loadRules()
})

// ===== 奖励操作 =====
async function handleRewardAction(row: ReferralReward, action: 'confirm' | 'reject' | 'issue') {
  const labels = { confirm: '确认', reject: '拒绝', issue: '发放' }
  try {
    if (action === 'confirm') await confirmReward(row.id)
    else if (action === 'reject') await rejectReward(row.id)
    else await issueReward(row.id)
    message.success(`已${labels[action]}奖励`)
    await loadRewards(rewardsPage.value)
  } catch (e: any) {
    message.error(e?.response?.data?.message || `${labels[action]}失败`)
  }
}

function onAddSuccess() {
  // 刷新战绩和记录
  loadSummary()
  loadRecords(recordsPage.value)
}

onMounted(() => loadCode())
</script>

<style scoped>
.referral-page { padding: 0; }
.code-display {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  border-radius: 8px;
  color: white;
}
.code-text {
  font-size: 36px;
  font-weight: 700;
  letter-spacing: 4px;
  font-family: 'SF Mono', Menlo, monospace;
}
.stat-card .stat-value {
  font-size: 32px;
  font-weight: 600;
  margin: 12px 0;
}
</style>
