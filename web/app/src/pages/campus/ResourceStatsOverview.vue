<template>
  <!--
    轮岗资源 · 「统计概览」面板（2026-10-22 兵哥指令）。

    **数据源**：真实接口 `GET /campus-rotation/resources/stats-overview/`
    （逐列口径见后端 `apps/campus_rotation/services/stats_overview.py`）；
    真实数据为空时按仓库既有约定兜底到示例数据，并用 `CampusMockBar` 明示。

    **版式**（三段式，而不是一张 22 列的巨表）：
    ① 工具栏 —— 指标视图切换 + 数据来源 + 刷新；
    ② 总体概览条 —— 6 个关键指标，比率类带**量度条**（全页统一的「条长 = 比例」视觉语言）；
    ③ 明细表 —— 按视图只渲染该主题的列组，最宽 8 列，**不再需要横向滚动**；
       「全部指标」视图保留 22 列全量对照（需横向滚动）。
  -->
  <div class="campus-panel">
    <div class="campus-panel-body">
      <!-- ① 工具栏 -->
      <div class="toolbar">
        <n-radio-group v-model:value="view" size="small" class="view-switch">
          <n-radio-button v-for="v in VIEWS" :key="v.key" :value="v.key">
            {{ v.label }}
          </n-radio-button>
        </n-radio-group>
        <div class="spacer"></div>
        <CampusMockBar :is-mock="isMock" @change="load" />
        <n-button :loading="loading" @click="load">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </div>

      <!-- ② 总体概览条 -->
      <section class="kpi" aria-label="总体概览">
        <div class="kpi__head">
          <span class="kpi__title">总体</span>
          <span v-if="unassignedDemand > 0" class="kpi__flag">
            {{ unassignedDemand }} 人校招需求未能归属到组织维度，已计入「未分配」行
          </span>
        </div>
        <div class="kpi__grid">
          <div v-for="k in kpis" :key="k.key" class="kpi__cell">
            <div class="kpi__label">{{ k.label }}</div>
            <div class="kpi__value">{{ k.text }}</div>
            <div v-if="k.ratio != null" class="kpi__track" aria-hidden="true">
              <span
                class="kpi__fill"
                :class="`kpi__fill--${k.tone}`"
                :style="{ transform: `scaleX(${k.ratio})` }"
              ></span>
            </div>
            <div class="kpi__basis">{{ k.basis }}</div>
          </div>
        </div>
      </section>

      <!-- ③ 明细表 -->
      <n-data-table
        class="stat-table"
        :data="detailRows"
        :columns="columns"
        :row-key="(row: DetailRow) => row.__key"
        :loading="loading"
        :bordered="true"
        :single-line="false"
        :scroll-x="tableScrollX"
        flex-height
        size="small"
      >
        <template #empty>
          <n-empty description="暂无统计数据" />
        </template>
      </n-data-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, ref } from 'vue'
import {
  NButton,
  NDataTable,
  NEmpty,
  NIcon,
  NRadioButton,
  NRadioGroup,
  type DataTableColumns,
} from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import CampusMockBar from '../../components/campus/CampusMockBar.vue'
import StatsBgCell from '../../components/campus/StatsBgCell.vue'
import StatsRateCell, { type RateTone } from '../../components/campus/StatsRateCell.vue'
import { useCampusMock } from '../../composables/useCampusMock'
import { fetchStatsOverview, type StatsOverviewRow } from '../../api/campusRotation'
import { buildMockResourceStats } from '../../mocks/campusStats'

type Row = StatsOverviewRow
/** 明细行：附加一个稳定主键（buName 在不同 BG 下可重复，不能直接当 key）。 */
type DetailRow = Row & { __key: string }

/** 指标视图：按主题切列，避免一张表横跨 7 个列组、宽到必须左右拖。 */
type ViewKey = 'all' | 'demand' | 'onoff' | 'dist' | 'gender'

const VIEWS: { key: ViewKey; label: string; groups: GroupKey[] }[] = [
  { key: 'all', label: '全部指标', groups: ['org', 'demand', 'onoff', 'dist', 'gender'] },
  { key: 'demand', label: '需求与定岗', groups: ['org', 'demand'] },
  { key: 'onoff', label: '入离职', groups: ['org', 'onoff'] },
  { key: 'dist', label: '轮岗分布', groups: ['org', 'dist'] },
  { key: 'gender', label: '性别与意向', groups: ['org', 'gender'] },
]

type GroupKey = 'org' | 'demand' | 'onoff' | 'dist' | 'gender'

const view = ref<ViewKey>('all')

const rows = ref<DetailRow[]>([])
const totals = ref<Row | null>(null)
const unassignedDemand = ref(0)
const loading = ref(false)

const { pickBy, isMock, isMockOnly } = useCampusMock()

/* ───────────────────────── 取数：真实接口 + 示例兜底 ───────────────────────── */

function mockPayload() {
  const all = buildMockResourceStats() as unknown as Row[]
  return { rows: all.slice(1) as Row[], totals: all[0] as Row, unassignedDemand: 0 }
}

function apply(p: { rows: Row[]; totals: Row | null; unassignedDemand: number }) {
  rows.value = p.rows.map((r, i) => ({ ...r, __key: `${i}-${r.bgGroup}-${r.buName}` }))
  totals.value = p.totals
  unassignedDemand.value = p.unassignedDemand
}

async function load() {
  loading.value = true
  try {
    // 强制示例模式：跳过接口，直接渲染示例数据
    if (isMockOnly.value) {
      apply(mockPayload())
      return
    }
    let real: Row[] = []
    let realTotals: Row | null = null
    let unassigned = 0
    try {
      const data = await fetchStatsOverview()
      // rows[0] 是「整体」汇总行 —— 表里不显示（概览条已承担），这里剔除
      real = (data.rows ?? []).slice(1)
      realTotals = data.totals
      unassigned = data.unassignedDemand
    } catch {
      // 接口失败：走示例兜底（auto 模式）；错误由全局拦截器统一 toast
      real = []
      realTotals = null
    }
    apply(pickBy(real.length > 0, { rows: real, totals: realTotals, unassignedDemand: unassigned }, mockPayload()))
  } finally {
    loading.value = false
  }
}

const detailRows = computed(() => rows.value)

/* ───────────────────────── 总体概览条 ───────────────────────── */

/** 「越高越好」的比率档位；女生比等无好坏之分的指标用 neutral。 */
function higherIsBetter(v: number | null): RateTone {
  if (v == null) return 'neutral'
  if (v >= 0.8) return 'good'
  if (v >= 0.4) return 'warn'
  return 'bad'
}

const num = (v: number | null | undefined) =>
  v == null ? '—' : Number(v).toLocaleString('zh-CN')

const kpis = computed(() => {
  const t = totals.value
  if (!t) return []
  return [
    { key: 'demand', label: '业务需求', text: num(t.demand), ratio: null as number | null, tone: 'neutral' as RateTone, basis: '校招需求人数合计' },
    { key: 'fill', label: '满足率', text: t.fillRate == null ? '—' : `${(t.fillRate * 100).toFixed(1)}%`, ratio: t.fillRate, tone: higherIsBetter(t.fillRate), basis: '已定岗 ÷ 业务需求' },
    { key: 'onboard', label: '入职', text: num(t.onboard), ratio: null as number | null, tone: 'neutral' as RateTone, basis: '有实际入职日期的人数' },
    { key: 'retain', label: '留存率', text: t.retainRate == null ? '—' : `${(t.retainRate * 100).toFixed(1)}%`, ratio: t.retainRate, tone: higherIsBetter(t.retainRate), basis: '在职 ÷ 入职' },
    { key: 'active', label: '在职', text: num(t.active), ratio: null as number | null, tone: 'neutral' as RateTone, basis: '状态为在职的人数' },
    { key: 'female', label: '女生比', text: t.femaleRatio == null ? '—' : `${(t.femaleRatio * 100).toFixed(1)}%`, ratio: t.femaleRatio, tone: 'neutral' as RateTone, basis: '意向女 ÷（意向男 + 意向女）' },
  ]
})

/* ───────────────────────── 列定义 ───────────────────────── */

/** 带口径说明的列标题（原生 title 提示，零成本）。 */
const titleWithHint = (text: string, hint: string) => () => h('span', { title: hint }, text)

/** 整数列：右对齐 + tabular-nums（样式走 :deep()，见样式块）。 */
const numCol = (title: string, key: keyof Row, width: number, hint?: string) => ({
  title: hint ? titleWithHint(title, hint) : title,
  key: key as string,
  width,
  align: 'right' as const,
})

/** 比率列：数字 + 量度条（数值由 StatsRateCell 渲染）。 */
const rateCol = (
  title: string,
  key: keyof Row,
  width: number,
  tone: (v: number | null) => RateTone,
  hint: string,
) => ({
  title: titleWithHint(title, hint),
  key: key as string,
  width,
  align: 'right' as const,
  render: (row: Row) => {
    const v = (row[key] as number | null) ?? null
    return h(StatsRateCell, { value: v, tone: tone(v) })
  },
})

const bgColumn = {
  title: 'BG',
  key: 'bgGroup',
  width: 140,
  fixed: 'left' as const,
  // BG 跨行合并：组首行返回组行数，组内其余行返回 0（naive-ui 会跳过被覆盖的格）
  rowSpan: (row: Row) => row.bgSpan,
  render: (row: Row) =>
    row.bgSpan > 0 ? h(StatsBgCell, { name: row.bgGroup, total: row.bgTotal }) : '',
}

const buColumn = {
  title: '当前BU',
  key: 'buName',
  width: 150,
  fixed: 'left' as const,
}

const GROUP_COLUMNS: Record<GroupKey, DataTableColumns<Row>> = {
  org: [
    {
      title: '组织',
      key: 'g-org',
      children: [bgColumn, buColumn],
    },
  ],
  demand: [
    {
      title: '26年需求',
      key: 'g-demand',
      children: [
        numCol('业务需求', 'demand', 92, '校招需求人数合计'),
        numCol('已定岗', 'fixed', 84, '轮岗安排中已填「定岗去向」的人数'),
        numCol('定岗流失', 'lost', 84, '已定岗、且当前已离职的人数'),
        rateCol('满足率', 'fillRate', 96, higherIsBetter, '已定岗 ÷ 业务需求；分母为 0 显示「—」'),
      ],
    },
  ],
  onoff: [
    {
      title: '26届入离职情况',
      key: 'g-onoff',
      children: [
        numCol('入职', 'onboard', 84, '有实际入职日期的人数'),
        numCol('离职', 'offboard', 84, '状态为离职的人数'),
        numCol('在职', 'active', 84, '状态为在职的人数'),
        rateCol('留存率', 'retainRate', 96, higherIsBetter, '在职 ÷ 入职；分母为 0 显示「—」'),
      ],
    },
  ],
  dist: [
    {
      title: '26届离职分布(轮岗部门)',
      key: 'g-offdist',
      children: [
        numCol('客服', 'offCS', 76),
        numCol('主播', 'offAnchor', 76),
        numCol('其他岗位', 'offOther', 92),
      ],
    },
    {
      title: '26届在职分布(当前)',
      key: 'g-ondist',
      children: [
        numCol('客服', 'onCS', 76),
        numCol('主播', 'onAnchor', 76),
        numCol('其他岗位', 'onOther', 92),
      ],
    },
  ],
  gender: [
    {
      title: '性别分布(当前)',
      key: 'g-gender',
      children: [
        numCol('男', 'male', 76, '在职校招生的性别分布'),
        numCol('女', 'female', 76, '在职校招生的性别分布'),
      ],
    },
    {
      title: '意向BU',
      key: 'g-intend',
      children: [
        numCol('男', 'intendMale', 76, '该 BU 投递意向人群（不限状态）的性别分布'),
        numCol('女', 'intendFemale', 76, '该 BU 投递意向人群（不限状态）的性别分布'),
        rateCol('女生比', 'femaleRatio', 96, () => 'neutral', '意向女 ÷（意向男 + 意向女）；无好坏之分'),
      ],
    },
  ],
}

const columns = computed<DataTableColumns<Row>>(() => {
  const v = VIEWS.find((x) => x.key === view.value) ?? VIEWS[0]
  return v.groups.flatMap((g) => GROUP_COLUMNS[g])
})

/** 横向滚动宽度 = 当前视图的叶子列宽之和（naive 需显式给 scroll-x 才横向滚动）。 */
const tableScrollX = computed(() => {
  let sum = 0
  const walk = (cols: any[]) => {
    for (const c of cols) {
      if (Array.isArray(c.children) && c.children.length) walk(c.children)
      else if (typeof c.width === 'number') sum += c.width
    }
  }
  walk(columns.value as any[])
  return sum
})

load()
</script>

<style scoped>
.campus-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.campus-panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: hidden;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
/* 视图切换：窄屏换行而非被裁切
   （n-radio-group 默认 inline-flex，5 个按钮 ≈ 440px > 320px 视口，
     而 .campus-panel-body 是 overflow-x:hidden → 后面的视图在手机上点不到）。
   ⚠️ 换行后控件会变高，而全局 .toolbar 是 align-items:center
      → 右侧「示例数据 / 刷新」会被垂直居中到中间那行、与按钮**重叠**。
      故窄屏让视图切换独占一行（flex-basis:100%），右侧控件落到下一行。 */
.view-switch {
  display: flex;
  flex-wrap: wrap;
  /* naive 的 n-radio-group--button-group 带**固定高度**（实测 28px），
     按钮换行后容器不会长高 → 内容溢出并与右侧控件重叠。必须显式放开。 */
  height: auto;
  max-width: 100%;
}
@media (max-width: 767px) {
  .view-switch {
    flex: 1 1 100%;
  }
}

/* ── 总体概览条 ── */
.kpi {
  flex-shrink: 0;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.kpi__head {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.kpi__title {
  font-size: var(--text-meta);
  font-weight: 600;
  color: var(--ink-faint);
  letter-spacing: 0.06em;
  /* 窄屏下「总体」会被长提示文案挤成两行 → 禁止压缩换行 */
  flex-shrink: 0;
  white-space: nowrap;
}
.kpi__flag {
  font-size: var(--text-meta);
  color: var(--c-warning-deep);
  min-width: 0;
}
.kpi__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  column-gap: var(--space-4);
  row-gap: var(--space-2);
}
.kpi__cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.kpi__label {
  font-size: var(--text-meta);
  color: var(--ink-faint);
}
.kpi__value {
  font-size: var(--text-h3);
  font-weight: 600;
  line-height: 1.2;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.kpi__track {
  height: 3px;
  border-radius: 2px;
  background: var(--border-hairline);
  overflow: hidden;
  margin-top: 2px;
}
/* 只动 transform（不改 width）→ 满足 R-206「只动画 transform / opacity」 */
.kpi__fill {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 2px;
  transform-origin: left center;
  background: var(--ink-faint);
}
.kpi__fill--good {
  background: var(--c-success-deep);
}
.kpi__fill--warn {
  background: var(--c-warning-deep);
}
.kpi__fill--bad {
  background: var(--c-error-deep);
}
.kpi__fill--neutral {
  background: var(--c-info-deep);
}
.kpi__basis {
  font-size: var(--text-meta);
  color: var(--ink-faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 明细表 ── */
.stat-table {
  flex: 1;
  min-height: 0;
}
/* 表格内部元素由 naive-ui 渲染，不带本组件的 scope id → 必须用 :deep() */
.stat-table :deep(.n-data-table-td),
.stat-table :deep(.n-data-table-th) {
  font-variant-numeric: tabular-nums;
}
</style>
