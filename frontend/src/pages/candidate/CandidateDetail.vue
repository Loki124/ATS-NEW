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
        <a-button type="primary" @click="openNotificationModal" class="send-btn">
          <template #icon><SendOutlined /></template>
          发送通知
        </a-button>
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
            <!-- 有简历时 -->
            <div v-if="resumeData.url" class="resume-content">
              <div class="resume-toolbar">
                <a-space>
                  <a-button type="primary" class="download-btn" @click="handleDownloadResume">
                    <template #icon><ExportOutlined /></template>
                    下载简历
                  </a-button>
                  <a-button @click="openEditResumeModal">
                    编辑简历
                  </a-button>
                </a-space>
              </div>
              <div class="resume-preview">
                <a-typography-title :level="5">简历预览</a-typography-title>
                <div class="resume-info">
                  <div class="resume-field">
                    <span class="field-label">姓名：</span>
                    <span class="field-value">{{ resumeData.name }}</span>
                  </div>
                  <div class="resume-field">
                    <span class="field-label">手机号：</span>
                    <span class="field-value">{{ resumeData.phone }}</span>
                  </div>
                  <div class="resume-field">
                    <span class="field-label">邮箱：</span>
                    <span class="field-value">{{ resumeData.email }}</span>
                  </div>
                  <div class="resume-field">
                    <span class="field-label">最高学历：</span>
                    <span class="field-value">{{ resumeData.education }}</span>
                  </div>
                  <div class="resume-field">
                    <span class="field-label">毕业院校：</span>
                    <span class="field-value">{{ resumeData.school }}</span>
                  </div>
                  <div class="resume-field">
                    <span class="field-label">工作年限：</span>
                    <span class="field-value">{{ resumeData.workYears }}年</span>
                  </div>
                  <div class="resume-field">
                    <span class="field-label">当前公司：</span>
                    <span class="field-value">{{ resumeData.currentCompany }}</span>
                  </div>
                  <div class="resume-field">
                    <span class="field-label">期望薪资：</span>
                    <span class="field-value">{{ resumeData.expectedSalary }}</span>
                  </div>
                  <div class="resume-field">
                    <span class="field-label">简历来源：</span>
                    <span class="field-value">{{ resumeData.source }}</span>
                  </div>
                </div>
              </div>
            </div>
            <!-- 无简历时 -->
            <div v-else class="empty-state">
              <FileTextOutlined style="font-size: 64px; color: #7431d3" />
              <a-typography-title :level="4" style="margin-top: 16px">暂无简历</a-typography-title>
              <a-typography-text type="secondary">该候选人还没有上传简历</a-typography-text>
              <div style="margin-top: 24px">
                <a-space>
                  <a-button type="primary" @click="openUploadResumeModal">
                    <template #icon><UploadOutlined /></template>
                    上传简历
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

    <!-- 发送通知弹窗 -->
    <a-modal
      v-model:open="notificationModalVisible"
      :width="1000"
      :footer="null"
      :maskClosable="false"
      class="notification-modal"
    >
      <template #title>
        <div class="modal-header">
          <span class="modal-title">发送通知</span>
          <button class="close-btn" @click="notificationModalVisible = false">
            <CloseOutlined />
          </button>
        </div>
        <div class="candidate-summary">
          <a-avatar :size="48" class="candidate-avatar-sm">
            {{ candidateData.name[0] }}
          </a-avatar>
          <div class="candidate-info">
            <div class="candidate-name-row">
              <span class="candidate-name">{{ candidateData.name }}</span>
              <a-tag class="position-tag-sm">{{ candidateData.position }}</a-tag>
              <a-tag class="experience-tag">5年经验</a-tag>
            </div>
            <div class="candidate-contact-row">
              <span><PhoneOutlined /> {{ candidateData.phone }}</span>
              <span><MailOutlined /> {{ candidateData.email }}</span>
            </div>
          </div>
        </div>
      </template>

      <div class="modal-content">
        <!-- 左侧选择区域 -->
        <div class="left-sidebar">
          <!-- Step 1: 选择发送内容 -->
          <div class="step-section">
            <h3 class="step-title">
              <span class="step-number">1</span>
              选择发送内容
            </h3>
            <!-- 提示信息 -->
            <div class="info-callout">
              <span>系统将基于选择的「发送内容」自动为候选人生成对应待办，选择多个内容时会同时发送</span>
            </div>
            <div class="step-content">
              <!-- 面试登记表 -->
              <div class="content-group">
                <div class="content-group-title">面试登记表</div>
                <label class="content-item selected">
                  <a-checkbox v-model:checked="notificationForm.interviewForm"></a-checkbox>
                  <span>收集候选人基本信息</span>
                </label>
              </div>
              <!-- 性格测试 -->
              <div class="content-group">
                <div class="content-group-title">性格测试</div>
                <div class="radio-group">
                  <label class="radio-item">
                    <a-radio-group v-model:value="notificationForm.personalityTest">
                      <a-radio value="pdp_mbti_20">PDP+20题版MBTI</a-radio>
                    </a-radio-group>
                  </label>
                  <label class="radio-item">
                    <a-radio-group v-model:value="notificationForm.personalityTest">
                      <a-radio value="pdp_mbti_93">PDP+93题版MBTI</a-radio>
                    </a-radio-group>
                  </label>
                </div>
              </div>
              <!-- 应聘登记表 -->
              <div class="content-group">
                <div class="content-group-title">应聘登记表</div>
                <label class="content-item">
                  <a-checkbox v-model:checked="notificationForm.applicationForm"></a-checkbox>
                  <span>完善工作履历及教育背景</span>
                </label>
              </div>
              <!-- 入职材料 -->
              <div class="content-group">
                <div class="content-group-title">入职材料</div>
                <label class="content-item">
                  <a-checkbox v-model:checked="notificationForm.onboardingDocs"></a-checkbox>
                  <span>收集入职资料及相关证明</span>
                </label>
              </div>
            </div>
          </div>

          <!-- Step 2: 选择通知方式 -->
          <div class="step-section">
            <h3 class="step-title">
              <span class="step-number">2</span>
              选择通知方式
            </h3>
            <div class="step-content">
              <label class="method-item selected">
                <a-checkbox v-model:checked="notificationForm.sendEmail"></a-checkbox>
                <MailOutlined class="method-icon" />
                <span class="method-name">邮件通知</span>
              </label>
              <label class="method-item selected">
                <a-checkbox v-model:checked="notificationForm.sendSms"></a-checkbox>
                <MessageOutlined class="method-icon" />
                <span class="method-name">短信通知</span>
              </label>
              <label class="method-item">
                <a-checkbox v-model:checked="notificationForm.sendWechat"></a-checkbox>
                <WechatOutlined class="method-icon" />
                <span class="method-name">微信企业号推送</span>
              </label>
            </div>
          </div>
        </div>

        <!-- 右侧内容区域 -->
        <div class="right-content">
          <!-- 邮件通知编辑 -->
          <div class="editor-section" v-if="notificationForm.sendEmail">
            <div class="editor-header">
              <MailOutlined class="editor-icon" />
              <h4 class="editor-title">邮件通知</h4>
            </div>
            <div class="editor-field">
              <label class="field-label">邮件主题</label>
              <a-input
                v-model:value="notificationForm.emailSubject"
                class="email-subject-input"
              />
            </div>
            <div class="editor-field">
              <label class="field-label">邮件正文</label>
              <a-textarea
                v-model:value="notificationForm.emailContent"
                :rows="8"
                class="email-content-input"
              />
            </div>
          </div>

          <!-- 短信通知编辑 -->
          <div class="editor-section" v-if="notificationForm.sendSms">
            <div class="editor-header">
              <MessageOutlined class="editor-icon" />
              <h4 class="editor-title">短信通知</h4>
            </div>
            <div class="editor-field">
              <div class="sms-counter">
                <label class="field-label">短信正文</label>
                <span class="counter-text">已输入 <strong>{{ notificationForm.smsContent.length }}</strong> / 70 字</span>
              </div>
              <a-textarea
                v-model:value="notificationForm.smsContent"
                :rows="4"
                class="sms-content-input"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 底部 -->
      <div class="modal-footer">
        <div class="recipient-info">
          通知将发送至: 1个手机号, 1个邮箱地址
        </div>
        <div class="footer-buttons">
          <a-button @click="notificationModalVisible = false">取消</a-button>
          <a-button type="primary" class="send-btn-primary" @click="handleSendNotification">
            <template #icon><SendOutlined /></template>
            确认发送
          </a-button>
        </div>
      </div>
    </a-modal>

    <!-- 编辑简历弹窗 -->
    <a-modal
      v-model:open="editResumeModalVisible"
      title="编辑简历"
      :width="600"
      @ok="handleSaveResume"
      @cancel="editResumeModalVisible = false"
      okText="保存"
      cancelText="取消"
    >
      <a-form :model="resumeForm" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="姓名">
              <a-input v-model:value="resumeForm.name" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="手机号">
              <a-input v-model:value="resumeForm.phone" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="邮箱">
              <a-input v-model:value="resumeForm.email" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="最高学历">
              <a-select v-model:value="resumeForm.education">
                <a-select-option value="高中">高中</a-select-option>
                <a-select-option value="大专">大专</a-select-option>
                <a-select-option value="本科">本科</a-select-option>
                <a-select-option value="硕士">硕士</a-select-option>
                <a-select-option value="博士">博士</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="毕业院校">
              <a-input v-model:value="resumeForm.school" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="工作年限">
              <a-input-number v-model:value="resumeForm.workYears" :min="0" :max="50" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="当前公司">
              <a-input v-model:value="resumeForm.currentCompany" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="期望薪资">
              <a-input v-model:value="resumeForm.expectedSalary" placeholder="如: 40K" />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>

    <!-- 上传简历弹窗 -->
    <a-modal
      v-model:open="uploadResumeModalVisible"
      title="上传简历"
      :width="500"
      @ok="handleUploadResume"
      @cancel="uploadResumeModalVisible = false"
      okText="上传"
      cancelText="取消"
    >
      <a-upload
        v-model:fileList="fileList"
        name="file"
        :maxCount="1"
        :beforeUpload="beforeUpload"
        accept=".pdf,.doc,.docx"
      >
        <a-button>
          <UploadOutlined /> 选择文件
        </a-button>
      </a-upload>
      <div class="upload-tip">支持 PDF、Word 格式文件，大小不超过 10MB</div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
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
  CloseOutlined,
  MessageOutlined,
  WechatOutlined,
  UploadOutlined,
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

// 简历数据
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

const handleDownloadResume = () => {
  if (resumeData.value.url) {
    message.success('开始下载简历')
    // 实际项目中这里会触发下载
    // window.open(resumeData.value.url, '_blank')
  } else {
    message.warning('暂无简历可下载')
  }
}

const openUploadResumeModal = () => {
  uploadResumeModalVisible.value = true
}

const openEditResumeModal = () => {
  message.info('编辑简历按钮点击成功')
  editResumeModalVisible.value = true
}

const uploadResumeModalVisible = ref(false)
const editResumeModalVisible = ref(false)
const fileList = ref<any[]>([])

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

const beforeUpload = (file: any) => {
  const isPDF = file.type === 'application/pdf'
  const isDoc = file.type === 'application/msword' || file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  const isLessThan10M = file.size / 1024 / 1024 < 10

  if (!isPDF && !isDoc) {
    message.error('只支持 PDF、Word 格式文件!')
    return false
  }
  if (!isLessThan10M) {
    message.error('文件大小不能超过 10MB!')
    return false
  }
  return true
}

const handleSaveResume = () => {
  // DEBUG: 保存简历
  message.success('简历保存成功')
  editResumeModalVisible.value = false
}

const handleUploadResume = () => {
  if (fileList.value.length === 0) {
    message.warning('请选择要上传的文件')
    return
  }
  // DEBUG: 上传简历
  message.success('简历上传成功')
  uploadResumeModalVisible.value = false
  fileList.value = []
}

const goBack = () => {
  router.push('/candidates')
}

const openNotificationModal = () => {
  notificationModalVisible.value = true
}

// 发送通知弹窗
const notificationModalVisible = ref(false)
const notificationForm = ref({
  interviewForm: true,
  personalityTest: 'pdp_mbti_20',
  applicationForm: false,
  onboardingDocs: false,
  sendEmail: true,
  sendSms: true,
  sendWechat: false,
  emailSubject: '【ATS招聘系统】面试邀请与前期准备事项',
  emailContent: `尊敬的 {{候选人姓名}}，您好！

感谢您对我司的关注。很高兴通知您，您的简历已通过初步筛选，我们诚邀您参加【{{职位名称}}】岗位的视频面试。

在面试前，为了更全面地了解您，请您点击下方专属链接，完成相关信息的填写：

📝 [面试登记表单] {{表单_面试登记表单_链接}}

如您在填写过程中有任何疑问，请随时通过本邮件与我们联系。

祝您一切顺利！
ATS 招聘团队`,
  smsContent: '【ATS招聘系统】{{候选人姓名}}您好，诚邀您参加{{职位名称}}面试。为保证流程顺畅，请在今天内点击短链接完成信息登记：{{表单_面试登记表单_短链接}}。详情已发送至您的邮箱，请注意查收。退订回T',
})

const handleSendNotification = () => {
  // DEBUG: 发送通知
  message.success('通知已发送')
  notificationModalVisible.value = false
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
  padding: 24px;
}

.resume-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.resume-toolbar {
  display: flex;
  justify-content: flex-start;
}

.resume-preview {
  background: #f8f9ff;
  border-radius: 12px;
  padding: 24px;
}

.resume-preview :deep(.ant-typography) {
  margin-bottom: 16px;
}

.resume-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.resume-field {
  display: flex;
  align-items: center;
}

.resume-field .field-label {
  width: 100px;
  color: #414753;
  font-size: 14px;
}

.resume-field .field-value {
  color: #161c23;
  font-weight: 500;
  font-size: 14px;
}

.upload-tip {
  margin-top: 16px;
  color: #727785;
  font-size: 12px;
}

.resume-section .download-btn {
  background: #005ab6;
  border-color: #005ab6;
  border-radius: 8px;
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

.notification-modal :deep(.ant-form-item-label > label) {
  font-weight: 500;
  color: #414753;
}

/* 发送通知弹窗样式 */
.notification-modal :deep(.ant-modal-content) {
  padding: 0;
  border-radius: 12px;
  overflow: hidden;
}

.notification-modal :deep(.ant-modal-body) {
  padding: 0;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(194, 198, 213, 0.4);
}

.modal-title {
  font-size: 20px;
  font-weight: 700;
  color: #161c23;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #414753;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(222, 227, 237, 0.5);
  color: #161c23;
}

.candidate-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #ecf1fb;
  border-radius: 8px;
  padding: 12px;
  margin-top: 16px;
}

.candidate-avatar-sm {
  background: linear-gradient(135deg, #7431d3 0%, #005ab6 100%);
  font-size: 20px;
  font-weight: 600;
}

.candidate-info {
  flex: 1;
}

.candidate-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.candidate-name {
  font-size: 16px;
  font-weight: 600;
  color: #161c23;
}

.position-tag-sm {
  background: #d7e3ff;
  color: #00458e;
  border: none;
  border-radius: 9999px;
  font-size: 12px;
  padding: 2px 8px;
}

.experience-tag {
  background: #dee3ed;
  color: #414753;
  border: none;
  border-radius: 9999px;
  font-size: 12px;
  padding: 2px 8px;
}

.candidate-contact-row {
  display: flex;
  gap: 16px;
  font-size: 14px;
  color: #414753;
}

.candidate-contact-row span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.modal-content {
  display: flex;
  min-height: 400px;
}

.left-sidebar {
  width: 340px;
  background: #f8f9ff;
  border-right: 1px solid rgba(194, 198, 213, 0.4);
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.step-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step-title {
  font-size: 16px;
  font-weight: 600;
  color: #161c23;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.step-number {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #1672df;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.content-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.content-group-title {
  font-size: 14px;
  font-weight: 600;
  color: #161c23;
  padding-left: 4px;
}

.content-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #c1c6d5;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: #161c23;
}

.content-item:hover {
  border-color: #005ab6;
  background: #f0f7ff;
}

.content-item.selected {
  border-color: #005ab6;
  background: rgba(215, 227, 255, 0.2);
}

.radio-group {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid rgba(194, 198, 213, 0.6);
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.radio-item {
  font-size: 14px;
  color: #414753;
  cursor: pointer;
}

.radio-item:hover {
  color: #161c23;
}

.method-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #c1c6d5;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.method-item:hover {
  border-color: #005ab6;
  background: #f0f7ff;
}

.method-item.selected {
  border-color: #005ab6;
  background: rgba(215, 227, 255, 0.2);
}

.method-icon {
  font-size: 20px;
  color: #005ab6;
}

.method-name {
  font-size: 14px;
  font-weight: 600;
  color: #161c23;
}

.right-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
  background: #fff;
}

.info-callout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 214, 102, 0.1);
  border: 1px solid #ffd666;
  border-radius: 8px;
  font-size: 14px;
  color: #765c00;
}

.info-callout .info-icon {
  color: #765c00;
  font-size: 20px;
  flex-shrink: 0;
}

.right-content .info-callout {
  margin-bottom: 0;
}

.editor-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editor-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(194, 198, 213, 0.3);
}

.editor-icon {
  font-size: 24px;
  color: #005ab6;
}

.editor-title {
  font-size: 16px;
  font-weight: 600;
  color: #161c23;
  margin: 0;
}

.editor-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 12px;
  font-weight: 500;
  color: #414753;
}

.sms-counter {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.counter-text {
  font-size: 12px;
  color: #727785;
}

.counter-text strong {
  color: #005ab6;
  font-weight: 500;
}

.email-subject-input,
.email-content-input,
.sms-content-input {
  background: rgba(222, 227, 237, 0.3);
  border: 1px solid rgba(194, 198, 213, 0.3);
  border-radius: 6px;
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-top: 1px solid rgba(194, 198, 213, 0.4);
  background: #f8f9ff;
}

.recipient-info {
  font-size: 12px;
  color: #414753;
}

.footer-buttons {
  display: flex;
  gap: 16px;
  align-items: center;
}

.footer-buttons :deep(.ant-btn) {
  height: 40px;
  padding: 0 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.footer-buttons :deep(.ant-btn:not(.send-btn-primary)) {
  color: #414753;
}

.footer-buttons :deep(.ant-btn:not(.send-btn-primary):hover) {
  background: rgba(222, 227, 237, 0.5);
  color: #161c23;
}

.send-btn-primary {
  background: #ffd666 !important;
  border-color: #ffd666 !important;
  color: #241a00 !important;
}

.send-btn-primary:hover {
  background: #ffdf90 !important;
  border-color: #ffdf90 !important;
}

.send-btn-primary :deep(.anticon) {
  margin-right: 6px;
}
</style>