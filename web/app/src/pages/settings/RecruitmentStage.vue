<template>
  <div class="page-container recruitment-stage">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">{ t('pages.settings.RecruitmentStage.s1') }</h1>
        <p class="page-subtitle">{ t('pages.settings.RecruitmentStage.s2') }</p>
      </div>
    </div>

    <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
      阶段是<strong>{ t('pages.settings.RecruitmentStage.s3') }</strong>，所有流程可引用。系统预置的「初评」「正式录用」不可停用/删除。引用次数显示在「使用」列。
    </n-alert>

    <div class="toolbar">
      <n-input v-model:value="keyword" :placeholder="t('pages.settings.RecruitmentStage.s4')" clearable style="width: 200px">
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <n-select v-model:value="filterType" :options="typeFilterOptions" placeholder="按类型筛选" clearable style="width: 160px" />
      <n-select v-model:value="filterStatus" :options="statusFilterOptions" style="width: 120px" />
      <div class="spacer"></div>
      <n-button type="primary" class="gradient-btn" @click="handleCreate">
        <template #icon><n-icon :component="AddOutline" /></template>
        新增阶段
      </n-button>
    </div>

    <div class="table-wrap">
    <n-data-table
      :columns="columns"
      :data="filteredStages"
      :loading="loading"
      :pagination="{ pageSize: 20 }"
      :row-key="(r) => r.id"
      :max-height="tableMaxHeight"
      :row-height="TABLE_ROW_HEIGHT"
    />
    </div>

    <!-- 新增/编辑阶段弹窗 -->
</div><!-- /.page-body -->
<!-- P1-4: 弹窗 560→600px 给 4 字段 + 4 checkbox + textarea + 双按钮更舒展的横向空间 -->
<n-modal v-model:show="showCreateModal" preset="card" :title="editing ? '编辑阶段' : '新增阶段'" style="width: 600px; max-width: 92vw" :bordered="false" :segmented="{ content: true, footer: true }">
      <n-form :model="form" label-placement="top">
        <!-- P1-3: 错误就近显示（R-209），不再只走全局 toast -->
        <n-form-item
          label="阶段名称"
          required
          :validation-status="nameError ? 'error' : undefined"
          :feedback="nameError ?? undefined"
        >
          <n-input v-model:value="form.name" placeholder="如：HRBP筛选" />
        </n-form-item>
        <!-- P0-2: 编辑锁死时给文字解释（R-101/R-109 键盘可达 + 不被颜色唯一表达） -->
        <n-form-item label="阶段类型" required>
          <n-tooltip :disabled="!editing" placement="top-start">
            <template #trigger>
              <div class="stage-type-wrap">
                <n-select v-model:value="form.stageType" :options="stageTypeOptionsForForm" :disabled="!!editing" />
              </div>
            </template>
            阶段类型已绑定现有流程，编辑时不可修改；如需变更请在流程中重新编排阶段。
          </n-tooltip>
        </n-form-item>
        <!-- 系统默认功能：只读展示（不可配置），中文名；与可选功能区分（兵哥 2026-09-08） -->
        <n-form-item label="默认功能">
          <n-space class="feature-checks" :wrap="false">
            <n-tag
              v-for="code in (editing?.defaultFeatures || editing?.default_features || [])"
              :key="code"
              size="small"
              type="default"
            >
{{ featureLabelMap[code] || code }}
</n-tag>
            <n-text v-if="!(editing?.defaultFeatures || editing?.default_features || []).length" depth="3" style="font-size: 13px">
              无（新建阶段暂无系统默认功能）
            </n-text>
          </n-space>
        </n-form-item>
        <!-- 用户可配置功能：可多选，选项来自 OPTIONAL_FEATURE_CATALOG（系统真正可配项） -->
        <n-form-item label="可选功能（可多选）">
          <n-checkbox-group v-model:value="form.optionalFeatures">
            <n-space v-if="(OPTIONAL_FEATURE_CATALOG[form.stageType] || []).length" class="feature-checks">
              <n-checkbox v-for="code in OPTIONAL_FEATURE_CATALOG[form.stageType]" :key="code" :value="code">
                {{ featureLabelMap[code] || code }}
              </n-checkbox>
            </n-space>
            <n-empty v-else size="small" description="请先选择阶段类型" style="padding: 12px 0" />
          </n-checkbox-group>
        </n-form-item>
        <!-- P0-3: textarea 约束（R-110）resize:none + max-height + overflow-wrap + 字数上限 -->
        <n-form-item label="阶段说明">
          <n-input
            v-model:value="form.description"
            type="textarea"
            :rows="3"
            :max-length="500"
            show-count
            :resizable="false"
            placeholder="例如：对简历进行初步评估，是候选人进入流程的第一道关卡"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="drawer-footer">
          <!-- P1-2: 微文案（R-204）动词+宾语；编辑态「放弃修改」明确后果 -->
          <n-button @click="showCreateModal = false">{{ editing ? '放弃修改' : '取消' }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="saving" @click="handleSave">
            {{ editing ? '保存修改' : '保存阶段' }}
          </n-button>
        </div>
      </template>
    </n-modal>
</div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, onMounted, computed, watch, h } from 'vue'
import { useMessage, NButton, NTag, NPopconfirm, NIcon, NSpace, NInput, NSelect, NCheckbox, NCheckboxGroup, NForm, NFormItem, NModal, NDataTable, NAlert, NTooltip, NEmpty, NText } from 'naive-ui'
import { useFormDraft } from '../../composables/useFormDraft'
import { AddOutline, TrashOutline, SearchOutline } from '@vicons/ionicons5'
import { listStages, createStage, updateStage, deleteStage, disableStage, enableStage } from '../../api/recruitment-process'
// 2026-08-17 PR #69: 阶段类型改从后端数据字典 (apps/dictionary) 读取, single source of truth.
//   旧 api/dict.ts 是占位 stub (永远返回 []), 现在接真端点 /api/v1/dictionary-items/?type_code=recruitment_stage_type.
import { listStageTypeOptions } from '../../api/dictionary'
const { t } = useI18n()

const message = useMessage()

const keyword = ref('')
const filterType = ref<string | null>(null)
// 2026-09-08: 列表增加状态筛选，默认选中「启用」（兵哥要求）。
const filterStatus = ref<string | null>('ENABLED')
const statusFilterOptions = [
  { label: '启用', value: 'ENABLED' },
  { label: '停用', value: 'DISABLED' },
  { label: '全部', value: '' as string },
]
const stages = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreateModal = ref(false)
const editing = ref<any>(null)
// 2026-08-29 UX 整改：表头固定 + 行高统一 — 视窗高 - 上方累计(标题/工具条/信息条/分页)≈ 560，按 1 屏可见行数倒推
// 2026-08-30 UX 二改：56→44 + td 垂直 padding 10→6，压缩行间距（兵哥嫌"行间距太大"）
const TABLE_ROW_HEIGHT = 44
const tableMaxHeight = computed(() => {
  if (typeof window === 'undefined') return 560
  // 预留分页器 64 + page-header 80 + toolbar 56 + alert 60 + page-body gap 48 ≈ 308，余下给表
  return Math.max(320, window.innerHeight - 308)
})
const form = reactive({
  name: '',
  // 2026-06-17: 默认值跟 stageTypeOptions 第一个同步 (BE 是 SCREEN, 旧 FILTER 写错导致 400)
  // 2026-06-29 花无缺: BE (apps/process/models.py:23-28) StageType = SCREEN/INVITATION/INTERVIEW/OFFER (无 ONBOARDING).
  //   旧 form.stageType 类型 includes 'ONBOARDING' (跟 api/recruitment-process.ts 同样的错),
  //   改成跟 BE 对齐. 入参 createStage stageType Partial<RecruitmentStage> 通过 api 接口校验.
  //   用 type alias 不用 inline union (inline union 会被 TS 当 enum, + 1 → number, 触发 TS2362/TS2363)
  stageType: '' as StageType,
  features: [] as string[],
  optionalFeatures: [] as string[],
  description: '',
})

// P0-1: 草稿自动保存（R-105）。新建模式启用，编辑模式禁用（避免草稿覆盖真实 row 数据）。
// 必须放在 form / editing 声明之后（避免 TDZ 引用错误）。
const draft = useFormDraft('recruitment-stage', form, { enabled: () => !editing.value })

type StageType = 'START_END' | 'SCREEN' | 'INVITATION' | 'INTERVIEW' | 'ASSESSMENT' | 'OFFER' | 'OTHER'

// 阶段类型已改为系统内置枚举 (后端 StageType, 经 /api/v1/recruitment-stages/stage-types/ 暴露),
//   不再依赖数据字典 recruitment_stage_type. 启动时 fetch 枚举, 拿不到才用 fallback (以 BE 枚举为准).
//   fallback 的 value=存储值 (code), label=展示名, 必须跟后端 StageType.choices 一致.
const FALLBACK_STAGE_TYPE = [
  { label: '起止阶段', value: 'START_END' },
  { label: '筛选型', value: 'SCREEN' },
  { label: '邀约型', value: 'INVITATION' },
  { label: '面试型', value: 'INTERVIEW' },
  { label: '测评型', value: 'ASSESSMENT' },
  { label: 'offer型', value: 'OFFER' },
  { label: '其他', value: 'OTHER' },
]
const stageTypeOptions = ref<Array<{ label: string; value: string }>>([...FALLBACK_STAGE_TYPE])

const typeFilterOptions = stageTypeOptions

// 起止阶段类型仅系统预置 (初评/正式录用) 可用: 新增阶段时从下拉剔除 START_END; 编辑态保留全部 (下拉 disabled 不改值)
const stageTypeOptionsForForm = computed<Array<{ label: string; value: string }>>(() =>
  editing.value
    ? stageTypeOptions.value
    : stageTypeOptions.value.filter((o) => o.value !== 'START_END'),
)

// 2026-06-17: FILTER 改 SCREEN (跟 form.stageType 默认值 + BE StageType 枚举对齐).
//   之前 filterOptions 的 key 是 FILTER (FE 旧值), BE 用 SCREEN → featureOptions['SCREEN'] 返 undefined → 0 checkbox.
// 功能项 code -> 中文名称（单一事实来源，对齐后端 recruitment_stages.default_features 实际取值）。
// 后端 code 集合见 apps/django/apps/core/management/commands/init_demo_data.py：
//   AUTO_MATCH / BULK_IMPORT / CANDIDATE_INFO / CANDIDATE_RESPONSE / CODE_EDITOR / EVALUATION_FORM /
//   INTERVIEW / INTERVIEWER / INTERVIEW_SCHEDULE / JOINT_INTERVIEW / MULTI_ROUND / OFFER /
//   OFFER_APPROVAL / OFFER_GENERATION / PHONE_CALL / RESUME_REVIEW / SCORING / TMPL_INTERVIEWER / VIDEO_RECORD
// 旧版 featureOptions 用的是 INVITE_FILTER/ARRANGE_INTERVIEW 等前端臆造 code，与后端不匹配，
// 导致列表「功能项」列回退显示英文 code（兵哥 2026-09-08 反馈）。中文名在此统一维护，弹窗选项与列表共用。
const FEATURE_LABELS: Record<string, string> = {
  RESUME_REVIEW: '简历评估',
  AUTO_MATCH: '自动匹配',
  BULK_IMPORT: '批量导入',
  CANDIDATE_INFO: '候选人信息',
  CANDIDATE_RESPONSE: '候选人回复',
  CODE_EDITOR: '代码编辑器',
  EVALUATION_FORM: '评估表单',
  INTERVIEW: '面试',
  INTERVIEWER: '面试官',
  TMPL_INTERVIEWER: '模板面试官',
  INTERVIEW_SCHEDULE: '面试安排',
  JOINT_INTERVIEW: '联合面试',
  MULTI_ROUND: '多轮面试',
  OFFER: 'Offer',
  OFFER_APPROVAL: 'Offer 审批',
  OFFER_GENERATION: 'Offer 生成',
  PHONE_CALL: '电话沟通',
  SCORING: '评分',
  VIDEO_RECORD: '视频录制',
  // —— 以下为 DB default_features 中出现的系统默认功能（兵哥 2026-09-08 要求默认项也用中文名展示）——
  INVITE_FILTER: '邀约筛选',
  INVITE_UPDATE_INFO: '邀约信息更新',
  TRANSFER_STAGE: '阶段流转',
  ARCHIVE: '归档',
  NOTES: '备注',
  // —— 以下为 DB optional_features 中出现的用户可配置功能 ——
  SCORE_RANK: '评分排名',
  DUPLICATE_CHECK: '查重',
  AI_SCORE: 'AI 评分',
  VOICE_RECORD: '语音记录',
  SALARY_NEGOTIATION: '薪资协商',
  BACKGROUND_CHECK: '背景调查',
}

// 各阶段类型「可选功能」全集（来自后端 seed 数据各阶段 optional_features 的并集，是用户真正可勾选的配置项）。
// 与 default_features（系统默认功能，只读展示，不在此勾选）区分开，避免把系统项当成可配项（兵哥 2026-09-08 反馈）。
const OPTIONAL_FEATURE_CATALOG: Record<string, string[]> = {
  SCREEN: ['SCORE_RANK', 'DUPLICATE_CHECK', 'AI_SCORE'],
  INVITATION: ['VOICE_RECORD'],
  INTERVIEW: ['VIDEO_RECORD', 'MULTI_ROUND', 'JOINT_INTERVIEW'],
  OFFER: ['SALARY_NEGOTIATION', 'BACKGROUND_CHECK'],
}

// 功能项 code -> 中文 label 映射，从 FEATURE_LABELS 推导（单一来源，列表展示与弹窗共用）。
const featureLabelMap: Record<string, string> = { ...FEATURE_LABELS }

const columns = computed(() => [
  { title: '阶段编号', key: 'code', width: 100 },
  { title: '阶段名称', key: 'name', width: 160 },
  {
    title: '类型',
    key: 'stageType',
    width: 100,
    // 2026-08-30 UX 六改: row.stageType 是存储的英文 code (SCREEN/INVITATION/INTERVIEW/OFFER),
    //   列表展示必须走 stageTypeOptions (来自 BE 字典 / fallback) 做 label 映射, 否则业务侧全看到英文.
    render: (row: any) => {
      const opt = stageTypeOptions.value.find((o) => o.value === row.stageType)
      return h(NTag, { type: 'info', size: 'small' }, { default: () => opt?.label ?? row.stageType })
    },
  },
  {
    title: '阶段来源',
    key: 'source',
    width: 100,
    render: (row: any) => (row.isBuiltin ?? row.isSystem)
      ? h(NTag, { type: 'warning', size: 'small' }, { default: () => '系统预置' })
      : h(NTag, { type: 'default', size: 'small' }, { default: () => '自定义' }),
  },
  {
    title: '使用',
    key: 'links',
    width: 80,
    render: (row: any) => {
      const count = row.referenceCount ?? row._count?.links ?? 0
      return h(NTag, { type: count > 0 ? 'success' : 'default', size: 'small' }, { default: () => `${count} 流程` })
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row: any) => h(NTag, { type: row.status === 'ENABLED' ? 'success' : 'default', size: 'small' }, { default: () => row.status === 'ENABLED' ? '启用' : '停用' }),
  },
  { title: '功能项', key: 'features', width: 280,
    ellipsis: { tooltip: false },
    render: (row: any) => {
    // 合并「默认功能(default_features) + 可选功能(optional_features)」全部以中文名展示
    const def = Array.isArray(row.defaultFeatures ?? row.default_features) ? (row.defaultFeatures ?? row.default_features) : (Array.isArray(row.features) ? row.features : [])
    const opt = Array.isArray(row.optionalFeatures ?? row.optional_features) ? (row.optionalFeatures ?? row.optional_features) : []
    const feats = [...def, ...opt]
    if (!feats.length) return '-'
    const labels = feats.map((code: string) => featureLabelMap[code] || code)
    const MAX_VISIBLE = 3
    const visible = labels.slice(0, MAX_VISIBLE)
    const overflow = labels.length - visible.length
    const tags = visible.map((label: string, i: number) =>
      h(NTag, { key: `t${i}`, size: 'small', type: 'default' }, { default: () => label }))
    if (overflow > 0) {
      tags.push(h(NTag, { key: 'overflow', size: 'small', type: 'default' }, { default: () => `+${overflow}` }))
    }
    // 内容较多时 hover 展示完整功能项列表（中文名）
    return h(NTooltip, { placement: 'top', keepAliveOnHover: true }, {
      trigger: () => h(NSpace, { size: 'small', wrap: false }, () => tags),
      default: () => `全部功能项（${labels.length}）：${labels.join('、')}`,
    })
  }},
  {
    title: '操作',
    key: 'action',
    width: 220,
    fixed: 'right' as const,
    render: (row: any) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'small', text: true, onClick: () => handleEdit(row) }, { default: () => '编辑' }),
      h(NButton, { size: 'small', text: true, onClick: () => handleToggleStatus(row), disabled: row.isBuiltin ?? row.isSystem }, { default: () => row.status === 'ENABLED' ? '停用' : '启用' }),
      h(NPopconfirm, { onPositiveClick: () => handleDelete(row), disabled: (row.isBuiltin ?? row.isSystem) || ((row.referenceCount ?? row._count?.links ?? 0) > 0) }, {
        trigger: () => h(NButton, { size: 'small', text: true, type: 'error', disabled: (row.isBuiltin ?? row.isSystem) || ((row.referenceCount ?? row._count?.links ?? 0) > 0) }, { default: () => '删除' }),
        default: () => (row.isBuiltin ?? row.isSystem) ? '系统预置阶段不可删除' : (row.referenceCount ?? row._count?.links ?? 0) > 0 ? `被 ${row.referenceCount ?? row._count?.links} 个流程引用，请先在流程中移除` : '确定要删除吗？',
      }),
    ]),
  },
])

const filteredStages = computed(() => {
  let list = stages.value
  // 2026-09-08: 状态筛选（默认启用在前，filterStatus 为 null 时不过滤 = 全部）
  if (filterStatus.value) list = list.filter((s) => s.status === filterStatus.value)
  if (filterType.value) list = list.filter((s) => s.stageType === filterType.value)
  if (keyword.value) {
    const k = keyword.value.toLowerCase()
    list = list.filter((s) => s.name.toLowerCase().includes(k) || s.code.toLowerCase().includes(k))
  }
  return list
})

async function loadList() {
  loading.value = true
  try {
    stages.value = await listStages()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

// P1-3: 校验就近显示（R-209）—— 错误在 form-item 下红字反馈，而非仅全局 toast
const nameError = computed<string | null>(() => {
  const v = form.name.trim()
  if (!v) return '请输入阶段名称'
  if (v.length > 30) return '阶段名称不超过 30 字'
  return null
})
const stageTypeError = computed<string | null>(() => {
  if (!form.stageType) return '请选择阶段类型'
  return null
})

function handleCreate() {
  editing.value = null
  Object.assign(form, { name: '', stageType: stageTypeOptionsForForm.value[0]?.value || 'SCREEN', features: [], optionalFeatures: [], description: '' })
  showCreateModal.value = true
  // P0-1: 草稿静默恢复（兵哥 2026-09-08 反馈：去掉恢复提示 toast，仅静默回填草稿内容，不干扰用户）。
  if (draft.probe()) draft.restore()
}

function handleEdit(row: any) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    stageType: row.stageType,
    // default_features 只读展示，optional_features 可配置
    features: Array.isArray(row.features) ? row.features : (Array.isArray(row.defaultFeatures ?? row.default_features) ? (row.defaultFeatures ?? row.default_features) : []),
    optionalFeatures: Array.isArray(row.optionalFeatures) ? row.optionalFeatures : (Array.isArray(row.optional_features) ? row.optional_features : []),
    description: row.description || '',
  })
  showCreateModal.value = true
  // 编辑模式不启用草稿（draft.enabled=false），无需探测/恢复
}

async function handleSave() {
  // P1-3: 提交前先跑就近校验（R-209）。有任何错误则不提交，错误已在字段下红字显示。
  if (nameError.value || stageTypeError.value) {
    message.error(nameError.value || stageTypeError.value || '请检查表单')
    return
  }
  saving.value = true
  try {
    // optionalFeatures → optional_features（用户可配置项）；不发送 features，避免覆盖系统默认功能 default_features（弹窗中只读展示）。
    // stageType 后端 update 也要求必填（RecruitmentStageSerializer 中 stage_type 非 read_only），必须始终发送（编辑时取原值）。
    const payload = {
      name: form.name,
      description: form.description,
      stageType: form.stageType,
      optionalFeatures: form.optionalFeatures,
    }
    if (editing.value) {
      await updateStage(editing.value.id, payload)
      message.success('已保存')
    } else {
      await createStage(payload)
      message.success('已新增（全局模板，可被任意流程引用）')
    }
    showCreateModal.value = false
    // P0-1: 提交成功后立即清除草稿（R-105: 提交成功后 MUST 立即清除）
    draft.clear()
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: any) {
  if (row.isBuiltin ?? row.isSystem) {
    message.warning('系统预置阶段不可删除')
    return
  }
  const refs = row.referenceCount ?? row._count?.links ?? 0
  if (refs > 0) {
    message.warning(`被 ${refs} 个流程引用，请先在流程中移除`)
    return
  }
  try {
    await deleteStage(row.id)
    message.success('已删除')
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '删除失败')
  }
}

async function handleToggleStatus(row: any) {
  if (row.isBuiltin ?? row.isSystem) {
    message.warning('系统预置阶段不可停用')
    return
  }
  try {
    if (row.status === 'ENABLED') {
      await disableStage(row.id)
      message.success('已停用')
    } else {
      await enableStage(row.id)
      message.success('已启用')
    }
    loadList()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '操作失败')
  }
}

onMounted(async () => {
  // 2026-08-30 UX 六改: 弹窗关闭时统一清理 editing 残留, 防止下一次点「新增阶段」按钮打开弹窗时
  //   editing 还指向旧的 row (来自上一次编辑), 导致 form.stageType 沿用旧值、:disabled="!!editing" 锁死下拉、
  //   视觉上像「类型只能选筛选项」. 之前 Bug 链: 编辑 → 关闭 → 新增 → 表单沿用旧值 + 下拉 disabled.
  watch(showCreateModal, (show) => {
    if (!show) editing.value = null
  })
  // 2026-08-17 PR #69: 阶段类型从后端数据字典拿 (single source of truth).
  //   listStageTypeOptions() 返回 [{label:展示名, value:stage_type存储值}], 拿不到就 fallback, 不阻塞页面.
  try {
    const opts = await listStageTypeOptions()
    if (Array.isArray(opts) && opts.length > 0) {
      stageTypeOptions.value = opts
      // form.stageType 默认用字典第 1 个, 跟 BE 同步
      if (!form.stageType || !stageTypeOptions.value.find((o) => o.value === form.stageType)) {
        form.stageType = stageTypeOptionsForForm.value[0].value as any
      }
    }
  } catch (e) {
    // fallback 已在 ref 初始值里, 不做事
  }
  loadList()
})
</script>

<style scoped>
/* 模型 B：固定标题 + 内部滚动三件套（与 AccountSettings/DemandConfig 同款） */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header {
  flex-shrink: 0;
  /* 2026-08-30 UX 四改：显式重置 padding/margin，防 n-layout 内容 padding 注入把 header 撑到 80px */
  padding: 0;
  margin: 0 0 8px 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  /* 2026-08-30 UX 四改：gap 16px→12px，缓解 11 层嵌套 + 多 padding 叠加的视觉膨胀 */
  gap: var(--space-3);
}

.recruitment-stage {
  /* 2026-08-30 UX 五改：容器外边距交还 SettingsLayout 统一管控（.settings-scroll 20px + 清零规则 !important），
     本处不再设 padding，避免与 .settings-scroll 叠加成 32px（见 SETTINGS_LAYOUT_DIAGNOSIS.md §2） */
}

/* 2026-08-29 UX 整改：禁首行多 tag wrap 后视觉偏移、行内 vertical-align 中线对齐；X-05 严禁硬编码颜色 */
/* 2026-08-30 UX 三改：补 padding:6px 12px !important 把行内垂直空白从 Naive 默认 ~10px 收到 6px，让 row-height=44 真正生效。
   theme-overrides 是首选，此处 !important 兜底防 HMR/特异性竞态 */
.recruitment-stage :deep(.n-data-table .n-data-table-tr .n-data-table-td) {
  vertical-align: middle;
  padding: 6px 12px !important;
}

/* === 2026-09-08 弹窗修复（P0-3 / P1-4）=== */
/* P0-3: textarea 不得撑破布局（R-110）—— 禁用拖拽 + 限高 + 长文字换行 */
.recruitment-stage :deep(.n-input .n-input__textarea-el) {
  resize: none;
  overflow-wrap: anywhere;
  word-break: break-word;
  max-height: 160px;
}
/* P1-4: 功能项 checkbox 容器窄屏换行容错（< 480px 下 4 项不再溢出） */
.stage-type-wrap {
  width: 100%;
}
.feature-checks {
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-4);
}
</style>
