<script setup lang="ts">
/**
 * 背调面板 (G26) - 4 等级 + 报告下载
 */
import { ref, onMounted, h } from 'vue'
import {
  NCard, NSpace, NButton, NDataTable, NTag, NModal, NForm, NFormItem, NInput,
  NSelect, NEmpty, NSpin, useMessage, type DataTableColumns,
} from 'naive-ui'
import {
  listBackgroundChecks, createBackgroundCheck, completeBackgroundCheck, downloadBackgroundCheckReport,
  BG_CHECK_LEVEL_LABEL, BG_CHECK_LEVEL_COLOR,
  type BackgroundCheck,
} from '../../api/offer'

const props = defineProps<{ offerId: string }>()

const message = useMessage()
const loading = ref(false)
const list = ref<BackgroundCheck[]>([])

const showCreateModal = ref(false)
const showCompleteModal = ref(false)
const currentBid = ref<string | null>(null)

const createForm = ref<{ checkType: string; supplier: string; note: string }>({
  checkType: '学历', supplier: '', note: '',
})

const completeForm = ref<{ level: 'PASS' | 'WARN' | 'INCONCLUSIVE' | 'FAIL' | null; risks: string }>({
  level: null,
  risks: '[]',
})

const levelOptions = [
  { label: BG_CHECK_LEVEL_LABEL.PASS + ' (100 分)',         value: 'PASS' },
  { label: BG_CHECK_LEVEL_LABEL.WARN + ' (70 分)',          value: 'WARN' },
  { label: BG_CHECK_LEVEL_LABEL.INCONCLUSIVE + ' (50 分)',  value: 'INCONCLUSIVE' },
  { label: BG_CHECK_LEVEL_LABEL.FAIL + ' (0 分)',           value: 'FAIL' },
]

async function loadList() {
  loading.value = true
  try {
    list.value = await listBackgroundChecks(props.offerId)
  } catch (e: any) {
    message.error(`加载失败: ${e?.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.value = { checkType: '学历', supplier: '', note: '' }
  showCreateModal.value = true
}

async function handleCreate() {
  if (!createForm.value.checkType) {
    message.error('请输入背调类型')
    return
  }
  try {
    await createBackgroundCheck(props.offerId, createForm.value)
    message.success('背调已创建')
    showCreateModal.value = false
    await loadList()
  } catch (e: any) {
    message.error(`创建失败: ${e?.response?.data?.message || e?.message || '未知错误'}`)
  }
}

function openComplete(bid: string) {
  currentBid.value = bid
  completeForm.value = { level: null, risks: '[]' }
  showCompleteModal.value = true
}

async function handleComplete() {
  if (!currentBid.value || !completeForm.value.level) {
    message.error('请选择等级')
    return
  }
  let risks: any[] = []
  try {
    risks = JSON.parse(completeForm.value.risks || '[]')
    if (!Array.isArray(risks)) throw new Error('risks 必须是 JSON 数组')
  } catch (e: any) {
    message.error(`risks 字段 JSON 解析失败: ${e.message}`)
    return
  }
  try {
    await completeBackgroundCheck(props.offerId, currentBid.value, {
      level: completeForm.value.level,
      risks,
    })
    message.success('背调已完成, 等级已记录')
    showCompleteModal.value = false
    await loadList()
  } catch (e: any) {
    message.error(`完成失败: ${e?.response?.data?.message || e?.message || '未知错误'}`)
  }
}

async function handleDownload(bid: string) {
  try {
    const blob = await downloadBackgroundCheckReport(props.offerId, bid)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bg-check-${bid}.pdf`
    a.click()
    URL.revokeObjectURL(url)
    message.success('报告已下载')
  } catch (e: any) {
    message.error(`下载失败: ${e?.response?.data?.message || e?.message || '未知错误'}`)
  }
}

const columns: DataTableColumns<BackgroundCheck> = [
  { title: '背调类型', key: 'checkType', width: 120 },
  {
    title: '供应商', key: 'supplier', width: 120,
    render: (row) => row.supplier || '-',
  },
  {
    title: '等级', key: 'level', width: 120,
    render: (row) => {
      if (!row.level) return h(NTag, { type: 'default' }, () => '未完成')
      return h(NTag, { type: BG_CHECK_LEVEL_COLOR[row.level] as any || 'default' }, () => BG_CHECK_LEVEL_LABEL[row.level] || row.level)
    },
  },
  {
    title: '评分', key: 'score', width: 80,
    render: (row) => row.score ?? '-',
  },
  {
    title: '完成时间', key: 'completedAt', width: 160,
    render: (row) => row.completedAt ? new Date(row.completedAt).toLocaleString() : '-',
  },
  {
    title: '操作', key: 'actions', width: 280, fixed: 'right',
    render: (row) => {
      return h(NSpace, { size: 'small' }, () => [
        h(NButton, {
          size: 'small', type: 'primary', ghost: true,
          disabled: !!row.level,
          onClick: () => openComplete(row.id),
        }, () => row.level ? '已完成' : '完成'),
        h(NButton, {
          size: 'small', type: 'info', ghost: true,
          disabled: !row.level,
          onClick: () => handleDownload(row.id),
        }, () => '下载报告'),
      ])
    },
  },
]

onMounted(loadList)
</script>

<template>
  <n-card title="背调记录" :bordered="false">
    <template #header-extra>
      <n-button type="primary" size="small" @click="openCreate">
        新建背调
      </n-button>
    </template>
    <n-spin :show="loading">
      <n-empty v-if="!loading && list.length === 0" description="暂无背调记录" />
      <n-data-table
        v-else
        :columns="columns"
        :data="list"
        :bordered="false"
        :single-line="false"
        size="small"
      />
    </n-spin>

    <!-- 新建背调弹窗 -->
    <n-modal v-model:show="showCreateModal" preset="dialog" title="新建背调" positive-text="创建" negative-text="取消" @positive-click="handleCreate">
      <n-form label-placement="top" style="margin-top: 12px;">
        <n-form-item label="背调类型" required>
          <n-input v-model:value="createForm.checkType" placeholder="如: 学历 / 工作履历 / 信用" />
        </n-form-item>
        <n-form-item label="供应商">
          <n-input v-model:value="createForm.supplier" placeholder="可选项, 如: 内部 / 第三方" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="createForm.note" type="textarea" :rows="2" />
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- 完成背调弹窗 -->
    <n-modal v-model:show="showCompleteModal" preset="dialog" title="完成背调 - 选择等级" positive-text="提交" negative-text="取消" @positive-click="handleComplete">
      <n-form label-placement="top" style="margin-top: 12px;">
        <n-form-item label="等级 (4 选 1)" required>
          <n-select
            v-model:value="completeForm.level"
            :options="levelOptions"
            placeholder="请选择背调结果等级"
          />
        </n-form-item>
        <n-form-item label="风险项 (JSON 数组)">
          <n-input
            v-model:value="completeForm.risks"
            type="textarea"
            :rows="3"
            placeholder='[{"category":"学历","severity":"LOW","description":"..."}]'
          />
        </n-form-item>
      </n-form>
    </n-modal>
  </n-card>
</template>
