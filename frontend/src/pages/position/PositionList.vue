<template>
  <div class="page-container">
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <h1 class="page-title">职位管理</h1>
      <n-button type="primary" @click="handleCreate">
        <template #icon><n-icon :component="AddOutline" /></template>
        创建职位
      </n-button>
    </div>

    <n-card>
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="all" tab="全部职位">
          <n-data-table :columns="columns" :data="positions" :pagination="{ pageSize: 10 }" :row-key="(row: Position) => row.id" />
        </n-tab-pane>
        <n-tab-pane name="recruiting" tab="招聘中">
          <n-data-table :columns="columns" :data="positions.filter(p => p.status === '招聘中')" :pagination="{ pageSize: 10 }" :row-key="(row: Position) => row.id" />
        </n-tab-pane>
        <n-tab-pane name="stopped" tab="已停招">
          <n-data-table :columns="columns" :data="positions.filter(p => p.status === '已停招')" :pagination="{ pageSize: 10 }" :row-key="(row: Position) => row.id" />
        </n-tab-pane>
        <n-tab-pane name="completed" tab="已完成">
          <n-data-table :columns="columns" :data="positions.filter(p => p.status === '已完成')" :pagination="{ pageSize: 10 }" :row-key="(row: Position) => row.id" />
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 创建/编辑职位弹窗 -->
    <n-modal
      v-model:show="modalVisible"
      preset="card"
      :title="selectedPosition ? '编辑职位' : '创建职位'"
      style="width: 800px"
    >
      <n-divider title-placement="left">基本信息</n-divider>
      <n-form ref="formRef" :model="formState" label-placement="top">
        <div class="grid grid-cols-2 gap-x-4">
          <n-form-item path="name" label="职位名称" :rule="{ required: true, message: '请输入职位名称', trigger: 'blur' }">
            <n-input v-model:value="formState.name" placeholder="请输入职位名称" />
          </n-form-item>
          <n-form-item path="department" label="所属部门" :rule="{ required: true, message: '请选择部门', trigger: 'change' }">
            <n-select v-model:value="formState.department" placeholder="请选择部门" :options="departmentOptions" />
          </n-form-item>

          <n-form-item path="demandCode" label="关联需求" :rule="{ required: true, message: '请选择关联需求', trigger: 'change' }">
            <n-select v-model:value="formState.demandCode" placeholder="请选择需求" :options="demandOptions" />
          </n-form-item>
          <n-form-item path="recruitmentProcess" label="招聘流程" :rule="{ required: true, message: '请选择招聘流程', trigger: 'change' }">
            <n-select v-model:value="formState.recruitmentProcess" placeholder="请选择流程" :options="processOptions" />
          </n-form-item>

          <n-form-item path="priority" label="优先级" :rule="{ required: true, message: '请选择优先级', trigger: 'change' }">
            <n-select v-model:value="formState.priority" placeholder="请选择" :options="priorityOptions" />
          </n-form-item>
          <n-form-item path="headCount" label="需求人数" :rule="{ required: true, type: 'number', message: '请输入需求人数', trigger: 'blur' }">
            <n-input-number v-model:value="formState.headCount" :min="1" :max="100" style="width: 100%;" />
          </n-form-item>

          <n-form-item path="salaryRange" label="薪资范围">
            <n-select v-model:value="formState.salaryRange" placeholder="请选择" :options="salaryOptions" />
          </n-form-item>
          <n-form-item path="location" label="工作地点">
            <n-input v-model:value="formState.location" placeholder="请输入工作地点" />
          </n-form-item>
        </div>

        <n-divider title-placement="left">人员配置</n-divider>
        <div class="grid grid-cols-2 gap-x-4">
          <n-form-item path="positionOwner" label="职位负责人" :rule="{ required: true, message: '请选择职位负责人', trigger: 'change' }">
            <n-select v-model:value="formState.positionOwner" placeholder="请选择" :options="ownerOptions" />
          </n-form-item>
          <n-form-item path="hiringManager" label="用人经理" :rule="{ required: true, type: 'array', message: '请选择用人经理', trigger: 'change' }">
            <n-select v-model:value="formState.hiringManager" placeholder="请选择" multiple :options="managerOptions" />
          </n-form-item>
        </div>

        <n-divider title-placement="left">职位详情</n-divider>
        <n-form-item path="description" label="职位描述">
          <n-input v-model:value="formState.description" type="textarea" :rows="4" placeholder="请输入职位描述和任职要求" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <n-button @click="modalVisible = false">取消</n-button>
          <n-button type="primary" @click="handleSave">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 职位详情弹窗 -->
    <n-modal
      v-model:show="detailVisible"
      preset="card"
      title="职位详情"
      style="width: 700px"
    >
      <template v-if="selectedPosition">
        <div class="grid grid-cols-2 gap-4">
          <div><strong>职位编号：</strong>{{ selectedPosition.code }}</div>
          <div><strong>职位名称：</strong>{{ selectedPosition.name }}</div>
          <div><strong>所属部门：</strong>{{ selectedPosition.department }}</div>
          <div><strong>关联需求：</strong>{{ selectedPosition.demandCode }}</div>
          <div><strong>招聘流程：</strong>{{ selectedPosition.recruitmentProcess }}</div>
          <div><strong>优先级：</strong><n-tag :type="getPriorityType(selectedPosition.priority)">{{ selectedPosition.priority }}</n-tag></div>
          <div><strong>职位状态：</strong><n-tag :type="getStatusType(selectedPosition.status)">{{ selectedPosition.status }}</n-tag></div>
          <div><strong>需求人数：</strong>{{ selectedPosition.headCount }}人</div>
          <div><strong>已入职：</strong>{{ selectedPosition.hiredCount }}人</div>
          <div><strong>薪资范围：</strong>{{ selectedPosition.salaryRange }}</div>
          <div><strong>工作地点：</strong>{{ selectedPosition.location }}</div>
          <div><strong>创建时间：</strong>{{ selectedPosition.createdAt }}</div>
        </div>
        <n-divider />
        <div class="grid grid-cols-2 gap-4">
          <div><strong>职位负责人：</strong>{{ selectedPosition.positionOwner }}</div>
          <div class="col-span-2"><strong>用人经理：</strong>{{ selectedPosition.hiringManager }}</div>
        </div>
        <n-divider />
        <div>
          <strong>职位描述：</strong>
          <p>{{ selectedPosition.description }}</p>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h } from 'vue';
import { useMessage, NTag, NButton, NSpace } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5';

interface Position {
  id: string;
  code: string;
  name: string;
  department: string;
  demandCode: string;
  recruitmentProcess: string;
  priority: string;
  status: string;
  headCount: number;
  hiredCount: number;
  createdAt: string;
  positionOwner: string;
  hiringManager: string;
  salaryRange: string;
  location: string;
  description: string;
}

const message = useMessage()

const activeTab = ref('all');
const modalVisible = ref(false);
const detailVisible = ref(false);
const selectedPosition = ref<Position | null>(null);
const formRef = ref();

const defaultFormState = {
  name: '',
  department: undefined,
  demandCode: undefined,
  recruitmentProcess: undefined,
  priority: undefined,
  headCount: 1,
  salaryRange: undefined,
  location: '',
  positionOwner: undefined,
  hiringManager: [],
  description: ''
};

const formState = reactive<any>({ ...defaultFormState });

const departmentOptions = [
  { label: '技术部', value: '技术部' },
  { label: '产品部', value: '产品部' },
  { label: '设计部', value: '设计部' },
  { label: '销售部', value: '销售部' },
  { label: '人事部', value: '人事部' }
]

const demandOptions = [
  { label: 'HC001 - 前端开发工程师', value: 'HC001' },
  { label: 'HC002 - 产品经理', value: 'HC002' },
  { label: 'HC003 - UI设计师', value: 'HC003' }
]

const processOptions = [
  { label: '社会招聘流程', value: '社会招聘流程' },
  { label: '校园招聘流程', value: '校园招聘流程' },
  { label: '实习生招聘流程', value: '实习生招聘流程' }
]

const priorityOptions = [
  { label: '高', value: '高' },
  { label: '中', value: '中' },
  { label: '低', value: '低' }
]

const salaryOptions = [
  { label: '8K-12K', value: '8K-12K' },
  { label: '12K-18K', value: '12K-18K' },
  { label: '15K-25K', value: '15K-25K' },
  { label: '20K-35K', value: '20K-35K' },
  { label: '30K-50K', value: '30K-50K' }
]

const ownerOptions = [
  { label: '王五', value: '王五' },
  { label: '周八', value: '周八' },
  { label: '吴一', value: '吴一' }
]

const managerOptions = [
  { label: '李四', value: '李四' },
  { label: '孙七', value: '孙七' },
  { label: '郑十', value: '郑十' }
]

const positions = ref<Position[]>([
  {
    id: '1',
    code: 'POS001',
    name: '高级前端开发工程师',
    department: '技术部',
    demandCode: 'HC001',
    recruitmentProcess: '社会招聘流程',
    priority: '高',
    status: '招聘中',
    headCount: 2,
    hiredCount: 0,
    createdAt: '2024-01-15',
    positionOwner: '王五',
    hiringManager: '李四',
    salaryRange: '18K-30K',
    location: '上海市',
    description: '负责公司前端技术开发',
  },
  {
    id: '2',
    code: 'POS002',
    name: '产品经理',
    department: '产品部',
    demandCode: 'HC002',
    recruitmentProcess: '社会招聘流程',
    priority: '中',
    status: '招聘中',
    headCount: 1,
    hiredCount: 0,
    createdAt: '2024-01-20',
    positionOwner: '周八',
    hiringManager: '孙七',
    salaryRange: '20K-35K',
    location: '上海市',
    description: '负责产品规划和设计',
  },
  {
    id: '3',
    code: 'POS003',
    name: 'UI设计师',
    department: '设计部',
    demandCode: 'HC003',
    recruitmentProcess: '社会招聘流程',
    priority: '低',
    status: '已完成',
    headCount: 1,
    hiredCount: 1,
    createdAt: '2024-01-10',
    positionOwner: '吴一',
    hiringManager: '郑十',
    salaryRange: '12K-20K',
    location: '深圳市',
    description: '负责产品UI设计',
  },
]);

const getStatusType = (status: string): 'success' | 'error' | 'info' | 'default' => {
  const colors: Record<string, 'success' | 'error' | 'info' | 'default'> = {
    '招聘中': 'success',
    '已停招': 'error',
    '已完成': 'info',
  };
  return colors[status] || 'default';
};

const getPriorityType = (priority: string): 'error' | 'warning' | 'success' | 'default' => {
  const colors: Record<string, 'error' | 'warning' | 'success' | 'default'> = {
    '高': 'error',
    '中': 'warning',
    '低': 'success',
  };
  return colors[priority] || 'default';
};

const handleCreate = () => {
  selectedPosition.value = null;
  Object.assign(formState, defaultFormState);
  modalVisible.value = true;
};

const handleEdit = (record: Position) => {
  selectedPosition.value = record;
  Object.assign(formState, {
    name: record.name,
    department: record.department,
    demandCode: record.demandCode,
    recruitmentProcess: record.recruitmentProcess,
    priority: record.priority,
    headCount: record.headCount,
    salaryRange: record.salaryRange,
    location: record.location,
    positionOwner: record.positionOwner,
    hiringManager: record.hiringManager,
    description: record.description
  });
  modalVisible.value = true;
};

const handleView = (record: Position) => {
  selectedPosition.value = record;
  detailVisible.value = true;
};

const handleSave = async () => {
  try {
    await formRef.value?.validate()
    if (selectedPosition.value) {
      const index = positions.value.findIndex(p => p.id === selectedPosition.value!.id);
      if (index !== -1) {
        positions.value[index] = { ...positions.value[index], ...formState };
      }
      message.success('职位更新成功');
    } else {
      const newPosition: Position = {
        id: Date.now().toString(),
        code: `POS00${positions.value.length + 1}`,
        status: '招聘中',
        hiredCount: 0,
        createdAt: new Date().toISOString().split('T')[0],
        ...formState
      };
      positions.value.push(newPosition);
      message.success('职位创建成功');
    }
    modalVisible.value = false;
  } catch (error) {
    console.error('验证失败:', error);
  }
};

const handleToggleStatus = (record: Position) => {
  const index = positions.value.findIndex(p => p.id === record.id);
  if (index !== -1) {
    const currentStatus = positions.value[index].status;
    positions.value[index].status = currentStatus === '招聘中' ? '已停招' : '招聘中';
    message.success(`职位已${currentStatus === '招聘中' ? '停招' : '开启招聘'}`);
  }
};

const columns = computed(() => [
  { title: '职位编号', key: 'code', width: 100 },
  { title: '职位名称', key: 'name', width: 180, ellipsis: { tooltip: true } },
  { title: '所属部门', key: 'department', width: 100 },
  { title: '关联需求', key: 'demandCode', width: 100 },
  { title: '招聘流程', key: 'recruitmentProcess', width: 120 },
  {
    title: '优先级',
    key: 'priority',
    width: 80,
    render: (row: Position) => h(NTag, { type: getPriorityType(row.priority) }, { default: () => row.priority })
  },
  {
    title: '职位状态',
    key: 'status',
    width: 90,
    render: (row: Position) => h(NTag, { type: getStatusType(row.status) }, { default: () => row.status })
  },
  {
    title: '需求/已入职',
    key: 'headCount',
    width: 110,
    render: (row: Position) => `${row.headCount}/${row.hiredCount}`
  },
  { title: '创建时间', key: 'createdAt', width: 110 },
  {
    title: '操作',
    key: 'action',
    width: 200,
    render: (row: Position) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleView(row) }, { default: () => '查看' }),
      h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleEdit(row) }, { default: () => '编辑' }),
      h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleToggleStatus(row) }, { default: () =>
        row.status === '招聘中' ? '停招' : '开启'
      })
    ])
  },
]);
</script>

<style scoped>
.page-container {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 500;
}
</style>
