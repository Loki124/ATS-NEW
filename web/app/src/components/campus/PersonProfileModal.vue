<template>
  <n-modal
    :show="show"
    preset="card"
    class="pp-profile-modal"
    :title="modalTitle"
    :content-style="contentStyle"
    :mask-closable="false"
    :bordered="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <!-- 加载态：骨架屏（R-205 300ms 内不闪；此处为弹窗首屏，直接给骨架） -->
    <n-skeleton v-if="loading" :repeat="5" :sharp="false" />

    <!-- 失败态：错误三段式（R-203）——人话描述 + 数据安全说明 + 可点击恢复动作 -->
    <n-result
      v-else-if="error"
      status="error"
      title="没取到这份档案"
      :description="`${error}。你填的内容仍保存在本地，未受影响。`"
    >
      <template #footer>
        <n-space justify="center">
          <n-button @click="emit('update:show', false)">关闭</n-button>
          <n-button type="primary" @click="load">重新加载档案</n-button>
        </n-space>
      </template>
    </n-result>

    <div v-else-if="profile" class="pp-body">
      <!-- ── 顶部名片 ───────────────────────────────────────────── -->
      <section class="pp-banner">
        <div class="pp-banner-main">
          <div class="pp-avatar" aria-hidden="true">{{ initial }}</div>
          <div class="pp-banner-text">
            <h2 class="pp-name">{{ p.name || '未命名' }}</h2>
            <p class="pp-subtitle">{{ subtitle }}</p>
            <div class="pp-tags">
              <span class="pp-chip">{{ p.status || '状态未知' }}</span>
              <span v-if="p.sex" class="pp-chip">{{ p.sex }}</span>
              <span v-if="p.batch" class="pp-chip">批次 {{ p.batch }}</span>
            </div>
          </div>
        </div>
        <div class="pp-banner-score">
          <div class="pp-score-circle">{{ scoreText }}</div>
          <div class="pp-score-label">综合评分</div>
          <div class="pp-score-sub">排名 {{ rankText }}</div>
        </div>
      </section>

      <!-- ── 四项统计 ───────────────────────────────────────────── -->
      <div class="pp-stats">
        <div v-for="s in statCards" :key="s.label" class="pp-stat">
          <div class="pp-stat-icon" :style="{ background: s.bg, color: s.fg }">
            <n-icon :component="s.icon" :aria-hidden="true" />
          </div>
          <div class="pp-stat-body">
            <div class="pp-stat-value">{{ s.value }}</div>
            <div class="pp-stat-label">{{ s.label }}</div>
          </div>
        </div>
      </div>

      <!-- ── 基本信息 ───────────────────────────────────────────── -->
      <section class="pp-section">
        <h3 class="pp-section-title">
          <n-icon :component="DocumentTextOutline" :aria-hidden="true" />
          基本信息
        </h3>
        <div class="pp-fields">
          <div v-for="f in basicFields" :key="f.label" class="pp-field">
            <div class="pp-field-label">{{ f.label }}</div>
            <div class="pp-field-value" :title="f.value">{{ f.value }}</div>
          </div>
        </div>
      </section>

      <!-- ── 轮岗期考核结果 ─────────────────────────────────────── -->
      <section class="pp-section">
        <h3 class="pp-section-title">
          <n-icon :component="ClipboardOutline" :aria-hidden="true" />
          轮岗期考核结果
        </h3>
        <n-data-table
          :data="profile.stages"
          :columns="stageColumns"
          :row-key="rowKey"
          :bordered="false"
          size="small"
        >
          <template #empty><n-empty description="暂无数据" /></template>
        </n-data-table>
      </section>

      <!-- ── 轮岗期月度考核明细 ─────────────────────────────────── -->
      <section class="pp-section">
        <h3 class="pp-section-title">
          <n-icon :component="CalendarOutline" :aria-hidden="true" />
          轮岗期月度考核明细
        </h3>
        <n-data-table
          :data="profile.monthlyAssessments"
          :columns="monthlyColumns"
          :row-key="rowKey"
          :bordered="false"
          size="small"
        >
          <template #empty><n-empty description="暂无数据" /></template>
        </n-data-table>
      </section>

      <!-- ── 日报及评价 ─────────────────────────────────────────── -->
      <section class="pp-section">
        <h3 class="pp-section-title">
          <n-icon :component="ChatbubblesOutline" :aria-hidden="true" />
          日报及评价
        </h3>
        <n-data-table
          :data="profile.dailyReports"
          :columns="dailyReportColumns"
          :row-key="rowKey"
          :bordered="false"
          size="small"
        >
          <template #empty><n-empty description="暂无日报记录" /></template>
        </n-data-table>
      </section>

      <!-- ── 推介意见（导师 / 班主任推介） ───────────────────────── -->
      <section class="pp-section">
        <h3 class="pp-section-title">
          <n-icon :component="PricetagOutline" :aria-hidden="true" />
          推介意见（导师 / 班主任推介）
        </h3>
        <n-data-table
          :data="profile.recommendations"
          :columns="recommendationColumns"
          :row-key="rowKey"
          :bordered="false"
          size="small"
        >
          <template #empty><n-empty description="暂无推介意见" /></template>
        </n-data-table>
      </section>

      <!-- ── 反馈记录 ───────────────────────────────────────────── -->
      <section class="pp-section">
        <h3 class="pp-section-title">
          <n-icon :component="ChatboxEllipsesOutline" :aria-hidden="true" />
          反馈记录
        </h3>
        <n-data-table
          :data="profile.feedbacks"
          :columns="feedbackColumns"
          :row-key="rowKey"
          :bordered="false"
          size="small"
        >
          <template #empty><n-empty description="暂无反馈" /></template>
        </n-data-table>
      </section>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('update:show', false)">关闭</n-button>
        <n-button
          v-if="!readonly"
          type="primary"
          class="gradient-btn"
          :disabled="loading || !profile"
          @click="onEdit"
        >
          <template #icon><n-icon :component="CreateOutline" /></template>
          编辑基础信息
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * PersonProfileModal —— 校招生「个人档案」详情弹窗（2026-10-21 二期）。
 *
 * 边界：
 * - 只读展示 + 一个「编辑基础信息」出口（编辑复用父页面的编辑弹窗，本组件不持有表单状态）。
 * - 数据源唯一：GET /campus/persons/{id}/profile/（后端一次聚合返回），
 *   前端不再拼装多次请求，避免详情与列表口径漂移。
 * - 「轮岗期月度考核明细 / 日报及评价 / 推介意见 / 反馈记录」四个业务域
 *   后端暂未建模，返回空数组 → 此处渲染空态（与设计稿「暂无数据」一致）；
 *   后续模型落地时只需后端补数据，前端表格列已按设计稿预置，无需改动。
 *
 * 交互约束（AGENTS.md）：
 * - R-224 默认居中弹窗（n-modal preset=card），非抽屉。
 * - R-223 内容区固定高度（height，非 max-height），切换态不跳动。
 * - R-223 底部操作区走 #footer 插槽。
 * - R-104 / R-111 覆盖加载 / 失败 / 空态 / 成功四态。
 */
import { ref, computed, watch } from 'vue'
import {
  NButton,
  NDataTable,
  NEmpty,
  NIcon,
  NModal,
  NResult,
  NSkeleton,
  NSpace,
} from 'naive-ui'
import {
  BarChartOutline,
  CalendarOutline,
  ChatboxEllipsesOutline,
  ChatbubblesOutline,
  ClipboardOutline,
  CreateOutline,
  DocumentTextOutline,
  MedalOutline,
  PricetagOutline,
  TrophyOutline,
} from '@vicons/ionicons5'
import { getPersonProfile, type PersonProfile } from '../../api/campusControl'
import { extractError } from '../../utils/campus'
import { column } from '../../composables/useTableColumns'

const props = defineProps<{
  show: boolean
  personId: string | null
  personName?: string
  /**
   * 直接给档案载荷（示例数据模式用）：给了就**不发请求**，直接渲染。
   * 真实数据模式不传此参数，走 `GET /campus/persons/{id}/profile/`。
   */
  preloaded?: PersonProfile | null
  /** 只读模式（示例数据）：隐藏「编辑基础信息」出口，示例数据不落库。 */
  readonly?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'edit', profile: PersonProfile): void
}>()

const loading = ref(false)
const error = ref('')
const profile = ref<PersonProfile | null>(null)

/**
 * 内容区样式（R-223 / R-224）。
 *
 * 弹窗尺寸走**全局 CSS**（见本文件底部非 scoped 样式块）：卡片宽 80vw、高 90vh；
 * 卡片根节点是纵向 flex（naive-ui `.n-card`），内容区 `flex: 1; min-height: 0`
 * ⇒ **内容区高度由卡片固定高度决定，不随内容变化**（不是 max-height，
 * 切页签/出现错误提示时容器高度不跳动），超出部分在内容区内部滚动。
 */
const contentStyle = {
  overflowY: 'auto',
  padding: 'var(--modal-pad-y) var(--modal-pad-x)',
} as const

/** 行 key：统一走 id；暂无 id 的行（未建模业务域）退化为空串（空表不渲染行）。 */
const rowKey = (row: any) => row.id ?? ''

const modalTitle = computed(() => `个人档案 · ${props.personName || profile.value?.person?.name || ''}`)

const p = computed(() => profile.value?.person ?? ({} as PersonProfile['person']))
const stats = computed(() => profile.value?.stats ?? ({} as PersonProfile['stats']))

/** 姓名首字（无姓名时回落为「?」） */
const initial = computed(() => (p.value.name || '?').trim().charAt(0) || '?')

/** 副标题：院校名称 · 专业 · 学历（缺项自动跳过，不留多余分隔符） */
const subtitle = computed(() => {
  const parts = [p.value.schoolName || p.value.school, p.value.major, p.value.education]
  return parts.filter(Boolean).join(' · ') || '—'
})

/** 综合评分：0 分与「无数据」须区分 —— 无数据显示「—」 */
const scoreText = computed(() => {
  const v = stats.value.overallScore
  return v === null || v === undefined ? '—' : String(v)
})
const rankText = computed(() => {
  const v = stats.value.rank
  return v === null || v === undefined ? '—' : `第 ${v} 名`
})

/** 评分展示：保留一位小数，空值统一「—」 */
const fmtScore = (v: number | null | undefined): string =>
  v === null || v === undefined ? '—' : Number(v).toFixed(1)

const statCards = computed(() => [
  {
    label: '轮岗均分',
    value: fmtScore(stats.value.rotationAvgScore),
    icon: BarChartOutline,
    bg: 'var(--c-info-soft)',
    fg: 'var(--c-info-deep)',
  },
  {
    label: '月度综合均分',
    value: fmtScore(stats.value.monthlyAvgScore),
    icon: BarChartOutline,
    bg: 'var(--c-success-soft)',
    fg: 'var(--c-success-deep)',
  },
  {
    label: '综合排名',
    value: rankText.value,
    icon: TrophyOutline,
    bg: 'var(--c-warning-soft)',
    fg: 'var(--c-warning-deep)',
  },
  {
    label: '综合评级',
    value: stats.value.rating || '—',
    icon: MedalOutline,
    bg: 'var(--c-info-soft)',
    fg: 'var(--c-info-deep)',
  },
])

/** 基本信息九宫格（空值统一「—」，不留空格子） */
const basicFields = computed(() => {
  const rot = profile.value?.rotation
  const cr = profile.value?.classRoom
  const list = [
    { label: '编号', value: p.value.code },
    { label: '院校名称', value: p.value.schoolName || p.value.school },
    // 2026-10-23（聂荣口径）教育经历取「院校标签就高原则」命中的那条 → 专业用真实名称
    { label: '专业', value: p.value.majorName || p.value.major },
    { label: '学历', value: p.value.education },
    { label: '联系电话', value: p.value.phone },
    // 2026-10-21 兵哥口径：工号 8 位纯数字（待入职无）；入职日期仅已入职有；预计入职日期全员有
    { label: '工号', value: p.value.employeeId },
    { label: '实际入职日期', value: p.value.actualEntryDate },
    { label: '预计入职日期', value: p.value.expectedEntryDate },
    { label: '当前轮岗部门', value: rot?.currentDept },
    { label: '综合评分', value: fmtScore(stats.value.overallScore) },
    { label: '班主任', value: p.value.headTeacherName || cr?.headTeacher },
    { label: 'HRBP', value: p.value.hrbpName || cr?.hrbp },
    { label: '班级', value: p.value.classRoomName || cr?.name },
    // 2026-10-23（聂荣口径）基本信息补三项：
    //   轮岗状态分类 = 当前轮岗安排所处阶段（待分配/审批中/轮岗中/已完成/已终止）
    { label: '轮岗状态分类', value: p.value.rotationStatusLabel || rot?.stageLabel },
    //   班长（档案级，基于班级自动带出可修改）
    { label: '班长', value: p.value.classMonitorName },
    //   带教导师（档案级）
    { label: '带教导师', value: p.value.mentorName },
  ]
  return list.map((f) => ({ ...f, value: f.value || '—' }))
})

/* ── 各表格列定义（按设计稿列序；数据落地后即可直接渲染） ────────── */
const stageColumns = [
  column({ title: '轮岗部门', key: 'department', width: 120 }, 'short'),
  column({ title: '二级部门', key: 'bu', width: 110 }, 'short'),
  column({ title: '轮岗周期', key: 'period', width: 180 }, 'short'),
  column({ title: '状态', key: 'status', width: 90 }, 'short'),
  column({ title: '评分', key: 'score', width: 80, render: (r: any) => fmtScore(r.score) }, 'short'),
  column({ title: '阶段结果', key: 'result', width: 140, ellipsis: true }, 'text'),
  column({ title: '导师', key: 'mentor', width: 100 }, 'short'),
]

const monthlyColumns = [
  column({ title: '月份', key: 'month', width: 80 }, 'short'),
  column({ title: '所属阶段', key: 'stageName', width: 110 }, 'short'),
  column({ title: 'KPI', key: 'kpi', width: 90 }, 'short'),
  column({ title: '考试', key: 'exam', width: 90 }, 'short'),
  column({ title: '加减分', key: 'bonus', width: 80 }, 'short'),
  column({ title: '总分', key: 'total', width: 80 }, 'short'),
  column({ title: '状态', key: 'status', width: 90 }, 'short'),
  column({ title: '说明', key: 'remark', width: 160, ellipsis: true }, 'text'),
]

const dailyReportColumns = [
  column({ title: '日期', key: 'date', width: 110 }, 'short'),
  column({ title: '提交人', key: 'submitter', width: 100 }, 'short'),
  column({ title: '日报内容', key: 'content', width: 220, ellipsis: true }, 'text'),
  column({ title: '导师评价', key: 'mentorComment', width: 180, ellipsis: true }, 'text'),
  column({ title: '状态', key: 'status', width: 90 }, 'short'),
]

const recommendationColumns = [
  column({ title: '推介人', key: 'promoter', width: 100 }, 'short'),
  column({ title: '角色', key: 'role', width: 110 }, 'short'),
  column({ title: '日期', key: 'date', width: 110 }, 'short'),
  column({ title: '推介内容', key: 'content', width: 320, ellipsis: true }, 'text'),
]

const feedbackColumns = [
  column({ title: '日期', key: 'date', width: 110 }, 'short'),
  column({ title: '记录人', key: 'recorder', width: 100 }, 'short'),
  column({ title: '类型', key: 'type', width: 100 }, 'short'),
  column({ title: '描述', key: 'description', width: 220, ellipsis: true }, 'text'),
  column({ title: '状态', key: 'status', width: 90 }, 'short'),
  column({ title: '证据', key: 'evidence', width: 140, ellipsis: true }, 'text'),
]

const load = async () => {
  // 示例数据模式：父页面已把档案载荷传进来 ⇒ 直接渲染，**不发请求**
  // （mock 行 id 形如 MOCK_PS_01，后端没有这条记录，请求必然 404）
  if (props.preloaded) {
    profile.value = props.preloaded
    error.value = ''
    loading.value = false
    return
  }
  if (!props.personId) return
  loading.value = true
  error.value = ''
  try {
    profile.value = await getPersonProfile(props.personId)
  } catch (e: any) {
    profile.value = null
    error.value = extractError(e)
  } finally {
    loading.value = false
  }
}

/** 「编辑基础信息」：把当前档案抛给父页面（父页面复用既有编辑弹窗，本组件不持有表单状态）。 */
const onEdit = () => {
  if (profile.value) emit('edit', profile.value)
}

watch(
  () => [props.show, props.personId, props.preloaded] as const,
  ([show]) => {
    if (show) load()
    else {
      profile.value = null
      error.value = ''
    }
  },
  { immediate: true },
)

/** 暴露给父页面：保存基础信息后刷新档案详情（档案页不消失但数据要同步）。 */
defineExpose({ reload: load })
</script>

<style scoped>
.pp-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* ── 顶部名片 ─────────────────────────────────────────────── */
.pp-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--brand-grad-from), var(--brand-grad-to));
  color: var(--on-brand);
  flex-wrap: wrap;
}
.pp-banner-main {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}
.pp-avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-h3);
  font-weight: 600;
  background: var(--brand-a32);
  flex-shrink: 0;
}
.pp-banner-text {
  min-width: 0;
}
.pp-name {
  margin: 0;
  font-size: var(--text-h3);
  font-weight: 600;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.pp-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-small);
  opacity: .9;
  overflow-wrap: anywhere;
}
.pp-tags {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-2);
  flex-wrap: wrap;
}
.pp-chip {
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--brand-a22);
  font-size: var(--text-meta);
  line-height: 1.6;
}
.pp-banner-score {
  text-align: center;
  flex-shrink: 0;
}
.pp-score-circle {
  width: 56px;
  height: 56px;
  margin: 0 auto;
  border-radius: var(--radius-pill);
  background: var(--surface);
  color: var(--brand-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-h2);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.pp-score-label {
  margin-top: var(--space-2);
  font-size: var(--text-meta);
  opacity: .9;
}
.pp-score-sub {
  font-size: var(--text-meta);
  opacity: .9;
}

/* ── 四项统计 ─────────────────────────────────────────────── */
/* 列宽下限 200px：弹窗 960px 时一行 4 张（对齐设计稿），窄屏自动降列。
 * min(200px, 100%) 兜底：容器比 200px 还窄时列宽收缩到容器宽，不撑破（R-103）。 */
.pp-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(200px, 100%), 1fr));
  gap: var(--space-3);
}
.pp-stat {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.pp-stat-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-h4);
  flex-shrink: 0;
}
.pp-stat-body {
  min-width: 0;
}
.pp-stat-value {
  font-size: var(--text-h4);
  font-weight: 600;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
.pp-stat-label {
  font-size: var(--text-meta);
  color: var(--ink-faint);
}

/* ── 区块 ─────────────────────────────────────────────────── */
.pp-section {
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  background: var(--surface);
}
.pp-section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-3);
  padding-left: var(--space-2);
  border-left: 3px solid var(--brand);
  font-size: var(--text-h4);
  font-weight: 600;
  line-height: 1.3;
}

/* ── 基本信息九宫格 ───────────────────────────────────────── */
/* 列宽下限 260px：弹窗 960px 时一行 3 张（对齐设计稿），窄屏自动降列。
 * min(260px, 100%) 兜底：容器比 260px 还窄时列宽收缩到容器宽，不撑破（R-103）。 */
.pp-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr));
  gap: var(--space-3);
}
.pp-field {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--brand-tint);
  min-width: 0;
}
.pp-field-label {
  font-size: var(--text-meta);
  color: var(--ink-faint);
}
.pp-field-value {
  font-size: var(--text-body);
  font-weight: 600;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
</style>

<!--
  弹窗尺寸：**非 scoped**（弹窗被 teleport 到 body，scoped 选择器命中不到）。
  - 宽 = 浏览器宽度的 80%（80vw）
  - 高 = 浏览器高度的 90%（90vh）
  naive-ui 的 `.n-card` 根节点是纵向 flex（display:flex; flex-direction:column），
  内容区 `.n-card-content` 自带 `flex:1; min-width:0`
  ⇒ 头/尾固定、内容区自动填满剩余高度并内部滚动（高度不随内容变化）。
-->
<style>
.pp-profile-modal.n-modal {
  width: 80vw;
  max-width: 80vw;
  height: 90vh;
}
/* 头尾不参与压缩，内容区独占剩余高度 */
.pp-profile-modal.n-modal > .n-card__header,
.pp-profile-modal.n-modal > .n-card__footer {
  flex-shrink: 0;
}
.pp-profile-modal.n-modal > .n-card-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}
</style>
