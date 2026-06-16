<template>
  <div class="special-approval-container">
    <n-card title="特殊简历审批">
      <template #header-extra>
        <n-space>
          <n-button @click="loadFlows">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
        </n-space>
      </template>

      <n-data-table
        :columns="columns"
        :data="approvalFlows"
        :loading="loading"
        :row-key="(row: any) => row.id"
        :pagination="{ pageSize: 10 }"
      />
    </n-card>

    <!-- 审批详情弹窗 -->
    <n-modal
      v-model:show="detailVisible"
      preset="card"
      title="审批详情"
      style="width: 600px"
    >
      <template v-if="currentFlow">
        <n-descriptions :column="2" bordered>
          <n-descriptions-item label="简历">
            {{ currentFlow.resume?.candidate?.name || '未知' }}
          </n-descriptions-item>
          <n-descriptions-item label="目标职位">
            {{ currentFlow.position?.name || '未知' }}
          </n-descriptions-item>
          <n-descriptions-item label="当前状态">
            <n-tag :type="getStatusType(currentFlow.status)">
              {{ getStatusText(currentFlow.status) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="发起时间">
            {{ formatDate(currentFlow.createdAt) }}
          </n-descriptions-item>
        </n-descriptions>

        <n-divider>审批进度</n-divider>

        <n-timeline>
          <n-timeline-item
            v-for="(node, index) in getNodes(currentFlow)"
            :key="index"
            :type="getNodeType(node.status)"
          >
            <p><strong>{{ node.nodeName }}</strong></p>
            <p v-if="node.approverName">{{ node.approverName }}</p>
            <p v-if="node.comment">{{ node.comment }}</p>
            <p class="node-time" v-if="node.decidedAt">{{ formatDate(node.decidedAt) }}</p>
            <p v-else-if="node.status === 'PENDING'" class="node-pending">待审批</p>
          </n-timeline-item>
        </n-timeline>
      </template>
    </n-modal>

    <!-- 审批操作弹窗 -->
    <n-modal
      v-model:show="approveVisible"
      preset="dialog"
      title="审批操作"
      positive-text="确定"
      negative-text="取消"
      :loading="submitting"
      @positive-click="handleSubmitApproval"
    >
      <n-form :model="approveForm" label-placement="top" class="mt-4">
        <n-form-item label="审批意见" required>
          <n-input
            v-model:value="approveForm.comment"
            type="textarea"
            placeholder="请输入审批意见"
            :rows="4"
          />
        </n-form-item>
        <n-form-item label="操作">
          <n-radio-group v-model:value="approveForm.action">
            <n-radio value="APPROVED">通过</n-radio>
            <n-radio value="REJECTED">驳回</n-radio>
          </n-radio-group>
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage, NTag, NButton, NSpace } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { get, post } from '../../api/auth'

const message = useMessage()

const loading = ref(false)
const approvalFlows = ref<any[]>([])
const detailVisible = ref(false)
const currentFlow = ref<any>(null)
const approveVisible = ref(false)
const submitting = ref(false)

const approveForm = reactive({
  flowId: '',
  action: 'APPROVED',
  comment: ''
})

const columns = [
  {
    title: '简历',
    key: 'resume',
    render: (row: any) => row.resume?.candidate?.name || '-'
  },
  {
    title: '目标职位',
    key: 'position',
    render: (row: any) => row.position?.name || '-'
  },
  {
    title: '状态',
    key: 'status',
    render: (row: any) => h(NTag, { type: getStatusType(row.status) }, { default: () => getStatusText(row.status) })
  },
  {
    title: '进度',
    key: 'progress',
    render: (row: any) => getProgress(row)
  },
  {
    title: '发起时间',
    key: 'createdAt'
  },
  {
    title: '操作',
    key: 'action',
    width: 150,
    render: (row: any) => h(NSpace, {}, () => {
      const actions = [
        h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleViewDetail(row) }, { default: () => '查看' })
      ]
      if (canApprove(row)) {
        actions.push(
          h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleApprove(row) }, { default: () => '审批' })
        )
      }
      return actions
    })
  }
]

const loadFlows = async () => {
  loading.value = true
  try {
    const res = await get('/resumes/approval-flows')
    if (res.data.success) {
      approvalFlows.value = res.data.data
    }
  } catch (error) {
    console.error('加载审批流程失败', error)
  } finally {
    loading.value = false
  }
}

const handleViewDetail = async (flow: any) => {
  currentFlow.value = flow
  detailVisible.value = true
}

const canApprove = (flow: any) => {
  if (flow.status !== 'PENDING') return false
  const nodes = JSON.parse(flow.nodes || '[]')
  const currentNode = nodes.find((n: any) => n.nodeId === flow.currentNodeId)
  if (!currentNode) return false
  // 当前用户是否是当前节点的审批人
  return currentNode.approverId === localStorage.getItem('userId')
}

const handleApprove = (flow: any) => {
  approveForm.flowId = flow.id
  approveForm.action = 'APPROVED'
  approveForm.comment = ''
  approveVisible.value = true
}

const handleSubmitApproval = async () => {
  if (!approveForm.comment.trim()) {
    message.warning('请输入审批意见')
    return false
  }

  submitting.value = true
  try {
    const res = await post(`/resumes/approval-flows/${approveForm.flowId}/approve`, {
      action: approveForm.action,
      comment: approveForm.comment,
      approverId: localStorage.getItem('userId')
    })

    if (res.data.success) {
      message.success(res.data.data.status === 'APPROVED' ? '审批通过' : '审批已驳回')
      approveVisible.value = false
      loadFlows()
    } else {
      message.error(res.data.message || '审批失败')
    }
  } catch (error: any) {
    message.error(error?.response?.data?.message || '审批失败')
  } finally {
    submitting.value = false
  }
}

const getStatusType = (status: string): 'info' | 'success' | 'error' | 'default' => {
  const map: Record<string, 'info' | 'success' | 'error' | 'default'> = {
    'PENDING': 'info',
    'APPROVED': 'success',
    'REJECTED': 'error',
    'CANCELLED': 'default'
  }
  return map[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'PENDING': '审批中',
    'APPROVED': '已通过',
    'REJECTED': '已驳回',
    'CANCELLED': '已取消'
  }
  return texts[status] || status
}

const getProgress = (flow: any) => {
  const nodes = JSON.parse(flow.nodes || '[]')
  const approved = nodes.filter((n: any) => n.status === 'APPROVED').length
  return `${approved}/${nodes.length}`
}

const getNodes = (flow: any) => {
  return JSON.parse(flow.nodes || '[]')
}

const getNodeType = (status: string): 'success' | 'error' | 'info' | 'default' => {
  if (status === 'APPROVED') return 'success'
  if (status === 'REJECTED') return 'error'
  if (status === 'PENDING') return 'info'
  return 'default'
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  loadFlows()
})
</script>

<style scoped>
.special-approval-container {
  padding: 24px;
}

.node-time {
  font-size: 12px;
  color: #999;
}

.node-pending {
  color: #1890ff;
  font-style: italic;
}
</style>
