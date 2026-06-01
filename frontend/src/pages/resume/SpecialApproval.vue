<template>
  <div class="special-approval-container">
    <a-card title="特殊简历审批">
      <template #extra>
        <a-space>
          <a-button @click="loadFlows">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
        </a-space>
      </template>

      <a-table
        :columns="columns"
        :dataSource="approvalFlows"
        :loading="loading"
        row-key="id"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>
          <template v-if="column.key === 'progress'">
            {{ getProgress(record) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleViewDetail(record)">
                查看
              </a-button>
              <a-button
                v-if="canApprove(record)"
                type="link"
                size="small"
                @click="handleApprove(record)"
              >
                审批
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 审批详情弹窗 -->
    <a-modal
      v-model:open="detailVisible"
      title="审批详情"
      :footer="null"
      width="600"
    >
      <template v-if="currentFlow">
        <a-descriptions :column="2" bordered>
          <a-descriptions-item label="简历">
            {{ currentFlow.resume?.candidate?.name || '未知' }}
          </a-descriptions-item>
          <a-descriptions-item label="目标职位">
            {{ currentFlow.position?.name || '未知' }}
          </a-descriptions-item>
          <a-descriptions-item label="当前状态">
            <a-tag :color="getStatusColor(currentFlow.status)">
              {{ getStatusText(currentFlow.status) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="发起时间">
            {{ formatDate(currentFlow.createdAt) }}
          </a-descriptions-item>
        </a-descriptions>

        <a-divider>审批进度</a-divider>

        <a-timeline>
          <a-timeline-item
            v-for="(node, index) in getNodes(currentFlow)"
            :key="index"
            :color="getNodeColor(node.status)"
          >
            <p><strong>{{ node.nodeName }}</strong></p>
            <p v-if="node.approverName">{{ node.approverName }}</p>
            <p v-if="node.comment">{{ node.comment }}</p>
            <p class="node-time" v-if="node.decidedAt">{{ formatDate(node.decidedAt) }}</p>
            <p v-else-if="node.status === 'PENDING'" class="node-pending">待审批</p>
          </a-timeline-item>
        </a-timeline>
      </template>
    </a-modal>

    <!-- 审批操作弹窗 -->
    <a-modal
      v-model:open="approveVisible"
      title="审批操作"
      @ok="handleSubmitApproval"
      :confirmLoading="submitting"
    >
      <a-form :model="approveForm" layout="vertical">
        <a-form-item label="审批意见" required>
          <a-textarea
            v-model:value="approveForm.comment"
            placeholder="请输入审批意见"
            :rows="4"
          />
        </a-form-item>
        <a-form-item label="操作">
          <a-radio-group v-model:value="approveForm.action">
            <a-radio value="APPROVED">通过</a-radio>
            <a-radio value="REJECTED">驳回</a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { get, post } from '../../api/auth'

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
  { title: '简历', dataIndex: ['resume', 'candidate', 'name'], key: 'resume' },
  { title: '目标职位', dataIndex: ['position', 'name'], key: 'position' },
  { title: '状态', key: 'status' },
  { title: '进度', key: 'progress' },
  { title: '发起时间', dataIndex: 'createdAt', key: 'createdAt' },
  { title: '操作', key: 'action', width: 150 }
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
    return
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

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    'PENDING': 'blue',
    'APPROVED': 'green',
    'REJECTED': 'red',
    'CANCELLED': 'gray'
  }
  return colors[status] || 'default'
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

const getNodeColor = (status: string) => {
  if (status === 'APPROVED') return 'green'
  if (status === 'REJECTED') return 'red'
  if (status === 'PENDING') return 'blue'
  return 'gray'
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