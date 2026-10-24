<template>
  <div class="page-container">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" class="page-tabs" @update:value="onTabChange">
        <n-tab-pane name="list" tab="活动列表" />
        <n-tab-pane name="mine" tab="我的成绩" />
      </n-tabs>

      <!-- ① 活动列表 -->
      <template v-if="activeTab === 'list'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">活动</span>
            <n-input
              v-model:value="activitySearch"
              aria-label="活动名称"
              class="toolbar-search"
              placeholder="搜索活动名称"
              clearable
              @keyup.enter="loadActivities"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
          </div>
          <div class="filter">
            <span class="filter-label">状态</span>
            <n-select
              v-model:value="activityStatusFilter"
              aria-label="活动状态"
              class="toolbar-select"
              :options="activityStatusOptions"
              placeholder="全部状态"
              clearable
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="activityLoading" @click="loadActivities">查询活动</n-button>
          <n-button type="primary" @click="openActivityCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增活动
          </n-button>
        </div>

        <div v-if="activityError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">活动列表没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，你填的活动信息仍保留在本页，不会丢失。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ activityError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(activityError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="activityLoading" @click="loadActivities">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="activityLoading && !activityRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="activityColumns"
            :data="activityRows"
            :loading="activityLoading"
            :bordered="false"
            :scroll-x="ACTIVITY_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: Activity) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="activityEmptyText" size="small">
                <template #extra>
                  <n-button v-if="activityHasFilter" size="small" @click="clearActivityFilter">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ② 我的成绩 -->
      <template v-if="activeTab === 'mine'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">活动</span>
            <n-select
              v-model:value="scoreActivityFilter"
              aria-label="活动"
              class="toolbar-select-wide"
              :options="activityOptions"
              placeholder="全部活动"
              clearable
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="scoreLoading" @click="loadScores">刷新成绩</n-button>
          <n-button type="primary" @click="openScoreCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            录入成绩
          </n-button>
        </div>

        <div v-if="scoreError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">活动成绩没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，已录入的成绩仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ scoreError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(scoreError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="scoreLoading" @click="loadScores">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="scoreLoading && !scoreRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="scoreColumns"
            :data="scoreRows"
            :loading="scoreLoading"
            :bordered="false"
            :scroll-x="SCORE_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: ActivityScore) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="scoreEmptyText" size="small">
                <template #extra>
                  <n-button v-if="scoreActivityFilter" size="small" @click="scoreActivityFilter = null">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- 活动 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="activityFormVisible"
        preset="card"
        :title="activityEditing ? '编辑活动' : '新增活动'"
        :style="{ width: '720px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(560px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <!-- 写入失败三段式（R-203）：① 人话标题 ② 数据安全说明 ③ 折叠详情 + 恢复动作 -->
        <div v-if="activityWriteError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">{{ activityWriteError.title }}</div>
            <div class="error-state-desc">{{ activityWriteError.safe }}</div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ activityWriteError.detail }}</pre>
              <n-button size="tiny" quaternary @click="copyText(activityWriteError.detail)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="activitySaving" :disabled="activitySaving" @click="saveActivity">
            重新保存活动
          </n-button>
        </div>

        <n-form :model="activityForm" label-placement="top">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <!-- 字段级校验（R-221）：错误就近显示，图标 + 文字双通道，不只靠颜色 -->
              <n-form-item
                label="活动名称"
                required
                :validation-status="activityErrors.name ? 'error' : undefined"
                :show-feedback="Boolean(activityErrors.name)"
              >
                <n-input
                  ref="activityNameRef"
                  v-model:value="activityForm.name"
                  placeholder="请输入活动名称"
                  @update:value="clearActivityError('name')"
                />
                <template #feedback>
                  <span class="field-error">
                    <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                    {{ activityErrors.name }}
                  </span>
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="活动类型"
                required
                :validation-status="activityErrors.type ? 'error' : undefined"
                :show-feedback="Boolean(activityErrors.type)"
              >
                <n-input
                  ref="activityTypeRef"
                  v-model:value="activityForm.type"
                  placeholder="如 演讲赛 / 辩论赛"
                  @update:value="clearActivityError('type')"
                />
                <template #feedback>
                  <span class="field-error">
                    <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                    {{ activityErrors.type }}
                  </span>
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="活动日期"
                required
                :validation-status="activityErrors.dateTs ? 'error' : undefined"
                :show-feedback="Boolean(activityErrors.dateTs)"
              >
                <n-date-picker
                  ref="activityDateRef"
                  v-model:value="activityForm.dateTs"
                  type="date"
                  style="width: 100%"
                  @update:value="clearActivityError('dateTs')"
                />
                <template #feedback>
                  <span class="field-error">
                    <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                    {{ activityErrors.dateTs }}
                  </span>
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="活动状态" required>
                <n-select v-model:value="activityForm.status" :options="activityStatusOptions" placeholder="请选择活动状态" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="奖励说明">
                <n-input v-model:value="activityForm.reward" placeholder="如 +3 分" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="启用活动">
                <n-switch v-model:value="activityForm.enabled">
                  <template #checked>已启用</template>
                  <template #unchecked>已停用</template>
                </n-switch>
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-form-item label="活动规则">
            <n-input v-model:value="activityForm.rule" type="textarea" placeholder="参赛规则与计分方式" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="activityFormVisible = false">{{ activityEditing ? '取消编辑' : '取消新增' }}</n-button>
            <n-button type="primary" :loading="activitySaving" :disabled="activitySaving" @click="saveActivity">保存活动</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 活动评分录入 弹窗 -->
      <n-modal
        v-model:show="scoreFormVisible"
        preset="card"
        title="录入活动成绩"
        :style="{ width: '620px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(460px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <!-- 写入失败三段式（R-203）：① 人话标题 ② 数据安全说明 ③ 折叠详情 + 恢复动作 -->
        <div v-if="scoreWriteError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">{{ scoreWriteError.title }}</div>
            <div class="error-state-desc">{{ scoreWriteError.safe }}</div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ scoreWriteError.detail }}</pre>
              <n-button size="tiny" quaternary @click="copyText(scoreWriteError.detail)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="scoreSaving" :disabled="scoreSaving" @click="saveScore">
            重新保存成绩
          </n-button>
        </div>

        <n-form :model="scoreForm" label-placement="top">
          <!-- 字段级校验（R-221）：错误就近显示，图标 + 文字双通道，不只靠颜色 -->
          <n-form-item
            label="活动"
            required
            :validation-status="scoreErrors.activity ? 'error' : undefined"
            :show-feedback="Boolean(scoreErrors.activity)"
          >
            <n-select
              ref="scoreActivityRef"
              v-model:value="scoreForm.activity"
              :options="activityOptions"
              placeholder="请选择活动"
              @update:value="clearScoreError('activity')"
            />
            <template #feedback>
              <span class="field-error">
                <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                {{ scoreErrors.activity }}
              </span>
            </template>
          </n-form-item>
          <n-form-item
            label="校招生"
            required
            :validation-status="scoreErrors.person ? 'error' : undefined"
            :show-feedback="Boolean(scoreErrors.person)"
          >
            <n-select
              ref="scorePersonRef"
              v-model:value="scoreForm.person"
              :options="personOptions"
              placeholder="搜索并选择校招生"
              clearable
              filterable
              remote
              :loading="personLoading"
              :on-search="onPersonSearch"
              @update:value="clearScoreError('person')"
            />
            <template #feedback>
              <span class="field-error">
                <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                {{ scoreErrors.person }}
              </span>
            </template>
          </n-form-item>
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="活动得分" required>
                <n-input-number v-model:value="scoreForm.score" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="名次">
                <n-input-number v-model:value="scoreForm.rank" :min="1" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-form-item label="奖励">
            <n-input v-model:value="scoreForm.reward" placeholder="如 +3 分" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="scoreFormVisible = false">取消录入</n-button>
            <n-button type="primary" :loading="scoreSaving" :disabled="scoreSaving" @click="saveScore">保存成绩</n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, nextTick, onMounted, reactive, ref } from 'vue'
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
  useMessage,
  useNotification,
} from 'naive-ui'
import { AddOutline, AlertCircleOutline, CreateOutline, SearchOutline, TrashOutline } from '@vicons/ionicons5'
import {
  createActivity,
  createActivityScore,
  deleteActivity,
  listActivities,
  listActivityScores,
  restoreActivity,
  updateActivity,
  type Activity,
  type ActivityScore,
} from '../../api/campusLearning'
import { buildWriteError, extractError, searchPersons, type SelectOption, type WriteErrorInfo } from '../../utils/campus'
import { useFormDraft } from '../../composables/useFormDraft'

const message = useMessage()
const notification = useNotification()

type TabKey = 'list' | 'mine'
const activeTab = ref<TabKey>('list')

const ACTIVITY_STATUS_VALUES = ['未开始', '进行中', '已结束']
const activityStatusOptions = ACTIVITY_STATUS_VALUES.map((v) => ({ label: v, value: v }))

/* ───────────────────────── 通用工具 ───────────────────────── */

function textCell(text: unknown, width = 140) {
  const s = text == null || text === '' ? '—' : String(text)
  return h('span', { title: s, style: { display: 'inline-block', maxWidth: `${width}px`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, s)
}

async function copyText(text: string) {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      message.success('错误信息已复制')
      return
    }
  } catch {
    /* 降级提示 */
  }
  message.warning('复制失败，请手动选中详情内容复制')
}

/* ───────────────────────── ① 活动列表 ───────────────────────── */

const activityRows = ref<Activity[]>([])
const activityLoading = ref(false)
const activityError = ref('')
const activitySearch = ref('')
const activityStatusFilter = ref<string | null>(null)

const activityHasFilter = computed(() => Boolean(activitySearch.value.trim() || activityStatusFilter.value))
const activityEmptyText = computed(() => (activityHasFilter.value ? '没有符合筛选条件的活动' : '暂无数据'))

const activityOptions = computed(() =>
  activityRows.value.map((a) => ({ label: a.name || String(a.id), value: String(a.id) })),
)

async function loadActivities() {
  activityLoading.value = true
  activityError.value = ''
  try {
    const kw = activitySearch.value.trim()
    const rows = await listActivities({ search: kw || undefined })
    activityRows.value = kw
      ? rows.filter((r) => String(r.name || '').includes(kw))
      : activityStatusFilter.value
        ? rows.filter((r) => r.status === activityStatusFilter.value)
        : rows
  } catch (e: any) {
    activityError.value = extractError(e)
    activityRows.value = []
  } finally {
    activityLoading.value = false
  }
}

function clearActivityFilter() {
  activitySearch.value = ''
  activityStatusFilter.value = null
  loadActivities()
}

const activityColumns = computed(() => [
  { title: '活动名称', key: 'name', width: 200, ellipsis: true, render: (row: Activity) => textCell(row.name, 180) },
  { title: '类型', key: 'type', width: 130, ellipsis: true, render: (row: Activity) => textCell(row.type, 110) },
  { title: '日期', key: 'date', width: 120, render: (row: Activity) => row.date || '—' },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: Activity) => {
      const map: Record<string, any> = { 未开始: 'default', 进行中: 'success', 已结束: 'info' }
      return h(NTag, { type: map[row.status] || 'default', size: 'small' }, { default: () => row.status || '—' })
    },
  },
  { title: '奖励', key: 'reward', width: 120, ellipsis: true, render: (row: Activity) => textCell(row.reward, 100) },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    fixed: 'right' as const,
    render: (row: Activity) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openActivityEdit(row) }, {
            default: () => '编辑活动',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeActivity(row) }, {
            default: () => '删除活动',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const ACTIVITY_SCROLL_X = 850

/* ── 活动 新增 / 编辑 ── */
const activityFormVisible = ref(false)
const activitySaving = ref(false)
const activityEditing = ref<Activity | null>(null)
const activityForm = reactive({
  name: '',
  type: '',
  dateTs: null as number | null,
  status: '未开始',
  reward: '',
  rule: '',
  enabled: true,
})

// P0-1 草稿自动保存（R-105）：新增活动需人工撰写规则，耗时 > 1 分钟。
// 编辑态关闭草稿，避免草稿覆盖真实 row 数据。
const activityDraft = useFormDraft('campus-activity-create', activityForm, {
  enabled: () => !activityEditing.value,
})

// 字段级校验状态（R-221）。
const activityErrors = reactive({ name: '', type: '', dateTs: '' })
const activityNameRef = ref<any>(null)
const activityTypeRef = ref<any>(null)
const activityDateRef = ref<any>(null)

// 写入失败三段式（R-203）。
const activityWriteError = ref<WriteErrorInfo | null>(null)

function clearActivityError(field: keyof typeof activityErrors) {
  activityErrors[field] = ''
}

/** 聚焦第一个出错字段（R-221）。 */
async function focusFirstInvalid(pairs: Array<[string, { value: any }]>) {
  await nextTick()
  for (const [msg, r] of pairs) {
    if (!msg) continue
    const inst = r?.value
    if (inst && typeof inst.focus === 'function') {
      inst.focus()
      return
    }
  }
}

function toDateStr(ts: number | null) {
  if (!ts) return undefined
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function resetActivityForm() {
  Object.assign(activityForm, {
    name: '',
    type: '',
    dateTs: Date.now(),
    status: '未开始',
    reward: '',
    rule: '',
    enabled: true,
  })
}

function openActivityCreate() {
  activityErrors.name = ''
  activityErrors.type = ''
  activityErrors.dateTs = ''
  activityWriteError.value = null
  activityEditing.value = null
  // 先探测草稿再决定要不要重置表单：直接重置会把上次草稿内容抹掉（R-105）。
  if (activityDraft.probe()) {
    activityDraft.restore()
    if (activityForm.name.trim() || activityForm.type.trim() || activityForm.rule.trim()) {
      notification.create({
        content: '已恢复上次填写的内容',
        duration: 8000,
        keepAliveOnHover: true,
        action: () =>
          h(
            NButton,
            { text: true, type: 'primary', onClick: clearActivityDraft },
            { default: () => '清空' },
          ),
      })
    } else {
      // 空草稿（只打开过弹窗没填写）→ 直接丢弃，不给用户假提示。
      activityDraft.clear()
      resetActivityForm()
    }
  } else {
    resetActivityForm()
  }
  activityFormVisible.value = true
}

/** 「清空」出口：清掉草稿并把恢复出来的内容一并清掉。 */
function clearActivityDraft() {
  activityDraft.clear()
  resetActivityForm()
}

function openActivityEdit(row: Activity) {
  Object.assign(activityForm, {
    name: row.name || '',
    type: row.type || '',
    dateTs: row.date ? new Date(row.date).getTime() : null,
    status: row.status || '未开始',
    reward: row.reward || '',
    rule: row.rule || '',
    enabled: row.enabled !== false,
  })
  activityEditing.value = row
  activityFormVisible.value = true
}

async function saveActivity() {
  activityErrors.name = activityForm.name.trim() ? '' : '请填写活动名称'
  activityErrors.type = activityForm.type.trim() ? '' : '请填写活动类型'
  activityErrors.dateTs = activityForm.dateTs ? '' : '请选择活动日期'
  if (activityErrors.name || activityErrors.type || activityErrors.dateTs) {
    await focusFirstInvalid([
      [activityErrors.name, activityNameRef],
      [activityErrors.type, activityTypeRef],
      [activityErrors.dateTs, activityDateRef],
    ])
    return
  }
  activitySaving.value = true
  activityWriteError.value = null
  const payload = {
    name: activityForm.name.trim(),
    type: activityForm.type.trim(),
    date: toDateStr(activityForm.dateTs),
    status: activityForm.status,
    reward: activityForm.reward.trim(),
    rule: activityForm.rule.trim(),
    enabled: activityForm.enabled,
  }
  try {
    if (activityEditing.value) {
      await updateActivity(activityEditing.value.id, payload)
      message.success('活动已更新')
    } else {
      await createActivity(payload)
      message.success('活动已创建')
      // 保存成功后立即清除草稿（R-105），并重置表单避免待写入的定时器把旧内容写回。
      activityDraft.clear()
      resetActivityForm()
    }
    activityFormVisible.value = false
    loadActivities()
  } catch (e: any) {
    // 写入失败 → 三段式（R-203），不再只弹一条原始报文 toast。
    activityWriteError.value = buildWriteError(e, { action: '保存活动' })
  } finally {
    activitySaving.value = false
  }
}

/** 删除单条活动 = 中等破坏性操作 → 直接执行 + 通知撤销（R-106）。 */
async function removeActivity(row: Activity) {
  try {
    await deleteActivity(row.id)
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
              await restoreActivity(row.id)
              message.success('活动已恢复')
              loadActivities()
            } catch (e: any) {
              message.error(extractError(e))
            }
          },
        }, { default: () => '撤销' }),
    })
    loadActivities()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ───────────────────────── ② 我的成绩 ───────────────────────── */

const scoreRows = ref<ActivityScore[]>([])
const scoreLoading = ref(false)
const scoreError = ref('')
const scoreActivityFilter = ref<string | null>(null)

const scoreEmptyText = computed(() =>
  scoreActivityFilter.value ? '该活动还没有成绩记录' : '暂无数据',
)

async function loadScores() {
  scoreLoading.value = true
  scoreError.value = ''
  try {
    scoreRows.value = await listActivityScores({ activity: scoreActivityFilter.value ?? undefined })
  } catch (e: any) {
    scoreError.value = extractError(e)
    scoreRows.value = []
  } finally {
    scoreLoading.value = false
  }
}

const scoreColumns = computed(() => [
  { title: '活动', key: 'activityName', width: 200, ellipsis: true, render: (row: ActivityScore) => textCell(row.activityName, 180) },
  { title: '校招生', key: 'personName', width: 140, ellipsis: true, render: (row: ActivityScore) => textCell(row.personName, 120) },
  { title: '我的成绩', key: 'score', width: 110, render: (row: ActivityScore) => h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, String(row.score ?? '—')) },
  { title: '排名', key: 'rank', width: 100, render: (row: ActivityScore) => (row.rank == null ? '—' : h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, String(row.rank))) },
  { title: '奖励', key: 'reward', width: 120, ellipsis: true, render: (row: ActivityScore) => textCell(row.reward, 100) },
])

const SCORE_SCROLL_X = 670

/* ── 活动评分录入 ── */
const scoreFormVisible = ref(false)
const scoreSaving = ref(false)
const personOptions = ref<SelectOption[]>([])
const personLoading = ref(false)
const scoreForm = reactive({
  activity: null as string | null,
  person: null as string | null,
  score: 0,
  rank: null as number | null,
  reward: '',
})

// 字段级校验状态（R-221）。
const scoreErrors = reactive({ activity: '', person: '' })
const scoreActivityRef = ref<any>(null)
const scorePersonRef = ref<any>(null)

// 写入失败三段式（R-203）。
const scoreWriteError = ref<WriteErrorInfo | null>(null)

function clearScoreError(field: keyof typeof scoreErrors) {
  scoreErrors[field] = ''
}

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

function openScoreCreate() {
  Object.assign(scoreForm, {
    activity: scoreActivityFilter.value ?? (activityOptions.value[0]?.value ?? null),
    person: null,
    score: 0,
    rank: null,
    reward: '',
  })
  scoreFormVisible.value = true
}

async function saveScore() {
  scoreErrors.activity = scoreForm.activity ? '' : '请选择活动'
  scoreErrors.person = scoreForm.person ? '' : '请选择校招生'
  if (scoreErrors.activity || scoreErrors.person) {
    await focusFirstInvalid([
      [scoreErrors.activity, scoreActivityRef],
      [scoreErrors.person, scorePersonRef],
    ])
    return
  }
  scoreSaving.value = true
  scoreWriteError.value = null
  try {
    await createActivityScore({
      activity: String(scoreForm.activity),
      person: String(scoreForm.person),
      score: scoreForm.score,
      rank: scoreForm.rank ?? undefined,
      reward: scoreForm.reward.trim(),
    })
    message.success('活动成绩已保存')
    scoreFormVisible.value = false
    loadScores()
  } catch (e: any) {
    // 写入失败 → 三段式（R-203），不再只弹一条原始报文 toast。
    scoreWriteError.value = buildWriteError(e, { action: '保存成绩' })
  } finally {
    scoreSaving.value = false
  }
}

/* ───────────────────────── 生命周期 ───────────────────────── */

function onTabChange(tab: TabKey) {
  if (tab === 'mine') {
    if (!activityRows.value.length) loadActivities()
    loadScores()
  } else {
    loadActivities()
  }
}

onMounted(() => {
  loadActivities()
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
  max-width: 100%;
}
.toolbar-select {
  width: 150px;
  max-width: 100%;
}
.toolbar-select-wide {
  width: 280px;
  max-width: 100%;
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

/* 字段级校验提示：图标 + 文字双通道（R-221，不只靠颜色） */
.field-error {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-small);
  color: var(--c-error-deep);
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
