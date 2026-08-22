<template>
  <div class="dashboard-workbench">
    <!-- ========== Hero: AI 助手问候 (H5 Letter) ========== -->
    <section class="dashboard-hero workbench-card workbench-card--stagger-1">
      <div class="hero-main">
        <div class="hero-greeting">
          <div class="ai-avatar" aria-hidden="true">小森</div>
          <div class="hero-text">
            <h1 class="hero-title">{{ greeting }}, {{ userName }}</h1>
            <p class="hero-subtitle">{{ todaySummary }}</p>
          </div>
        </div>
        <div class="hero-search">
          <n-input
            v-model:value="searchKeyword"
            placeholder="搜索网络简历"
            clearable
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
        </div>
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
            { key: 'pendingTodo', label: '待办', value: data?.stats?.pendingTodo ?? 0, accentColor: 'rose', href: '/notifications' },
            { key: 'pendingRecommend', label: '推荐人才', value: data?.stats?.pendingRecommend ?? 0, accentColor: 'sky', href: '/referral' },
            { key: 'pendingScreeningDone', label: '初筛中', value: data?.stats?.pendingScreening ?? 0, accentColor: 'emerald', href: '/screenings' },
          ]"
        />

        <!-- ========== 重要事项 (tabbed panel) — 主区第二顺位, 强引导 ========== -->
        <n-card
          title="重要事项"
          class="workbench-card workbench-card--stagger-3 matters-card"
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

        <n-card
          title="招聘日程"
          class="workbench-card workbench-card--stagger-6 schedule-card"
          :bordered="true"
        >
          <WeeklySchedule :interviews="data?.interviews ?? []" />
        </n-card>
      </div>

      <!-- 右辅: 搜索 / 雷达访问 / 快捷入口 / 我发的筛选 -->
      <aside class="dashboard-side">
        <!-- 政策制度：工作台右侧卡片（知识库风格），置顶于参考资源区 -->
        <n-card
          v-if="showAnnouncementModule"
          title="政策制度"
          class="workbench-card workbench-card--stagger-3 side-card announcement-card"
          :bordered="true"
        >
          <template #header-extra>
            <n-button text size="small" type="primary" @click="goAnnouncementList">
              更多<n-icon :component="ChevronForwardOutline" :size="16" style="margin-left: 2px" />
            </n-button>
          </template>
          <div class="announcement-list">
            <div
              v-for="item in workbenchAnnouncements.slice(0, 6)"
              :key="item.id"
              class="announcement-item"
              role="button"
              tabindex="0"
              @click="goAnnouncementDetail(item.id)"
              @keydown.enter="goAnnouncementDetail(item.id)"
            >
              <div class="announcement-item__icon">
                <n-icon :component="DocumentTextOutline" :size="18" />
              </div>
              <div class="announcement-item__content">
                <span class="announcement-item__title" :title="item.title">{{ item.title }}</span>
                <span class="announcement-item__date">{{ fmtAnnouncementDate(item.updatedAt || item.publishedAt) }} 更新</span>
              </div>
              <n-icon :component="ChevronForwardOutline" :size="16" class="announcement-item__arrow" />
            </div>
            <div v-if="announcements.length === 0" class="announcement-list__empty">
              <n-empty size="small" description="暂无制度公告" />
            </div>
          </div>
        </n-card>

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
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { SearchOutline, MailUnreadOutline, StarOutline, LockClosedOutline, BriefcaseOutline, DocumentTextOutline, ChevronForwardOutline } from '@vicons/ionicons5'
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
// 工作台是否展示政策制度模块（模块总开关；默认 true，配置读取失败时 fail-open 仍展示）
const showAnnouncementModule = ref(true)
// 仅展示标记为「工作台」的单条公告
const workbenchAnnouncements = computed(() =>
  announcements.value.filter((a) => a.showOnWorkbench),
)
// 是否存在已发布公告（用于快捷入口是否出现政策制度入口）
const hasMoreAnnouncements = computed(() =>
  announcements.value.some((a) => a.isActive),
)

function goAnnouncementDetail(id: string) {
  router.push(`/announcements/${id}`)
}

function categoryType(c: AnnouncementCategory): 'info' | 'success' | 'warning' {
  if (c === 'NOTICE') return 'success'
  if (c === 'PROCESS') return 'warning'
  return 'info'
}

function fmtAnnouncementDate(iso?: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())}`
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
    // 配置读取失败：fail-open，保持模块展示
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

// 今日摘要: 基于真实 stats 字段拼接, 不造假数据
const todaySummary = computed(() => {
  const s = data.value?.stats
  if (!s) return '正在加载今天的招聘概况…'
  const parts: string[] = []
  if (s.pendingInitial) parts.push(`${s.pendingInitial} 份待初筛`)
  if (s.pendingTodo) parts.push(`${s.pendingTodo} 条待办`)
  if (s.pendingRecommend) parts.push(`${s.pendingRecommend} 个推荐`)
  if (s.pendingScreening) parts.push(`${s.pendingScreening} 个初筛中`)
  if (parts.length === 0) return '今天的事项都已处理完毕，状态很棒！'
  return `今天有 ${parts.join(' · ')}`
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

const quickEntries = computed<QuickEntryData[]>(() => {
  const entries: QuickEntryData[] = [
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
  ]
  // 存在标记为「更多」的单条公告时，在「快捷入口」提供政策制度入口
  if (hasMoreAnnouncements.value) {
    entries.push({
      key: 'announcements',
      label: '政策制度',
      subtitle: '制度、公告与流程指引',
      count: announcements.value.filter((a) => a.isActive).length,
      icon: DocumentTextOutline,
      to: '/announcements',
    })
  }
  return entries
})

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
  background: var(--glass-bg-panel);
  backdrop-filter: blur(var(--glass-blur-panel));
  -webkit-backdrop-filter: blur(var(--glass-blur-panel));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  padding: var(--space-8) var(--space-8);
  box-shadow: var(--shadow-panel);
}

.hero-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
}

.hero-greeting {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  min-width: 0;
}

.ai-avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-pill);
  background: var(--brand);
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
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.hero-title {
  margin: 0;
  color: var(--ink);
  font-size: var(--text-h2);
  font-weight: 500;
  line-height: 1.3;
}

.hero-subtitle {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body);
  line-height: 1.5;
}

.hero-search {
  flex-shrink: 0;
  width: 300px;
  max-width: 40vw;
}

@media (max-width: 768px) {
  .dashboard-workbench { gap: var(--space-4); }
  .dashboard-hero { padding: var(--space-6); }
  .hero-main {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-4);
  }
  .hero-search {
    width: 100%;
    max-width: none;
  }
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

/* ===== Cards overrides =====
 * 卡片底色统一由全局 .n-card.n-card 玻璃规则提供，无需在此覆盖。
 * 仅保留内容区 padding 微调（见下方 :deep）。 */

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

/* ===== 政策制度 (右侧栏 - 知识库风格) ===== */
.announcement-list {
  display: flex;
  flex-direction: column;
}

.announcement-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

.announcement-item:hover {
  background: var(--brand-tint);
}

.announcement-item__icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--c-info-soft);
  color: var(--c-info);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.announcement-item__content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.announcement-item__title {
  color: var(--ink);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.announcement-item__date {
  color: var(--ink-faint);
  font-size: 12px;
}

.announcement-item__arrow {
  color: var(--ink-faint);
  flex-shrink: 0;
}

.announcement-item:hover .announcement-item__arrow {
  color: var(--c-info);
}

.announcement-list__empty {
  padding: var(--space-4) 0;
  display: flex;
  justify-content: center;
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
  background: var(--c-info-soft);
  color: var(--c-info);
  font-size: 10px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.matter-tab__count--urgent {
  background: var(--c-error-soft);
  color: var(--c-error);
}
</style>
