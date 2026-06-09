<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    :style="{ width: '720px' }"
    :mask-closable="false"
    @close="handleCancel"
  >
    <template #header>
      <div class="modal-title">
        <div class="title-icon">
          <n-icon :component="AddOutline" />
        </div>
        <span>新增候选人</span>
      </div>
    </template>

    <n-steps
      :current="currentStep + 1"
      style="margin-bottom: 24px; padding: 0 20px"
    >
      <n-step v-for="(step, i) in steps" :key="i" :title="step.title" />
    </n-steps>

    <div class="modal-content">
      <!-- 步骤1: 基本信息 -->
      <div v-show="currentStep === 0">
        <n-form
          ref="formRef"
          :model="formState"
          :rules="rules"
          label-placement="top"
        >
          <div class="grid grid-cols-2 gap-x-4">
            <n-form-item label="姓名" path="name" :rule="{ required: true, message: '请输入候选人姓名', trigger: 'blur' }">
              <n-input v-model:value="formState.name" placeholder="请输入候选人姓名" size="large" />
            </n-form-item>
            <n-form-item label="手机号" path="phone" :rule="[{ required: true, message: '请输入手机号', trigger: 'blur' }, { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }]">
              <n-input v-model:value="formState.phone" placeholder="请输入手机号" size="large">
                <template #prefix><n-icon :component="CallOutline" /></template>
              </n-input>
            </n-form-item>
            <n-form-item label="邮箱" path="email">
              <n-input v-model:value="formState.email" placeholder="请输入邮箱" size="large">
                <template #prefix><n-icon :component="MailOutline" /></template>
              </n-input>
            </n-form-item>
            <n-form-item label="性别" path="gender">
              <n-select v-model:value="formState.gender" placeholder="请选择性别" size="large" :options="genderOptions" />
            </n-form-item>
            <n-form-item label="出生日期" path="birthDate">
              <n-input v-model:value="formState.birthDate" type="text" placeholder="请选择出生日期 (YYYY-MM-DD)" size="large" />
            </n-form-item>
            <n-form-item label="最高学历" path="education">
              <n-select v-model:value="formState.education" placeholder="请选择学历" size="large" :options="educationOptions" />
            </n-form-item>
            <n-form-item class="col-span-2" label="应聘职位" path="position" :rule="{ required: true, message: '请选择应聘职位', trigger: 'change' }">
              <n-select
                v-model:value="formState.position"
                placeholder="请选择应聘职位"
                size="large"
                filterable
                :options="positionOptions"
              />
            </n-form-item>
            <n-form-item class="col-span-2" label="简历来源" path="channel" :rule="{ required: true, message: '请选择简历来源', trigger: 'change' }">
              <n-select v-model:value="formState.channel" placeholder="请选择简历来源" size="large" :options="channelOptions" />
            </n-form-item>
            <n-form-item class="col-span-2" label="简历推荐人" path="recommender">
              <n-input v-model:value="formState.recommender" placeholder="请输入推荐人姓名" size="large" />
            </n-form-item>
            <n-form-item class="col-span-2" label="备注" path="remark">
              <n-input v-model:value="formState.remark" type="textarea" :rows="3" placeholder="请输入备注信息" />
            </n-form-item>
          </div>
        </n-form>
      </div>

      <!-- 步骤2: 简历上传 -->
      <div v-show="currentStep === 1">
        <n-upload
          :default-upload="false"
          :file-list="resumeFile ? [{ id: 'resume', name: resumeFile.name, status: 'finished' }] : []"
          accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.xls,.xlsx"
          @change="handleFileChange"
          @before-upload="beforeUpload"
        >
          <n-upload-dragger style="padding: 40px">
            <div class="upload-drag-icon">
              <n-icon :component="FileTrayFullOutline" :size="48" color="#FBCE5B" />
            </div>
            <p style="font-size: 16px; font-weight: 500">
              点击或拖拽上传简历文件
            </p>
            <p style="color: #999">
              支持 PDF、Word、Excel、图片格式，单个文件不超过10MB
            </p>
          </n-upload-dragger>
        </n-upload>

        <n-divider>或</n-divider>

        <div style="text-align: center">
          <n-upload :show-file-list="false" :default-upload="false" @change="handleFileChange" @before-upload="beforeUpload">
            <n-button size="large">
              <template #icon><n-icon :component="CloudUploadOutline" /></template>
              选择文件
            </n-button>
          </n-upload>
        </div>

        <div v-if="resumeFile" class="file-preview">
          <div class="file-item">
            <div class="file-icon">
              <n-icon :component="PersonOutline" />
            </div>
            <div class="file-info">
              <div class="file-name">{{ resumeFile.name }}</div>
              <div class="file-size">{{ (resumeFile.size / 1024 / 1024).toFixed(2) }} MB</div>
            </div>
            <n-button text type="error" @click="removeFile">移除</n-button>
          </div>
        </div>
      </div>

      <!-- 步骤3: 确认提交 -->
      <div v-show="currentStep === 2">
        <div class="info-confirm">
          <div class="confirm-title">📋 信息确认</div>

          <div class="grid grid-cols-2 gap-3">
            <div class="info-item">
              <div class="info-label">姓名</div>
              <div class="info-value">{{ formState.name || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">手机号</div>
              <div class="info-value">{{ formState.phone || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">邮箱</div>
              <div class="info-value">{{ formState.email || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">性别</div>
              <div class="info-value">{{ formState.gender === 'male' ? '男' : '女' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">最高学历</div>
              <div class="info-value">{{ formState.education || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">简历来源</div>
              <div class="info-value">{{ formState.channel || '-' }}</div>
            </div>
          </div>
        </div>

        <div v-if="resumeFile" class="resume-uploaded">
          <div class="uploaded-icon">
            <n-icon :component="CloudUploadOutline" />
          </div>
          <div class="uploaded-info">
            <div class="uploaded-title">已上传简历</div>
            <div class="uploaded-name">{{ resumeFile.name }}</div>
          </div>
        </div>

        <div class="tip-box">
          💡 提示：提交后将自动进行简历解析和查重，重复简历会有提示。
        </div>
      </div>
    </div>

    <template #footer>
      <div class="modal-footer">
        <n-button v-if="currentStep > 0" @click="prevStep">上一步</n-button>
        <div v-else></div>
        <n-space>
          <n-button @click="handleCancel">取消</n-button>
          <n-button v-if="currentStep < steps.length - 1" type="primary" @click="nextStep">下一步</n-button>
          <n-button v-else type="primary" :loading="loading" @click="handleSubmit">确认提交</n-button>
        </n-space>
      </div>
    </div>

    <!-- G45: 查重重复列表 Modal -->
    <n-modal
      v-model:show="showDuplicateModal"
      preset="card"
      :style="{ width: '720px' }"
      :mask-closable="false"
      title="检测到重复候选人"
    >
      <div style="margin-bottom: 12px; color: #d97706;">
        系统检测到 {{ duplicates.length }} 个相似的候选人, 请确认是否继续创建。
      </div>
      <n-data-table
        :columns="duplicateColumns"
        :data="duplicates"
        :bordered="false"
        :single-line="false"
        size="small"
      />
      <template #footer>
        <n-space justify="end">
          <n-button @click="cancelDuplicate">取消</n-button>
          <n-button type="warning" @click="forceCreateCandidate">继续创建 (强制)</n-button>
        </n-space>
      </template>
    </n-modal>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useMessage } from 'naive-ui'
import {
  AddOutline,
  CloudUploadOutline,
  PersonOutline,
  CallOutline,
  MailOutline,
  FileTrayFullOutline,
} from '@vicons/ionicons5'
import axios from 'axios'
import config from '../../config'
import type { DuplicateCandidate } from '../../api/duplicate-check'

interface Props {
  visible: boolean
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'close'): void
  (e: 'success'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const message = useMessage()

const formRef = ref()
const currentStep = ref(0)
const loading = ref(false)
const resumeFile = ref<any>(null)

const formState = reactive({
  name: '',
  phone: '',
  email: '',
  gender: 'male',
  birthDate: '',
  education: '本科',
  position: '',
  channel: '',
  recommender: '',
  remark: '',
})

const rules = {
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  email: [{ type: 'email', message: '请输入正确的邮箱', trigger: 'blur' }],
}

const steps = [
  { title: '基本信息' },
  { title: '简历上传' },
  { title: '确认提交' },
]

const genderOptions = [
  { label: '男', value: 'male' },
  { label: '女', value: 'female' }
]

const educationOptions = [
  { label: '高中', value: '高中' },
  { label: '大专', value: '大专' },
  { label: '本科', value: '本科' },
  { label: '硕士', value: '硕士' },
  { label: '博士', value: '博士' }
]

const positionOptions = [
  { label: '前端开发工程师', value: '1' },
  { label: '后端开发工程师', value: '2' },
  { label: '产品经理', value: '3' },
  { label: 'UI设计师', value: '4' },
  { label: '测试工程师', value: '5' }
]

const channelOptions = [
  { label: 'Boss直聘', value: 'boss' },
  { label: '拉勾网', value: 'lagou' },
  { label: '猎聘网', value: 'liepin' },
  { label: '智联招聘', value: 'zhilian' },
  { label: '前程无忧', value: '51job' },
  { label: '内部推荐', value: 'internal' },
  { label: '其他渠道', value: 'other' }
]

const visible = ref(props.visible)

watch(() => props.visible, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:visible', val)
})

const beforeUpload = (options: any) => {
  resumeFile.value = options.file?.file || options.file
  return false
}

const handleFileChange = (info: any) => {
  const file = info.file?.file || info.file
  if (file) {
    resumeFile.value = file
    message.success(`${file.name} 上传成功`)
  }
}

const removeFile = () => {
  resumeFile.value = null
}

const nextStep = async () => {
  if (currentStep.value === 0) {
    try {
      await formRef.value?.validate()
      currentStep.value++
    } catch (error) {
      console.error('表单验证失败:', error)
    }
  } else {
    currentStep.value++
  }
}

const prevStep = () => {
  currentStep.value--
}

// G45: 查重相关状态
const showDuplicateModal = ref(false)
const duplicates = ref<DuplicateCandidate[]>([])

const duplicateColumns = [
  { title: '姓名', key: 'candidate.name' },
  { title: '手机号', key: 'candidate.phone' },
  { title: '邮箱', key: 'candidate.email' },
  { title: '匹配度', key: 'score',
    render: (row: DuplicateCandidate) => `${(row.score * 100).toFixed(0)}% (${row.matchType})` },
]

const cancelDuplicate = () => {
  showDuplicateModal.value = false
  duplicates.value = []
  loading.value = false
}

const forceCreateCandidate = async () => {
  showDuplicateModal.value = false
  loading.value = true
  try {
    await submitCandidate(true)
  } catch (e) {
    console.error('forceCreate failed', e)
    loading.value = false
  }
}

const submitCandidate = async (forceCreate = false) => {
  const token = localStorage.getItem('token')
  const resp = await axios.post(
    `${config.api.baseUrl}/candidates`,
    {
      name: formState.name,
      phone: formState.phone,
      email: formState.email,
      gender: formState.gender,
      birthday: formState.birthDate,
      highestEducation: formState.education,
      channelSource: formState.channel,
      recommenderName: formState.recommender,
      forceCreate,
    },
    {
      headers: { Authorization: token ? `Bearer ${token}` : '' },
      validateStatus: () => true, // 自己处理 status
    },
  )
  if (resp.status === 409) {
    // 重复: 弹 modal
    duplicates.value = resp.data?.duplicates || []
    showDuplicateModal.value = true
    return
  }
  if (resp.status >= 200 && resp.status < 300) {
    message.success('候选人添加成功！')
    resetForm()
    emit('success')
    emit('close')
  } else {
    message.error(resp.data?.message || `提交失败 (${resp.status})`)
  }
}

const handleSubmit = async () => {
  try {
    loading.value = true
    await submitCandidate(false)
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  resetForm()
  emit('close')
}

const resetForm = () => {
  formState.name = ''
  formState.phone = ''
  formState.email = ''
  formState.gender = 'male'
  formState.birthDate = ''
  formState.education = '本科'
  formState.position = ''
  formState.channel = ''
  formState.recommender = ''
  formState.remark = ''
  currentStep.value = 0
  resumeFile.value = null
}
</script>

<style scoped>
.modal-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}

.title-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #000;
  font-size: 16px;
}

.modal-content {
  min-height: 400px;
}

.upload-drag-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.file-preview {
  margin-top: 24px;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #FBCE5B;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #000;
}

.file-info {
  flex: 1;
}

.file-name {
  font-weight: 500;
}

.file-size {
  font-size: 12px;
  color: #999;
}

.info-confirm {
  background: #f8f9ff;
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 24px;
}

.confirm-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #333;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-label {
  color: #999;
  font-size: 12px;
}

.info-value {
  font-weight: 500;
}

.resume-uploaded {
  background: #fff7e6;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #ffe58f;
  display: flex;
  align-items: center;
  gap: 12px;
}

.uploaded-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #faad14;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.uploaded-title {
  font-weight: 500;
}

.uploaded-name {
  font-size: 12px;
  color: #999;
}

.tip-box {
  margin-top: 24px;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 8px;
  color: #FBCE5B;
  font-weight: 500;
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  width: 100%;
}
</style>
