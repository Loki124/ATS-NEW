<template>
  <div class="candidate-detail-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <n-space>
        <n-button @click="goBack" class="back-btn">
          <template #icon><n-icon :component="ChevronBackOutline" /></template>
          返回
        </n-button>
        <n-h4 style="margin: 0; font-weight: 700">候选人详情</n-h4>
      </n-space>

      <n-space>
        <n-button type="primary" @click="openNotificationModal" class="send-btn">
          <template #icon><n-icon :component="PaperPlaneOutline" /></template>
          发送通知
        </n-button>
      </n-space>
    </div>

    <!-- 候选人基本信息卡片 -->
    <n-card class="info-card">
      <div class="flex items-center">
        <div class="mr-6">
          <n-avatar :size="80" round class="candidate-avatar">
            {{ candidateData.name[0] }}
          </n-avatar>
        </div>
        <div class="flex-1">
          <div class="candidate-header">
            <div class="candidate-main">
              <n-h3 style="margin: 0 0 8px 0">
                {{ candidateData.name }}
                <n-tag :type="candidateData.status === 'interview' ? 'warning' : 'success'" :bordered="false" style="margin-left: 12px">
                  {{ candidateData.status === 'interview' ? '面试中' : '已入职' }}
                </n-tag>
              </n-h3>
              <n-space size="large" style="margin-bottom: 12px">
                <span class="contact-info">
                  <n-icon :component="CallOutline" style="margin-right: 4px" /> {{ candidateData.phone }}
                </span>
                <span class="contact-info">
                  <n-icon :component="MailOutline" style="margin-right: 4px" /> {{ candidateData.email }}
                </span>
              </n-space>
              <n-space wrap>
                <n-tag class="position-tag" :bordered="false">{{ candidateData.position }}</n-tag>
                <n-tag class="channel-tag" :bordered="false">Boss直聘</n-tag>
              </n-space>
            </div>
            <div class="candidate-meta">
              <div>HRBP：{{ candidateData.hrbp }}</div>
              <div>用人经理：{{ candidateData.hiringManager }}</div>
            </div>
          </div>
        </div>
      </div>
    </n-card>

    <!-- Tab 区域 -->
    <n-card class="tabs-card">
      <n-tabs v-model:value="activeTab">
        <!-- 基本信息 -->
        <n-tab-pane name="info">
          <template #tab>
            <span><n-icon :component="PersonOutline" /> 基本信息</span>
          </template>
          <div class="info-section">
            <n-grid :cols="2" :x-gap="24" :y-gap="16" responsive="screen">
              <n-grid-item>
                <div class="info-row">
                  <div class="info-label">姓名</div>
                  <div class="info-value">{{ candidateData.name }}</div>
                </div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">性别</div><div class="info-value">男</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">年龄</div><div class="info-value">28岁</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">手机号</div><div class="info-value">{{ candidateData.phone }}</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">邮箱</div><div class="info-value">{{ candidateData.email }}</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">最高学历</div><div class="info-value">本科</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">毕业院校</div><div class="info-value">华东理工大学</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">专业</div><div class="info-value">计算机科学与技术</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">工作年限</div><div class="info-value">5年</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">当前公司</div><div class="info-value">字节跳动</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row"><div class="info-label">期望薪资</div><div class="info-value">40K</div></div>
              </n-grid-item>
              <n-grid-item>
                <div class="info-row">
                  <div class="info-label">简历来源</div>
                  <n-tag :bordered="false" style="background: #ecdcff; color: #7431d3">Boss直聘</n-tag>
                </div>
              </n-grid-item>
            </n-grid>
          </div>
        </n-tab-pane>

        <!-- 招聘流程 -->
        <n-tab-pane name="process">
          <template #tab>
            <span><n-icon :component="CalendarOutline" /> 招聘流程</span>
          </template>
          <div class="process-section">
            <div class="timeline-section">
              <n-h5 style="margin-bottom: 16px">招聘进度</n-h5>
              <n-timeline>
                <n-timeline-item type="success" content="简历筛选" time="2026-04-20" line-type="success" />
                <n-timeline-item type="success" content="HRBP评估" time="2026-04-21" line-type="success" />
                <n-timeline-item type="success" content="用人经理筛选" time="2026-04-22" line-type="success" />
                <n-timeline-item type="success" content="邀约面试" time="2026-04-23" line-type="success" />
                <n-timeline-item type="info" content="联合面试" time="2026-04-25" line-type="info" />
                <n-timeline-item content="综合面试" time="-" line-type="default" />
                <n-timeline-item content="Offer沟通" time="-" line-type="default" />
              </n-timeline>
            </div>
            <n-divider style="margin: 24px 0" />
            <div class="interview-section">
              <n-h5 style="margin-bottom: 16px">面试记录</n-h5>
              <div class="interview-table">
                <div class="interview-header grid grid-cols-12 gap-2">
                  <div class="col-span-3">面试类型</div>
                  <div class="col-span-4">面试时间</div>
                  <div class="col-span-4">面试官</div>
                  <div class="col-span-3">结果</div>
                  <div class="col-span-7">反馈</div>
                  <div class="col-span-3">操作</div>
                </div>
                <div class="interview-row grid grid-cols-12 gap-2 items-center">
                  <div class="col-span-3">联合面试</div>
                  <div class="col-span-4">2026-04-25 14:00</div>
                  <div class="col-span-4">技术面试官A、B</div>
                  <div class="col-span-3"><n-tag type="success" :bordered="false">通过</n-tag></div>
                  <div class="col-span-7" style="color: #414753">技术能力强，项目经验丰富</div>
                  <div class="col-span-3"><n-button text type="primary" size="small">查看详情</n-button></div>
                </div>
                <div class="interview-row grid grid-cols-12 gap-2 items-center">
                  <div class="col-span-3">笔试</div>
                  <div class="col-span-4">2026-04-21 10:00</div>
                  <div class="col-span-4">HR</div>
                  <div class="col-span-3"><n-tag type="success" :bordered="false">通过</n-tag></div>
                  <div class="col-span-7" style="color: #414753">逻辑清晰，编码规范</div>
                  <div class="col-span-3"><n-button text type="primary" size="small">查看详情</n-button></div>
                </div>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <!-- 简历信息 -->
        <n-tab-pane name="resume">
          <template #tab>
            <span><n-icon :component="DocumentTextOutline" /> 简历信息</span>
          </template>
          <div class="resume-section">
            <div v-if="resumeData.url" class="resume-content">
              <div class="resume-toolbar">
                <n-space>
                  <n-button type="primary" class="download-btn" @click="handleDownloadResume">
                    <template #icon><n-icon :component="DownloadOutline" /></template>
                    下载简历
                  </n-button>
                  <n-button @click="openEditResumeModal">编辑简历</n-button>
                </n-space>
              </div>
              <div class="resume-preview">
                <n-h5>简历预览</n-h5>
                <div class="resume-info">
                  <div class="resume-field"><span class="field-label">姓名：</span><span class="field-value">{{ resumeData.name }}</span></div>
                  <div class="resume-field"><span class="field-label">手机号：</span><span class="field-value">{{ resumeData.phone }}</span></div>
                  <div class="resume-field"><span class="field-label">邮箱：</span><span class="field-value">{{ resumeData.email }}</span></div>
                  <div class="resume-field"><span class="field-label">最高学历：</span><span class="field-value">{{ resumeData.education }}</span></div>
                  <div class="resume-field"><span class="field-label">毕业院校：</span><span class="field-value">{{ resumeData.school }}</span></div>
                  <div class="resume-field"><span class="field-label">工作年限：</span><span class="field-value">{{ resumeData.workYears }}年</span></div>
                  <div class="resume-field"><span class="field-label">当前公司：</span><span class="field-value">{{ resumeData.currentCompany }}</span></div>
                  <div class="resume-field"><span class="field-label">期望薪资：</span><span class="field-value">{{ resumeData.expectedSalary }}</span></div>
                  <div class="resume-field"><span class="field-label">简历来源：</span><span class="field-value">{{ resumeData.source }}</span></div>
                </div>
              </div>
            </div>
            <div v-else class="empty-state text-center">
              <n-icon :component="DocumentTextOutline" :size="64" color="#7431d3" />
              <n-h4 style="margin-top: 16px">暂无简历</n-h4>
              <n-text :depth="3">该候选人还没有上传简历</n-text>
              <div style="margin-top: 24px">
                <n-space>
                  <n-button type="primary" @click="openUploadResumeModal">
                    <template #icon><n-icon :component="CloudUploadOutline" /></template>
                    上传简历
                  </n-button>
                </n-space>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <!-- 操作记录 -->
        <n-tab-pane name="history">
          <template #tab>
            <span><n-icon :component="TimeOutline" /> 操作记录</span>
          </template>
          <div class="history-section">
            <n-timeline>
              <n-timeline-item>
                <div>
                  <n-tag type="info" :bordered="false">发送面试通知</n-tag>
                  <n-text :depth="3" style="font-size: 12px; margin-left: 8px">2026-04-27 10:30</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">操作人：张强</n-text></div>
                  <div style="margin-top: 4px; color: #414753">发送给张三关于4月25日联合面试的通知</div>
                </div>
              </n-timeline-item>
              <n-timeline-item>
                <div>
                  <n-tag type="success" :bordered="false">完成面试</n-tag>
                  <n-text :depth="3" style="font-size: 12px; margin-left: 8px">2026-04-25 14:00</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">操作人：系统</n-text></div>
                  <div style="margin-top: 4px; color: #414753">联合面试已完成</div>
                </div>
              </n-timeline-item>
              <n-timeline-item>
                <div>
                  <n-tag type="info" :bordered="false">安排面试</n-tag>
                  <n-text :depth="3" style="font-size: 12px; margin-left: 8px">2026-04-23 16:00</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">操作人：张强</n-text></div>
                  <div style="margin-top: 4px; color: #414753">安排联合面试时间：4月25日14:00</div>
                </div>
              </n-timeline-item>
              <n-timeline-item>
                <div>
                  <n-tag type="success" :bordered="false">筛选通过</n-tag>
                  <n-text :depth="3" style="font-size: 12px; margin-left: 8px">2026-04-22 11:00</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">操作人：王芳</n-text></div>
                  <div style="margin-top: 4px; color: #414753">用人经理筛选结果：通过</div>
                </div>
              </n-timeline-item>
              <n-timeline-item>
                <div>
                  <n-tag type="info" :bordered="false">添加候选人</n-tag>
                  <n-text :depth="3" style="font-size: 12px; margin-left: 8px">2026-04-20 09:00</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">操作人：张强</n-text></div>
                  <div style="margin-top: 4px; color: #414753">从Boss直聘导入候选人信息</div>
                </div>
              </n-timeline-item>
            </n-timeline>
          </div>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 发送通知弹窗 -->
    <n-modal
      v-model:show="notificationModalVisible"
      :width="1000"
      :mask-closable="false"
      preset="card"
      class="notification-modal"
    >
      <template #header>
        <div class="modal-header">
          <span class="modal-title">发送通知</span>
          <button class="close-btn" @click="notificationModalVisible = false">
            <n-icon :component="CloseOutline" />
          </button>
        </div>
        <div class="candidate-summary">
          <n-avatar :size="48" class="candidate-avatar-sm">
            {{ candidateData.name[0] }}
          </n-avatar>
          <div class="candidate-info">
            <div class="candidate-name-row">
              <span class="candidate-name">{{ candidateData.name }}</span>
              <n-tag class="position-tag-sm" :bordered="false">{{ candidateData.position }}</n-tag>
              <n-tag class="experience-tag" :bordered="false">5年经验</n-tag>
            </div>
            <div class="candidate-contact-row">
              <span><n-icon :component="CallOutline" /> {{ candidateData.phone }}</span>
              <span><n-icon :component="MailOutline" /> {{ candidateData.email }}</span>
            </div>
          </div>
        </div>
      </template>

      <div class="modal-content">
        <div class="left-sidebar">
          <div class="step-section">
            <h3 class="step-title">
              <span class="step-number">1</span>
              选择发送内容
            </h3>
            <div class="info-callout">
              <span>系统将基于选择的「发送内容」自动为候选人生成对应待办，选择多个内容时会同时发送</span>
            </div>
            <div class="step-content">
              <div class="content-group">
                <div class="content-group-title">面试登记表</div>
                <label class="content-item selected">
                  <n-checkbox v-model:checked="notificationForm.interviewForm" />
                  <span>收集候选人基本信息</span>
                </label>
              </div>
              <div class="content-group">
                <div class="content-group-title">性格测试</div>
                <n-radio-group v-model:value="notificationForm.personalityTest">
                  <n-space vertical>
                    <n-radio value="pdp_mbti_20">PDP+20题版MBTI</n-radio>
                    <n-radio value="pdp_mbti_93">PDP+93题版MBTI</n-radio>
                  </n-space>
                </n-radio-group>
              </div>
              <div class="content-group">
                <div class="content-group-title">应聘登记表</div>
                <label class="content-item">
                  <n-checkbox v-model:checked="notificationForm.applicationForm" />
                  <span>完善工作履历及教育背景</span>
                </label>
              </div>
              <div class="content-group">
                <div class="content-group-title">入职材料</div>
                <label class="content-item">
                  <n-checkbox v-model:checked="notificationForm.onboardingDocs" />
                  <span>收集入职资料及相关证明</span>
                </label>
              </div>
            </div>
          </div>

          <div class="step-section">
            <h3 class="step-title">
              <span class="step-number">2</span>
              选择通知方式
            </h3>
            <div class="step-content">
              <label class="method-item selected">
                <n-checkbox v-model:checked="notificationForm.sendEmail" />
                <n-icon :component="MailOutline" class="method-icon" />
                <span class="method-name">邮件通知</span>
              </label>
              <label class="method-item selected">
                <n-checkbox v-model:checked="notificationForm.sendSms" />
                <n-icon :component="ChatbubblesOutline" class="method-icon" />
                <span class="method-name">短信通知</span>
              </label>
              <label class="method-item">
                <n-checkbox v-model:checked="notificationForm.sendWechat" />
                <n-icon :component="LogoWechat" class="method-icon" />
                <span class="method-name">微信企业号推送</span>
              </label>
            </div>
          </div>
        </div>

        <div class="right-content">
          <div class="editor-section" v-if="notificationForm.sendEmail">
            <div class="editor-header">
              <n-icon :component="MailOutline" class="editor-icon" />
              <h4 class="editor-title">邮件通知</h4>
            </div>
            <div class="editor-field">
              <label class="field-label">邮件主题</label>
              <n-input v-model:value="notificationForm.emailSubject" class="email-subject-input" />
            </div>
            <div class="editor-field">
              <label class="field-label">邮件正文</label>
              <n-input v-model:value="notificationForm.emailContent" type="textarea" :rows="8" class="email-content-input" />
            </div>
          </div>

          <div class="editor-section" v-if="notificationForm.sendSms">
            <div class="editor-header">
              <n-icon :component="ChatbubblesOutline" class="editor-icon" />
              <h4 class="editor-title">短信通知</h4>
            </div>
            <div class="editor-field">
              <div class="sms-counter">
                <label class="field-label">短信正文</label>
                <span class="counter-text">已输入 <strong>{{ notificationForm.smsContent.length }}</strong> / 70 字</span>
              </div>
              <n-input v-model:value="notificationForm.smsContent" type="textarea" :rows="4" class="sms-content-input" />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer">
          <div class="recipient-info">通知将发送至: 1个手机号, 1个邮箱地址</div>
          <div class="footer-buttons">
            <n-button @click="notificationModalVisible = false">取消</n-button>
            <n-button type="primary" class="send-btn-primary" @click="handleSendNotification">
              <template #icon><n-icon :component="PaperPlaneOutline" /></template>
              确认发送
            </n-button>
          </div>
        </div>
      </template>
    </n-modal>

    <!-- 编辑简历弹窗 -->
    <n-modal
      v-model:show="editResumeModalVisible"
      preset="card"
      title="编辑简历"
      :width="600"
      style="max-width: 90vw"
      @positive-click="handleSaveResume"
    >
      <n-form :model="resumeForm" label-placement="top">
        <n-grid :cols="2" :x-gap="16" :y-gap="0" responsive="screen">
          <n-grid-item>
            <n-form-item label="姓名">
              <n-input v-model:value="resumeForm.name" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="手机号">
              <n-input v-model:value="resumeForm.phone" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="邮箱">
              <n-input v-model:value="resumeForm.email" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="最高学历">
              <n-select v-model:value="resumeForm.education" :options="educationOptions" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="毕业院校">
              <n-input v-model:value="resumeForm.school" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="工作年限">
              <n-input-number v-model:value="resumeForm.workYears" :min="0" :max="50" style="width: 100%" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="当前公司">
              <n-input v-model:value="resumeForm.currentCompany" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="期望薪资">
              <n-input v-model:value="resumeForm.expectedSalary" placeholder="如: 40K" />
            </n-form-item>
          </n-grid-item>
        </n-grid>
      </n-form>
    </n-modal>

    <!-- 上传简历弹窗 -->
    <n-modal
      v-model:show="uploadResumeModalVisible"
      preset="card"
      title="上传简历"
      :width="500"
      style="max-width: 90vw"
      @positive-click="handleUploadResume"
    >
      <n-upload
        v-model:file-list="fileList"
        :max="1"
        :default-upload="false"
        accept=".pdf,.doc,.docx"
        @before-upload="beforeUpload"
      >
        <n-button>
          <template #icon><n-icon :component="CloudUploadOutline" /></template>
          选择文件
        </n-button>
      </n-upload>
      <div class="upload-tip">支持 PDF、Word 格式文件，大小不超过 10MB</div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  ChevronBackOutline,
  MailOutline,
  CallOutline,
  CalendarOutline,
  PersonOutline,
  DocumentTextOutline,
  TimeOutline,
  PaperPlaneOutline,
  CloseOutline,
  ChatbubblesOutline,
  LogoWechat,
  CloudUploadOutline,
  DownloadOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const message = useMessage()

const activeTab = ref('info')

const candidateData = {
  id: route.params.id || '1',
  name: '张三',
  phone: '138****8888',
  email: 'zhangsan@example.com',
  position: '前端开发工程师',
  status: 'interview',
  hrbp: '李明',
  hiringManager: '王芳',
  createdAt: '2026-04-20',
}

const resumeData = ref({
  url: 'https://example.com/resume.pdf',
  name: '张三',
  phone: '138****8888',
  email: 'zhangsan@example.com',
  education: '本科',
  school: '华东理工大学',
  workYears: 5,
  currentCompany: '字节跳动',
  expectedSalary: '40K',
  source: 'Boss直聘',
})

const resumeForm = ref({
  name: '张三',
  phone: '138****8888',
  email: 'zhangsan@example.com',
  education: '本科',
  school: '华东理工大学',
  workYears: 5,
  currentCompany: '字节跳动',
  expectedSalary: '40K',
})

const educationOptions = [
  { label: '高中', value: '高中' },
  { label: '大专', value: '大专' },
  { label: '本科', value: '本科' },
  { label: '硕士', value: '硕士' },
  { label: '博士', value: '博士' },
]

const uploadResumeModalVisible = ref(false)
const editResumeModalVisible = ref(false)
const notificationModalVisible = ref(false)
const fileList = ref<any[]>([])

const notificationForm = ref({
  interviewForm: true,
  personalityTest: 'pdp_mbti_20',
  applicationForm: false,
  onboardingDocs: false,
  sendEmail: true,
  sendSms: true,
  sendWechat: false,
  emailSubject: '【ATS招聘系统】面试邀请与前期准备事项',
  emailContent: '尊敬的候选人，您好！...',
  smsContent: '',
})

const goBack = () => router.push('/candidates')
const openNotificationModal = () => { notificationModalVisible.value = true }
const openUploadResumeModal = () => { uploadResumeModalVisible.value = true }
const openEditResumeModal = () => { editResumeModalVisible.value = true }

const handleDownloadResume = () => {
  if (resumeData.value.url) message.success('开始下载简历')
  else message.warning('暂无简历可下载')
}

const beforeUpload = ({ file }: any) => {
  const fileObj = file?.file || file
  const isPDF = fileObj.type === 'application/pdf'
  const isDoc = fileObj.type === 'application/msword' || fileObj.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  const isLessThan10M = fileObj.size / 1024 / 1024 < 10
  if (!isPDF && !isDoc) { message.error('只支持 PDF、Word 格式文件!'); return false }
  if (!isLessThan10M) { message.error('文件大小不能超过 10MB!'); return false }
  return true
}

const handleSaveResume = () => {
  message.success('简历保存成功')
  editResumeModalVisible.value = false
}

const handleUploadResume = () => {
  if (fileList.value.length === 0) { message.warning('请选择要上传的文件'); return }
  message.success('简历上传成功')
  uploadResumeModalVisible.value = false
  fileList.value = []
}

const handleSendNotification = () => {
  message.success('通知已发送')
  notificationModalVisible.value = false
}
</script>

<style scoped>
.candidate-detail-page { padding: 24px; background: #f8f9ff; min-height: 100vh; }
.page-header { margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }
.back-btn { border: none; background: transparent; }
.send-btn { background: #005ab6; border-color: #005ab6; border-radius: 8px; font-weight: 600; }
.info-card { margin-bottom: 24px; border-radius: 24px; border: none; box-shadow: 0 8px 32px rgba(0,0,0,0.08); }
.candidate-avatar { background: linear-gradient(135deg, #7431d3 0%, #005ab6 100%) !important; font-size: 32px; font-weight: 700; }
.candidate-header { display: flex; justify-content: space-between; align-items: flex-start; }
.contact-info { color: #414753; }
.position-tag { border-radius: 9999px; padding: 4px 12px; background: #d7e3ff; color: #005ab6; }
.channel-tag { border-radius: 9999px; padding: 4px 12px; background: #ecdcff; color: #7431d3; }
.candidate-meta { text-align: right; color: #414753; font-size: 12px; }
.tabs-card { border-radius: 24px; border: none; box-shadow: 0 8px 32px rgba(0,0,0,0.08); }
.info-section { padding: 16px; }
.info-row { display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid #dee3ed; }
.info-label { width: 100px; color: #414753; font-size: 14px; }
.info-value { font-weight: 600; color: #161c23; }
.process-section, .interview-table { background: #f8f9ff; border-radius: 12px; padding: 16px; }
.interview-header { font-weight: 600; color: #414753; padding: 12px 0; border-bottom: 1px solid #dee3ed; }
.interview-row { padding: 12px 0; border-bottom: 1px solid #dee3ed; }
.resume-section { padding: 24px; }
.resume-content { display: flex; flex-direction: column; gap: 24px; }
.resume-toolbar { display: flex; justify-content: flex-start; }
.resume-preview { background: #f8f9ff; border-radius: 12px; padding: 24px; }
.resume-info { display: flex; flex-direction: column; gap: 12px; }
.resume-field { display: flex; align-items: center; }
.resume-field .field-label { width: 100px; color: #414753; font-size: 14px; }
.resume-field .field-value { color: #161c23; font-weight: 500; font-size: 14px; }
.upload-tip { margin-top: 16px; color: #727785; font-size: 12px; }
.download-btn { background: #005ab6; border-color: #005ab6; border-radius: 8px; }
.empty-state { padding: 40px; }
.history-section { padding: 16px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-bottom: 1px solid rgba(194, 198, 213, 0.4); }
.modal-title { font-size: 20px; font-weight: 700; color: #161c23; }
.close-btn { width: 32px; height: 32px; border: none; background: transparent; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; color: #414753; transition: all 0.2s; }
.close-btn:hover { background: rgba(222, 227, 237, 0.5); color: #161c23; }
.candidate-summary { display: flex; align-items: center; gap: 16px; background: #ecf1fb; border-radius: 8px; padding: 12px; margin-top: 16px; }
.candidate-avatar-sm { background: linear-gradient(135deg, #7431d3 0%, #005ab6 100%) !important; font-size: 20px; font-weight: 600; }
.candidate-info { flex: 1; }
.candidate-name-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.candidate-name { font-size: 16px; font-weight: 600; color: #161c23; }
.position-tag-sm { background: #d7e3ff; color: #00458e; border-radius: 9999px; font-size: 12px; padding: 2px 8px; }
.experience-tag { background: #dee3ed; color: #414753; border-radius: 9999px; font-size: 12px; padding: 2px 8px; }
.candidate-contact-row { display: flex; gap: 16px; font-size: 14px; color: #414753; }
.candidate-contact-row span { display: flex; align-items: center; gap: 4px; }
.modal-content { display: flex; min-height: 400px; }
.left-sidebar { width: 340px; background: #f8f9ff; border-right: 1px solid rgba(194, 198, 213, 0.4); padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 32px; }
.step-section { display: flex; flex-direction: column; gap: 16px; }
.step-title { font-size: 16px; font-weight: 600; color: #161c23; display: flex; align-items: center; gap: 8px; margin: 0; }
.step-number { width: 24px; height: 24px; border-radius: 50%; background: #1672df; color: #fff; font-size: 12px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.step-content { display: flex; flex-direction: column; gap: 16px; }
.content-group { display: flex; flex-direction: column; gap: 8px; }
.content-group-title { font-size: 14px; font-weight: 600; color: #161c23; padding-left: 4px; }
.content-item { display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: 8px; border: 1px solid #c1c6d5; background: #fff; cursor: pointer; transition: all 0.2s; font-size: 14px; color: #161c23; }
.content-item:hover { border-color: #005ab6; background: #f0f7ff; }
.content-item.selected { border-color: #005ab6; background: rgba(215, 227, 255, 0.2); }
.method-item { display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: 8px; border: 1px solid #c1c6d5; background: #fff; cursor: pointer; transition: all 0.2s; }
.method-item:hover { border-color: #005ab6; background: #f0f7ff; }
.method-item.selected { border-color: #005ab6; background: rgba(215, 227, 255, 0.2); }
.method-icon { font-size: 20px; color: #005ab6; }
.method-name { font-size: 14px; font-weight: 600; color: #161c23; }
.right-content { flex: 1; padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 24px; background: #fff; }
.info-callout { display: flex; align-items: flex-start; gap: 8px; padding: 12px; background: rgba(255, 214, 102, 0.1); border: 1px solid #ffd666; border-radius: 8px; font-size: 14px; color: #765c00; }
.editor-section { display: flex; flex-direction: column; gap: 12px; }
.editor-header { display: flex; align-items: center; gap: 8px; padding-bottom: 12px; border-bottom: 1px solid rgba(194, 198, 213, 0.3); }
.editor-icon { font-size: 24px; color: #005ab6; }
.editor-title { font-size: 16px; font-weight: 600; color: #161c23; margin: 0; }
.editor-field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: 12px; font-weight: 500; color: #414753; }
.sms-counter { display: flex; justify-content: space-between; align-items: center; }
.counter-text { font-size: 12px; color: #727785; }
.email-subject-input, .email-content-input, .sms-content-input { background: rgba(222, 227, 237, 0.3); border: 1px solid rgba(194, 198, 213, 0.3); border-radius: 6px; }
.modal-footer { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-top: 1px solid rgba(194, 198, 213, 0.4); background: #f8f9ff; }
.recipient-info { font-size: 12px; color: #414753; }
.footer-buttons { display: flex; gap: 16px; align-items: center; }
.send-btn-primary { background: #ffd666 !important; border-color: #ffd666 !important; color: #241a00 !important; }
.send-btn-primary:hover { background: #ffdf90 !important; border-color: #ffdf90 !important; }
</style>
