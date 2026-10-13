<template>
  <div class="candidate-detail-page">
    <!-- 顶部导航（仅返回 + 标题；操作按钮移至右侧操作栏） -->
    <div class="page-header">
      <n-space>
        <n-button class="back-btn" @click="goBack">
          <template #icon><n-icon :component="ChevronBackOutline" /></template>
          {{ t('pages.candidate.CandidateDetail.s1') }}
        </n-button>
        <n-h4 style="margin: 0; font-weight: 700">{{ t('pages.candidate.CandidateDetail.s2') }}</n-h4>
      </n-space>
    </div>

    <!-- 候选人身份条：头像 + 姓名 + 编号 + 状态 + 应聘职位 + 关键信息 -->
    <n-card class="identity-card">
      <div class="identity-row">
        <n-avatar :size="64" round class="candidate-avatar">
          {{ candidateData.name[0] }}
        </n-avatar>
        <div class="identity-main">
          <div class="identity-name-row">
            <span class="identity-name">{{ candidateData.name }}</span>
            <span v-if="candidateData.code" class="identity-code">{{ candidateData.code }}</span>
            <n-tag v-if="candidateData.stateDisplay" type="info" :bordered="false" size="small">
              {{ candidateData.stateDisplay }}
            </n-tag>
            <n-tag v-if="appliedPosition" class="position-tag" :bordered="false" size="small">
              {{ appliedPosition }}
            </n-tag>
          </div>
          <div class="identity-meta-row">
            <span v-if="genderAgeText" class="meta-chip">{{ genderAgeText }}</span>
            <span v-if="candidateDetail?.highest_education" class="meta-chip">{{ candidateDetail.highest_education }}</span>
            <span v-if="candidateData.phone !== '—'" class="meta-chip"><n-icon :component="CallOutline" /> {{ candidateData.phone }}</span>
            <span v-if="candidateData.email !== '—'" class="meta-chip"><n-icon :component="MailOutline" /> {{ candidateData.email }}</span>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 主体：左主内容区 + 右操作栏 -->
    <div class="detail-layout">
      <div class="main-col">
        <n-card class="tabs-card">
          <n-tabs v-model:value="activeTab" type="line" animated>
            <!-- 档案信息（基本信息 + 简历信息整合，按业务板块分组） -->
            <n-tab-pane name="profile">
              <template #tab>
                <span><n-icon :component="PersonOutline" />{{ t('pages.candidate.CandidateDetail.s183') }}</span>
              </template>
              <div class="profile-section">
                <n-spin v-if="loading" style="margin: 24px 0" />
                <template v-else>
                  <div v-for="group in profileGroups" :key="group.code" class="profile-group">
                    <div class="section-title">{{ group.title }}</div>
                    <div class="field-grid">
                      <div v-for="f in group.fields" :key="f.fieldKey" class="field-cell">
                        <div class="field-label">{{ f.label }}</div>
                        <div class="field-value" :class="{ empty: f.value === '—' }">{{ f.value }}</div>
                      </div>
                    </div>
                  </div>
                  <n-empty
                    v-if="profileGroups.length === 0"
                    :description="t('pages.candidate.CandidateDetail.s7')"
                    style="margin: 24px 0"
                  />

                  <!-- 简历附件（原「简历信息」Tab 整合入档案） -->
                  <div class="profile-group">
                    <div class="section-title">{{ t('pages.candidate.CandidateDetail.s198') }}</div>
                    <div class="resume-actions">
                      <n-button
                        v-if="resumeFileUrl"
                        type="primary"
                        class="download-btn"
                        @click="handleDownloadResume"
                      >
                        <template #icon><n-icon :component="DownloadOutline" /></template>
                        {{ t('pages.candidate.CandidateDetail.s34') }}
                      </n-button>
                      <n-button
                        v-permission="'recruit:candidate:edit'"
                        @click="openEditResumeModal"
                      >
                        {{ t('pages.candidate.CandidateDetail.s201') }}
                      </n-button>
                      <n-button @click="openUploadResumeModal">
                        <template #icon><n-icon :component="CloudUploadOutline" /></template>
                        {{ t('pages.candidate.CandidateDetail.s49') }}
                      </n-button>
                    </div>
                    <n-text v-if="!resumeFileUrl" :depth="3" style="font-size: var(--fs-12)">
                      {{ t('pages.candidate.CandidateDetail.s48') }}
                    </n-text>
                  </div>
                </template>
              </div>
            </n-tab-pane>

            <!-- 操作记录（真实操作历史） -->
            <n-tab-pane name="history">
              <template #tab>
                <span><n-icon :component="TimeOutline" />{{ t('pages.candidate.CandidateDetail.s50') }}</span>
              </template>
              <div class="history-section">
                <n-timeline v-if="histories.length > 0">
                  <n-timeline-item v-for="h in histories" :key="h.id" type="info">
                    <div>
                      <n-tag type="info" :bordered="false" size="small">{{ h.action }}</n-tag>
                      <n-text :depth="3" style="font-size: var(--fs-12); margin-left: 8px">{{ formatTime(h.createdAt) }}</n-text>
                      <div style="margin-top: 4px"><n-text :depth="2">{{ h.detail }}</n-text></div>
                      <div style="margin-top: var(--space-1); color: var(--ink-soft); font-size: var(--fs-12)">{{ h.operatorName }}</div>
                    </div>
                  </n-timeline-item>
                </n-timeline>
                <n-empty v-else :description="t('pages.candidate.CandidateDetail.s7')" style="margin: 24px 0" />
              </div>
            </n-tab-pane>
          </n-tabs>
        </n-card>
      </div>

      <!-- 右侧操作栏 -->
      <div class="rail-col">
        <!-- 当前阶段 -->
        <div class="rail-card">
          <div class="rail-title">{{ t('pages.candidate.CandidateDetail.s191') }}</div>
          <div class="stage-value">
            <n-tag type="warning" :bordered="false">{{ currentStage || candidateData.stateDisplay || '—' }}</n-tag>
          </div>
          <div v-if="appliedPosition" class="rail-sub">{{ t('pages.candidate.CandidateDetail.s204') }}：{{ appliedPosition }}</div>
          <div v-if="candidateData.stateDisplay && currentStage" class="rail-sub">{{ candidateData.stateDisplay }}</div>
          <div v-if="createdAtText" class="rail-sub">{{ createdAtText }}</div>
        </div>

        <!-- 操作 -->
        <div class="rail-card">
          <div class="rail-title">{{ t('pages.candidate.CandidateDetail.s192') }}</div>
          <n-space vertical :size="8">
            <n-button type="primary" block @click="openNotificationModal">
              <template #icon><n-icon :component="PaperPlaneOutline" /></template>
              {{ t('pages.candidate.CandidateDetail.s3') }}
            </n-button>
            <n-button type="warning" block @click="bgModalVisible = true">
              <template #icon><n-icon :component="ShieldCheckmarkOutline" /></template>
              {{ t('pages.candidate.InitiateBgCheck.title') }}
            </n-button>
            <n-button type="warning" secondary block @click="openSupplementBg">
              <template #icon><n-icon :component="ShieldCheckmarkOutline" /></template>
              {{ t('pages.candidate.InitiateBgCheck.titleSupplement') }}
            </n-button>
          </n-space>
        </div>

        <!-- 简历标签 -->
        <div class="rail-card">
          <div class="rail-title">{{ t('pages.candidate.CandidateDetail.s193') }}</div>
          <n-space v-if="candidateTags.length > 0" :size="6">
            <n-tag v-for="(tag, i) in candidateTags" :key="i" :bordered="false" size="small">{{ tag }}</n-tag>
          </n-space>
          <n-text v-else :depth="3" style="font-size: var(--fs-12)">{{ t('pages.candidate.CandidateDetail.s199') }}</n-text>
        </div>

        <!-- 添加备注 -->
        <div class="rail-card">
          <div class="rail-title">{{ t('pages.candidate.CandidateDetail.s194') }}</div>
          <n-input
            v-model:value="noteContent"
            type="textarea"
            :rows="3"
            :placeholder="t('pages.candidate.CandidateDetail.s195')"
          />
          <n-button size="small" style="margin-top: 8px" @click="handleSaveNote">
            {{ t('pages.candidate.CandidateDetail.s196') }}
          </n-button>
        </div>

        <!-- 应聘记录 -->
        <div class="rail-card">
          <div class="rail-title">{{ t('pages.candidate.CandidateDetail.s197') }}</div>
          <div v-if="applications.length > 0" class="application-list">
            <div v-for="app in applications" :key="app.id" class="application-item">
              <div class="application-position">{{ app.positionTitle || '—' }}</div>
              <div class="application-meta">
                <span v-if="app.currentStage">{{ app.currentStage }}</span>
                <span v-if="app.createdAt">{{ formatTime(app.createdAt) }}</span>
              </div>
            </div>
          </div>
          <n-text v-else :depth="3" style="font-size: var(--fs-12)">{{ t('pages.candidate.CandidateDetail.s202') }}</n-text>
        </div>
      </div>
    </div>

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
              <n-tag v-if="appliedPosition" class="position-tag-sm" :bordered="false">{{ appliedPosition }}</n-tag>
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

    <!-- 编辑档案弹窗 (按标准简历配置驱动, 全部 enabled 字段可编辑; 模型列字段只读) -->
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

    <!-- 发起背调（供应商集成系统） -->
    <InitiateBackgroundCheckModal
      v-model:show="bgModalVisible"
      :candidate="{ id: candidateData.id, name: candidateData.name, phone: candidateData.phone,
                    idCardNo: pickDetail('id_card_no') || '', email: candidateDetail?.email,
                    position: appliedPosition, expectedOnboardingDate: '' }"
      :parent-order-id="bgParentOrderId"
    />
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
  PersonOutline,
  TimeOutline,
  PaperPlaneOutline,
  ShieldCheckmarkOutline,
  CloseOutline,
  ChatbubblesOutline,
  LogoWechat,
  CloudUploadOutline,
  DownloadOutline,
} from '@vicons/ionicons5'
import { getCandidate } from '../../api/candidate'
import { fetchConfig, defaultConfig, type StandardResumeConfig } from '../../api/standard-resume'
import { getResumeFields, putResumeFields } from '../../api/candidate-resume-fields'
import { listFields, type FieldDefinition } from '../../api/dynamic-field'
import InitiateBackgroundCheckModal from './InitiateBackgroundCheckModal.vue'
import { listBackgroundCheckOrders } from '../../api/integration'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const { t } = useI18n()

const activeTab = ref('profile')

/**
 * 中文标签映射：snake_case fieldKey → i18n key（s102–s157 现有译文）。
 * 权威来源为「标准简历设置」的动态字段（fieldKey 已由迁移 0023 归一为 snake_case，
 * 但组件曾用英文显示标签作键 → 查不到 → 页面直接裸显 about_me 等英文键）。
 * 此表不依赖 listFields 权限（HR 无 recruit:settings:dynamic-fields:list 也可用）。
 */
const FIELD_LABEL_I18N: Record<string, string> = {
  name: 's154', gender: 's111', about_me: 's104', birth_date_age: 's105',
  mobile: 's103', wechat: 's141', email: 's107', political_affiliation: 's131',
  registered_birthplace: 's134', highest_degree: 's121', work_experience: 's124',
  id_card_photo_front: 's143', id_card_photo_back: 's156',
  id_card_issuing_authority: 's135', id_card_validity_period: 's129',
  id_card_number: 's102', country_region: 's146', ethnicity: 's145',
  residence_address: 's115', hobbies: 's117', graduation_date: 's120', major: 's106',
  current_company: 's128', industry: 's130', current_title: 's140', location: 's137',
  current_salary: 's112', expected_salary: 's157', onboarding_time: 's148',
  expected_city: 's116', expected_industry: 's132', rating: 's150',
  resume_update_time: 's144', start_date: 's123', school: 's119', degree: 's139',
  company: 's126', current_department: 's113', job_title: 's155',
  responsibilities: 's136', team_leader: 's110', work_location: 's114',
  company_size: 's133', company_type: 's153', salary: 's108',
  reason_for_leaving: 's125', no_of_subordinates: 's138', end_date: 's123',
  project_name: 's142', organizational_role: 's118', project_description: 's109',
  language: 's149', proficiency: 's147', listening_and_speaking: 's152',
  reading_and_writing: 's151', award_time: 's122', award_name: 's127',
}

// 板块 code → i18n（迁移 0023 MODULES：候选人信息/求职意向/工作经历/项目经历/教育背景/技能语言/证书荣誉）
const MODULE_I18N: Record<string, string> = {
  candidate: 's184', expectation: 's185', work: 's186', project: 's187',
  edu: 's188', skill: 's189', certificate: 's190',
}
const MODULE_ORDER = ['candidate', 'expectation', 'work', 'project', 'edu', 'skill', 'certificate']

// listFields 不可用（如 HR 无字段管理权限）时的板块归属兜底（对齐迁移 0023 MODULE_ASSIGN）
const MODULE_ASSIGN_FALLBACK: Record<string, string> = {
  name: 'candidate', gender: 'candidate', about_me: 'candidate',
  birth_date_age: 'candidate', mobile: 'candidate', wechat: 'candidate',
  email: 'candidate', political_affiliation: 'candidate',
  registered_birthplace: 'candidate', country_region: 'candidate',
  ethnicity: 'candidate', residence_address: 'candidate', hobbies: 'candidate',
  highest_degree: 'candidate', location: 'candidate', rating: 'candidate',
  resume_update_time: 'candidate', id_card_photo_front: 'candidate',
  id_card_photo_back: 'candidate', id_card_issuing_authority: 'candidate',
  id_card_validity_period: 'candidate', id_card_number: 'candidate',
  expected_salary: 'expectation', current_salary: 'expectation',
  onboarding_time: 'expectation', expected_city: 'expectation',
  expected_industry: 'expectation',
  work_experience: 'work', industry: 'work', current_company: 'work',
  current_title: 'work', start_date: 'work', end_date: 'work',
  company: 'work', current_department: 'work', job_title: 'work',
  responsibilities: 'work', team_leader: 'work', work_location: 'work',
  company_size: 'work', company_type: 'work', salary: 'work',
  reason_for_leaving: 'work', no_of_subordinates: 'work',
  project_name: 'project', organizational_role: 'project',
  project_description: 'project',
  graduation_date: 'edu', school: 'edu', degree: 'edu', major: 'edu',
  language: 'skill', proficiency: 'skill',
  listening_and_speaking: 'skill', reading_and_writing: 'skill',
  award_time: 'certificate', award_name: 'certificate',
}

/**
 * 动态字段 fieldKey → Candidate 模型列（值在候选人主表上）。
 * 详情接口经 CamelCaseJSONRenderer 输出 camelCase 键（如 id_card_no → idCardNo），
 * 读取时先试 camelCase 再回退 snake_case。
 */
const MODEL_COL: Record<string, string> = {
  name: 'name', mobile: 'phone', email: 'email', gender: 'gender',
  birth_date_age: 'age', id_card_number: 'id_card_no',
  highest_degree: 'highest_education', work_experience: 'work_years',
  expected_city: 'expected_city', current_company: 'current_company',
  current_title: 'current_position', expected_salary: 'expected_salary',
  rating: 'resume_score',
}

/** 候选人详情真实数据形态（对齐后端 CandidateDetailSerializer，camelCase 键） */
interface CandidateDetailData {
  id?: string
  code?: string
  name?: string
  phone?: string
  email?: string
  gender?: string
  age?: number | null
  highest_education?: string | null
  current_state?: string
  state_display?: string
  created_at?: string
  updated_at?: string
  resume_file_url?: string | null
  tags?: Array<string | { name?: string }> | null
  /** 投递记录（后端 get_applications，CamelCase 键） */
  applications?: Array<{
    id?: string; code?: string; positionTitle?: string | null
    state?: string; currentStage?: string | null; createdAt?: string
  }> | null
  /** 操作历史（CandidateHistorySerializer，CamelCase 键） */
  histories?: Array<{
    id?: string; action?: string; detail?: string
    operatorName?: string; createdAt?: string
  }> | null
  [key: string]: any
}

interface DisplayField {
  fieldKey: string
  label: string
  value: string
  hasCol: boolean
}

const candidateDetail = ref<CandidateDetailData | null>(null)
const standardResumeConfig = ref<StandardResumeConfig | null>(null)
// 扩展简历字段值 (fieldKey -> value), 来自 CandidateResumeFieldsView; 覆盖无模型列的 40+ 字段
const resumeFields = ref<Record<string, any>>({})
// 动态字段定义（fieldKey -> FieldDefinition），提供中文 label 与板块归属；403 时为空表
const fieldDefMap = ref<Record<string, FieldDefinition>>({})
const loading = ref(false)

const camelize = (s: string) => s.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase())

/** 从详情中取模型列值：优先 camelCase 键（渲染器输出），回退 snake_case */
function pickDetail(col: string): string {
  const cd = candidateDetail.value
  if (!cd) return ''
  const camel = cd[camelize(col)]
  if (camel != null && camel !== '') return String(camel)
  const snake = cd[col]
  if (snake != null && snake !== '') return String(snake)
  return ''
}

/** 从扩展简历字段中取值：响应键可能是 snake_case 或被渲染器 camelCase */
function pickResume(fieldKey: string): string {
  const rf = resumeFields.value
  const snake = rf[fieldKey]
  if (snake != null && snake !== '') return String(snake)
  const camel = rf[camelize(fieldKey)]
  if (camel != null && camel !== '') return String(camel)
  return ''
}

/** 中文标签解析：i18n 映射（57 个已知字段）→ 动态字段定义 label → 原始 key */
function labelFor(fieldKey: string): string {
  const sKey = FIELD_LABEL_I18N[fieldKey]
  if (sKey) return t(`pages.candidate.CandidateDetail.${sKey}`)
  const def = fieldDefMap.value[fieldKey]
  if (def?.label) return def.label
  return fieldKey
}

/** 板块归属：动态字段定义 module → 本地兜底映射 → candidate */
function moduleCodeOf(fieldKey: string): string {
  const def = fieldDefMap.value[fieldKey]
  if (def?.module?.code && MODULE_I18N[def.module.code]) return def.module.code
  return MODULE_ASSIGN_FALLBACK[fieldKey] ?? 'candidate'
}

function moduleTitleOf(code: string): string {
  return t(`pages.candidate.CandidateDetail.${MODULE_I18N[code] ?? 's183'}`)
}

function buildDisplayField(fieldKey: string): DisplayField {
  let value = ''
  const col = MODEL_COL[fieldKey]
  if (col) value = pickDetail(col)
  if (!value) value = pickResume(fieldKey)
  return {
    fieldKey,
    label: labelFor(fieldKey),
    value: value || '—',
    hasCol: !!col,
  }
}

/** 仅展示「标准简历设置」中 enabled 的字段，按业务板块分组（板块顺序固定，组内按配置顺序） */
const profileGroups = computed<Array<{ code: string; title: string; fields: DisplayField[] }>>(() => {
  const cfg = standardResumeConfig.value
  if (!cfg) return []
  const buckets = new Map<string, DisplayField[]>()
  const order: string[] = []
  for (const f of cfg.fields) {
    if (!f.enabled) continue
    const code = moduleCodeOf(f.fieldKey)
    if (!buckets.has(code)) { buckets.set(code, []); order.push(code) }
    buckets.get(code)!.push(buildDisplayField(f.fieldKey))
  }
  const ordered = MODULE_ORDER.filter((c) => order.includes(c))
  const rest = order.filter((c) => !MODULE_ORDER.includes(c))
  return [...ordered, ...rest].map((code) => ({
    code,
    title: moduleTitleOf(code),
    fields: buckets.get(code) ?? [],
  }))
})

/** 编辑弹窗用的扁平字段列表（同 profileGroups 数据源） */
const displayFields = computed<DisplayField[]>(() =>
  profileGroups.value.flatMap((g) => g.fields),
)

const candidateTags = computed<string[]>(() => {
  const raw = candidateDetail.value?.tags
  if (!Array.isArray(raw)) return []
  return raw
    .map((item) => (typeof item === 'string' ? item : item?.name ?? ''))
    .filter((s) => !!s)
})

const histories = computed(() => candidateDetail.value?.histories ?? [])
const applications = computed(() => candidateDetail.value?.applications ?? [])
const currentStage = computed(() => applications.value[0]?.currentStage ?? '')
const resumeFileUrl = computed(() => pickDetail('resume_file_url'))

const genderAgeText = computed(() => {
  const parts: string[] = []
  const g = pickDetail('gender')
  if (g) parts.push(g)
  const age = pickDetail('age')
  if (age) parts.push(`${age}${t('pages.candidate.CandidateDetail.s43')}`)
  return parts.join(' · ')
})

function formatTime(iso?: string): string {
  if (!iso) return ''
  return String(iso).replace('T', ' ').slice(0, 16)
}

/** 入库时间（候选人创建时间），用于右侧「当前阶段」卡片的副信息 */
const createdAtText = computed(() => {
  const v = pickDetail('created_at')
  return v ? `${t('pages.candidate.CandidateDetail.s203')} ${v}` : ''
})

// 兼容模板既有 candidateData 字段访问（从真实详情映射；不再使用假数据）
const candidateData = computed(() => {
  const c = candidateDetail.value
  return {
    id: (route.params.id as string) || '',
    code: c?.code ?? '',
    name: c?.name ?? t('pages.candidate.CandidateDetail.s158'),
    phone: c?.phone ?? '—',
    email: c?.email ?? '—',
    // 后端 state_display（CamelCase 后为 stateDisplay）= current_state 的中文展示名
    stateDisplay: pickDetail('state_display') || '',
  }
})

/**
 * 应聘职位：取自投递记录（applications[].positionTitle），
 * 而非候选人的「当前头衔」current_title（二者语义不同，后者常为空）。
 * 多次投递时优先取最新一条（后端 applications 已按 -created_at 排序）。
 */
const appliedPosition = computed<string>(() => {
  const apps = candidateDetail.value?.applications ?? []
  const hit = apps.find((a) => (a?.positionTitle || '').trim())
  return (hit?.positionTitle || '').trim()
})

onMounted(async () => {
  const id = route.params.id
  loading.value = true
  try {
    const [cfg, det, rf, defs] = await Promise.all([
      fetchConfig().catch(() => defaultConfig()),
      id
        ? getCandidate(String(id)).then((r: any) => r?.data ?? r).catch(() => null)
        : Promise.resolve(null),
      id
        ? getResumeFields(String(id)).catch(() => ({}))
        : Promise.resolve({}),
      // 动态字段定义：提供 label / 板块；无权限或异常时降级为本地映射
      listFields('Candidate').catch(() => [] as FieldDefinition[]),
    ])
    standardResumeConfig.value = cfg
    candidateDetail.value = det ?? null
    resumeFields.value = rf || {}
    const map: Record<string, FieldDefinition> = {}
    for (const d of defs) if (d?.fieldKey) map[d.fieldKey] = d
    fieldDefMap.value = map
  } finally {
    loading.value = false
  }
})

// ===== 编辑档案 (配置驱动) =====
// 控件类型: 长文本 / 数字 / 下拉 / 普通文本, 由 snake_case fieldKey 推断
const genderOptions = [
  { label: t('pages.candidate.CandidateDetail.s164'), value: '男' },
  { label: t('pages.candidate.CandidateDetail.s165'), value: '女' },
  { label: t('pages.candidate.CandidateDetail.s166'), value: '未知' },
]
const TEXTAREA_KEYS = new Set([
  'about_me', 'project_description', 'reason_for_leaving', 'responsibilities',
  'reading_and_writing', 'listening_and_speaking', 'hobbies',
])
const NUMBER_KEYS = new Set([
  'work_experience', 'no_of_subordinates', 'rating', 'current_salary',
  'award_time', 'salary',
])
function controlType(fieldKey: string): 'textarea' | 'number' | 'select' | 'text' {
  if (TEXTAREA_KEYS.has(fieldKey)) return 'textarea'
  if (NUMBER_KEYS.has(fieldKey)) return 'number'
  if (fieldKey === 'highest_degree' || fieldKey === 'degree' || fieldKey === 'gender') return 'select'
  return 'text'
}
// educationOptions 在下方定义, 此处惰性引用 (函数调用时已完成模块初始化)
function selectOptionsFor(fieldKey: string) {
  if (fieldKey === 'highest_degree' || fieldKey === 'degree') return educationOptions
  if (fieldKey === 'gender') return genderOptions
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
const bgModalVisible = ref(false)
const bgParentOrderId = ref('')
const noteContent = ref('')

async function openSupplementBg() {
  // 补充背调：定位该候选人最新一条背调订单作为父单，复用统一弹窗
  bgParentOrderId.value = ''
  try {
    const res = await listBackgroundCheckOrders({ candidate_id: candidateData.value.id, page_size: 1 })
    const d = (res?.data ?? {}) as any
    const items: any[] = Array.isArray(d) ? d : (d.results ?? [])
    if (items.length > 0) bgParentOrderId.value = items[0].id
  } catch (e: any) {
    bgParentOrderId.value = ''
  }
  bgModalVisible.value = true
}
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
  const url = resumeFileUrl.value
  if (url) window.open(url, '_blank')
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
      if (f.hasCol) continue
      extValues[f.fieldKey] = editForm.value[f.fieldKey] ?? ''
    }
    if (Object.keys(extValues).length) {
      const saved = await putResumeFields(String(id), extValues)
      resumeFields.value = { ...resumeFields.value, ...(saved || {}) }
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

const handleSaveNote = () => {
  // 备注后端端点尚未接入：明确提示，不伪造保存成功
  message.info(t('pages.candidate.CandidateDetail.s200'))
}

const handleSendNotification = () => {
  message.success(t('pages.candidate.CandidateDetail.s182'))
  notificationModalVisible.value = false
}
</script>

<style scoped>
.candidate-detail-page { padding: var(--space-6); background: var(--c-info-soft); min-height: 100vh; }
.page-header { margin-bottom: var(--space-4); display: flex; justify-content: space-between; align-items: center; }
.back-btn { border: none; background: transparent; }

/* ===== 身份条 ===== */
.identity-card { margin-bottom: var(--space-4); border-radius: 16px; border: 1px solid var(--border-hairline); box-shadow: none; }
.identity-row { display: flex; align-items: center; gap: var(--space-4); }
.candidate-avatar { background: linear-gradient(135deg, var(--brand) 0%, color-mix(in srgb, var(--brand) 45%, var(--brand)) 100%); font-size: 26px; font-weight: 700; flex-shrink: 0; }
.identity-main { flex: 1; min-width: 0; }
.identity-name-row { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.identity-name { font-size: var(--fs-20); font-weight: 700; color: var(--ink); }
.identity-code { font-size: var(--fs-12); color: var(--ink-soft); background: var(--border-hairline); border-radius: 6px; padding: 2px 8px; font-family: ui-monospace, monospace; }
.position-tag { background: var(--brand-soft); color: var(--brand-fg); border-radius: 9999px; max-width: 320px; overflow: hidden; text-overflow: ellipsis; }
.identity-meta-row { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; margin-top: var(--space-2); }
.meta-chip { font-size: var(--fs-12); color: var(--ink-soft); display: inline-flex; align-items: center; gap: 4px; }

/* ===== 左主区 / 右操作栏 ===== */
.detail-layout { display: flex; gap: var(--space-4); align-items: flex-start; }
.main-col { flex: 1; min-width: 0; }
.rail-col { width: 300px; flex-shrink: 0; display: flex; flex-direction: column; gap: var(--space-4); position: sticky; top: var(--space-4); }
@media (max-width: 960px) {
  .detail-layout { flex-direction: column; }
  .rail-col { width: 100%; position: static; }
}

.tabs-card { border-radius: 16px; border: 1px solid var(--border-hairline); box-shadow: none; }

/* ===== 档案信息（板块分组 + 标签在上/值在下的栅格） ===== */
.profile-section { padding: var(--space-2) 0; }
.profile-group { margin-bottom: var(--space-6); }
.section-title { font-size: var(--fs-16); font-weight: 700; color: var(--ink); display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.section-title::before { content: ''; width: 4px; height: 16px; background: var(--brand); border-radius: 2px; flex-shrink: 0; }
.field-grid { display: grid; grid-template-columns: repeat(3, 1fr); column-gap: var(--space-8); }
@media (max-width: 1200px) { .field-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .field-grid { grid-template-columns: 1fr; } }
.field-cell { padding: var(--space-3) 0; border-bottom: 1px solid var(--border-hairline); min-width: 0; }
.field-label { font-size: var(--fs-12); color: var(--ink-soft); margin-bottom: 4px; }
.field-value { font-size: var(--fs-14); color: var(--ink); font-weight: 500; word-break: break-all; }
.field-value.empty { color: var(--ink-faint); font-weight: 400; }

.resume-actions { display: flex; gap: var(--space-3); flex-wrap: wrap; margin-top: var(--space-2); }
.download-btn { background: var(--brand); border-color: var(--brand); border-radius: 8px; }

/* ===== 操作记录 ===== */
.history-section { padding: var(--space-2) 0; }

/* ===== 右侧操作栏卡片 ===== */
.rail-card { background: var(--glass-bg-card); border: 1px solid var(--border-hairline); border-radius: 16px; padding: var(--space-4); }
.rail-title { font-size: var(--fs-14); font-weight: 700; color: var(--ink); margin-bottom: var(--space-3); }
.stage-value { margin-bottom: var(--space-2); }
.rail-sub { font-size: var(--fs-12); color: var(--ink-soft); margin-top: var(--space-1); }
.application-list { display: flex; flex-direction: column; gap: var(--space-2); }
.application-item { padding: var(--space-2) var(--space-3); background: var(--brand-soft); border-radius: 8px; }
.application-position { font-size: var(--fs-14); font-weight: 600; color: var(--brand-fg); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.application-meta { display: flex; gap: var(--space-3); font-size: var(--fs-12); color: var(--ink-soft); margin-top: 2px; }
.upload-tip { margin-top: var(--space-4); color: var(--ink-faint); font-size: var(--fs-12); }

/* ===== 发送通知弹窗（保持既有交互） ===== */
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: var(--space-4) var(--space-6); border-bottom: 1px solid var(--overlay-glass-mid); }
.modal-title { font-size: var(--fs-20); font-weight: 700; color: var(--ink); }
.close-btn { width: 32px; height: 32px; border: none; background: transparent; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--ink-soft); transition: all var(--duration-base) var(--ease-out); }
.close-btn:hover { background: var(--overlay-glass-mid); color: var(--ink); }
.candidate-summary { display: flex; align-items: center; gap: var(--space-4); background: var(--brand-soft); border-radius: 8px; padding: var(--space-3); margin-top: var(--space-4); }
.candidate-avatar-sm { background: linear-gradient(135deg, var(--brand) 0%, color-mix(in srgb, var(--brand) 45%, var(--brand)) 100%); font-size: var(--fs-20); font-weight: 600; }
.candidate-info { flex: 1; }
.candidate-name-row { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); }
.candidate-name { font-size: var(--fs-16); font-weight: 600; color: var(--ink); }
.position-tag-sm { background: var(--brand-soft); color: var(--brand-dark); border-radius: 9999px; font-size: var(--fs-12); padding: 2px var(--space-2); }
.candidate-contact-row { display: flex; gap: var(--space-4); font-size: var(--fs-14); color: var(--ink-soft); }
.candidate-contact-row span { display: flex; align-items: center; gap: var(--space-1); }
.modal-content { display: flex; min-height: 400px; }
.left-sidebar { width: 340px; background: var(--c-info-soft); border-right: 1px solid var(--overlay-glass-mid); padding: var(--space-6); overflow-y: auto; display: flex; flex-direction: column; gap: var(--space-8); }
.step-section { display: flex; flex-direction: column; gap: var(--space-4); }
.step-title { font-size: var(--fs-16); font-weight: 600; color: var(--ink); display: flex; align-items: center; gap: var(--space-2); margin: 0; }
.step-number { width: 24px; height: 24px; border-radius: 50%; background: var(--brand-button); color: var(--on-brand); font-size: var(--fs-12); font-weight: 600; display: flex; align-items: center; justify-content: center; }
.step-content { display: flex; flex-direction: column; gap: var(--space-4); }
.content-group { display: flex; flex-direction: column; gap: var(--space-2); }
.content-group-title { font-size: var(--fs-14); font-weight: 600; color: var(--ink); padding-left: var(--space-1); }
.content-item { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); border-radius: 8px; border: 1px solid var(--border-hairline); background: var(--glass-bg-card); cursor: pointer; transition: all var(--duration-base) var(--ease-out); font-size: var(--fs-14); color: var(--ink); }
.content-item:hover { border-color: var(--brand); background: var(--brand-soft); }
.content-item.selected { border-color: var(--brand); background: var(--brand-a12); }
.method-item { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); border-radius: 8px; border: 1px solid var(--border-hairline); background: var(--glass-bg-card); cursor: pointer; transition: all var(--duration-base) var(--ease-out); }
.method-item:hover { border-color: var(--brand); background: var(--brand-soft); }
.method-item.selected { border-color: var(--brand); background: var(--brand-a12); }
.method-icon { font-size: var(--fs-20); color: var(--brand-fg); }
.method-name { font-size: var(--fs-14); font-weight: 600; color: var(--ink); }
.right-content { flex: 1; padding: var(--space-6); overflow-y: auto; display: flex; flex-direction: column; gap: var(--space-6); background: var(--glass-bg-card); }
.info-callout { display: flex; align-items: flex-start; gap: var(--space-2); padding: var(--space-3); background: var(--c-warning-soft); border: 1px solid var(--c-warning); border-radius: 8px; font-size: var(--fs-14); color: var(--ink); }
.editor-section { display: flex; flex-direction: column; gap: var(--space-3); }
.editor-header { display: flex; align-items: center; gap: var(--space-2); padding-bottom: var(--space-3); border-bottom: 1px solid var(--overlay-glass-mid); }
.editor-icon { font-size: var(--fs-24); color: var(--brand-fg); }
.editor-title { font-size: var(--fs-16); font-weight: 600; color: var(--ink); margin: 0; }
.editor-field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: var(--fs-12); font-weight: 500; color: var(--ink-soft); }
.sms-counter { display: flex; justify-content: space-between; align-items: center; }
.counter-text { font-size: var(--fs-12); color: var(--ink-faint); }
.email-subject-input, .email-content-input, .sms-content-input { background: var(--overlay-glass-mid); border: 1px solid var(--overlay-glass-mid); border-radius: 6px; }
.modal-footer { display: flex; justify-content: space-between; align-items: center; padding: var(--space-4) var(--space-6); border-top: 1px solid var(--overlay-glass-mid); background: var(--c-info-soft); }
.recipient-info { font-size: var(--fs-12); color: var(--ink-soft); }
.footer-buttons { display: flex; gap: var(--space-4); align-items: center; }
.send-btn-primary {
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
  border-color: var(--overlay-glass-mid);
}
.send-btn-primary:hover {
  transform: translateY(-1px);
}
</style>
