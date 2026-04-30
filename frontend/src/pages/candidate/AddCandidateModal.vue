<template>
  <a-modal
    v-model:open="visible"
    :width="720"
    :footer="null"
    :destroyOnClose="true"
    @cancel="handleCancel"
  >
    <template #title>
      <div class="modal-title">
        <div class="title-icon">
          <PlusOutlined />
        </div>
        <span>新增候选人</span>
      </div>
    </template>

    <a-steps 
      :current="currentStep" 
      :items="steps"
      style="margin-bottom: 24px; padding: 0 20px"
    />

    <div class="modal-content">
      <!-- 步骤1: 基本信息 -->
      <div v-show="currentStep === 0">
        <a-form
          ref="formRef"
          :model="formState"
          :rules="rules"
          layout="vertical"
          :initialValues="{ gender: 'male', education: '本科' }"
        >
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="姓名" name="name" :rules="[{ required: true, message: '请输入候选人姓名' }]">
                <a-input v-model:value="formState.name" placeholder="请输入候选人姓名" size="large" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="手机号" name="phone" :rules="[{ required: true, message: '请输入手机号' }, { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' }]">
                <a-input v-model:value="formState.phone" placeholder="请输入手机号" size="large">
                  <template #prefix><PhoneOutlined /></template>
                </a-input>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="邮箱" name="email" :rules="[{ type: 'email', message: '请输入正确的邮箱' }]">
                <a-input v-model:value="formState.email" placeholder="请输入邮箱" size="large">
                  <template #prefix><MailOutlined /></template>
                </a-input>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="性别" name="gender">
                <a-select v-model:value="formState.gender" placeholder="请选择性别" size="large">
                  <a-select-option value="male">男</a-select-option>
                  <a-select-option value="female">女</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="出生日期" name="birthDate">
                <a-input v-model:value="formState.birthDate" type="date" placeholder="请选择出生日期" size="large" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="最高学历" name="education">
                <a-select v-model:value="formState.education" placeholder="请选择学历" size="large">
                  <a-select-option value="高中">高中</a-select-option>
                  <a-select-option value="大专">大专</a-select-option>
                  <a-select-option value="本科">本科</a-select-option>
                  <a-select-option value="硕士">硕士</a-select-option>
                  <a-select-option value="博士">博士</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="24">
              <a-form-item label="应聘职位" name="position" :rules="[{ required: true, message: '请选择应聘职位' }]">
                <a-select 
                  v-model:value="formState.position" 
                  placeholder="请选择应聘职位" 
                  size="large"
                  show-search
                  :filter-option="(input: string, option: any) => option.children.toLowerCase().includes(input.toLowerCase())"
                >
                  <a-select-option value="1">前端开发工程师</a-select-option>
                  <a-select-option value="2">后端开发工程师</a-select-option>
                  <a-select-option value="3">产品经理</a-select-option>
                  <a-select-option value="4">UI设计师</a-select-option>
                  <a-select-option value="5">测试工程师</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="24">
              <a-form-item label="简历来源" name="channel" :rules="[{ required: true, message: '请选择简历来源' }]">
                <a-select v-model:value="formState.channel" placeholder="请选择简历来源" size="large">
                  <a-select-option value="boss">Boss直聘</a-select-option>
                  <a-select-option value="lagou">拉勾网</a-select-option>
                  <a-select-option value="liepin">猎聘网</a-select-option>
                  <a-select-option value="zhilian">智联招聘</a-select-option>
                  <a-select-option value="51job">前程无忧</a-select-option>
                  <a-select-option value="internal">内部推荐</a-select-option>
                  <a-select-option value="other">其他渠道</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="24">
              <a-form-item label="简历推荐人" name="recommender">
                <a-input v-model:value="formState.recommender" placeholder="请输入推荐人姓名" size="large" />
              </a-form-item>
            </a-col>
            <a-col :span="24">
              <a-form-item label="备注" name="remark">
                <a-textarea v-model:value="formState.remark" :rows="3" placeholder="请输入备注信息" />
              </a-form-item>
            </a-col>
          </a-row>
        </a-form>
      </div>

      <!-- 步骤2: 简历上传 -->
      <div v-show="currentStep === 1">
        <a-upload-dragger
          :beforeUpload="beforeUpload"
          :fileList="resumeFile ? [resumeFile] : []"
          @change="handleFileChange"
          accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.xls,.xlsx"
          style="padding: 40px"
        >
          <p class="ant-upload-drag-icon">
            <InboxOutlined style="font-size: 48px; color: #667eea" />
          </p>
          <p class="ant-upload-text" style="font-size: 16px; font-weight: 500">
            点击或拖拽上传简历文件
          </p>
          <p class="ant-upload-hint" style="color: #999">
            支持 PDF、Word、Excel、图片格式，单个文件不超过10MB
          </p>
        </a-upload-dragger>

        <a-divider>或</a-divider>

        <div style="text-align: center">
          <a-upload :showUploadList="false" :beforeUpload="beforeUpload" @change="handleFileChange">
            <a-button size="large">
              <template #icon><UploadOutlined /></template>
              选择文件
            </a-button>
          </a-upload>
        </div>

        <div v-if="resumeFile" class="file-preview">
          <div class="file-item">
            <div class="file-icon">
              <UserOutlined />
            </div>
            <div class="file-info">
              <div class="file-name">{{ resumeFile.name }}</div>
              <div class="file-size">{{ (resumeFile.size / 1024 / 1024).toFixed(2) }} MB</div>
            </div>
            <a-button type="link" danger @click="removeFile">移除</a-button>
          </div>
        </div>
      </div>

      <!-- 步骤3: 确认提交 -->
      <div v-show="currentStep === 2">
        <div class="info-confirm">
          <div class="confirm-title">📋 信息确认</div>
          
          <a-row :gutter="[12, 12]">
            <a-col :span="12">
              <div class="info-item">
                <div class="info-label">姓名</div>
                <div class="info-value">{{ formState.name || '-' }}</div>
              </div>
            </a-col>
            <a-col :span="12">
              <div class="info-item">
                <div class="info-label">手机号</div>
                <div class="info-value">{{ formState.phone || '-' }}</div>
              </div>
            </a-col>
            <a-col :span="12">
              <div class="info-item">
                <div class="info-label">邮箱</div>
                <div class="info-value">{{ formState.email || '-' }}</div>
              </div>
            </a-col>
            <a-col :span="12">
              <div class="info-item">
                <div class="info-label">性别</div>
                <div class="info-value">{{ formState.gender === 'male' ? '男' : '女' }}</div>
              </div>
            </a-col>
            <a-col :span="12">
              <div class="info-item">
                <div class="info-label">最高学历</div>
                <div class="info-value">{{ formState.education || '-' }}</div>
              </div>
            </a-col>
            <a-col :span="12">
              <div class="info-item">
                <div class="info-label">简历来源</div>
                <div class="info-value">{{ formState.channel || '-' }}</div>
              </div>
            </a-col>
          </a-row>
        </div>

        <div v-if="resumeFile" class="resume-uploaded">
          <div class="uploaded-icon">
            <UploadOutlined />
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

    <div class="modal-footer">
      <a-button v-if="currentStep > 0" @click="prevStep">上一步</a-button>
      <a-space>
        <a-button @click="handleCancel">取消</a-button>
        <a-button v-if="currentStep < steps.length - 1" type="primary" @click="nextStep">下一步</a-button>
        <a-button v-else type="primary" :loading="loading" @click="handleSubmit">确认提交</a-button>
      </a-space>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  UploadOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  InboxOutlined,
} from '@ant-design/icons-vue'

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
  phone: [{ required: true, message: '请输入手机号' }],
  email: [{ type: 'email', message: '请输入正确的邮箱' }],
}

const steps = [
  { title: '基本信息' },
  { title: '简历上传' },
  { title: '确认提交' },
]

const visible = ref(props.visible)

watch(() => props.visible, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:visible', val)
})

const beforeUpload = (file: any) => {
  resumeFile.value = file
  return false
}

const handleFileChange = (info: any) => {
  const file = info.file.originFileObj || info.file
  if (file) {
    resumeFile.value = file
    message.success(`${info.file.name} 上传成功`)
  }
}

const removeFile = () => {
  resumeFile.value = null
}

const nextStep = async () => {
  if (currentStep.value === 0) {
    try {
      await formRef.value.validate()
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

const handleSubmit = async () => {
  try {
    loading.value = true
    // 模拟提交
    setTimeout(() => {
      message.success('候选人添加成功！')
      loading.value = false
      resetForm()
      emit('success')
      emit('close')
    }, 1000)
  } catch (error) {
    console.error('提交失败:', error)
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
}

.modal-content {
  min-height: 400px;
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
  background: #667eea;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
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
  color: #667eea;
  font-weight: 500;
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
}
</style>