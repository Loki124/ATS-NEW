<template>
  <div class="page-container">
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center">
      <h1 class="page-title">招聘需求</h1>
      <a-button type="primary" @click="handleCreate">
        <template #icon><PlusOutlined /></template>
        创建需求
      </a-button>
    </div>
    
    <a-card>
      <a-table
        :columns="columns"
        :dataSource="demands"
        row-key="id"
        :pagination="{ pageSize: 10 }"
      />
    </a-card>

    <!-- 创建/编辑需求弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="selectedDemand ? '编辑需求' : '创建需求'"
      @ok="handleSave"
      @cancel="modalVisible = false"
      :width="800"
      ok-text="保存"
      cancel-text="取消"
    >
      <a-form :form="form" layout="vertical">
        <a-divider orientation="left">基本信息</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="name" label="需求名称" :rules="[{ required: true, message: '请输入需求名称' }]">
              <a-input v-model:value="formState.name" placeholder="请输入需求名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item name="demandType" label="需求类型" :rules="[{ required: true, message: '请选择需求类型' }]">
              <a-select v-model:value="formState.demandType" placeholder="请选择">
                <a-select-option value="新增">新增</a-select-option>
                <a-select-option value="替补">替补</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="department" label="所属部门" :rules="[{ required: true, message: '请选择部门' }]">
              <a-select v-model:value="formState.department" placeholder="请选择部门">
                <a-select-option value="技术部">技术部</a-select-option>
                <a-select-option value="产品部">产品部</a-select-option>
                <a-select-option value="设计部">设计部</a-select-option>
                <a-select-option value="销售部">销售部</a-select-option>
                <a-select-option value="人事部">人事部</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item name="position" label="职位" :rules="[{ required: true, message: '请选择职位' }]">
              <a-select v-model:value="formState.position" placeholder="请选择职位">
                <a-select-option value="前端开发">前端开发</a-select-option>
                <a-select-option value="后端开发">后端开发</a-select-option>
                <a-select-option value="产品经理">产品经理</a-select-option>
                <a-select-option value="UI设计">UI设计</a-select-option>
                <a-select-option value="销售专员">销售专员</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="count" label="需求人数" :rules="[{ required: true, message: '请输入需求人数' }]">
              <a-input-number v-model:value="formState.count" :min="1" :max="100" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item name="salaryRange" label="薪资范围" :rules="[{ required: true, message: '请选择薪资范围' }]">
              <a-select v-model:value="formState.salaryRange" placeholder="请选择">
                <a-select-option value="8K-12K">8K-12K</a-select-option>
                <a-select-option value="12K-18K">12K-18K</a-select-option>
                <a-select-option value="15K-25K">15K-25K</a-select-option>
                <a-select-option value="20K-35K">20K-35K</a-select-option>
                <a-select-option value="30K-50K">30K-50K</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="deadline" label="需求截止日期">
              <a-date-picker v-model:value="formState.deadline" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">人员配置</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="hrbp" label="HRBP" :rules="[{ required: true, message: '请选择HRBP' }]">
              <a-select v-model:value="formState.hrbp" placeholder="请选择HRBP">
                <a-select-option value="张三">张三</a-select-option>
                <a-select-option value="赵六">赵六</a-select-option>
                <a-select-option value="钱九">钱九</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item name="hiringManager" label="用人经理" :rules="[{ required: true, message: '请选择用人经理' }]">
              <a-select v-model:value="formState.hiringManager" mode="multiple" placeholder="请选择用人经理">
                <a-select-option value="李四">李四</a-select-option>
                <a-select-option value="孙七">孙七</a-select-option>
                <a-select-option value="郑十">郑十</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="demandOwner" label="需求负责人" :rules="[{ required: true, message: '请选择需求负责人' }]">
              <a-select v-model:value="formState.demandOwner" placeholder="请选择">
                <a-select-option value="王五">王五</a-select-option>
                <a-select-option value="周八">周八</a-select-option>
                <a-select-option value="吴一">吴一</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">需求详情</a-divider>
        <a-form-item name="description" label="需求描述">
          <a-textarea v-model:value="formState.description" :rows="4" placeholder="请输入需求描述和职位要求" />
        </a-form-item>

        <a-form-item name="jd" label="职位JD">
          <a-upload :before-upload="() => false" :max-count="1">
            <a-button>上传职位JD文件</a-button>
          </a-upload>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 需求详情弹窗 -->
    <a-modal
      v-model:open="detailVisible"
      title="需求详情"
      @cancel="detailVisible = false"
      :footer="null"
      :width="700"
    >
      <template v-if="selectedDemand">
        <a-row :gutter="[16, 16]">
          <a-col :span="12"><strong>需求编号：</strong>{{ selectedDemand.code }}</a-col>
          <a-col :span="12"><strong>需求名称：</strong>{{ selectedDemand.name }}</a-col>
          <a-col :span="12"><strong>所属部门：</strong>{{ selectedDemand.department }}</a-col>
          <a-col :span="12"><strong>需求人数：</strong>{{ selectedDemand.count }}人</a-col>
          <a-col :span="12"><strong>需求类型：</strong>{{ selectedDemand.demandType }}</a-col>
          <a-col :span="12"><strong>薪资范围：</strong>{{ selectedDemand.salaryRange }}</a-col>
          <a-col :span="12"><strong>需求状态：</strong><a-tag :color="getStatusColor(selectedDemand.status)">{{ selectedDemand.status }}</a-tag></a-col>
          <a-col :span="12"><strong>审批状态：</strong><a-tag :color="getApprovalStatusColor(selectedDemand.approvalStatus)">{{ selectedDemand.approvalStatus }}</a-tag></a-col>
          <a-col :span="12"><strong>截止日期：</strong>{{ selectedDemand.deadline }}</a-col>
          <a-col :span="12"><strong>创建时间：</strong>{{ selectedDemand.createdAt }}</a-col>
        </a-row>
        <a-divider />
        <a-row :gutter="[16, 16]">
          <a-col :span="12"><strong>HRBP：</strong>{{ selectedDemand.hrbp }}</a-col>
          <a-col :span="12"><strong>需求负责人：</strong>{{ selectedDemand.demandOwner }}</a-col>
          <a-col :span="24"><strong>用人经理：</strong>{{ selectedDemand.hiringManager }}</a-col>
        </a-row>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, h } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons-vue'

interface Demand {
  id: string
  code: string
  name: string
  department: string
  count: number
  status: string
  approvalStatus: string
  createdAt: string
  demandType: string
  position: string
  salaryRange: string
  deadline: string
  hrbp: string
  hiringManager: string
  demandOwner: string
}

const modalVisible = ref(false)
const detailVisible = ref(false)
const selectedDemand = ref<Demand | null>(null)

const formState = reactive<{
  name: string
  demandType: string
  department: string
  position: string
  count: number
  salaryRange: string
  deadline: string
  hrbp: string
  hiringManager: string
  demandOwner: string
  description: string
}>({
  name: '',
  demandType: '',
  department: '',
  position: '',
  count: 1,
  salaryRange: '',
  deadline: '',
  hrbp: '',
  hiringManager: [],
  demandOwner: '',
  description: ''
})

const demands = ref<Demand[]>([
  {
    id: '1',
    code: 'HC001',
    name: '前端开发工程师',
    department: '技术部',
    count: 2,
    status: '进行中',
    approvalStatus: '已通过',
    createdAt: '2024-01-15',
    demandType: '新增',
    position: '前端开发',
    salaryRange: '15K-25K',
    deadline: '2024-03-31',
    hrbp: '张三',
    hiringManager: '李四',
    demandOwner: '王五',
  },
  {
    id: '2',
    code: 'HC002',
    name: '产品经理',
    department: '产品部',
    count: 1,
    status: '进行中',
    approvalStatus: '审批中',
    createdAt: '2024-01-20',
    demandType: '替补',
    position: '产品经理',
    salaryRange: '20K-35K',
    deadline: '2024-04-15',
    hrbp: '赵六',
    hiringManager: '孙七',
    demandOwner: '周八',
  },
  {
    id: '3',
    code: 'HC003',
    name: 'UI设计师',
    department: '设计部',
    count: 1,
    status: '已完成',
    approvalStatus: '已通过',
    createdAt: '2024-01-10',
    demandType: '新增',
    position: 'UI设计',
    salaryRange: '12K-20K',
    deadline: '2024-02-28',
    hrbp: '钱九',
    hiringManager: '郑十',
    demandOwner: '吴一',
  },
])

const handleCreate = () => {
  selectedDemand.value = null
  Object.assign(formState, {
    name: '',
    demandType: '',
    department: '',
    position: '',
    count: 1,
    salaryRange: '',
    deadline: '',
    hrbp: '',
    hiringManager: [],
    demandOwner: '',
    description: ''
  })
  modalVisible.value = true
}

const handleEdit = (record: Demand) => {
  selectedDemand.value = record
  Object.assign(formState, record)
  modalVisible.value = true
}

const handleView = (record: Demand) => {
  selectedDemand.value = record
  detailVisible.value = true
}

const handleSave = () => {
  if (selectedDemand.value) {
    const index = demands.value.findIndex(d => d.id === selectedDemand.value!.id)
    if (index !== -1) {
      demands.value[index] = { ...demands.value[index], ...formState }
    }
    message.success('需求更新成功')
  } else {
    const newDemand: Demand = {
      id: Date.now().toString(),
      code: `HC00${demands.value.length + 1}`,
      ...formState,
      status: '草稿',
      approvalStatus: '未发起',
      createdAt: new Date().toISOString().split('T')[0],
    }
    demands.value.push(newDemand)
    message.success('需求创建成功')
  }
  modalVisible.value = false
}

const handleSubmitApproval = (record: Demand) => {
  const index = demands.value.findIndex(d => d.id === record.id)
  if (index !== -1) {
    demands.value[index] = { ...demands.value[index], approvalStatus: '审批中', status: '进行中' }
  }
  message.success('已提交审批')
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    '草稿': 'default',
    '进行中': 'processing',
    '已完成': 'success',
    '已暂停': 'warning',
    '已停招': 'error',
    '已超期': 'orange',
  }
  return colors[status] || 'default'
}

const getApprovalStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    '未发起': 'default',
    '审批中': 'processing',
    '已通过': 'success',
    '已拒绝': 'error',
    '已撤销': 'warning',
  }
  return colors[status] || 'default'
}

const columns = [
  { title: '需求编号', dataIndex: 'code', key: 'code', width: 100 },
  { title: '需求名称', dataIndex: 'name', key: 'name' },
  { title: '所属部门', dataIndex: 'department', key: 'department', width: 100 },
  { title: '需求人数', dataIndex: 'count', key: 'count', width: 90 },
  { title: '需求类型', dataIndex: 'demandType', key: 'demandType', width: 90,
    customRender: ({ text }: { text: string }) => h('a-tag', { color: text === '新增' ? 'blue' : 'green' }, text)
  },
  { title: '薪资范围', dataIndex: 'salaryRange', key: 'salaryRange', width: 110 },
  { title: '需求状态', dataIndex: 'status', key: 'status', width: 90,
    customRender: ({ text }: { text: string }) => h('a-tag', { color: getStatusColor(text) }, text)
  },
  { title: '审批状态', dataIndex: 'approvalStatus', key: 'approvalStatus', width: 90,
    customRender: ({ text }: { text: string }) => h('a-tag', { color: getApprovalStatusColor(text) }, text)
  },
  { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 110 },
  { title: '操作', key: 'action', width: 180,
    customRender: ({ record }: { record: Demand }) => {
      return h('span', {}, [
        h('a-button', { type: 'link', size: 'small', onClick: () => handleView(record) }, { default: () => '查看' }),
        h('a-button', { type: 'link', size: 'small', onClick: () => handleEdit(record) }, { default: () => '编辑' }),
        record.approvalStatus !== '已通过' && h('a-button', { type: 'link', size: 'small', onClick: () => handleSubmitApproval(record) }, { default: () => '提交审批' })
      ])
    }
  },
]
</script>

<style scoped>
.page-container {
  padding: 24px;
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}
</style>