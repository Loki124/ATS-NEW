<template>
  <div class="page-container">
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <h1 class="page-title">职位管理</h1>
      <a-button type="primary" @click="handleCreate">
        <template #icon><PlusOutlined /></template>
        创建职位
      </a-button>
    </div>
    
    <a-card>
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="all">
          <template #tab>全部职位</template>
          <a-table :columns="columns" :data-source="positions" :pagination="{ pageSize: 10 }" row-key="id" />
        </a-tab-pane>
        <a-tab-pane key="recruiting">
          <template #tab>招聘中</template>
          <a-table :columns="columns" :data-source="positions.filter(p => p.status === '招聘中')" :pagination="{ pageSize: 10 }" row-key="id" />
        </a-tab-pane>
        <a-tab-pane key="stopped">
          <template #tab>已停招</template>
          <a-table :columns="columns" :data-source="positions.filter(p => p.status === '已停招')" :pagination="{ pageSize: 10 }" row-key="id" />
        </a-tab-pane>
        <a-tab-pane key="completed">
          <template #tab>已完成</template>
          <a-table :columns="columns" :data-source="positions.filter(p => p.status === '已完成')" :pagination="{ pageSize: 10 }" row-key="id" />
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <!-- 创建/编辑职位弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="selectedPosition ? '编辑职位' : '创建职位'"
      @ok="handleSave"
      @cancel="modalVisible = false"
      width="800px"
      ok-text="保存"
      cancel-text="取消"
    >
      <a-divider orientation="left">基本信息</a-divider>
      <a-form ref="formRef" :model="formState" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="name" label="职位名称" :rules="[{ required: true, message: '请输入职位名称' }]">
              <a-input v-model:value="formState.name" placeholder="请输入职位名称" />
            </a-form-item>
          </a-col>
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
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="demandCode" label="关联需求" :rules="[{ required: true, message: '请选择关联需求' }]">
              <a-select v-model:value="formState.demandCode" placeholder="请选择需求">
                <a-select-option value="HC001">HC001 - 前端开发工程师</a-select-option>
                <a-select-option value="HC002">HC002 - 产品经理</a-select-option>
                <a-select-option value="HC003">HC003 - UI设计师</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item name="recruitmentProcess" label="招聘流程" :rules="[{ required: true, message: '请选择招聘流程' }]">
              <a-select v-model:value="formState.recruitmentProcess" placeholder="请选择流程">
                <a-select-option value="社会招聘流程">社会招聘流程</a-select-option>
                <a-select-option value="校园招聘流程">校园招聘流程</a-select-option>
                <a-select-option value="实习生招聘流程">实习生招聘流程</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="priority" label="优先级" :rules="[{ required: true, message: '请选择优先级' }]">
              <a-select v-model:value="formState.priority" placeholder="请选择">
                <a-select-option value="高">高</a-select-option>
                <a-select-option value="中">中</a-select-option>
                <a-select-option value="低">低</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item name="headCount" label="需求人数" :rules="[{ required: true, message: '请输入需求人数' }]">
              <a-input-number v-model:value="formState.headCount" :min="1" :max="100" style="width: 100%;" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="salaryRange" label="薪资范围">
              <a-select v-model:value="formState.salaryRange" placeholder="请选择">
                <a-select-option value="8K-12K">8K-12K</a-select-option>
                <a-select-option value="12K-18K">12K-18K</a-select-option>
                <a-select-option value="15K-25K">15K-25K</a-select-option>
                <a-select-option value="20K-35K">20K-35K</a-select-option>
                <a-select-option value="30K-50K">30K-50K</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item name="location" label="工作地点">
              <a-input v-model:value="formState.location" placeholder="请输入工作地点" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">人员配置</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item name="positionOwner" label="职位负责人" :rules="[{ required: true, message: '请选择职位负责人' }]">
              <a-select v-model:value="formState.positionOwner" placeholder="请选择">
                <a-select-option value="王五">王五</a-select-option>
                <a-select-option value="周八">周八</a-select-option>
                <a-select-option value="吴一">吴一</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item name="hiringManager" label="用人经理" :rules="[{ required: true, message: '请选择用人经理' }]">
              <a-select v-model:value="formState.hiringManager" placeholder="请选择" mode="multiple">
                <a-select-option value="李四">李四</a-select-option>
                <a-select-option value="孙七">孙七</a-select-option>
                <a-select-option value="郑十">郑十</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">职位详情</a-divider>
        <a-form-item name="description" label="职位描述">
          <a-textarea v-model:value="formState.description" :rows="4" placeholder="请输入职位描述和任职要求" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 职位详情弹窗 -->
    <a-modal
      v-model:open="detailVisible"
      title="职位详情"
      @cancel="detailVisible = false"
      :footer="null"
      width="700px"
    >
      <template v-if="selectedPosition">
        <a-row :gutter="[16, 16]">
          <a-col :span="12"><strong>职位编号：</strong>{{ selectedPosition.code }}</a-col>
          <a-col :span="12"><strong>职位名称：</strong>{{ selectedPosition.name }}</a-col>
          <a-col :span="12"><strong>所属部门：</strong>{{ selectedPosition.department }}</a-col>
          <a-col :span="12"><strong>关联需求：</strong>{{ selectedPosition.demandCode }}</a-col>
          <a-col :span="12"><strong>招聘流程：</strong>{{ selectedPosition.recruitmentProcess }}</a-col>
          <a-col :span="12"><strong>优先级：</strong><a-tag :color="getPriorityColor(selectedPosition.priority)">{{ selectedPosition.priority }}</a-tag></a-col>
          <a-col :span="12"><strong>职位状态：</strong><a-tag :color="getStatusColor(selectedPosition.status)">{{ selectedPosition.status }}</a-tag></a-col>
          <a-col :span="12"><strong>需求人数：</strong>{{ selectedPosition.headCount }}人</a-col>
          <a-col :span="12"><strong>已入职：</strong>{{ selectedPosition.hiredCount }}人</a-col>
          <a-col :span="12"><strong>薪资范围：</strong>{{ selectedPosition.salaryRange }}</a-col>
          <a-col :span="12"><strong>工作地点：</strong>{{ selectedPosition.location }}</a-col>
          <a-col :span="12"><strong>创建时间：</strong>{{ selectedPosition.createdAt }}</a-col>
        </a-row>
        <a-divider />
        <a-row :gutter="[16, 16]">
          <a-col :span="12"><strong>职位负责人：</strong>{{ selectedPosition.positionOwner }}</a-col>
          <a-col :span="24"><strong>用人经理：</strong>{{ selectedPosition.hiringManager }}</a-col>
        </a-row>
        <a-divider />
        <div>
          <strong>职位描述：</strong>
          <p>{{ selectedPosition.description }}</p>
        </div>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h } from 'vue';
import {
  PlusOutlined,
  EditOutlined,
  EyeOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue';
import {
  ATable,
  AButton,
  ACard,
  ASpace,
  ATag,
  AModal,
  AForm,
  AInput,
  ASelect,
  AInputNumber,
  ADivider,
  ARow,
  ACol,
  ATabs,
  ATabPane,
  message
} from 'ant-design-vue';

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

const formState = reactive({ ...defaultFormState });

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

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    '招聘中': 'success',
    '已停招': 'error',
    '已完成': 'blue',
  };
  return colors[status] || 'default';
};

const getPriorityColor = (priority: string) => {
  const colors: Record<string, string> = {
    '高': 'red',
    '中': 'orange',
    '低': 'green',
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
    await formRef.value.validate();
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

const handleDelete = (id: string) => {
  positions.value = positions.value.filter(p => p.id !== id);
  message.success('职位已删除');
};

const columns = computed(() => [
  { title: '职位编号', dataIndex: 'code', key: 'code', width: 100 },
  { title: '职位名称', dataIndex: 'name', key: 'name' },
  { title: '所属部门', dataIndex: 'department', key: 'department', width: 100 },
  { title: '关联需求', dataIndex: 'demandCode', key: 'demandCode', width: 100 },
  { title: '招聘流程', dataIndex: 'recruitmentProcess', key: 'recruitmentProcess', width: 120 },
  {
    title: '优先级',
    dataIndex: 'priority',
    key: 'priority',
    width: 80,
    customRender: ({ text }: { text: string }) => h(ATag, { color: getPriorityColor(text) }, () => text)
  },
  {
    title: '职位状态',
    dataIndex: 'status',
    key: 'status',
    width: 90,
    customRender: ({ text }: { text: string }) => h(ATag, { color: getStatusColor(text) }, () => text)
  },
  {
    title: '需求/已入职',
    key: 'headCount',
    width: 110,
    customRender: ({ record }: { record: Position }) => `${record.headCount}/${record.hiredCount}`
  },
  { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 110 },
  {
    title: '操作',
    key: 'action',
    width: 200,
    customRender: ({ record }: { record: Position }) => h(ASpace, { size: 'small' }, () => [
      h(AButton, { type: 'link', size: 'small', onClick: () => handleView(record) }, () => [
        h(EyeOutlined),
        '查看'
      ]),
      h(AButton, { type: 'link', size: 'small', onClick: () => handleEdit(record) }, () => [
        h(EditOutlined),
        '编辑'
      ]),
      h(AButton, { type: 'link', size: 'small', onClick: () => handleToggleStatus(record) }, () => 
        record.status === '招聘中' ? '停招' : '开启'
      )
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
