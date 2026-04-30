<template>
  <div class="candidate-detail-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <a-space>
        <a-button @click="goBack" class="back-btn">
          <template #icon><ArrowLeftOutlined /></template>
          返回
        </a-button>
        <a-typography-title :level="4" style="margin: 0; font-weight: 700">候选人详情</a-typography-title>
      </a-space>
      
      <a-space>
        <a-button type="primary" @click="showNotificationModal" class="send-btn">
          <template #icon><SendOutlined /></template>
          发送通知
        </a-button>
        <a-dropdown :trigger="['click']">
          <a-button><MoreOutlined /></a-button>
          <template #overlay>
            <a-menu>
              <a-menu-item key="edit"><EditOutlined /> 编辑信息</a-menu-item>
              <a-menu-item key="export"><ExportOutlined /> 导出简历</a-menu-item>
              <a-menu-divider />
              <a-menu-item key="archive" danger><DeleteOutlined /> 归档候选人</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </a-space>
    </div>

    <!-- 候选人基本信息卡片 -->
    <a-card class="info-card">
      <a-row :gutter="24" align="middle">
        <a-col :span="3">
          <a-avatar :size="80" class="candidate-avatar">
            {{ candidateData.name[0] }}
          </a-avatar>
        </a-col>
        <a-col :span="21">
          <div class="candidate-header">
            <div class="candidate-main">
              <a-typography-title :level="3" style="margin: 0 0 8px 0">
                {{ candidateData.name }}
                <a-badge 
                  :status="candidateData.status === 'interview' ? 'processing' : 'success'" 
                  :text="candidateData.status === 'interview' ? '面试中' : '已入职'" 
                  style="margin-left: 12px" 
                />
              </a-typography-title>
              <a-space size="large" style="margin-bottom: 12px">
                <span class="contact-info"><PhoneOutlined style="margin-right: 4px" /> {{ candidateData.phone }}</span>
                <span class="contact-info"><MailOutlined style="margin-right: 4px" /> {{ candidateData.email }}</span>
              </a-space>
              <a-space wrap>
                <a-tag class="position-tag">{{ candidateData.position }}</a-tag>
                <a-tag class="channel-tag">Boss直聘</a-tag>
              </a-space>
            </div>
            <div class="candidate-meta">
              <div>HRBP：{{ candidateData.hrbp }}</div>
              <div>用人经理：{{ candidateData.hiringManager }}</div>
            </div>
          </div>
        </a-col>
      </a-row>
    </a-card>

    <!-- Tab区域 -->
    <a-card class="tabs-card">
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="info">
          <template #tab><span><UserOutlined /> 基本信息</span></template>
          <div class="info-section">
            <a-row :gutter="[24, 16]">
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">姓名</div>
                  <div class="info-value">{{ candidateData.name }}</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">性别</div>
                  <div class="info-value">男</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">年龄</div>
                  <div class="info-value">28岁</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">手机号</div>
                  <div class="info-value">{{ candidateData.phone }}</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">邮箱</div>
                  <div class="info-value">{{ candidateData.email }}</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">最高学历</div>
                  <div class="info-value">本科</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">毕业院校</div>
                  <div class="info-value">华东理工大学</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">专业</div>
                  <div class="info-value">计算机科学与技术</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">工作年限</div>
                  <div class="info-value">5年</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">当前公司</div>
                  <div class="info-value">字节跳动</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">期望薪资</div>
                  <div class="info-value">40K</div>
                </div>
              </a-col>
              <a-col :span="12">
                <div class="info-row">
                  <div class="info-label">简历来源</div>
                  <a-tag style="border-radius: 9999px; background: #ecdcff; color: #7431d3; border: none">Boss直聘</a-tag>
                </div>
              </a-col>
            </a-row>
          </div>
        </a-tab-pane>

        <a-tab-pane key="process">
          <template #tab><span><CalendarOutlined /> 招聘流程</span></template>
          <div class="process-section">
            <div class="timeline-section">
              <a-typography-title :level="5" style="margin-bottom: 16px">招聘进度</a-typography-title>
              <a-timeline>
                <a-timeline-item color="green">
                  <div><div style="font-weight: 600">简历筛选</div><div style="font-size: 12px; color: #414753">时间：2026-04-20 | 操作人：李明</div></div>
                </a-timeline-item>
                <a-timeline-item color="green">
                  <div><div style="font-weight: 600">HRBP评估</div><div style="font-size: 12px; color: #414753">时间：2026-04-21 | 操作人：李明</div></div>
                </a-timeline-item>
                <a-timeline-item color="green">
                  <div><div style="font-weight: 600">用人经理筛选</div><div style="font-size: 12px; color: #414753">时间：2026-04-22 | 操作人：王芳</div></div>
                </a-timeline-item>
                <a-timeline-item color="green">
                  <div><div style="font-weight: 600">邀约面试</div><div style="font-size: 12px; color: #414753">时间：2026-04-23 | 操作人：张强</div></div>
                </a-timeline-item>
                <a-timeline-item color="blue">
                  <div><div style="font-weight: 600">联合面试</div><div style="font-size: 12px; color: #414753">时间：2026-04-25 | 操作人：技术面试官</div></div>
                </a-timeline-item>
                <a-timeline-item color="gray">
                  <div><div style="font-weight: 600; color: #727785">综合面试</div><div style="font-size: 12px; color: #727785">时间：- | 操作人：-</div></div>
                </a-timeline-item>
                <a-timeline-item color="gray">
                  <div><div style="font-weight: 600; color: #727785">Offer沟通</div><div style="font-size: 12px; color: #727785">时间：- | 操作人：-</div></div>
                </a-timeline-item>
              </a-timeline>
            </div>
            <a-divider style="margin: 24px 0" />
            <div class="interview-section">
              <a-typography-title :level="5" style="margin-bottom: 16px">面试记录</a-typography-title>
              <div class="interview-table">
                <a-row class="interview-header">
                  <a-col :span="3">面试类型</a-col>
                  <a-col :span="4">面试时间</a-col>
                  <a-col :span="4">面试官</a-col>
                  <a-col :span="3">结果</a-col>
                  <a-col :span="7">反馈</a-col>
                  <a-col :span="3">操作</a-col>
                </a-row>
                <a-row class="interview-row" align="middle">
                  <a-col :span="3">联合面试</a-col>
                  <a-col :span="4">2026-04-25 14:00</a-col>
                  <a-col :span="4">技术面试官A、B</a-col>
                  <a-col :span="3"><a-tag color="success" style="border-radius: 9999px">通过</a-tag></a-col>
                  <a-col :span="7" style="color: #414753">技术能力强，项目经验丰富</a-col>
                  <a-col :span="3"><a-button type="link" size="small">查看详情</a-button></a-col>
                </a-row>
                <a-row class="interview-row" align="middle">
                  <a-col :span="3">笔试</a-col>
                  <a-col :span="4">2026-04-21 10:00</a-col>
                  <a-col :span="4">HR</a-col>
                  <a-col :span="3"><a-tag color="success" style="border-radius: 9999px">通过</a-tag></a-col>
                  <a-col :span="7" style="color: #414753">逻辑清晰，编码规范</a-col>
                  <a-col :span="3"><a-button type="link" size="small">查看详情</a-button></a-col>
                </a-row>
              </div>
            </div>
          </div>
        </a-tab-pane>

        <a-tab-pane key="resume">
          <template #tab><span><FileTextOutlined /> 简历信息</span></template>
          <div class="resume-section">
            <div class="empty-state">
              <FileTextOutlined style="font-size: 64px; color: #7431d3" />
              <a-typography-title :level="4" style="margin-top: 16px">简历预览</a-typography-title>
              <a-typography-text type="secondary">简历文件将在这里展示</a-typography-text>
              <div style="margin-top: 24px">
                <a-space>
                  <a-button type="primary" class="download-btn">
                    <template #icon><ExportOutlined /></template>
                    下载简历
                  </a-button>
                  <a-button>
                    <template #icon><EditOutlined /></template>
                    编辑简历
                  </a-button>
                </a-space>
              </div>
            </div>
          </div>
        </a-tab-pane>

        <a-tab-pane key="history">
          <template #tab><span><HistoryOutlined /> 操作记录</span></template>
          <div class="history-section">
            <a-timeline>
              <a-timeline-item>
                <div>
                  <a-tag color="blue" style="border-radius: 4px">发送面试通知</a-tag>
                  <a-typography-text type="secondary" style="font-size: 12px; margin-left: 8px">2026-04-27 10:30</a-typography-text>
                  <div style="margin-top: 4px"><a-typography-text type="secondary">操作人：张强</a-typography-text></div>
                  <div style="margin-top: 4px; color: #414753">发送给张三关于4月25日联合面试的通知</div>
                </div>
              </a-timeline-item>
              <a-timeline-item>
                <div>
                  <a-tag color="success" style="border-radius: 4px">完成面试</a-tag>
                  <a-typography-text type="secondary" style="font-size: 12px; margin-left: 8px">2026-04-25 14:00</a-typography-text>
                  <div style="margin-top: 4px"><a-typography-text type="secondary">操作人：系统</a-typography-text></div>
                  <div style="margin-top: 4px; color: #414753">联合面试已完成</div>
                </div>
              </a-timeline-item>
              <a-timeline-item>
                <div>
                  <a-tag color="blue" style="border-radius: 4px">安排面试</a-tag>
                  <a-typography-text type="secondary" style="font-size: 12px; margin-left: 8px">2026-04-23 16:00</a-typography-text>
                  <div style="margin-top: 4px"><a-typography-text type="secondary">操作人：张强</a-typography-text></div>
                  <div style="margin-top: 4px; color: #414753">安排联合面试时间：4月25日14:00</div>
                </div>
              </a-timeline-item>
              <a-timeline-item>
                <div>
                  <a-tag color="success" style="border-radius: 4px">筛选通过</a-tag>
                  <a-typography-text type="secondary" style="font-size: 12px; margin-left: 8px">2026-04-22 11:00</a-typography-text>
                  <div style="margin-top: 4px"><a-typography-text type="secondary">操作人：王芳</a-typography-text></div>
                  <div style="margin-top: 4px; color: #414753">用人经理筛选结果：通过</div>
                </div>
              </a-timeline-item>
              <a-timeline-item>
                <div>
                  <a-tag color="blue" style="border-radius: 4px">添加候选人</a-tag>
                  <a-typography-text type="secondary" style="font-size: 12px; margin-left: 8px">2026-04-20 09:00</a-typography-text>
                  <div style="margin-top: 4px"><a-typography-text type="secondary">操作人：张强</a-typography-text></div>
                  <div style="margin-top: 4px; color: #414753">从Boss直聘导入候选人信息</div>
                </div>
              </a-timeline-item>
            </a-timeline>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ArrowLeftOutlined,
  MailOutlined,
  PhoneOutlined,
  CalendarOutlined,
  UserOutlined,
  FileTextOutlined,
  HistoryOutlined,
  SendOutlined,
  MoreOutlined,
  EditOutlined,
  DeleteOutlined,
  ExportOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()

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

const goBack = () => {
  router.push('/candidates')
}

const showNotificationModal = () => {
  // TODO: 实现发送通知弹窗
}
</script>

<style scoped>
.candidate-detail-page {
  padding: 24px;
  background: #f8f9ff;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.back-btn {
  border: none;
  background: transparent;
}

.send-btn {
  background: #005ab6;
  border-color: #005ab6;
  border-radius: 8px;
  font-weight: 600;
}

.info-card {
  margin-bottom: 24px;
  border-radius: 24px;
  border: none;
  box-shadow: 0 8px 32px rgba(0,0,0,0.08);
}

.candidate-avatar {
  background: linear-gradient(135deg, #7431d3 0%, #005ab6 100%);
  font-size: 32px;
  font-weight: 700;
}

.candidate-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.contact-info {
  color: #414753;
}

.position-tag {
  border-radius: 9999px;
  padding: 4px 12px;
  border: none;
  background: #d7e3ff;
  color: #005ab6;
}

.channel-tag {
  border-radius: 9999px;
  padding: 4px 12px;
  border: none;
  background: #ecdcff;
  color: #7431d3;
}

.candidate-meta {
  text-align: right;
  color: #414753;
  font-size: 12px;
}

.tabs-card {
  border-radius: 24px;
  border: none;
  box-shadow: 0 8px 32px rgba(0,0,0,0.08);
}

.info-section {
  padding: 16px;
}

.info-row {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #dee3ed;
}

.info-label {
  width: 100px;
  color: #414753;
  font-size: 14px;
}

.info-value {
  font-weight: 600;
  color: #161c23;
}

.process-section,
.interview-table {
  background: #f8f9ff;
  border-radius: 12px;
  padding: 16px;
}

.interview-header {
  font-weight: 600;
  color: #414753;
  padding: 12px 0;
  border-bottom: 1px solid #dee3ed;
}

.interview-row {
  padding: 12px 0;
  border-bottom: 1px solid #dee3ed;
}

.resume-section {
  text-align: center;
  padding: 60px 0;
}

.download-btn {
  background: #005ab6;
  border-color: #005ab6;
  border-radius: 8px;
}

.empty-state {
  padding: 40px;
}

.history-section {
  padding: 16px;
}
</style>