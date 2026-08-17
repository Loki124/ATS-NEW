<template>
  <div class="recruitment-stage">
    <div class="page-header">
      <h2>招聘阶段配置</h2>
      <n-space>
        <n-input v-model:value="keyword" placeholder="搜索阶段" clearable style="width: 200px" />
        <n-select v-model:value="filterType" :options="typeFilterOptions" placeholder="按类型筛选" clearable style="width: 160px" />
        <n-button type="primary" @click="showCreateModal = true">
          <template #icon><n-icon :component="AddOutline" /></template>
          新增阶段
        </n-button>
      </n-space>
    </div>

    <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
      阶段是<strong>全局模板</strong>，所有流程可引用。系统预置的「初评」「正式录用」不可停用/删除。引用次数显示在「使用」列。
    </n-alert>

    <n-data-table
      :columns="columns"
      :data="filteredStages"
      :loading="loading"
      :pagination="{ pageSize: 20 }"
      :row-key="(r) => r.id"
    />

    <!-- 新增/编辑阶段弹窗 -->
    <n-modal v-model:show="showCreateModal" preset="card" :title="editing ? '编辑阶段' : '新增阶段'" style="width: 560px">
      <n-form :model="form" label-placement="top">
        <n-form-item label="阶段名称" required>
          <n-input v-model:value="form.name" placeholder="如：HRBP筛选" />
        </n-form-item>
        <n-form-item label="阶段类型" required>
          <n-select v-model:value="form.stageType" :options="stageTypeOptions" :disabled="!!editing" />
        </n-form-item>
        <n-form-item label="功能项（可多选）">
          <n-checkbox-group v-model:value="form.features">
            <n-space>
              <n-checkbox v-for="opt in featureOptions[form.stageType] || []" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </n-checkbox>
            </n-space>
          </n-checkbox-group>
        </n-form-item>
        <n-form-item label="阶段说明">
          <n-input v-model:value="form.description" type="textarea" :rows="2" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, h } from 'vue'
import { useMessage, NButton, NTag, NPopconfirm, NIcon, NSpace, NInput, NSelect, NCheckbox, NCheckboxGroup, NForm, NFormItem, NModal, NDataTable, NAlert, NTooltip } from 'naive-ui'
import { AddOutline, TrashOutline } from '@vicons/ionicons5'
import { listStages, createStage, updateStage, deleteStage, disableStage, enableStage } from '../../api/recruitment-process'
// 2026-08-17 PR #69: 阶段类型改从后端数据字典 (apps/dictionary) 读取, single source of truth.
//   旧 api/dict.ts 是占位 stub (永远返回 []), 现在接真端点 /api/v1/dictionary-items/?type_code=recruitment_stage_type.
import { listStageTypeOptions } from '../../api/dictionary'

const message = useMessage()
const keyword = ref('')
const filterType = ref<string | null>(null)
const stages = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreateModal = ref(false)
const editing = ref<any>(null)
const form = reactive({
  name: '',
  // 2026-06-17: 默认值跟 stageTypeOptions 第一个同步 (BE 是 SCREEN, 旧 FILTER 写错导致 400)
  // 2026-06-29 花无缺: BE (apps/process/models.py:23-28) StageType = SCREEN/INVITATION/INTERVIEW/OFFER (无 ONBOARDING).
  //   旧 form.stageType 类型 includes 'ONBOARDING' (跟 api/recruitment-process.ts 同样的错),
  //   改成跟 BE 对齐. 入参 createStage stageType Partial<RecruitmentStage> 通过 api 接口校验.
  //   用 type alias 不用 inline union (inline union 会被 TS 当 enum, + 1 → number, 触发 TS2362/TS2363)
  stageType: '' as StageType,
  features: [] as string[],
  description: '',
})

type StageType = 'SCREEN' | 'INVITATION' | 'INTERVIEW' | 'OFFER'

// 2026-08-17 PR #69: 阶段类型从后端数据字典 (apps/dictionary, type_code=recruitment_stage_type) 拿, single source of truth.
//   FE 启动时 fetch 字典项, 拿不到 (网络/未登录) 才用 fallback — 同样以 BE 字典为准.
//   fallback 的 value=stage_type 存储值 (key), label=展示名 (value), 必须跟字典项一致.
const FALLBACK_STAGE_TYPE = [
  { label: '筛选', value: 'SCREEN' },
  { label: '邀约', value: 'INVITATION' },
  { label: '面试', value: 'INTERVIEW' },
  { label: '录用', value: 'OFFER' },
]
const stageTypeOptions = ref<Array<{ label: string; value: string }>>([...FALLBACK_STAGE_TYPE])

const typeFilterOptions = stageTypeOptions

// 2026-06-17: FILTER 改 SCREEN (跟 form.stageType 默认值 + BE StageType 枚举对齐).
//   之前 filterOptions 的 key 是 FILTER (FE 旧值), BE 用 SCREEN → featureOptions['SCREEN'] 返 undefined → 0 checkbox.
const featureOptions: Record<string, any[]> = {
  SCREEN: [
    { label: '邀请筛选', value: 'INVITE_FILTER' },
    { label: '邀请更新信息', value: 'INVITE_UPDATE_INFO' },
    { label: '转移阶段', value: 'TRANSFER_STAGE' },
    { label: '归档', value: 'ARCHIVE' },
  ],
  INVITATION: [
    { label: '安排面试', value: 'ARRANGE_INTERVIEW' },
    { label: '邀请更新信息', value: 'INVITE_UPDATE_INFO' },
    { label: '转移阶段', value: 'TRANSFER_STAGE' },
    { label: '归档', value: 'ARCHIVE' },
  ],
  INTERVIEW: [
    { label: '安排面试', value: 'ARRANGE_INTERVIEW' },
    { label: '邀请面试', value: 'INVITE_INTERVIEW' },
    { label: '邀请更新信息', value: 'INVITE_UPDATE_INFO' },
    { label: '转移阶段', value: 'TRANSFER_STAGE' },
    { label: '归档', value: 'ARCHIVE' },
  ],
  OFFER: [
    { label: '发送 Offer', value: 'SEND_OFFER' },
    { label: '发起背调', value: 'START_BACKGROUND_CHECK' },
    { label: '邀请更新信息', value: 'INVITE_UPDATE_INFO' },
    { label: '转移阶段', value: 'TRANSFER_STAGE' },
    { label: '归档', value: 'ARCHIVE' },
  ],
  ONBOARDING: [
    { label: '发起入职', value: 'START_ONBOARDING' },
    { label: '邀请更新信息', value: 'INVITE_UPDATE_INFO' },
    { label: '转移阶段', value: 'TRANSFER_STAGE' },
    { label: '归档', value: 'ARCHIVE' },
  ],
}

// 功能项 code -> 中文 label 映射，从 featureOptions 推导（单一来源，避免重复维护）。
const featureLabelMap: Record<string, string> = {}
Object.values(featureOptions).forEach((opts) => {
  opts.forEach((opt) => { featureLabelMap[opt.value] = opt.label })
})

const columns = [
  { title: '阶段编号', key: 'code', width: 100 },
  { title: '阶段名称', key: 'name', width: 160 },
  {
    title: '类型',
    key: 'stageType',
    width: 100,
    render: (row: any) => h(NTag, { type: 'info', size: 'small' }, { default: () => row.stageType }),
  },
  {
    title: '系统预置',
    key: 'isBuiltin',
    width: 90,
    render: (row: any) => (row.isBuiltin ?? row.isSystem) ? h(NTag, { type: 'warning', size: 'small' }, { default: () => '系统' }) : '-',
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
  { title: '功能项', key: 'features', render: (row: any) => {
    const feats = row.features ?? row.defaultFeatures
    if (!Array.isArray(feats) || feats.length === 0) return '-'
    const items = feats.map((code: string) => {
      const label = featureLabelMap[code] || code
      return h(NTooltip, { key: code }, {
        trigger: () => h(NTag, { size: 'small', type: 'default' }, { default: () => label }),
        default: () => code,
      })
    })
    return h(NSpace, { size: 'small', wrap: true }, () => items)
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
]

const filteredStages = computed(() => {
  let list = stages.value
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

function handleCreate() {
  editing.value = null
  Object.assign(form, { name: '', stageType: stageTypeOptions.value[0]?.value || 'SCREEN', features: [], description: '' })
  showCreateModal.value = true
}

function handleEdit(row: any) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    stageType: row.stageType,
    features: Array.isArray(row.features) ? row.features : (Array.isArray(row.defaultFeatures) ? row.defaultFeatures : []),
    description: row.description || '',
  })
  showCreateModal.value = true
}

async function handleSave() {
  if (!form.name.trim()) {
    message.error('阶段名称必填')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateStage(editing.value.id, form)
      message.success('已保存')
    } else {
      await createStage(form)
      message.success('已新增（全局模板，可被任意流程引用）')
    }
    showCreateModal.value = false
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
  // 2026-08-17 PR #69: 阶段类型从后端数据字典拿 (single source of truth).
  //   listStageTypeOptions() 返回 [{label:展示名, value:stage_type存储值}], 拿不到就 fallback, 不阻塞页面.
  try {
    const opts = await listStageTypeOptions()
    if (Array.isArray(opts) && opts.length > 0) {
      stageTypeOptions.value = opts
      // form.stageType 默认用字典第 1 个, 跟 BE 同步
      if (!form.stageType || !stageTypeOptions.value.find((o) => o.value === form.stageType)) {
        form.stageType = stageTypeOptions.value[0].value as any
      }
    }
  } catch (e) {
    // fallback 已在 ref 初始值里, 不做事
  }
  loadList()
})
</script>

<style scoped>
.recruitment-stage {
  padding: 20px 24px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
</style>
