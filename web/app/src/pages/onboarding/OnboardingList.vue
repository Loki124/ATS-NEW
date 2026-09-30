<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, h, onMounted, computed } from 'vue'
import { NTag, NSpace, NButton, NIcon, NDrawer, NDrawerContent, NDataTable, NDropdown, useMessage, useDialog } from 'naive-ui'
import { RefreshOutline, BulbOutline } from '@vicons/ionicons5'
import {
  listOnboardings, transitionOnboarding,
  ONBOARDING_STATUS_LABEL, ONBOARDING_STATUS_COLOR,
  type Onboarding,
} from '../../api/onboarding'
import {
  recommendPositionsForCandidate,
  type RecommendedPosition,
} from '../../api/recommendation'
import StateView from '../../components/common/StateView.vue'
const { t } = useI18n()

const message = useMessage()
const loading = ref(false)
const error = ref<string | null>(null)
const dataSource = ref<Onboarding[]>([])
const filterStatus = ref<string | null>(null)
const pagination = ref({ page: 1, pageSize: 20, itemCount: 0, pageCount: 0 })

// G31 智能分配
const drawerVisible = ref(false)
const drawerLoading = ref(false)
const recommendedPositions = ref<RecommendedPosition[]>([])
const currentOnboarding = ref<Onboarding | null>(null)

const recommendColumns = [
  { title: '职位', key: 'title', render: (row: RecommendedPosition) => row.title || row.name || '—' },
  { title: '地点', key: 'workLocation', width: 100, render: (row: RecommendedPosition) => row.workLocation || '—' },
  { title: '学历', key: 'education', width: 80, render: (row: RecommendedPosition) => row.education || '—' },
  { title: '经验', key: 'experience', width: 100, render: (row: RecommendedPosition) => `${row.minExperience ?? 0}-${row.maxExperience ?? 99}年` },
  {
    title: '匹配分', key: 'score', width: 100,
    render: (row: RecommendedPosition) => h(NTag, { type: row.score >= 0.8 ? 'success' : row.score >= 0.6 ? 'info' : 'default', size: 'small' }, { default: () => (row.score * 100).toFixed(0) + '%' }),
  },
  { title: '原因', key: 'matchReason', render: (row: RecommendedPosition) => row.matchReason || '—' },
]

const stats = computed(() => {
  const counts: Record<string, number> = {}
  for (const it of (dataSource.value ?? [])) {
    counts[it.onboardingStatus] = (counts[it.onboardingStatus] || 0) + 1
  }
  return counts
})

const columns = computed(() => [
  { title: '岗位', key: 'jobTitle', width: 160, render: (row: Onboarding) => row.jobTitle || '—' },
  { title: '职级', key: 'jobLevel', width: 80, render: (row: Onboarding) => row.jobLevel || '—' },
  { title: '期望入职', key: 'expectedJoinDate', width: 120, render: (row: Onboarding) => row.expectedJoinDate?.slice(0, 10) },
  { title: '实际入职', key: 'onboardedAt', width: 140, render: (row: Onboarding) => row.onboardedAt?.slice(0, 16) || '—' },
  {
    title: '状态', key: 'onboardingStatus', width: 100,
    render: (row: Onboarding) => h(NTag, { type: ONBOARDING_STATUS_COLOR[row.onboardingStatus] as any, size: 'small' }, { default: () => ONBOARDING_STATUS_LABEL[row.onboardingStatus] || row.onboardingStatus }),
  },
  {
    title: '操作', key: 'actions', width: 180, fixed: 'right' as const,
    render: (row: Onboarding) => {
      // v2: 主按钮「智能分配」 + 下拉（状态变更 + 取消）
      const items: Array<{ label: string; key: string; danger?: boolean; onClick: () => void }> = []
      if (row.onboardingStatus === 'NOT_STARTED') {
        items.push({ label: '提醒确认', key: 'remind', onClick: () => handleTransition(row, 'PENDING_CONFIRM') })
      }
      if (row.onboardingStatus === 'PENDING_CONFIRM') {
        items.push({ label: '已确认', key: 'confirm', onClick: () => handleTransition(row, 'CONFIRMED') })
        items.push({ label: '拒入职', key: 'reject', danger: true, onClick: () => handleTransition(row, 'PENDING_REJECT') })
      }
      if (row.onboardingStatus === 'CONFIRMED') {
        items.push({ label: '到入职日', key: 'to_onboard', onClick: () => handleTransition(row, 'PENDING_ONBOARD') })
      }
      if (row.onboardingStatus === 'PENDING_ONBOARD') {
        items.push({ label: '开始入职', key: 'start', onClick: () => handleTransition(row, 'ONBOARDING') })
      }
      if (row.onboardingStatus === 'ONBOARDING') {
        items.push({ label: '完成入职', key: 'finish', onClick: () => handleTransition(row, 'ONBOARDED') })
      }
      if (!['ONBOARDED', 'CANCELLED'].includes(row.onboardingStatus)) {
        items.push({ label: '取消', key: 'cancel', danger: true, onClick: () => handleTransition(row, 'CANCELLED') })
      }
      if (items.length === 0 && !row.candidateId) return '—'
      // 主按钮：智能分配（drawer 操作）；若无 candidateId 则选第一个状态变更
      const hasRecommend = !!row.candidateId
      const primary = hasRecommend
        ? { label: '智能分配', onClick: () => openRecommendDrawer(row) }
        : (items[0] ? { label: items[0].label, onClick: items[0].onClick } : null)
      if (!primary) return '—'
      const rest = hasRecommend ? items : items.slice(1)
      return h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'tiny', type: hasRecommend ? 'info' : 'primary', onClick: primary.onClick }, {
            default: () => primary.label,
            icon: hasRecommend ? () => h(NIcon, null, { default: () => h(BulbOutline) }) : undefined,
          }),
          rest.length
            ? h(NDropdown, {
                options: rest.map(it => ({
                  label: it.label,
                  key: it.key,
                  ...(it.danger ? { props: { style: 'color: var(--c-error)' } } : {}),
                })),
                trigger: 'click',
                onSelect: (k: string) => rest.find(it => it.key === k)?.onClick(),
              }, {
                default: () => h(NButton, { size: 'tiny', quaternary: true }, { default: () => '更多 ⌄' }),
              })
            : null,
        ].filter(Boolean),
      })
    },
  },
])

async function loadList() {
  loading.value = true
  try {
    const res = await listOnboardings({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...(filterStatus.value && { onboardingStatus: filterStatus.value }),
    })
    dataSource.value = res.data ?? []
    pagination.value.itemCount = res.pagination?.total ?? 0
    pagination.value.pageCount = res.pagination?.totalPages ?? 0
  } catch (e: any) {
    message.error(`加载失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

async function handleTransition(row: Onboarding, to: string) {
  // v2: 危险状态（PENDING_REJECT / CANCELLED）弹 dialog 二次确认
  if (['PENDING_REJECT', 'CANCELLED'].includes(to)) {
    try {
      const dialog = useDialog()
      await dialog.warning({
        title: '确认操作',
        content: `将该入职记录状态变更为「${to === 'PENDING_REJECT' ? '拒入职' : '取消'}」，是否继续？`,
        positiveText: '确认',
        negativeText: '取消',
      })
    } catch { return }
  }
  try {
    await transitionOnboarding(row.id, to)
    message.success('状态已更新')
    loadList()
  } catch (e: any) {
    message.error(`操作失败: ${e.message}`)
  }
}

async function openRecommendDrawer(row: Onboarding) {
  if (!row.candidateId) {
    message.warning('该入职记录无候选人信息, 无法推荐')
    return
  }
  currentOnboarding.value = row
  drawerVisible.value = true
  drawerLoading.value = true
  try {
    recommendedPositions.value = await recommendPositionsForCandidate(row.candidateId, 10)
  } catch (e: any) {
    message.error(`推荐失败: ${e.message}`)
    recommendedPositions.value = []
  } finally {
    drawerLoading.value = false
  }
}

onMounted(loadList)

// v2: 表格行键盘可达 [T8.4]
function rowProps(row: any) {
  return {
    tabindex: 0,
    role: 'button',
    'aria-label': `入职记录 ${row.candidateName || row.id}`,
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.onboarding.OnboardingList.s1') }}</h1>
      <n-space>
        <n-button :loading="loading" @click="loadList">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          {{ t('pages.onboarding.OnboardingList.s2') }}
        </n-button>
      </n-space>
    </div>

    <n-grid x-gap="12" y-gap="12" cols="4" class="stats-row">
      <n-gi v-for="(count, key) in stats" :key="key">
        <n-card size="small" :bordered="false" class="stat-card">
          <div class="stat-label">{{ ONBOARDING_STATUS_LABEL[key] }}</div>
          <div class="stat-value">{{ count }}</div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-card :bordered="false" class="rounded-xl">
      <n-space class="filter-row">
        <n-select
          v-model:value="filterStatus"
          :placeholder="t('pages.onboarding.OnboardingList.s3')"
          style="width: 140px"
          clearable
          :options="Object.entries(ONBOARDING_STATUS_LABEL).map(([v,l]) => ({value:v,label:l}))"
          @update:value="loadList"
        />
      </n-space>
      <n-data-table
        :columns="columns"
        :row-props="rowProps"
        :data="dataSource"
        :loading="loading"
        :row-key="(row: Onboarding) => row.id"
        :pagination="pagination"
        @update:page="(p: number) => { pagination.page = p; loadList() }"
      />
    </n-card>

    <!-- G31 智能分配抽屉 -->
    <n-drawer v-model:show="drawerVisible" :width="720" placement="right">
      <n-drawer-content
        :title="`智能分配 - ${currentOnboarding?.candidateName || ''}`"
        closable
      >
        <n-data-table
          :columns="recommendColumns"
          :data="recommendedPositions"
          :loading="drawerLoading"
          :row-key="(row: RecommendedPosition) => row.id"
          :pagination="{ pageSize: 10 }"
        />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<style scoped>
.page-container { animation: wb-fade-up var(--duration-slow) var(--ease-out) both; }
.page-header { margin-bottom: var(--space-4); display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: var(--fs-24); font-weight: 600; margin: 0; }
.stats-row { margin-bottom: var(--space-4); }
.stat-card { text-align: center; }
.stat-label { font-size: var(--fs-12); color: var(--ink-faint); }
.stat-value { font-size: 22px; font-weight: 600; margin-top: var(--space-1); }
.filter-row { margin-bottom: var(--space-3); }

/* === v2 响应式补丁 === */
@media (max-width: 1280px) {
  .page-title { font-size: var(--text-h2); }
  :deep(.n-data-table-wrapper) {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
@media (max-width: 768px) {
  .page-header { flex-direction: column; align-items: stretch; gap: var(--space-3); }
  .stats-row { grid-template-columns: repeat(2, 1fr) !important; } /* v2.9: 保留 !important（覆盖 Naive n-grid 内联 grid-template-columns，移除则移动端不退化为 2 列） */
}
@media (max-width: 480px) {
  .stats-row { grid-template-columns: 1fr !important; } /* v2.9: 保留 !important（覆盖 Naive n-grid 内联 grid-template-columns，移除则移动端不退化为 1 列） */
}

</style>
