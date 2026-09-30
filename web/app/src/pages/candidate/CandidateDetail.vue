<template>
  <div class="candidate-detail-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <n-space>
        <n-button class="back-btn" @click="goBack">
          <template #icon><n-icon :component="ChevronBackOutline" /></template>
          {{ t('pages.candidate.CandidateDetail.s1') }}
        </n-button>
        <n-h4 style="margin: 0; font-weight: 700">{{ t('pages.candidate.CandidateDetail.s2') }}</n-h4>
      </n-space>

      <n-space>
        <n-button type="primary" class="send-btn" @click="openNotificationModal">
          <template #icon><n-icon :component="PaperPlaneOutline" /></template>
          {{ t('pages.candidate.CandidateDetail.s3') }}
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
                  {{ candidateData.status === 'interview' ? t('pages.candidate.CandidateDetail.s99') : t('pages.candidate.CandidateDetail.s100') }}
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
                <n-tag class="channel-tag" :bordered="false">{{ t('pages.candidate.CandidateDetail.s4') }}</n-tag>
              </n-space>
            </div>
            <div class="candidate-meta">
              <div>HRBP：{{ candidateData.hrbp }}</div>
              <div>{{ t('pages.candidate.CandidateDetail.s5') }}{{ candidateData.hiringManager }}</div>
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
            <span><n-icon :component="PersonOutline" />{{ t('pages.candidate.CandidateDetail.s6') }}</span>
          </template>
          <div class="info-section">
            <n-grid :cols="2" :x-gap="24" :y-gap="16" responsive="screen">
              <n-grid-item v-for="f in displayFields" :key="f.fieldKey">
                <div class="info-row">
                  <div class="info-label">{{ f.label }}</div>
                  <div class="info-value">{{ f.value }}</div>
                </div>
              </n-grid-item>
              <n-grid-item v-if="displayFields.length === 0 && !loading">
                <n-empty :description="t('pages.candidate.CandidateDetail.s7')" />
              </n-grid-item>
            </n-grid>
            <n-spin v-if="loading" style="margin-top: 16px" />
          </div>
        </n-tab-pane>

        <!-- 招聘流程 -->
        <n-tab-pane name="process">
          <template #tab>
            <span><n-icon :component="CalendarOutline" />{{ t('pages.candidate.CandidateDetail.s8') }}</span>
          </template>
          <div class="process-section">
            <div class="timeline-section">
              <n-h5 style="margin-bottom: 16px">{{ t('pages.candidate.CandidateDetail.s9') }}</n-h5>
              <n-timeline>
                <n-timeline-item type="success" :content="t('pages.candidate.CandidateDetail.s10')" time="2026-04-20" line-type="success" />
                <n-timeline-item type="success" :content="t('pages.candidate.CandidateDetail.s11')" time="2026-04-21" line-type="success" />
                <n-timeline-item type="success" :content="t('pages.candidate.CandidateDetail.s12')" time="2026-04-22" line-type="success" />
                <n-timeline-item type="success" :content="t('pages.candidate.CandidateDetail.s13')" time="2026-04-23" line-type="success" />
                <n-timeline-item type="info" :content="t('pages.candidate.CandidateDetail.s14')" time="2026-04-25" line-type="info" />
                <n-timeline-item :content="t('pages.candidate.CandidateDetail.s15')" time="-" line-type="default" />
                <n-timeline-item :content="t('pages.candidate.CandidateDetail.s16')" time="-" line-type="default" />
              </n-timeline>
            </div>
            <n-divider style="margin: 24px 0" />
            <div class="interview-section">
              <n-h5 style="margin-bottom: 16px">{{ t('pages.candidate.CandidateDetail.s17') }}</n-h5>
              <div class="interview-table">
                <div class="interview-header grid grid-cols-12 gap-2">
                  <div class="col-span-3">{{ t('pages.candidate.CandidateDetail.s18') }}</div>
                  <div class="col-span-4">{{ t('pages.candidate.CandidateDetail.s19') }}</div>
                  <div class="col-span-4">{{ t('pages.candidate.CandidateDetail.s20') }}</div>
                  <div class="col-span-3">{{ t('pages.candidate.CandidateDetail.s21') }}</div>
                  <div class="col-span-7">{{ t('pages.candidate.CandidateDetail.s22') }}</div>
                  <div class="col-span-3">{{ t('pages.candidate.CandidateDetail.s23') }}</div>
                </div>
                <div class="interview-row grid grid-cols-12 gap-2 items-center">
                  <div class="col-span-3">{{ t('pages.candidate.CandidateDetail.s24') }}</div>
                  <div class="col-span-4">2026-04-25 14:00</div>
                  <div class="col-span-4">{{ t('pages.candidate.CandidateDetail.s25') }}</div>
                  <div class="col-span-3"><n-tag type="success" :bordered="false">{{ t('pages.candidate.CandidateDetail.s26') }}</n-tag></div>
                  <div class="col-span-7" style="color: var(--ink-soft)">{{ t('pages.candidate.CandidateDetail.s27') }}</div>
                  <div class="col-span-3"><n-button text type="primary" size="small">{{ t('pages.candidate.CandidateDetail.s28') }}</n-button></div>
                </div>
                <div class="interview-row grid grid-cols-12 gap-2 items-center">
                  <div class="col-span-3">{{ t('pages.candidate.CandidateDetail.s29') }}</div>
                  <div class="col-span-4">2026-04-21 10:00</div>
                  <div class="col-span-4">HR</div>
                  <div class="col-span-3"><n-tag type="success" :bordered="false">{{ t('pages.candidate.CandidateDetail.s30') }}</n-tag></div>
                  <div class="col-span-7" style="color: var(--ink-soft)">{{ t('pages.candidate.CandidateDetail.s31') }}</div>
                  <div class="col-span-3"><n-button text type="primary" size="small">{{ t('pages.candidate.CandidateDetail.s32') }}</n-button></div>
                </div>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <!-- 简历信息 -->
        <n-tab-pane name="resume">
          <template #tab>
            <span><n-icon :component="DocumentTextOutline" />{{ t('pages.candidate.CandidateDetail.s33') }}</span>
          </template>
          <div class="resume-section">
            <div v-if="resumeData.url" class="resume-content">
              <div class="resume-toolbar">
                <n-space>
                  <n-button type="primary" class="download-btn" @click="handleDownloadResume">
                    <template #icon><n-icon :component="DownloadOutline" /></template>
                    {{ t('pages.candidate.CandidateDetail.s34') }}
                  </n-button>
                  <n-button v-permission="'recruit:candidate:edit'" @click="openEditResumeModal">{{ t('pages.candidate.CandidateDetail.s35') }}</n-button>
                </n-space>
              </div>
              <div class="resume-preview">
                <n-h5>{{ t('pages.candidate.CandidateDetail.s36') }}</n-h5>
                <div class="resume-info">
                  <div class="resume-field"><span class="field-label">{{ t('pages.candidate.CandidateDetail.s37') }}</span><span class="field-value">{{ resumeData.name }}</span></div>
                  <div class="resume-field"><span class="field-label">{{ t('pages.candidate.CandidateDetail.s38') }}</span><span class="field-value">{{ resumeData.phone }}</span></div>
                  <div class="resume-field"><span class="field-label">{{ t('pages.candidate.CandidateDetail.s39') }}</span><span class="field-value">{{ resumeData.email }}</span></div>
                  <div class="resume-field"><span class="field-label">{{ t('pages.candidate.CandidateDetail.s40') }}</span><span class="field-value">{{ resumeData.education }}</span></div>
                  <div class="resume-field"><span class="field-label">{{ t('pages.candidate.CandidateDetail.s41') }}</span><span class="field-value">{{ resumeData.school }}</span></div>
                  <div class="resume-field"><span class="field-label">{{ t('pages.candidate.CandidateDetail.s42') }}</span><span class="field-value">{{ resumeData.workYears }}{{ t('pages.candidate.CandidateDetail.s43') }}</span></div>
                  <div class="resume-field"><span class="field-label">{{ t('pages.candidate.CandidateDetail.s44') }}</span><span class="field-value">{{ resumeData.currentCompany }}</span></div>
                  <div class="resume-field"><span class="field-label">{{ t('pages.candidate.CandidateDetail.s45') }}</span><span class="field-value">{{ resumeData.expectedSalary }}</span></div>
                  <div class="resume-field"><span class="field-label">{{ t('pages.candidate.CandidateDetail.s46') }}</span><span class="field-value">{{ resumeData.source }}</span></div>
                </div>
              </div>
            </div>
            <div v-else class="empty-state text-center">
              <n-icon :component="DocumentTextOutline" :size="64" color="var(--brand)" />
              <n-h4 style="margin-top: 16px">{{ t('pages.candidate.CandidateDetail.s47') }}</n-h4>
              <n-text :depth="3">{{ t('pages.candidate.CandidateDetail.s48') }}</n-text>
              <div style="margin-top: 24px">
                <n-space>
                  <n-button type="primary" @click="openUploadResumeModal">
                    <template #icon><n-icon :component="CloudUploadOutline" /></template>
                    {{ t('pages.candidate.CandidateDetail.s49') }}
                  </n-button>
                </n-space>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <!-- 操作记录 -->
        <n-tab-pane name="history">
          <template #tab>
            <span><n-icon :component="TimeOutline" />{{ t('pages.candidate.CandidateDetail.s50') }}</span>
          </template>
          <div class="history-section">
            <n-timeline>
              <n-timeline-item>
                <div>
                  <n-tag type="info" :bordered="false">{{ t('pages.candidate.CandidateDetail.s51') }}</n-tag>
                  <n-text :depth="3" style="font-size: var(--fs-12); margin-left: 8px">2026-04-27 10:30</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">{{ t('pages.candidate.CandidateDetail.s52') }}</n-text></div>
                  <div style="margin-top: var(--space-1); color: var(--ink-soft)">{{ t('pages.candidate.CandidateDetail.s53') }}</div>
                </div>
              </n-timeline-item>
              <n-timeline-item>
                <div>
                  <n-tag type="success" :bordered="false">{{ t('pages.candidate.CandidateDetail.s54') }}</n-tag>
                  <n-text :depth="3" style="font-size: var(--fs-12); margin-left: 8px">2026-04-25 14:00</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">{{ t('pages.candidate.CandidateDetail.s55') }}</n-text></div>
                  <div style="margin-top: var(--space-1); color: var(--ink-soft)">{{ t('pages.candidate.CandidateDetail.s56') }}</div>
                </div>
              </n-timeline-item>
              <n-timeline-item>
                <div>
                  <n-tag type="info" :bordered="false">{{ t('pages.candidate.CandidateDetail.s57') }}</n-tag>
                  <n-text :depth="3" style="font-size: var(--fs-12); margin-left: 8px">2026-04-23 16:00</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">{{ t('pages.candidate.CandidateDetail.s58') }}</n-text></div>
                  <div style="margin-top: var(--space-1); color: var(--ink-soft)">{{ t('pages.candidate.CandidateDetail.s59') }}</div>
                </div>
              </n-timeline-item>
              <n-timeline-item>
                <div>
                  <n-tag type="success" :bordered="false">{{ t('pages.candidate.CandidateDetail.s60') }}</n-tag>
                  <n-text :depth="3" style="font-size: var(--fs-12); margin-left: 8px">2026-04-22 11:00</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">{{ t('pages.candidate.CandidateDetail.s61') }}</n-text></div>
                  <div style="margin-top: var(--space-1); color: var(--ink-soft)">{{ t('pages.candidate.CandidateDetail.s62') }}</div>
                </div>
              </n-timeline-item>
              <n-timeline-item>
                <div>
                  <n-tag type="info" :bordered="false">{{ t('pages.candidate.CandidateDetail.s63') }}</n-tag>
                  <n-text :depth="3" style="font-size: var(--fs-12); margin-left: 8px">2026-04-20 09:00</n-text>
                  <div style="margin-top: 4px"><n-text :depth="3">{{ t('pages.candidate.CandidateDetail.s64') }}</n-text></div>
                  <div style="margin-top: var(--space-1); color: var(--ink-soft)">{{ t('pages.candidate.CandidateDetail.s65') }}</div>
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
          <span class="modal-title">{{ t('pages.candidate.CandidateDetail.s66') }}</span>
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
              <n-tag class="experience-tag" :bordered="false">{{ t('pages.candidate.CandidateDetail.s67') }}</n-tag>
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
              {{ t('pages.candidate.CandidateDetail.s68') }}
            </h3>
            <div class="info-callout">
              <span>{{ t('pages.candidate.CandidateDetail.s69') }}</span>
            </div>
            <div class="step-content">
              <div class="content-group">
                <div class="content-group-title">{{ t('pages.candidate.CandidateDetail.s70') }}</div>
                <label class="content-item selected">
                  <n-checkbox v-model:checked="notificationForm.interviewForm" />
                  <span>{{ t('pages.candidate.CandidateDetail.s71') }}</span>
                </label>
              </div>
              <div class="content-group">
                <div class="content-group-title">{{ t('pages.candidate.CandidateDetail.s72') }}</div>
                <n-radio-group v-model:value="notificationForm.personalityTest">
                  <n-space vertical>
                    <n-radio value="pdp_mbti_20">{{ t('pages.candidate.CandidateDetail.s73') }}</n-radio>
                    <n-radio value="pdp_mbti_93">{{ t('pages.candidate.CandidateDetail.s74') }}</n-radio>
                  </n-space>
                </n-radio-group>
              </div>
              <div class="content-group">
                <div class="content-group-title">{{ t('pages.candidate.CandidateDetail.s75') }}</div>
                <label class="content-item">
                  <n-checkbox v-model:checked="notificationForm.applicationForm" />
                  <span>{{ t('pages.candidate.CandidateDetail.s76') }}</span>
                </label>
              </div>
              <div class="content-group">
                <div class="content-group-title">{{ t('pages.candidate.CandidateDetail.s77') }}</div>
                <label class="content-item">
                  <n-checkbox v-model:checked="notificationForm.onboardingDocs" />
                  <span>{{ t('pages.candidate.CandidateDetail.s78') }}</span>
                </label>
              </div>
            </div>
          </div>

          <div class="step-section">
            <h3 class="step-title">
              <span class="step-number">2</span>
              {{ t('pages.candidate.CandidateDetail.s79') }}
            </h3>
            <div class="step-content">
              <label class="method-item selected">
                <n-checkbox v-model:checked="notificationForm.sendEmail" />
                <n-icon :component="MailOutline" class="method-icon" />
                <span class="method-name">{{ t('pages.candidate.CandidateDetail.s80') }}</span>
              </label>
              <label class="method-item selected">
                <n-checkbox v-model:checked="notificationForm.sendSms" />
                <n-icon :component="ChatbubblesOutline" class="method-icon" />
                <span class="method-name">{{ t('pages.candidate.CandidateDetail.s81') }}</span>
              </label>
              <label class="method-item">
                <n-checkbox v-model:checked="notificationForm.sendWechat" />
                <n-icon :component="LogoWechat" class="method-icon" />
                <span class="method-name">{{ t('pages.candidate.CandidateDetail.s82') }}</span>
              </label>
            </div>
          </div>
        </div>

        <div class="right-content">
          <div v-if="notificationForm.sendEmail" class="editor-section">
            <div class="editor-header">
              <n-icon :component="MailOutline" class="editor-icon" />
              <h4 class="editor-title">{{ t('pages.candidate.CandidateDetail.s83') }}</h4>
            </div>
            <div class="editor-field">
              <label class="field-label">{{ t('pages.candidate.CandidateDetail.s84') }}</label>
              <n-input v-model:value="notificationForm.emailSubject" class="email-subject-input" />
            </div>
            <div class="editor-field">
              <label class="field-label">{{ t('pages.candidate.CandidateDetail.s85') }}</label>
              <n-input v-model:value="notificationForm.emailContent" type="textarea" :rows="8" class="email-content-input" />
            </div>
          </div>

          <div v-if="notificationForm.sendSms" class="editor-section">
            <div class="editor-header">
              <n-icon :component="ChatbubblesOutline" class="editor-icon" />
              <h4 class="editor-title">{{ t('pages.candidate.CandidateDetail.s86') }}</h4>
            </div>
            <div class="editor-field">
              <div class="sms-counter">
                <label class="field-label">{{ t('pages.candidate.CandidateDetail.s87') }}</label>
                <span class="counter-text">{{ t('pages.candidate.CandidateDetail.s101') }} <strong>{{ notificationForm.smsContent.length }}</strong>{{ t('pages.candidate.CandidateDetail.s88') }}</span>
              </div>
              <n-input v-model:value="notificationForm.smsContent" type="textarea" :rows="4" class="sms-content-input" />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer">
          <div class="recipient-info">{{ t('pages.candidate.CandidateDetail.s89') }}</div>
          <div class="footer-buttons">
            <n-button @click="notificationModalVisible = false">{{ t('pages.candidate.CandidateDetail.s90') }}</n-button>
            <n-button type="primary" class="send-btn-primary" @click="handleSendNotification">
              <template #icon><n-icon :component="PaperPlaneOutline" /></template>
              {{ t('pages.candidate.CandidateDetail.s91') }}
            </n-button>
          </div>
        </div>
      </template>
    </n-modal>

    <!-- 编辑简历弹窗 (按标准简历配置驱动, 全部 enabled 字段可编辑) -->
    <n-modal
      v-model:show="editResumeModalVisible"
      preset="card"
      :title="t('pages.candidate.CandidateDetail.s92')"
      :width="640"
      style="max-width: 92vw"
    >
      <n-spin :show="savingResume">
        <n-form label-placement="top">
          <n-grid :cols="2" :x-gap="16" :y-gap="0" responsive="screen">
            <n-grid-item
              v-for="f in displayFields"
              :key="f.fieldKey"
              :span="controlType(f.fieldKey) === 'textarea' ? 2 : 1"
            >
              <n-form-item :label="f.label">
                <n-input
                  v-if="controlType(f.fieldKey) === 'textarea'"
                  v-model:value="editForm[f.fieldKey]"
                  type="textarea"
                  :rows="2"
                  :disabled="f.hasCol"
                />
                <n-input-number
                  v-else-if="controlType(f.fieldKey) === 'number'"
                  v-model:value="editForm[f.fieldKey]"
                  :min="0"
                  :disabled="f.hasCol"
                  style="width: 100%"
                />
                <n-select
                  v-else-if="controlType(f.fieldKey) === 'select'"
                  v-model:value="editForm[f.fieldKey]"
                  :options="selectOptionsFor(f.fieldKey)"
                  :disabled="f.hasCol"
                />
                <n-input v-else v-model:value="editForm[f.fieldKey]" :disabled="f.hasCol" />
                <n-text v-if="f.hasCol" :depth="3" style="font-size: 12px; display: block; margin-top: 2px">
                  {{ t('pages.candidate.CandidateDetail.s93') }}
                </n-text>
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
      </n-spin>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="savingResume" @click="editResumeModalVisible = false">{{ t('pages.candidate.CandidateDetail.s94') }}</n-button>
          <n-button type="primary" :loading="savingResume" @click="handleSaveResume">{{ t('pages.candidate.CandidateDetail.s95') }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 上传简历弹窗 -->
    <n-modal
      v-model:show="uploadResumeModalVisible"
      preset="card"
      :title="t('pages.candidate.CandidateDetail.s96')"
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
          {{ t('pages.candidate.CandidateDetail.s97') }}
        </n-button>
      </n-upload>
      <div class="upload-tip">{{ t('pages.candidate.CandidateDetail.s98') }}</div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
import { getCandidate } from '../../api/candidate'
import { fetchConfig, defaultConfig, type StandardResumeConfig } from '../../api/standard-resume'
import { getResumeFields, putResumeFields } from '../../api/candidate-resume-fields'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const { t } = useI18n()

const activeTab = ref('info')

// 标准简历配置驱动的基本信息字段元数据：fieldKey -> { 中文 label, 候选真实列 }
// 仅映射 Candidate 模型上存在的列；其余扩展字段暂无值存储（全仓无对应表/端点），显示占位符
const FIELD_META: Record<string, { label: string; col?: keyof CandidateDetailData }> = {
  'ID number': { label: t('pages.candidate.CandidateDetail.s102'), col: 'id_card_no' },
  'Mobile': { label: t('pages.candidate.CandidateDetail.s103'), col: 'phone' },
  'About me': { label: t('pages.candidate.CandidateDetail.s104') },
  'Birth Date (Age)': { label: t('pages.candidate.CandidateDetail.s105'), col: 'age' },
  'Major': { label: t('pages.candidate.CandidateDetail.s106') },
  'Email': { label: t('pages.candidate.CandidateDetail.s107'), col: 'email' },
  'Salary': { label: t('pages.candidate.CandidateDetail.s108') },
  'Project description': { label: t('pages.candidate.CandidateDetail.s109') },
  'Team leader': { label: t('pages.candidate.CandidateDetail.s110') },
  'Gender': { label: t('pages.candidate.CandidateDetail.s111'), col: 'gender' },
  'Current salary': { label: t('pages.candidate.CandidateDetail.s112') },
  'Current department': { label: t('pages.candidate.CandidateDetail.s113') },
  'Work location': { label: t('pages.candidate.CandidateDetail.s114') },
  'Residence address': { label: t('pages.candidate.CandidateDetail.s115') },
  'Expected city': { label: t('pages.candidate.CandidateDetail.s116'), col: 'expected_city' },
  'Hobbies': { label: t('pages.candidate.CandidateDetail.s117') },
  'Organizational role': { label: t('pages.candidate.CandidateDetail.s118') },
  'School': { label: t('pages.candidate.CandidateDetail.s119') },
  'Graduation date': { label: t('pages.candidate.CandidateDetail.s120') },
  'Highest degree': { label: t('pages.candidate.CandidateDetail.s121'), col: 'highest_education' },
  'Award time': { label: t('pages.candidate.CandidateDetail.s122') },
  'Start date': { label: t('pages.candidate.CandidateDetail.s123') },
  'Work experience': { label: t('pages.candidate.CandidateDetail.s124'), col: 'work_years' },
  'Reason for leaving': { label: t('pages.candidate.CandidateDetail.s125') },
  'Company': { label: t('pages.candidate.CandidateDetail.s126') },
  'Award name': { label: t('pages.candidate.CandidateDetail.s127') },
  'Current company': { label: t('pages.candidate.CandidateDetail.s128'), col: 'current_company' },
  'ID card validity period': { label: t('pages.candidate.CandidateDetail.s129') },
  'Industry': { label: t('pages.candidate.CandidateDetail.s130') },
  'Political affiliation': { label: t('pages.candidate.CandidateDetail.s131') },
  'Expected industry': { label: t('pages.candidate.CandidateDetail.s132') },
  'Company size': { label: t('pages.candidate.CandidateDetail.s133') },
  'End date': { label: t('pages.candidate.CandidateDetail.s123') },
  'Registered birthplace': { label: t('pages.candidate.CandidateDetail.s134') },
  'Issuing authority': { label: t('pages.candidate.CandidateDetail.s135') },
  'Responsibilities': { label: t('pages.candidate.CandidateDetail.s136') },
  'Location': { label: t('pages.candidate.CandidateDetail.s137') },
  'No. of subordinates': { label: t('pages.candidate.CandidateDetail.s138') },
  'Degree': { label: t('pages.candidate.CandidateDetail.s139') },
  'Current title': { label: t('pages.candidate.CandidateDetail.s140'), col: 'current_position' },
  'WeChat': { label: t('pages.candidate.CandidateDetail.s141') },
  'Project name': { label: t('pages.candidate.CandidateDetail.s142') },
  'Upload ID photo (portrait side)': { label: t('pages.candidate.CandidateDetail.s143') },
  'Resume update time': { label: t('pages.candidate.CandidateDetail.s144') },
  'Ethnicity': { label: t('pages.candidate.CandidateDetail.s145') },
  'Country/Region': { label: t('pages.candidate.CandidateDetail.s146') },
  'Proficiency': { label: t('pages.candidate.CandidateDetail.s147') },
  'Onboarding time': { label: t('pages.candidate.CandidateDetail.s148') },
  'Language': { label: t('pages.candidate.CandidateDetail.s149') },
  'Rating': { label: t('pages.candidate.CandidateDetail.s150'), col: 'resume_score' },
  'Reading and writing': { label: t('pages.candidate.CandidateDetail.s151') },
  'Listening and speaking': { label: t('pages.candidate.CandidateDetail.s152') },
  'Company type': { label: t('pages.candidate.CandidateDetail.s153') },
  'Name': { label: t('pages.candidate.CandidateDetail.s154'), col: 'name' },
  'Job title': { label: t('pages.candidate.CandidateDetail.s155') },
  'Upload ID photo (national emblem side)': { label: t('pages.candidate.CandidateDetail.s156') },
  'Expected salary': { label: t('pages.candidate.CandidateDetail.s157'), col: 'expected_salary' },
}

// 候选人详情真实数据形态（对齐后端 CandidateDetailSerializer 字段）
interface CandidateDetailData {
  id?: string
  name?: string
  phone?: string
  email?: string
  gender?: string
  age?: number | null
  birth_date?: string | null
  id_card_no?: string | null
  highest_education?: string | null
  work_years?: number | null
  expected_city?: string | null
  current_company?: string | null
  current_position?: string | null
  expected_salary?: string | null
  resume_score?: number | null
  current_state?: string
  state_display?: string
  created_at?: string
  [key: string]: any
}

const candidateDetail = ref<CandidateDetailData | null>(null)
const standardResumeConfig = ref<StandardResumeConfig | null>(null)
// 扩展简历字段值 (fieldKey -> value), 来自 CandidateResumeFieldsView; 覆盖无模型列的 40+ 字段
const resumeFields = ref<Record<string, any>>({})
const loading = ref(false)

// 仅展示「标准简历设置」中 enabled 的字段（顺序按配置）
// 值优先级: 候选真实模型列 (meta.col) > 扩展字段值 (resumeFields) > 占位符「—」
const displayFields = computed(() => {
  const cfg = standardResumeConfig.value
  if (!cfg) return []
  const cd = candidateDetail.value
  const rf = resumeFields.value
  return cfg.fields
    .filter((f) => f.enabled)
    .map((f) => {
      const meta = FIELD_META[f.fieldKey] || { label: f.fieldKey }
      let value = '—'
      if (cd && meta.col) {
        const raw = cd[meta.col]
        if (raw != null && raw !== '') value = String(raw)
      }
      if (value === '—' && rf[f.fieldKey] != null && rf[f.fieldKey] !== '') {
        value = String(rf[f.fieldKey])
      }
      return { fieldKey: f.fieldKey, label: meta.label, value, hasCol: !!meta.col }
    })
})

// 兼容 header 模板既有的 candidateData 字段访问（改为从真实详情映射）
const candidateData = computed(() => {
  const c = candidateDetail.value
  return {
    id: route.params.id || '1',
    name: c?.name ?? t('pages.candidate.CandidateDetail.s158'),
    phone: c?.phone ?? '—',
    email: c?.email ?? '—',
    position: c?.current_position ?? '—',
    status: c?.current_state ?? '',
    hrbp: '—',
    hiringManager: '—',
    createdAt: c?.created_at ?? '',
  }
})

onMounted(async () => {
  const id = route.params.id
  loading.value = true
  try {
    const [cfg, det, rf] = await Promise.all([
      fetchConfig().catch(() => defaultConfig()),
      id
        ? getCandidate(String(id)).then((r: any) => r?.data ?? r).catch(() => null)
        : Promise.resolve(null),
      id
        ? getResumeFields(String(id)).catch(() => ({}))
        : Promise.resolve({}),
    ])
    standardResumeConfig.value = cfg
    candidateDetail.value = det ?? null
    resumeFields.value = rf || {}
  } finally {
    loading.value = false
  }
})

const resumeData = ref({
  url: 'https://example.com/resume.pdf',
  name: t('pages.candidate.CandidateDetail.s159'),
  phone: '138****8888',
  email: 'zhangsan@example.com',
  education: t('pages.candidate.CandidateDetail.s160'),
  school: t('pages.candidate.CandidateDetail.s161'),
  workYears: 5,
  currentCompany: t('pages.candidate.CandidateDetail.s162'),
  expectedSalary: '40K',
  source: t('pages.candidate.CandidateDetail.s163'),
})

// ===== 编辑简历 (配置驱动) =====
// 控件类型: 长文本 / 数字 / 下拉 / 普通文本, 由 fieldKey 推断
const genderOptions = [
  { label: t('pages.candidate.CandidateDetail.s164'), value: '男' },
  { label: t('pages.candidate.CandidateDetail.s165'), value: '女' },
  { label: t('pages.candidate.CandidateDetail.s166'), value: '未知' },
]
const TEXTAREA_KEYS = new Set([
  'About me', 'Project description', 'Reason for leaving', 'Responsibilities',
  'Self evaluation', 'Reading and writing', 'Listening and speaking',
])
const NUMBER_KEYS = new Set([
  'Work experience', 'No. of subordinates', 'Rating', 'Current salary', 'Award time',
])
function controlType(fieldKey: string): 'textarea' | 'number' | 'select' | 'text' {
  if (TEXTAREA_KEYS.has(fieldKey)) return 'textarea'
  if (NUMBER_KEYS.has(fieldKey)) return 'number'
  if (fieldKey === 'Highest degree' || fieldKey === 'Degree' || fieldKey === 'Gender') return 'select'
  return 'text'
}
// educationOptions 在下方定义, 此处惰性引用 (函数调用时已完成模块初始化)
function selectOptionsFor(fieldKey: string) {
  if (fieldKey === 'Highest degree' || fieldKey === 'Degree') return educationOptions
  if (fieldKey === 'Gender') return genderOptions
  return []
}
// 编辑态表单: fieldKey -> 当前值
const editForm = ref<Record<string, any>>({})
const savingResume = ref(false)

const educationOptions = [
  { label: t('pages.candidate.CandidateDetail.s167'), value: '高中' },
  { label: t('pages.candidate.CandidateDetail.s168'), value: '大专' },
  { label: t('pages.candidate.CandidateDetail.s169'), value: '本科' },
  { label: t('pages.candidate.CandidateDetail.s170'), value: '硕士' },
  { label: t('pages.candidate.CandidateDetail.s171'), value: '博士' },
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
  emailSubject: t('pages.candidate.CandidateDetail.s172'),
  emailContent: t('pages.candidate.CandidateDetail.s173'),
  smsContent: '',
})

const goBack = () => router.push('/candidates')
const openNotificationModal = () => { notificationModalVisible.value = true }
const openUploadResumeModal = () => { uploadResumeModalVisible.value = true }
const openEditResumeModal = () => {
  // 用当前展示值初始化编辑表单 ('—' 视为空; 数字字段转为 number)
  const init: Record<string, any> = {}
  for (const f of displayFields.value) {
    let v: any = f.value === '—' ? '' : f.value
    if (controlType(f.fieldKey) === 'number' && v !== '') {
      const n = Number(v)
      if (!Number.isNaN(n)) v = n
    }
    init[f.fieldKey] = v
  }
  editForm.value = init
  editResumeModalVisible.value = true
}

const handleDownloadResume = () => {
  if (resumeData.value.url) message.success(t('pages.candidate.CandidateDetail.s174'))
  else message.warning(t('pages.candidate.CandidateDetail.s175'))
}

const beforeUpload = ({ file }: any) => {
  const fileObj = file?.file || file
  const isPDF = fileObj.type === 'application/pdf'
  const isDoc = fileObj.type === 'application/msword' || fileObj.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  const isLessThan10M = fileObj.size / 1024 / 1024 < 10
  if (!isPDF && !isDoc) { message.error(t('pages.candidate.CandidateDetail.s176')); return false }
  if (!isLessThan10M) { message.error(t('pages.candidate.CandidateDetail.s177')); return false }
  return true
}

const handleSaveResume = async () => {
  const id = route.params.id
  if (!id) return
  savingResume.value = true
  try {
    // 仅持久化扩展简历字段 (无 Candidate 模型列的 40+ 字段) 到 resume-fields 端点
    // 模型列字段 (姓名/手机/邮箱等) 为候选人档案字段, 在弹窗中只读, 不在此修改
    const extValues: Record<string, any> = {}
    for (const f of displayFields.value) {
      const meta = FIELD_META[f.fieldKey]
      if (meta && meta.col) continue
      extValues[f.fieldKey] = editForm.value[f.fieldKey] ?? ''
    }
    if (Object.keys(extValues).length) {
      const saved = await putResumeFields(String(id), extValues)
      resumeFields.value = { ...resumeFields.value, ...saved }
    }
    message.success(t('pages.candidate.CandidateDetail.s178'))
    editResumeModalVisible.value = false
  } catch (e) {
    message.error(t('pages.candidate.CandidateDetail.s179'))
  } finally {
    savingResume.value = false
  }
}

const handleUploadResume = () => {
  if (fileList.value.length === 0) { message.warning(t('pages.candidate.CandidateDetail.s180')); return }
  message.success(t('pages.candidate.CandidateDetail.s181'))
  uploadResumeModalVisible.value = false
  fileList.value = []
}

const handleSendNotification = () => {
  message.success(t('pages.candidate.CandidateDetail.s182'))
  notificationModalVisible.value = false
}
</script>

<style scoped>
.candidate-detail-page { padding: var(--space-6); background: var(--c-info-soft); min-height: 100vh; } /* v2.8 T2.8.3: 浅蓝 → var(--c-info-soft) */
.page-header { margin-bottom: var(--space-6); display: flex; justify-content: space-between; align-items: center; }
.back-btn { border: none; background: transparent; }
.send-btn { background: var(--brand); border-color: var(--brand); border-radius: 8px; font-weight: 600; }
.info-card { margin-bottom: var(--space-6); border-radius: 24px; border: 1px solid var(--border-hairline); box-shadow: none; }
.candidate-avatar { background: linear-gradient(135deg, var(--brand) 0%, color-mix(in srgb, var(--brand) 45%, var(--brand)) 100%); font-size: 32px; font-weight: 700; } /* v2.9: 越界硬编码渐变 var(--c-purple)/var(--c-info-deep) → brand 渐变 + 移除 !important */
.candidate-header { display: flex; justify-content: space-between; align-items: flex-start; }
.contact-info { color: var(--ink-soft); }
.position-tag { border-radius: 9999px; padding: var(--space-1) var(--space-3); background: var(--brand-soft); color: var(--brand); }
.channel-tag { border-radius: 9999px; padding: var(--space-1) var(--space-3); background: var(--brand-soft); color: var(--brand); }
.candidate-meta { text-align: right; color: var(--ink-soft); font-size: var(--fs-12); }
.tabs-card { border-radius: 24px; border: 1px solid var(--border-hairline); box-shadow: none; }
.info-section { padding: var(--space-4); }
.info-row { display: flex; align-items: center; padding: var(--space-3) 0; border-bottom: 1px solid var(--border-hairline); }
.info-label { width: 100px; color: var(--ink-soft); font-size: var(--fs-14); }
.info-value { font-weight: 600; color: var(--ink); }
.process-section, .interview-table { background: var(--c-info-soft); border-radius: 12px; padding: var(--space-4); } /* v2.8 T2.8.3: 浅蓝 → var(--c-info-soft) */
.interview-header { font-weight: 600; color: var(--ink-soft); padding: var(--space-3) 0; border-bottom: 1px solid var(--border-hairline); }
.interview-row { padding: var(--space-3) 0; border-bottom: 1px solid var(--border-hairline); }
.resume-section { padding: var(--space-6); }
.resume-content { display: flex; flex-direction: column; gap: var(--space-6); }
.resume-toolbar { display: flex; justify-content: flex-start; }
.resume-preview { background: var(--c-info-soft); border-radius: 12px; padding: var(--space-6); } /* v2.8 T2.8.3: 浅蓝 → var(--c-info-soft) */
.resume-info { display: flex; flex-direction: column; gap: var(--space-3); }
.resume-field { display: flex; align-items: center; }
.resume-field .field-label { width: 100px; color: var(--ink-soft); font-size: var(--fs-14); }
.resume-field .field-value { color: var(--ink); font-weight: 500; font-size: var(--fs-14); }
.upload-tip { margin-top: var(--space-4); color: var(--ink-faint); font-size: var(--fs-12); }
.download-btn { background: var(--brand); border-color: var(--brand); border-radius: 8px; }
.empty-state { padding: 40px; }
.history-section { padding: var(--space-4); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: var(--space-4) var(--space-6); border-bottom: 1px solid var(--overlay-glass-mid); }
.modal-title { font-size: var(--fs-20); font-weight: 700; color: var(--ink); }
.close-btn { width: 32px; height: 32px; border: none; background: transparent; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--ink-soft); transition: all var(--duration-base) var(--ease-out); }
.close-btn:hover { background: var(--overlay-glass-mid); color: var(--ink); }
.candidate-summary { display: flex; align-items: center; gap: var(--space-4); background: var(--brand-soft); border-radius: 8px; padding: var(--space-3); margin-top: var(--space-4); }
.candidate-avatar-sm { background: linear-gradient(135deg, var(--brand) 0%, color-mix(in srgb, var(--brand) 45%, var(--brand)) 100%); font-size: var(--fs-20); font-weight: 600; } /* v2.9: 越界硬编码渐变 → brand 渐变 + 移除 !important */
.candidate-info { flex: 1; }
.candidate-name-row { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); }
.candidate-name { font-size: var(--fs-16); font-weight: 600; color: var(--ink); }
.position-tag-sm { background: var(--brand-soft); color: var(--brand-dark); border-radius: 9999px; font-size: var(--fs-12); padding: 2px var(--space-2); }
.experience-tag { background: var(--border-hairline); color: var(--ink-soft); border-radius: 9999px; font-size: var(--fs-12); padding: 2px var(--space-2); }
.candidate-contact-row { display: flex; gap: var(--space-4); font-size: var(--fs-14); color: var(--ink-soft); }
.candidate-contact-row span { display: flex; align-items: center; gap: var(--space-1); }
.modal-content { display: flex; min-height: 400px; }
.left-sidebar { width: 340px; background: var(--c-info-soft); border-right: 1px solid var(--overlay-glass-mid); padding: var(--space-6); overflow-y: auto; display: flex; flex-direction: column; gap: var(--space-8); } /* v2.8 T2.8.3: 浅蓝 → var(--c-info-soft) */
.step-section { display: flex; flex-direction: column; gap: var(--space-4); }
.step-title { font-size: var(--fs-16); font-weight: 600; color: var(--ink); display: flex; align-items: center; gap: var(--space-2); margin: 0; }
.step-number { width: 24px; height: 24px; border-radius: 50%; background: var(--brand); color: #fff; font-size: var(--fs-12); font-weight: 600; display: flex; align-items: center; justify-content: center; }
.step-content { display: flex; flex-direction: column; gap: var(--space-4); }
.content-group { display: flex; flex-direction: column; gap: var(--space-2); }
.content-group-title { font-size: var(--fs-14); font-weight: 600; color: var(--ink); padding-left: var(--space-1); }
.content-item { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); border-radius: 8px; border: 1px solid var(--border-hairline); background: var(--glass-bg-card); cursor: pointer; transition: all var(--duration-base) var(--ease-out); font-size: var(--fs-14); color: var(--ink); } /* v2.8 T2.8.2: #c1c6d5/var(--g1)/#161c23 → var(--border-hairline)/var(--glass-bg-card)/var(--ink) */
.content-item:hover { border-color: var(--brand); background: var(--brand-soft); }
.content-item.selected { border-color: var(--brand); background: var(--brand-a12); }
.method-item { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); border-radius: 8px; border: 1px solid var(--border-hairline); background: var(--glass-bg-card); cursor: pointer; transition: all var(--duration-base) var(--ease-out); } /* v2.8 T2.8.2: var(--g6)/var(--g1) → var(--border-hairline)/var(--glass-bg-card) */
.method-item:hover { border-color: var(--brand); background: var(--brand-soft); }
.method-item.selected { border-color: var(--brand); background: var(--brand-a12); }
.method-icon { font-size: var(--fs-20); color: var(--brand); }
.method-name { font-size: var(--fs-14); font-weight: 600; color: var(--ink); }
.right-content { flex: 1; padding: var(--space-6); overflow-y: auto; display: flex; flex-direction: column; gap: var(--space-6); background: var(--glass-bg-card); } /* v2.8 T2.8.2: var(--g1) → var(--glass-bg-card) */
/* v2 bugfix P0-A: 金色硬编码 var(--c-warning-bg)/var(--c-warning-deep)/RGBA(255,214,102,0.1) → 改用 --c-warning 系列 token */
.info-callout { display: flex; align-items: flex-start; gap: var(--space-2); padding: var(--space-3); background: var(--c-warning-soft); border: 1px solid var(--c-warning); border-radius: 8px; font-size: var(--fs-14); color: var(--ink); }
.editor-section { display: flex; flex-direction: column; gap: var(--space-3); }
.editor-header { display: flex; align-items: center; gap: var(--space-2); padding-bottom: var(--space-3); border-bottom: 1px solid var(--overlay-glass-mid); }
.editor-icon { font-size: var(--fs-24); color: var(--brand); }
.editor-title { font-size: var(--fs-16); font-weight: 600; color: var(--ink); margin: 0; }
.editor-field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: var(--fs-12); font-weight: 500; color: var(--ink-soft); }
.sms-counter { display: flex; justify-content: space-between; align-items: center; }
.counter-text { font-size: var(--fs-12); color: var(--ink-faint); }
.email-subject-input, .email-content-input, .sms-content-input { background: var(--overlay-glass-mid); border: 1px solid var(--overlay-glass-mid); border-radius: 6px; }
.modal-footer { display: flex; justify-content: space-between; align-items: center; padding: var(--space-4) var(--space-6); border-top: 1px solid var(--overlay-glass-mid); background: var(--c-info-soft); } /* v2.8 T2.8.3: 浅蓝 → var(--c-info-soft) */
.recipient-info { font-size: var(--fs-12); color: var(--ink-soft); }
.footer-buttons { display: flex; gap: var(--space-4); align-items: center; }
/* v2 bugfix P0-A: 删 !important 金色硬编码（var(--c-warning-bg)/var(--c-warning-bg)/var(--n-850)），n-button type="primary" 已全局接管（App.vue themeOverrides 渐变按钮） */
.send-btn-primary {
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
  border-color: var(--overlay-glass-mid);
}
.send-btn-primary:hover {
  transform: translateY(-1px);
}
</style>
