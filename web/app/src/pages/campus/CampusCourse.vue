<template>
  <div class="page-container">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" class="page-tabs" @update:value="onTabChange">
        <n-tab-pane name="manage" tab="课程管理" />
        <n-tab-pane name="mine" tab="我的课程" />
        <n-tab-pane name="board" tab="学习龙虎榜" />
      </n-tabs>

      <!-- ① 课程管理（管理视角） -->
      <template v-if="activeTab === 'manage'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">课程</span>
            <n-input
              v-model:value="courseSearch"
              aria-label="课程名称"
              class="toolbar-search"
              placeholder="搜索课程名称或编码"
              clearable
              @keyup.enter="loadCourses"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
          </div>
          <div class="filter">
            <span class="filter-label">类型</span>
            <n-select
              v-model:value="courseTypeFilter"
              aria-label="课程类型"
              class="toolbar-select"
              :options="courseTypeOptions"
              placeholder="全部类型"
              clearable
            />
          </div>
          <div class="filter">
            <span class="filter-label">形式</span>
            <n-select
              v-model:value="courseFormFilter"
              aria-label="课程形式"
              class="toolbar-select"
              :options="courseFormOptions"
              placeholder="全部形式"
              clearable
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="courseLoading" @click="loadCourses">查询课程</n-button>
          <n-button type="primary" @click="openCourseCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增课程
          </n-button>
        </div>

        <div v-if="courseError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">课程列表没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，你填的课程内容仍保留在本页，不会丢失。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ courseError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(courseError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="courseLoading" @click="loadCourses">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="courseLoading && !courseRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="courseColumns"
            :data="courseRows"
            :loading="courseLoading"
            :bordered="false"
            :scroll-x="COURSE_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: Course) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="courseEmptyText" size="small">
                <template #extra>
                  <n-button v-if="courseHasFilter" size="small" @click="clearCourseFilter">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ② 我的课程（学生视角） -->
      <template v-if="activeTab === 'mine'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">校招生</span>
            <n-select
              v-model:value="minePerson"
              aria-label="校招生"
              class="toolbar-select"
              :options="personOptions"
              placeholder="全部校招生"
              clearable
              filterable
              remote
              :loading="personLoading"
              :on-search="onPersonSearch"
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="mineLoading" @click="loadMine">刷新进度</n-button>
        </div>

        <div v-if="mineError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">学习进度没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，你的学习记录仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ mineError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(mineError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="mineLoading" @click="loadMine">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="mineLoading && !mineRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="mineColumns"
            :data="mineRows"
            :loading="mineLoading"
            :bordered="false"
            :scroll-x="MINE_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: LearnProgress) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="mineEmptyText" size="small">
                <template #extra>
                  <n-button v-if="mineHasFilter" size="small" @click="minePerson = null">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ③ 学习龙虎榜 -->
      <template v-if="activeTab === 'board'">
        <div class="toolbar">
          <div class="toolbar-tip">按累计学习分钟降序，已排除离职人员</div>
          <div class="spacer"></div>
          <n-button :loading="boardLoading" @click="loadBoard">刷新榜单</n-button>
        </div>

        <div v-if="boardError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">学习龙虎榜没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，榜单数据暂时取不到。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ boardError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(boardError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="boardLoading" @click="loadBoard">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="boardLoading && !boardRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="boardColumns"
            :data="boardRows"
            :loading="boardLoading"
            :bordered="false"
            :scroll-x="BOARD_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: LearnBoardRow) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty description="暂无数据" size="small" />
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- 课程 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="courseFormVisible"
        preset="card"
        :title="courseEditing ? '编辑课程' : '新增课程'"
        :style="{ width: '720px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(560px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="courseForm" label-placement="top">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="课程编码" required>
                <n-input v-model:value="courseForm.code" placeholder="如 C0001" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="课程名称" required>
                <n-input v-model:value="courseForm.name" placeholder="请输入课程名称" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="课程形式" required>
                <n-select v-model:value="courseForm.form" :options="courseFormOptions" placeholder="请选择课程形式" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="时长（分钟）" required>
                <n-input-number v-model:value="courseForm.durationMin" :min="1" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="课程分类">
                <n-input v-model:value="courseForm.category" placeholder="如 业务知识 / 通用素养" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="课程类型" required>
                <n-select v-model:value="courseForm.type" :options="courseTypeOptions" placeholder="请选择课程类型" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="结课考试">
                <n-switch v-model:value="courseForm.examRequired">
                  <template #checked>需要</template>
                  <template #unchecked>不需要</template>
                </n-switch>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="启用课程">
                <n-switch v-model:value="courseForm.enabled">
                  <template #checked>已启用</template>
                  <template #unchecked>已停用</template>
                </n-switch>
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-form-item label="课程描述">
            <n-input v-model:value="courseForm.description" type="textarea" placeholder="课程内容简介" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="courseFormVisible = false">取消</n-button>
            <n-button type="primary" :loading="courseSaving" :disabled="courseSaving" @click="saveCourse">保存课程</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 记学习记录 弹窗 -->
      <n-modal
        v-model:show="recordVisible"
        preset="card"
        title="记录学习"
        :style="{ width: '560px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(420px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="recordForm" label-placement="top">
          <n-form-item label="课程">
            <n-input :value="recordCourseName" readonly />
          </n-form-item>
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="学习日期" required>
                <n-date-picker v-model:value="recordDateTs" type="date" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="开始时间">
                <n-time-picker v-model:value="recordStartTs" style="width: 100%" format="HH:mm" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-form-item label="学习时长（分钟）" required>
            <n-input-number v-model:value="recordForm.minutes" :min="1" style="width: 100%" />
          </n-form-item>
          <n-form-item label="学习备注">
            <n-input v-model:value="recordForm.remark" type="textarea" placeholder="本次学习内容摘要" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="recordVisible = false">取消</n-button>
            <n-button type="primary" :loading="recordSaving" :disabled="recordSaving" @click="saveRecord">保存记录</n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NDataTable,
  NDatePicker,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSkeleton,
  NSpace,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  NTimePicker,
  useMessage,
  useNotification,
} from 'naive-ui'
import { AddOutline, AlertCircleOutline, CreateOutline, SearchOutline, TrashOutline } from '@vicons/ionicons5'
import {
  createCourse,
  deleteCourse,
  getLearnBoard,
  listCourses,
  listLearnProgress,
  recordLearnProgress,
  restoreCourse,
  updateCourse,
  type Course,
  type LearnBoardRow,
  type LearnProgress,
} from '../../api/campusLearning'
import { extractError, searchPersons, type SelectOption } from '../../utils/campus'

const message = useMessage()
const notification = useNotification()

type TabKey = 'manage' | 'mine' | 'board'
const activeTab = ref<TabKey>('manage')

/* ───────────────────────── 通用工具 ───────────────────────── */

/** 课程形式 / 类型的枚举（口径与后端 choices 一致）。 */
const COURSE_FORM_VALUES = ['直播', '录播', '面授', '线上']
const COURSE_TYPE_VALUES = ['必修', '选修']

const courseFormOptions = COURSE_FORM_VALUES.map((v) => ({ label: v, value: v }))
const courseTypeOptions = COURSE_TYPE_VALUES.map((v) => ({ label: v, value: v }))

/**
 * 得分 / 进度条：用**内联样式**渲染。
 * ⚠️ h() 造出的 VNode 不带 data-v-*，scoped 规则不命中（AGENTS.md R-225），
 *    所以条形图的样式只能内联，且色值 / 尺寸一律走 tokens.css 变量。
 */
function progressBar(percent: number, color: string) {
  const p = Math.max(0, Math.min(100, Number(percent) || 0))
  return h('div', {
    style: {
      width: '100%',
      height: 'var(--fs-10)',
      background: 'var(--g1)',
      borderRadius: 'var(--radius-pill)',
      overflow: 'hidden',
    },
  }, [
    h('div', { style: { width: `${p}%`, height: '100%', background: color } }),
  ])
}

/** 进度条 + 百分比文本（百分比用 tabular-nums 防抖动，R-204）。 */
function progressCell(percent: number, color: string) {
  return h('div', { style: { display: 'flex', alignItems: 'center', gap: 'var(--space-2)' } }, [
    h('div', { style: { flex: '1', minWidth: '0' } }, [progressBar(percent, color)]),
    h(
      'span',
      { style: { fontVariantNumeric: 'tabular-nums', fontSize: 'var(--text-meta)', color: 'var(--ink-soft)' } },
      `${Math.max(0, Math.min(100, Number(percent) || 0))}%`,
    ),
  ])
}

/** 文本单元格：长文本省略 + title 悬浮全文（R-110）。 */
function textCell(text: unknown, width = 140) {
  const s = text == null || text === '' ? '—' : String(text)
  return h('span', { title: s, style: { display: 'inline-block', maxWidth: `${width}px`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, s)
}

/** 复制文本（错误详情可一键复制，R-203）。 */
async function copyText(text: string) {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      message.success('错误信息已复制')
      return
    }
  } catch {
    /* 降级到下面的提示 */
  }
  message.warning('复制失败，请手动选中详情内容复制')
}

/* ───────────────────────── ① 课程管理 ───────────────────────── */

const courseRows = ref<Course[]>([])
const courseLoading = ref(false)
const courseError = ref('')
const courseSearch = ref('')
const courseTypeFilter = ref<string | null>(null)
const courseFormFilter = ref<string | null>(null)

const courseHasFilter = computed(
  () => Boolean(courseSearch.value.trim() || courseTypeFilter.value || courseFormFilter.value),
)
const courseEmptyText = computed(() => (courseHasFilter.value ? '没有符合筛选条件的课程' : '暂无数据'))

async function loadCourses() {
  courseLoading.value = true
  courseError.value = ''
  try {
    const kw = courseSearch.value.trim()
    const rows = await listCourses({
      type: courseTypeFilter.value ?? undefined,
      form: courseFormFilter.value ?? undefined,
      search: kw || undefined,
    })
    courseRows.value = kw
      ? rows.filter((r) => `${r.name}${r.code}`.includes(kw))
      : rows
  } catch (e: any) {
    courseError.value = extractError(e)
    courseRows.value = []
  } finally {
    courseLoading.value = false
  }
}

function clearCourseFilter() {
  courseSearch.value = ''
  courseTypeFilter.value = null
  courseFormFilter.value = null
  loadCourses()
}

const courseColumns = computed(() => [
  { title: '课程', key: 'name', width: 200, ellipsis: true, render: (row: Course) => textCell(row.name, 180) },
  { title: '形式', key: 'form', width: 90, render: (row: Course) => row.form || '—' },
  { title: '时长', key: 'durationMin', width: 100, render: (row: Course) => `${row.durationMin ?? 0} 分钟` },
  { title: '分类', key: 'category', width: 130, ellipsis: true, render: (row: Course) => textCell(row.category, 120) },
  {
    title: '类型',
    key: 'type',
    width: 90,
    render: (row: Course) =>
      h(NTag, { type: row.type === '必修' ? 'error' : 'info', size: 'small' }, { default: () => row.type || '—' }),
  },
  {
    title: '结课考试',
    key: 'examRequired',
    width: 100,
    render: (row: Course) =>
      h(NTag, { type: row.examRequired ? 'warning' : 'default', size: 'small' }, {
        default: () => (row.examRequired ? '需要' : '不需要'),
      }),
  },
  {
    title: '完成情况',
    key: 'doneCount',
    width: 130,
    render: (row: Course) =>
      row.totalCount
        ? `${row.doneCount ?? 0} / ${row.totalCount} 人`
        : (row.doneCount != null ? `${row.doneCount} 人` : '—'),
  },
  {
    title: '状态',
    key: 'enabled',
    width: 90,
    render: (row: Course) =>
      h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small' }, {
        default: () => (row.enabled ? '已启用' : '已停用'),
      }),
  },
  {
    title: '操作',
    key: 'actions',
    width: 168,
    fixed: 'right' as const,
    render: (row: Course) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openCourseEdit(row) }, {
            default: () => '编辑课程',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeCourse(row) }, {
            default: () => '删除课程',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const COURSE_SCROLL_X = 1148

/* ── 课程 新增 / 编辑 ── */
const courseFormVisible = ref(false)
const courseSaving = ref(false)
const courseEditing = ref<Course | null>(null)
const courseForm = reactive({
  code: '',
  name: '',
  form: '直播',
  durationMin: 60,
  category: '',
  type: '必修',
  examRequired: false,
  enabled: true,
  description: '',
})

function openCourseCreate() {
  Object.assign(courseForm, {
    code: '',
    name: '',
    form: '直播',
    durationMin: 60,
    category: '',
    type: '必修',
    examRequired: false,
    enabled: true,
    description: '',
  })
  courseEditing.value = null
  courseFormVisible.value = true
}

function openCourseEdit(row: Course) {
  Object.assign(courseForm, {
    code: row.code || '',
    name: row.name || '',
    form: row.form || '直播',
    durationMin: row.durationMin ?? 60,
    category: row.category || '',
    type: row.type || '必修',
    examRequired: Boolean(row.examRequired),
    enabled: row.enabled !== false,
    description: row.description || '',
  })
  courseEditing.value = row
  courseFormVisible.value = true
}

async function saveCourse() {
  if (!courseForm.code.trim()) {
    message.warning('请填写课程编码')
    return
  }
  if (!courseForm.name.trim()) {
    message.warning('请填写课程名称')
    return
  }
  courseSaving.value = true
  const payload = {
    code: courseForm.code.trim(),
    name: courseForm.name.trim(),
    form: courseForm.form,
    durationMin: courseForm.durationMin,
    category: courseForm.category.trim(),
    type: courseForm.type,
    examRequired: courseForm.examRequired,
    enabled: courseForm.enabled,
    description: courseForm.description.trim(),
  }
  try {
    if (courseEditing.value) {
      await updateCourse(courseEditing.value.id, payload)
      message.success('课程已更新')
    } else {
      await createCourse(payload)
      message.success('课程已创建')
    }
    courseFormVisible.value = false
    loadCourses()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    courseSaving.value = false
  }
}

/** 删除单条课程 = 中等破坏性操作 → 直接执行 + 通知撤销（R-106）。 */
async function removeCourse(row: Course) {
  try {
    await deleteCourse(row.id)
    notification.create({
      content: `已删除「${row.name}」`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            try {
              await restoreCourse(row.id)
              message.success('课程已恢复')
              loadCourses()
            } catch (e: any) {
              message.error(extractError(e))
            }
          },
        }, { default: () => '撤销' }),
    })
    loadCourses()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ───────────────────────── ② 我的课程 ───────────────────────── */

const mineRows = ref<LearnProgress[]>([])
const mineLoading = ref(false)
const mineError = ref('')
const minePerson = ref<string | null>(null)
const personOptions = ref<SelectOption[]>([])
const personLoading = ref(false)
/** 课程主数据缓存：学生视角的「形式 / 时长 / 类型 / 结课考试」要从课程表取。 */
const courseMap = ref<Record<string, Course>>({})

const mineHasFilter = computed(() => Boolean(minePerson.value))
const mineEmptyText = computed(() => (mineHasFilter.value ? '该校招生还没有学习记录' : '暂无数据'))

async function onPersonSearch(kw: string) {
  personLoading.value = true
  try {
    personOptions.value = await searchPersons(kw)
  } catch {
    personOptions.value = []
  } finally {
    personLoading.value = false
  }
}

async function loadMine() {
  mineLoading.value = true
  mineError.value = ''
  try {
    const [progresses, courses] = await Promise.all([
      listLearnProgress({ person: minePerson.value ?? undefined }),
      listCourses(),
    ])
    const map: Record<string, Course> = {}
    courses.forEach((c) => {
      map[String(c.id)] = c
    })
    courseMap.value = map
    mineRows.value = progresses
  } catch (e: any) {
    mineError.value = extractError(e)
    mineRows.value = []
  } finally {
    mineLoading.value = false
  }
}

const mineColumns = computed(() => [
  { title: '课程', key: 'courseName', width: 190, ellipsis: true, render: (row: LearnProgress) => textCell(row.courseName || courseMap.value[String(row.course)]?.name, 170) },
  { title: '形式', key: 'form', width: 90, render: (row: LearnProgress) => courseMap.value[String(row.course)]?.form || '—' },
  { title: '时长', key: 'durationMin', width: 100, render: (row: LearnProgress) => {
    const d = courseMap.value[String(row.course)]?.durationMin
    return d ? `${d} 分钟` : '—'
  } },
  { title: '类型', key: 'type', width: 90, render: (row: LearnProgress) => {
    const t = courseMap.value[String(row.course)]?.type
    return t ? h(NTag, { type: t === '必修' ? 'error' : 'info', size: 'small' }, { default: () => t }) : '—'
  } },
  { title: '进度', key: 'progress', width: 180, render: (row: LearnProgress) => progressCell(row.progress, 'var(--c-success)') },
  { title: '累计学习', key: 'minutes', width: 120, render: (row: LearnProgress) => h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, `${row.minutes ?? 0} 分钟`) },
  { title: '结课考试', key: 'examRequired', width: 100, render: (row: LearnProgress) => {
    const need = courseMap.value[String(row.course)]?.examRequired
    if (need == null) return '—'
    return h(NTag, { type: need ? 'warning' : 'default', size: 'small' }, { default: () => (need ? '需要' : '不需要') })
  } },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
    render: (row: LearnProgress) =>
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openRecord(row) }, {
        default: () => '记录学习',
      }),
  },
])

const MINE_SCROLL_X = 990

/* ── 记学习记录 ── */
const recordVisible = ref(false)
const recordSaving = ref(false)
const recordTarget = ref<LearnProgress | null>(null)
const recordDateTs = ref<number | null>(null)
const recordStartTs = ref<number | null>(null)
const recordForm = reactive({ minutes: 30, remark: '' })

const recordCourseName = computed(() => {
  const row = recordTarget.value
  if (!row) return '—'
  return row.courseName || courseMap.value[String(row.course)]?.name || '—'
})

function openRecord(row: LearnProgress) {
  recordTarget.value = row
  recordDateTs.value = Date.now()
  recordStartTs.value = null
  recordForm.minutes = 30
  recordForm.remark = ''
  recordVisible.value = true
}

function toDateStr(ts: number | null) {
  if (!ts) return undefined
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function toTimeStr(ts: number | null) {
  if (!ts) return undefined
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function saveRecord() {
  const row = recordTarget.value
  if (!row) return
  if (!recordDateTs.value) {
    message.warning('请选择学习日期')
    return
  }
  if (!recordForm.minutes || recordForm.minutes <= 0) {
    message.warning('请填写学习时长')
    return
  }
  recordSaving.value = true
  try {
    await recordLearnProgress(row.id, {
      date: toDateStr(recordDateTs.value),
      start: toTimeStr(recordStartTs.value),
      minutes: recordForm.minutes,
      remark: recordForm.remark.trim(),
    })
    message.success('学习记录已保存')
    recordVisible.value = false
    loadMine()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    recordSaving.value = false
  }
}

/* ───────────────────────── ③ 学习龙虎榜 ───────────────────────── */

const boardRows = ref<LearnBoardRow[]>([])
const boardLoading = ref(false)
const boardError = ref('')

async function loadBoard() {
  boardLoading.value = true
  boardError.value = ''
  try {
    boardRows.value = await getLearnBoard()
  } catch (e: any) {
    boardError.value = extractError(e)
    boardRows.value = []
  } finally {
    boardLoading.value = false
  }
}

const boardColumns = computed(() => [
  { title: '排名', key: 'rank', width: 80, render: (_row: LearnBoardRow, index: number) => index + 1 },
  { title: '姓名', key: 'name', width: 130, ellipsis: true, render: (row: LearnBoardRow) => textCell(row.name, 120) },
  { title: '班级', key: 'class', width: 150, ellipsis: true, render: (row: LearnBoardRow) => textCell(row.class, 140) },
  { title: '累计学习', key: 'minutes', width: 130, render: (row: LearnBoardRow) => h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, `${row.minutes ?? 0} 分钟`) },
  { title: '完成课程', key: 'done', width: 110, render: (row: LearnBoardRow) => `${row.done ?? 0} / ${row.total ?? 0} 门` },
  { title: '平均进度', key: 'avgProg', width: 170, render: (row: LearnBoardRow) => progressCell(row.avgProg, 'var(--c-info)') },
])

const BOARD_SCROLL_X = 770

/* ───────────────────────── 生命周期 ───────────────────────── */

function onTabChange(tab: TabKey) {
  if (tab === 'mine') loadMine()
  else if (tab === 'board') loadBoard()
  else loadCourses()
}

onMounted(() => {
  loadCourses()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.page-tabs {
  flex-shrink: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  flex-wrap: wrap;
}
.toolbar-search {
  width: 240px;
}
.toolbar-select {
  width: 160px;
}
.toolbar-tip {
  font-size: var(--text-small);
  color: var(--ink-faint);
}
.spacer {
  flex: 1;
}
.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

/* 错误三段式（R-203）：图标 + 人话描述 + 数据安全说明 + 可点击恢复动作 */
.filter {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.filter-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  white-space: nowrap;
}

.error-state {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--c-error);
  border-radius: var(--radius-md);
  background: var(--c-error-soft);
  flex-shrink: 0;
}
.error-state-icon {
  color: var(--c-error-deep);
  font-size: var(--text-h4);
  flex-shrink: 0;
}
.error-state-body {
  flex: 1;
  min-width: 0;
}
.error-state-title {
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--c-error-deep);
}
.error-state-desc {
  font-size: var(--text-small);
  color: var(--ink-soft);
  margin-top: var(--space-1);
}
.error-state-detail {
  margin-top: var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.error-state-code {
  margin: var(--space-1) 0;
  padding: var(--space-2);
  background: var(--surface);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
