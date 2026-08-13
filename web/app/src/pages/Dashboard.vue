<template>
  <div class="dashboard-workbench">
    <!-- ========== Hero: AI 助手问候 (H5 Letter) ========== -->
    <section class="dashboard-hero workbench-card workbench-card--stagger-1">
      <div class="hero-greeting">
        <div class="ai-avatar" aria-hidden="true">小森</div>
        <div class="hero-text">
          <h1 class="hero-title">{{ greeting }}, {{ userName }}</h1>
          <p class="hero-subtitle">欢迎回来 — 这是您今天的招聘概况</p>
        </div>
        <n-button class="hero-action" @click="onHeroAction">查看更多</n-button>
      </div>
    </section>

    <!-- ========== 主区: 2-column 左主右辅 ========== -->
    <div class="dashboard-grid">
      <!-- 左主: 4 stat cards + 招聘日程 -->
      <div class="dashboard-main">
        <StatBar
          class="workbench-card workbench-card--stagger-2"
          :stats="[
            { key: 'pendingScreening', label: '待初筛', value: data?.stats?.pendingInitial ?? 0, accentColor: 'amber', href: '/candidates' },
            { key: 'pendingTodo', label: '待处理', value: data?.stats?.pendingTodo ?? 0, accentColor: 'rose', href: '/notifications' },
            { key: 'pendingRecommend', label: '推荐', value: data?.stats?.pendingRecommend ?? 0, accentColor: 'sky', href: '/referral' },
            { key: 'pendingScreeningDone', label: '初筛', value: data?.stats?.pendingScreening ?? 0, accentColor: 'emerald', href: '/screenings' },
          ]"
        />

        <n-card
          title="招聘日程"
          class="workbench-card workbench-card--stagger-6 schedule-card"
          :bordered="true"
        >
          <WeeklySchedule :interviews="data?.interviews ?? []" />
        </n-card>

        <!-- ========== 重要事项 (tabbed panel) — 置于招聘日程下方 ========== -->
        <n-card
          title="重要事项"
          class="workbench-card workbench-card--stagger-7 matters-card"
          :bordered="true"
        >
          <n-tabs v-model:value="matterTab" type="line" :tabs-padding="12">
            <n-tab-pane
              v-for="tab in MATTER_TABS"
              :key="tab.key"
              :name="tab.key"
            >
              <template #tab>
                <span class="matter-tab">
                  {{ tab.label }}
                  <span v-if="(data?.matterCounts?.[tab.key] ?? 0) > 0" class="matter-tab__count">
                    {{ data?.matterCounts?.[tab.key] }}
                  </span>
                </span>
              </template>
              <MatterList
                v-if="(data?.matters?.[tab.key]?.length ?? 0) > 0"
                :matters="data?.matters?.[tab.key] ?? []"
                @action="onMatterAction"
              />
              <EmptyState
                v-else
                title="暂无相关事项"
                description="当前 tab 下没有需要处理的提醒"
              />
            </n-tab-pane>
          </n-tabs>
        </n-card>
      </div>

      <!-- 右辅: 搜索 / 雷达访问 / 快捷入口 / 我发的筛选 -->
      <aside class="dashboard-side">
        <div class="workbench-card workbench-card--stagger-2">
          <n-input
            v-model:value="searchKeyword"
            placeholder="搜索网络简历, 多个关键词用逗号或空格隔开"
            clearable
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
        </div>

        <!-- 制度公告：招聘专家查看招聘相关制度与公告内容 -->
        <n-card
          v-if="showAnnouncementModule"
          title="制度公告"
          class="workbench-card workbench-card--stagger-3 side-card announcement-card"
          :bordered="true"
        >
          <template #header-extra>
            <n-button text size="small" type="primary" @click="goAnnouncementList">查看全部</n-button>
          </template>
          <div class="announcement-list">
            <div
              v-for="item in announcements.slice(0, 5)"
              :key="item.id"
              class="announcement-item"
              role="button"
              tabindex="0"
              @click="openAnnouncementDetail(item)"
              @keydown.enter="openAnnouncementDetail(item)"
            >
              <div class="announcement-item__head">
                <n-tag v-if="item.pinned" size="tiny" type="error" round>置顶</n-tag>
                <n-tag size="tiny" :type="categoryType(item.category)" round>{{ item.categoryDisplay }}</n-tag>
                <span class="announcement-item__title">{{ item.title }}</span>
                <span v-if="item.attachments?.length" class="announcement-item__attach" title="含附件">📎</span>
              </div>
              <p class="announcement-item__preview">{{ item.summary || '（暂无概述，请在后台配置）' }}</p>
            </div>
            <div v-if="announcements.length === 0" class="announcement-list__empty">
              <n-empty size="small" description="暂无制度公告" />
            </div>
          </div>
        </n-card>

        <!-- 制度公告 详情抽屉 -->
        <n-drawer
          v-model:show="announcementDetailVisible"
          :width="440"
          placement="right"
          :trap-focus="false"
        >
          <n-drawer-content :native-scrollbar="false">
            <template #header>
              <span class="ann-detail__title">{{ announcementDetail?.title }}</span>
            </template>
            <div v-if="announcementDetail" class="ann-detail">
              <div class="ann-detail__meta">
                <n-tag size="small" :type="categoryType(announcementDetail.category)" round>{{ announcementDetail.categoryDisplay }}</n-tag>
                <n-tag size="small" round>{{ announcementDetail.audienceDisplay }}</n-tag>
                <span class="ann-detail__time">{{ fmtAnnouncementTime(announcementDetail.publishedAt) }}</span>
              </div>
              <p class="ann-detail__body">{{ announcementDetail.body }}</p>
              <div v-if="announcementDetail.attachments && announcementDetail.attachments.length" class="ann-detail__attachments">
                <div class="ann-detail__attach-title">附件</div>
                <a
                  v-for="att in announcementDetail.attachments"
                  :key="att.id"
                  class="ann-detail__attach"
                  :href="att.fileUrl"
                  target="_blank"
                  rel="noopener"
                >
                  <span class="ann-detail__attach-name">📎 {{ att.originalName }}</span>
                  <span class="ann-detail__attach-size">{{ formatFileSize(att.fileSize) }}</span>
                </a>
              </div>
            </div>
          </n-drawer-content>
        </n-drawer>

        <n-card
          title="雷达访问职位"
          class="workbench-card workbench-card--stagger-3 side-card"
          :bordered="true"
        >
          <div class="job-list">
            <JobCard
              v-for="job in data?.jobs ?? []"
              :key="job.id"
              :job="job"
              @click="onJobClick"
            />
            <div v-if="(data?.jobs?.length ?? 0) === 0" class="job-list__empty">
              <n-empty size="small" description="暂无访问职位" />
            </div>
          </div>
        </n-card>

        <n-card
          title="快捷入口"
          class="workbench-card workbench-card--stagger-4 side-card"
          :bordered="true"
        >
          <n-grid :cols="2" :x-gap="12" :y-gap="12" responsive="screen">
            <n-grid-item
              v-for="entry in quickEntries"
              :key="entry.key"
              :span="2"
              class="quick-entry-item"
            >
              <QuickEntryCard :entry="entry" @click="onQuickEntry" />
            </n-grid-item>
          </n-grid>
        </n-card>

        <n-card
          title="我发的筛选"
          class="workbench-card workbench-card--stagger-5 side-card"
          :bordered="true"
        >
          <div class="screening-list">
            <ScreeningListItem
              v-for="screening in data?.screenings ?? []"
              :key="screening.id"
              :screening="screening"
              @click="onScreeningClick"
            />
            <div v-if="(data?.screenings?.length ?? 0) === 0" class="screening-list__empty">
              <n-empty size="small" description="暂无筛选" />
            </div>
          </div>
        </n-card>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { SearchOutline, MailUnreadOutline, StarOutline, LockClosedOutline, BriefcaseOutline } from '@vicons/ionicons5'
// Plan O: 子组件改 defineAsyncComponent 异步加载
//   - 减小首屏 JS bundle
//   - 配合 SkeletonCard 占位, 加载完才显示真实内容
import { SkeletonCard } from '../components/dashboard'
import { loadDashboardData, type DashboardData } from '../api/dashboard'
import { listAnnouncements, getAnnouncementConfig, type Announcement, type AnnouncementCategory } from '../api/announcement'
import type { QuickEntryData, JobCardData, ScreeningItemData, MatterItem } from '../components/dashboard'
// Plan O Task 6: 搜索 debounce (300ms)
import { debounce } from '../utils/debounce'

const StatBar = defineAsyncComponent(() => import('../components/dashboard/StatBar.vue'))
const WeeklySchedule = defineAsyncComponent(() => import('../components/dashboard/WeeklySchedule.vue'))
const JobCard = defineAsyncComponent(() => import('../components/dashboard/JobCard.vue'))
const QuickEntryCard = defineAsyncComponent(() => import('../components/dashboard/QuickEntryCard.vue'))
const ScreeningListItem = defineAsyncComponent(() => import('../components/dashboard/ScreeningListItem.vue'))
const MatterList = defineAsyncComponent(() => import('../components/dashboard/MatterList.vue'))
const EmptyState = defineAsyncComponent(() => import('../components/dashboard/EmptyState.vue'))

const router = useRouter()

const searchKeyword = ref('')
const matterTab = ref<string>('recruit')
const data = ref<DashboardData | null>(null)

// 制度公告（工作台右侧模块，招聘专家查看）
const announcements = ref<Announcement[]>([])
// 工作台是否展示制度公告模块（后台配置；默认 true，配置读取失败时 fail-open 仍展示）
const showAnnouncementModule = ref(true)

// 制度公告详情抽屉
const announcementDetailVisible = ref(false)
const announcementDetail = ref<Announcement | null>(null)

function openAnnouncementDetail(item: Announcement) {
  announcementDetail.value = item
  announcementDetailVisible.value = true
}

function categoryType(c: AnnouncementCategory): 'info' | 'success' | 'warning' {
  if (c === 'NOTICE') return 'success'
  if (c === 'PROCESS') return 'warning'
  return 'info'
}

function fmtAnnouncementTime(iso?: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function formatFileSize(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

async function fetchAnnouncements() {
  try {
    announcements.value = await listAnnouncements()
  } catch {
    announcements.value = []
  }
}

async function fetchAnnouncementConfig() {
  try {
    const cfg = await getAnnouncementConfig()
    if (typeof cfg?.showOnWorkbench === 'boolean') {
      showAnnouncementModule.value = cfg.showOnWorkbench
    }
  } catch {
    // 配置读取失败：fail-open，保持展示
    showAnnouncementModule.value = true
  }
}

function goAnnouncementList() {
  router.push('/announcements')
}

const MATTER_TABS = [
  { key: 'recruit', label: '招聘需求相关' },
  { key: 'position', label: '职位相关' },
  { key: 'interview', label: '面试相关' },
  { key: 'offer', label: 'Offer 相关' },
  { key: 'recommend', label: '推荐相关' },
  { key: 'other', label: '其他' },
] as const

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const userName = computed(() => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) {
      const u = JSON.parse(raw) as { realName?: string; username?: string }
      return u.realName || u.username || '招聘官'
    }
  } catch {
    /* noop */
  }
  return '招聘官'
})

const quickEntries = computed<QuickEntryData[]>(() => [
  {
    key: 'archived',
    label: '未归档简历',
    subtitle: '从历史记录继续',
    count: data.value?.quickCounts.archivedResumes ?? 0,
    icon: MailUnreadOutline,
    to: '/candidates',
  },
  {
    key: 'watching-positions',
    label: '我关注的职位',
    subtitle: '订阅职位动态',
    count: data.value?.quickCounts.watchingPositions ?? 0,
    icon: BriefcaseOutline,
    to: '/positions',
  },
  {
    key: 'watching-candidates',
    label: '我关注的应聘者',
    subtitle: '状态变化时通知我',
    count: data.value?.quickCounts.watchingCandidates ?? 0,
    icon: StarOutline,
    to: '/talent-pool',
  },
  {
    key: 'locked',
    label: '已锁定的应聘者',
    subtitle: '本季度独占',
    count: data.value?.quickCounts.lockedCandidates ?? 0,
    icon: LockClosedOutline,
    to: '/candidates',
  },
])

async function fetchData() {
  try {
    data.value = await loadDashboardData()
  } catch {
    // 全部失败时, 保留 null, 模板 fallback
    data.value = null
  }
}

// Plan O Task 6: 搜索 debounce (300ms)
//   - 用户停止输入 300ms 后再触发
//   - 避免每次按键都发请求
const debouncedSearch = debounce((keyword: string) => {
  // 触发 searchKeyword 副作用: 重新拉 jobs 列表
  if (keyword.trim()) {
    void loadJobs(keyword.trim())
  }
}, 300)

async function loadJobs(keyword: string) {
  try {
    // 简化为复用 fetchData, 后续可改为独立 /api/positions?keyword=
    await fetchData()
  } catch {
    // 静默失败
  }
}

watch(searchKeyword, (val) => {
  debouncedSearch(val)
})

onMounted(() => {
  void fetchData()
  void fetchAnnouncements()
  void fetchAnnouncementConfig()
})

// ===== 事件 =====

function onHeroAction() {
  matterTab.value = 'other'
  void nextTick(() => {
    const el = document.querySelector('.matters-card')
    if (el && 'scrollIntoView' in el) {
      (el as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
}

function onJobClick(job: JobCardData) {
  router.push(`/positions/${job.id}`)
}

function onScreeningClick(screening: ScreeningItemData) {
  router.push(`/screenings?demandId=${screening.id}`)
}

function onQuickEntry(entry: QuickEntryData) {
  // QuickEntryCard 内部已经 router.push; 这里只用于埋点扩展
  void entry
}

function onMatterAction(_matter: MatterItem) {
  // 默认行为: 跳转相关列表
  if (matterTab.value === 'recruit') router.push('/demands')
  else if (matterTab.value === 'position') router.push('/positions')
  else if (matterTab.value === 'interview') router.push('/interviews')
  else if (matterTab.value === 'offer') router.push('/offers')
  else if (matterTab.value === 'recommend') router.push('/referral')
  else router.push('/notifications')
}
</script>

<style scoped>
.dashboard-workbench {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;
}

/* ===== Hero ===== */
.dashboard-hero {
  background: var(--color-surface-sunk);
  border: 1px solid var(--color-border-hairline);
  border-radius: var(--radius-lg);
  padding: var(--space-8) var(--space-8);
}

.hero-greeting {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.ai-avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-pill);
  background: var(--color-accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-h3);
  font-weight: 500;
  flex-shrink: 0;
}

.hero-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.hero-title {
  margin: 0;
  color: var(--color-ink);
  font-size: var(--text-h2);
  font-weight: 500;
  line-height: 1.3;
}

.hero-subtitle {
  margin: 0;
  color: var(--color-ink-soft);
  font-size: var(--text-body);
  line-height: 1.5;
}

.hero-action {
  flex-shrink: 0;
}

/* ===== Grid (左主右辅) ===== */
.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: var(--space-6);
  align-items: start;
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

.dashboard-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.dashboard-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* ===== Cards overrides ===== */
.schedule-card,
.side-card,
.matters-card {
  background: var(--color-surface-raised);
}

.schedule-card :deep(.n-card__content) {
  padding-top: var(--space-2);
}

.side-card :deep(.n-card__content) {
  padding-top: var(--space-2);
}

/* ===== Job / Screening lists ===== */
.job-list,
.screening-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.job-list__empty,
.screening-list__empty {
  padding: var(--space-4) 0;
  display: flex;
  justify-content: center;
}

.quick-entry-item {
  display: block;
}

/* ===== 制度公告 (右侧栏) ===== */
.announcement-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.announcement-item {
  padding: var(--space-2) var(--space-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s ease;
}

.announcement-item:hover {
  background: var(--color-surface-sunk);
}

.announcement-item__head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.announcement-item__title {
  color: var(--color-ink);
  font-size: var(--text-body);
  line-height: 1.4;
  flex: 1;
  min-width: 0;
}

.announcement-item__attach {
  font-size: 13px;
  flex-shrink: 0;
}

.announcement-item__preview {
  margin: var(--space-1) 0 0;
  padding-left: var(--space-1);
  color: var(--color-ink-soft);
  font-size: var(--text-small);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.announcement-list__empty {
  padding: var(--space-4) 0;
  display: flex;
  justify-content: center;
}

/* ===== 制度公告 详情抽屉 ===== */
.ann-detail__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
}
.ann-detail__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
}
.ann-detail__time {
  color: var(--color-ink-soft);
  font-size: var(--text-small);
}
.ann-detail__body {
  margin: 0;
  color: var(--color-ink);
  font-size: var(--text-body);
  line-height: 1.7;
  white-space: pre-wrap;
}
.ann-detail__attachments {
  margin-top: var(--space-6);
  border-top: 1px solid var(--color-border-hairline);
  padding-top: var(--space-4);
}
.ann-detail__attach-title {
  font-size: var(--text-small);
  color: var(--color-ink-soft);
  margin-bottom: var(--space-2);
}
.ann-detail__attach {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface-sunk);
  color: var(--color-ink);
  text-decoration: none;
  margin-bottom: var(--space-2);
  transition: background 0.15s ease;
}
.ann-detail__attach:hover {
  background: var(--color-border-hairline);
}
.ann-detail__attach-size {
  color: var(--color-ink-soft);
  font-size: var(--text-small);
  flex-shrink: 0;
}

/* ===== Matters tab badge ===== */
.matter-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.matter-tab__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: var(--color-accent-soft);
  color: var(--color-accent);
  font-size: 10px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
</style>
