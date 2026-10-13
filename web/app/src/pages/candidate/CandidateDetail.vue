<template>
  <div class="candidate-detail-page" :class="{ 'page-zoomed': zoomed }">
    <!-- 顶部导航（返回 + 标题 + 候选人切换/编辑/放大/关闭操作） -->
    <div class="page-header">
      <n-space>
        <n-button class="back-btn" @click="goBack">
          <template #icon><n-icon :component="ChevronBackOutline" /></template>
          {{ t('pages.candidate.CandidateDetail.s1') }}
        </n-button>
        <n-h4 style="margin: 0; font-weight: 700">{{ t('pages.candidate.CandidateDetail.s2') }}</n-h4>
      </n-space>
      <n-space align="center" :size="8" class="header-ops">
        <n-button size="small" :disabled="!hasPrev" @click="goPrevCandidate">
          <template #icon><n-icon :component="ChevronBackOutline" /></template>
          {{ t('pages.candidate.CandidateDetail.s208') }}
        </n-button>
        <n-button size="small" :disabled="!hasNext" @click="goNextCandidate">
          {{ t('pages.candidate.CandidateDetail.s209') }}
          <template #icon><n-icon :component="ChevronForwardOutline" /></template>
        </n-button>
        <n-button size="small" @click="openEditResumeModal">
          <template #icon><n-icon :component="CreateOutline" /></template>
          {{ t('pages.candidate.CandidateDetail.s210') }}
        </n-button>
        <n-button size="small" @click="zoomed = !zoomed">
          <template #icon><n-icon :component="zoomed ? ContractOutline : ExpandOutline" /></template>
          {{ zoomed ? t('pages.candidate.CandidateDetail.s212') : t('pages.candidate.CandidateDetail.s211') }}
        </n-button>
        <n-button size="small" quaternary class="header-close" @click="goBack">
          <template #icon><n-icon :component="CloseOutline" /></template>
        </n-button>
      </n-space>
    </div>

    <!-- 候选人身份条：头像 + 姓名 + 编号 + 状态 + 锁定人 + 应聘职位 + 关键信息 -->
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
            <!-- 锁定人：候选人级招聘官为空时回退到投递记录认领人 -->
            <span v-if="lockOwnerText" class="meta-chip lock-chip">
              <n-icon :component="LockClosedOutline" />{{ t('pages.candidate.CandidateDetail.s205') }}：{{ lockOwnerText }}
            </span>
            <n-tag v-if="appliedPosition" class="position-tag" :bordered="false" size="small">
              {{ appliedPosition }}
            </n-tag>
          </div>
          <div class="identity-meta-row">
            <span v-if="genderAgeText" class="meta-chip">{{ genderAgeText }}</span>
            <span v-if="highestEducationText" class="meta-chip">{{ highestEducationText }}</span>
            <span v-if="candidateData.phone !== '—'" class="meta-chip"><n-icon :component="CallOutline" /> {{ candidateData.phone }}</span>
            <span v-if="candidateData.email !== '—'" class="meta-chip"><n-icon :component="MailOutline" /> {{ candidateData.email }}</span>
            <!-- 应聘渠道：来源渠道名（后端 source_channel_name） -->
            <span v-if="sourceChannelText" class="meta-chip">{{ t('pages.candidate.CandidateDetail.s206') }}：{{ sourceChannelText }}</span>
            <!-- 简历来源：按真实入库形态推导（摩卡同步/附件上传/手动录入） -->
            <span v-if="resumeSourceText" class="meta-chip">{{ t('pages.candidate.CandidateDetail.s207') }}：{{ resumeSourceText }}</span>
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

            <!-- 操作记录（真实操作历史：字段级追踪 + 哈希链完整性校验） -->
            <n-tab-pane name="history">
              <template #tab>
                <span><n-icon :component="TimeOutline" />{{ t('pages.candidate.CandidateDetail.s50') }}</span>
              </template>
              <div class="history-section">
                <div class="history-toolbar">
                  <n-button size="small" :loading="verifying" @click="handleVerifyHistories">
                    <template #icon><n-icon :component="ShieldCheckmarkOutline" /></template>
                    {{ t('pages.candidate.CandidateDetail.s225') }}
                  </n-button>
                  <n-tag v-if="verifyResult" :type="verifyResult.ok ? 'success' : 'error'" :bordered="false" size="small">
                    {{ verifyResult.ok
                      ? t('pages.candidate.CandidateDetail.s226', { n: verifyResult.checked })
                      : t('pages.candidate.CandidateDetail.s227', { seq: verifyResult.brokenAt }) }}
                  </n-tag>
                </div>
                <n-timeline v-if="histories.length > 0" class="history-timeline">
                  <n-timeline-item v-for="h in histories" :key="h.id" :type="actionTagType(h.action)">
                    <div class="history-card">
                      <div class="history-head">
                        <n-tag :type="actionTagType(h.action)" :bordered="false" size="small">{{ actionLabel(h) }}</n-tag>
                        <span class="history-seq">#{{ h.seq }}</span>
                        <span class="history-time">{{ formatTime(h.createdAt) }}</span>
                        <span class="history-operator">{{ h.operatorName || '—' }}</span>
                      </div>
                      <!-- 字段级 diff（信息更新 / 简历字段更新 / 简历上传替换） -->
                      <div v-if="historyChanges(h).length > 0" class="diff-table">
                        <div v-for="c in visibleChanges(h)" :key="c.field" class="diff-row">
                          <span class="diff-label">{{ changeLabel(c) }}</span>
                          <span class="diff-old">{{ fmtVal(c.old, 48) }}</span>
                          <span class="diff-arrow">→</span>
                          <span class="diff-new">{{ fmtVal(c.new, 48) }}</span>
                        </div>
                        <n-button
                          v-if="historyChanges(h).length > HISTORY_COLLAPSE"
                          quaternary type="primary" size="tiny" class="diff-toggle"
                          @click="toggleExpand(h.id)"
                        >
                          {{ isExpanded(h.id)
                            ? t('pages.candidate.CandidateDetail.s255')
                            : t('pages.candidate.CandidateDetail.s254', { n: historyChanges(h).length - HISTORY_COLLAPSE }) }}
                        </n-button>
                      </div>
                      <!-- 阶段/状态/解析等非 diff 动作 -->
                      <div v-else class="history-lines">
                        <div v-for="(line, i) in historyLines(h)" :key="i" class="history-line">{{ line }}</div>
                      </div>
                    </div>
                  </n-timeline-item>
                </n-timeline>
                <n-empty v-else :description="t('pages.candidate.CandidateDetail.s7')" style="margin: 24px 0" />
              </div>
            </n-tab-pane>

            <!-- Offer（2026-10-14：原「Offer管理」模块并入候选人管理，按 candidate 过滤） -->
            <n-tab-pane name="offer">
              <template #tab>
                <span><n-icon :component="GiftOutline" />{{ t('pages.candidate.CandidateDetail.s256') }}</span>
              </template>
              <CandidateOfferPanel :candidate-id="String(route.params.id || '')" />
            </n-tab-pane>
          </n-tabs>
        </n-card>
      </div>

      <!-- 右侧操作栏 -->
      <div class="rail-col">
        <!-- 当前阶段：琥珀色步骤面板（已完成=实心勾 / 当前=空心圆环 / 待办=浅点，悬浮显阶段名） -->
        <div class="rail-card">
          <div class="stage-panel">
            <div class="stage-panel-title">
              {{ t('pages.candidate.CandidateDetail.s191') }}：<span class="stage-panel-current">{{ currentStage || candidateData.stateDisplay || '—' }}</span>
            </div>
            <!-- 有流程阶段数据（>=2 个阶段）时渲染步骤条；悬浮任一节点显示该阶段名 -->
            <div v-if="stageSteps.length >= 2" class="stage-steps">
              <template v-for="(step, i) in stageSteps" :key="i">
                <n-tooltip placement="top">
                  <template #trigger>
                    <span class="stage-node" :class="step.state">
                      <n-icon v-if="step.state === 'done'" :component="CheckmarkOutline" class="stage-node-check" />
                    </span>
                  </template>
                  {{ step.name }}
                </n-tooltip>
                <span
                  v-if="i < stageSteps.length - 1"
                  class="stage-link"
                  :class="{ done: i < currentStageIdx }"
                />
              </template>
            </div>
            <!-- 兜底：无流程阶段数据时退化为当前阶段标签 -->
            <div v-else class="stage-value">
              <n-tag type="warning" :bordered="false">{{ currentStage || candidateData.stateDisplay || '—' }}</n-tag>
            </div>
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
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import {
  ChevronBackOutline,
  ChevronForwardOutline,
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
  CreateOutline,
  CheckmarkOutline,
  LockClosedOutline,
  ExpandOutline,
  ContractOutline,
  GiftOutline,
} from '@vicons/ionicons5'
import { getCandidate, listCandidates, verifyCandidateHistories } from '../../api/candidate'
import { fetchConfig, defaultConfig, type StandardResumeConfig } from '../../api/standard-resume'
import { getResumeFields, putResumeFields } from '../../api/candidate-resume-fields'
import { listFields, type FieldDefinition } from '../../api/dynamic-field'
import InitiateBackgroundCheckModal from './InitiateBackgroundCheckModal.vue'
import CandidateOfferPanel from '../../components/candidate/CandidateOfferPanel.vue'
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
  highestEducation?: string | null
  current_state?: string
  state_display?: string
  stateDisplay?: string
  created_at?: string
  updated_at?: string
  resume_file_url?: string | null
  tags?: Array<string | { name?: string }> | null
  /** 锁定人（候选人级招聘官用户名；为空时前端回退投递记录认领人） */
  recruiter_name?: string
  recruiterName?: string
  /** 简历来源（后端推导：摩卡同步 / 附件上传 / 手动录入） */
  resume_source?: string
  resumeSource?: string
  /** 应聘渠道（来源渠道名） */
  source_channel_name?: string
  sourceChannelName?: string
  /** 投递记录（后端 get_applications，CamelCase 键） */
  applications?: Array<{
    id?: string; code?: string; positionTitle?: string | null
    processName?: string | null
    state?: string; currentStage?: string | null
    grabbedByName?: string
    stageList?: string[]
    createdAt?: string
  }> | null
  /** 操作历史（CandidateHistorySerializer，CamelCase 键） */
  histories?: Array<{
    id?: string; seq?: number; action?: string; detail?: any
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

// ===== 操作记录渲染（字段级 diff / 阶段·状态流转 / 解析溯源 / 哈希链校验） =====
// 操作类型 → i18n key（s235–s244）；命中不到则回退原始 action 串，避免空白
const ACTION_LABEL_KEY: Record<string, string> = {
  CREATED: 's235', INFO_UPDATED: 's236', RESUME_FIELDS_UPDATED: 's237',
  RESUME_UPLOADED: 's238', RESUME_PARSED: 's239', STAGE_CHANGED: 's240',
  STATE_CHANGED: 's241', BLACKLIST_CHANGED: 's242', BLACKLISTED: 's243',
  UNBLACKLISTED: 's244',
}
const STATE_ENUM_LABEL_KEY: Record<string, string> = {
  APPLIED: 's245', IN_PROCESS: 's246', OFFER_SENT: 's247', ONBOARDED: 's248',
  PROCESS_FAILED: 's249', WITHDRAWN: 's250', TALENT_POOL: 's251', PROCESS_PAUSED: 's252',
}
// 操作类型 → tag 配色
const ACTION_TAG_TYPE: Record<string, 'success' | 'info' | 'warning' | 'error' | 'default'> = {
  CREATED: 'success', INFO_UPDATED: 'info', RESUME_FIELDS_UPDATED: 'info',
  RESUME_UPLOADED: 'info', RESUME_PARSED: 'warning', STAGE_CHANGED: 'warning',
  STATE_CHANGED: 'success', BLACKLIST_CHANGED: 'error', BLACKLISTED: 'error',
  UNBLACKLISTED: 'default',
}
function actionLabel(h: any): string {
  const key = ACTION_LABEL_KEY[h?.action]
  return key ? t(`pages.candidate.CandidateDetail.${key}`) : (h?.action || '')
}
function actionTagType(action?: string): 'success' | 'info' | 'warning' | 'error' | 'default' {
  return ACTION_TAG_TYPE[action ?? ''] ?? 'info'
}
function stateLabel(v: any): string {
  if (v == null || v === '') return '—'
  const key = STATE_ENUM_LABEL_KEY[v]
  return key ? t(`pages.candidate.CandidateDetail.${key}`) : String(v)
}
function fmtVal(v: any, max = 60): string {
  if (v === null || v === undefined) return '—'
  let s: string
  if (typeof v === 'object') {
    try { s = JSON.stringify(v) } catch { s = String(v) }
  } else {
    s = String(v)
  }
  if (s.trim() === '') return '—'
  return s.length > max ? `${s.slice(0, max)}…` : s
}

/** 空值归一化（对齐后端 audit.norm_empty）：null / '' / [] / {} 视为同义空 */
function normEmptyFE(v: any): unknown {
  if (v === null || v === undefined) return null
  if (typeof v === 'string' && v.trim() === '') return null
  if (Array.isArray(v) && v.length === 0) return null
  if (typeof v === 'object' && Object.keys(v).length === 0) return null
  return v
}

/** 字段级 diff 提取（信息更新 / 简历字段更新 / 简历上传替换），并过滤 null↔'' 假变更 */
function historyChanges(h: any): any[] {
  const action = h?.action
  if (action !== 'INFO_UPDATED' && action !== 'RESUME_FIELDS_UPDATED' && action !== 'RESUME_UPLOADED') return []
  const changes = Array.isArray(h?.detail?.changes) ? h.detail.changes : []
  return changes.filter((c: any) => normEmptyFE(c?.old) !== normEmptyFE(c?.new))
}

/** diff 行中文标签：后端 label → 动态字段定义 label → FIELD_LABEL_I18N 译文 → 裸 fieldKey */
function changeLabel(c: any): string {
  if (c?.label) return String(c.label)
  const fk = String(c?.field ?? '')
  const def = fieldDefMap.value[fk]
  if (def?.label) return def.label
  const i18nKey = FIELD_LABEL_I18N[fk]
  if (i18nKey) return t(`pages.candidate.CandidateDetail.${i18nKey}`)
  return fk
}

// 长列表折叠：默认展示前 N 条，可展开全部（单次批量保存可能 30+ 字段）
const HISTORY_COLLAPSE = 6
const expandedHistory = ref<Set<string>>(new Set())
function isExpanded(id: string | undefined): boolean {
  return expandedHistory.value.has(id ?? '')
}
function toggleExpand(id: string | undefined) {
  const key = id ?? ''
  const next = new Set(expandedHistory.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedHistory.value = next
}
function visibleChanges(h: any): any[] {
  const all = historyChanges(h)
  return isExpanded(h?.id) ? all : all.slice(0, HISTORY_COLLAPSE)
}

function historyLines(h: any): string[] {
  const d = h?.detail || {}
  const action = h?.action
  const lines: string[] = []
  if (action === 'INFO_UPDATED' || action === 'RESUME_FIELDS_UPDATED' || action === 'RESUME_UPLOADED') {
    // diff 动作由模板 diff-table 渲染；过滤后无真实变更时提示
    lines.push(t('pages.candidate.CandidateDetail.s228'))
  } else if (action === 'STAGE_CHANGED') {
    lines.push(`${fmtVal(d.from_stage, 40)} → ${fmtVal(d.to_stage, 40)}`)
    if (d.position) lines.push(`${t('pages.candidate.CandidateDetail.s204')}：${d.position}`)
    if (d.via) lines.push(t('pages.candidate.CandidateDetail.s230', { via: d.via }))
  } else if (action === 'STATE_CHANGED') {
    lines.push(`${stateLabel(d.from)} → ${stateLabel(d.to)}`)
  } else if (action === 'BLACKLISTED' || action === 'UNBLACKLISTED' || action === 'BLACKLIST_CHANGED') {
    const toStr = (v: any) =>
      v === true ? t('pages.candidate.CandidateDetail.s243') : v === false ? t('pages.candidate.CandidateDetail.s244') : fmtVal(v)
    lines.push(`${toStr(d.from)} → ${toStr(d.to)}`)
  } else if (action === 'RESUME_PARSED') {
    const p = d.parse || {}
    if (p.provider) lines.push(t('pages.candidate.CandidateDetail.s231', { provider: p.provider }))
    if (p.confidence != null) lines.push(t('pages.candidate.CandidateDetail.s232', { confidence: p.confidence }))
    if (p.educations != null) lines.push(t('pages.candidate.CandidateDetail.s233', { n: p.educations }))
    if (p.experiences != null) lines.push(t('pages.candidate.CandidateDetail.s234', { n: p.experiences }))
    if (p.channel) lines.push(`${t('pages.candidate.CandidateDetail.s253')}：${p.channel}`)
  } else if (action === 'CREATED') {
    lines.push(`${t('pages.candidate.CandidateDetail.s253')}：${d.source || '—'}`)
  } else {
    // 兜底：逐键展示 detail 内容
    for (const [k, v] of Object.entries(d)) lines.push(`${k}：${fmtVal(v)}`)
  }
  return lines
}

// 哈希链完整性校验（不可篡改检测）
const verifying = ref(false)
const verifyResult = ref<{ ok: boolean; checked: number; brokenAt: number | null } | null>(null)
async function handleVerifyHistories() {
  const id = route.params.id
  if (!id) return
  verifying.value = true
  verifyResult.value = null
  try {
    const res: any = await verifyCandidateHistories(String(id))
    // 响应体已抽成 { ok, checked, brokenAt }
    verifyResult.value = {
      ok: !!res?.ok,
      checked: Number(res?.checked ?? 0),
      brokenAt: res?.brokenAt ?? null,
    }
    if (verifyResult.value.ok) {
      message.success(t('pages.candidate.CandidateDetail.s226', { n: verifyResult.value.checked }))
    } else {
      message.error(t('pages.candidate.CandidateDetail.s227', { seq: verifyResult.value.brokenAt }))
    }
  } catch (e: any) {
    message.error(e?.message || t('pages.candidate.CandidateDetail.s227', { seq: '?' }))
  } finally {
    verifying.value = false
  }
}

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

/** 最高学历（渲染器 camelCase 后为 highestEducation，兼容 snake_case 回退） */
const highestEducationText = computed(() => pickDetail('highest_education'))

/** 锁定人：候选人级招聘官优先，为空回退到投递记录认领人（grabbedByName） */
const lockOwnerText = computed<string>(() => {
  const own = (pickDetail('recruiter_name') || '').trim()
  if (own) return own
  const apps = candidateDetail.value?.applications ?? []
  const hit = apps.find((a) => (a?.grabbedByName || '').trim())
  return (hit?.grabbedByName || '').trim()
})

/** 应聘渠道：来源渠道名（后端 source_channel_name） */
const sourceChannelText = computed(() => (pickDetail('source_channel_name') || '').trim())

/** 简历来源后端值 → i18n 键（后端返固定中文串，未知值原样展示，不虚构） */
const RESUME_SOURCE_I18N: Record<string, string> = {
  摩卡同步: 's214',
  附件上传: 's215',
  手动录入: 's216',
}
const resumeSourceText = computed(() => {
  const v = (pickDetail('resume_source') || '').trim()
  if (!v) return ''
  const key = RESUME_SOURCE_I18N[v]
  return key ? t(`pages.candidate.CandidateDetail.${key}`) : v
})

/** 流程阶段有序列表（后端 applications[0].stage_list，按 order 升序） */
const stageList = computed<string[]>(() => applications.value[0]?.stageList ?? [])

/** 当前阶段在阶段列表中的下标；-1 = 未匹配/无数据 */
const currentStageIdx = computed(() => {
  const list = stageList.value
  const cur = (currentStage.value || '').trim()
  if (!list.length || !cur) return -1
  return list.findIndex((s) => s === cur)
})

/** 步骤条节点状态：done=已完成(实心勾) / current=当前(空心圆环) / todo=待办(浅点) */
const stageSteps = computed(() => {
  const idx = currentStageIdx.value
  return stageList.value.map((name, i) => ({
    name,
    state: idx < 0 ? 'todo' : i < idx ? 'done' : i === idx ? 'current' : 'todo',
  }))
})

// ===== 上一位 / 下一位候选人 =====
// 列表页跳转详情不带筛选上下文，故在详情页按默认排序(-created_at)拉取候选人序列，
// 当前 id 不在首页则继续翻页（上限 5 页 × 200 条），找不到则禁用切换。
const navIds = ref<string[]>([])
const navIndex = ref(-1)
const hasPrev = computed(() => navIndex.value > 0)
const hasNext = computed(() => navIndex.value >= 0 && navIndex.value < navIds.value.length - 1)

async function loadNavContext() {
  const cur = String(route.params.id || '')
  const ids: string[] = []
  let found = -1
  try {
    for (let p = 1; p <= 5; p++) {
      const res = await listCandidates({ page: p, pageSize: 200 })
      const items: any[] = res?.data ?? []
      const pageIds = items.map((i) => String(i?.id || '')).filter(Boolean)
      ids.push(...pageIds)
      found = ids.indexOf(cur)
      if (found >= 0) break
      if (pageIds.length < 200) break
    }
  } catch {
    // 列表不可用（如无 recruit:candidate:list 权限）时静默降级：切换按钮禁用
  }
  navIds.value = ids
  navIndex.value = found
}

function goPrevCandidate() {
  if (!hasPrev.value) return
  router.push(`/candidates/${navIds.value[navIndex.value - 1]}`)
}
function goNextCandidate() {
  if (!hasNext.value) return
  router.push(`/candidates/${navIds.value[navIndex.value + 1]}`)
}

/** 放大页面（专注模式）：页面铺满视口，再次点击还原 */
const zoomed = ref(false)

async function loadCandidateData(id: string) {
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
}

onMounted(async () => {
  const id = route.params.id ? String(route.params.id) : ''
  await Promise.all([loadCandidateData(id), loadNavContext()])
})

// 上一位/下一位切换（同组件仅路由参数变化，onMounted 不重跑，须 watch 重载）
watch(() => route.params.id, async (newId, oldId) => {
  if (!newId || newId === oldId) return
  await loadCandidateData(String(newId))
  const idx = navIds.value.indexOf(String(newId))
  if (idx >= 0) navIndex.value = idx
  else await loadNavContext()
  window.scrollTo({ top: 0 })
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
.page-header { margin-bottom: var(--space-4); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-2); }
.back-btn { border: none; background: transparent; }
.header-ops { flex-wrap: wrap; }
.header-close { padding: 0 8px; }

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
.lock-chip .n-icon { color: var(--c-warning); }

/* 放大页面（专注模式）: 详情页铺满视口, 再次点击还原 */
.candidate-detail-page.page-zoomed {
  position: fixed; inset: 0; z-index: 1000;
  overflow-y: auto; overscroll-behavior: contain;
  background: var(--c-info-soft);
}

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
.history-toolbar { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-4); flex-wrap: wrap; }
.history-timeline :deep(.n-timeline-item-content) { min-width: 0; }
.history-card {
  background: var(--surface-1, rgba(0, 0, 0, 0.02));
  border: 1px solid var(--line-soft, rgba(0, 0, 0, 0.06));
  border-radius: var(--radius-2, 8px);
  padding: var(--space-3, 12px) var(--space-4, 16px);
}
.history-head { display: flex; align-items: center; gap: var(--space-2, 8px); flex-wrap: wrap; }
.history-seq { color: var(--ink-faint, var(--ink-soft)); font-size: var(--fs-12); font-variant-numeric: tabular-nums; }
.history-time { color: var(--ink-soft); font-size: var(--fs-12); }
.history-operator { margin-left: auto; color: var(--ink-soft); font-size: var(--fs-12); }
.history-lines { margin-top: var(--space-2, 8px); display: flex; flex-direction: column; gap: 2px; }
.history-line { font-size: var(--fs-12); color: var(--ink); line-height: 1.6; word-break: break-all; }
.diff-table { margin-top: var(--space-2, 8px); display: flex; flex-direction: column; }
.diff-row {
  display: grid;
  grid-template-columns: minmax(72px, max-content) 1fr 18px 1fr;
  align-items: baseline;
  gap: var(--space-2, 8px);
  padding: 3px 0;
  font-size: var(--fs-12);
  line-height: 1.55;
}
.diff-row + .diff-row { border-top: 1px dashed var(--line-soft, rgba(0, 0, 0, 0.05)); }
.diff-label { color: var(--ink-soft); white-space: nowrap; }
.diff-label::after { content: '：'; }
.diff-old {
  color: var(--ink-faint, var(--ink-soft));
  text-decoration: line-through;
  text-decoration-color: rgba(207, 68, 68, 0.45);
  word-break: break-all;
}
.diff-arrow { color: var(--brand, #4f6ef2); text-align: center; }
.diff-new { color: var(--ink); font-weight: 500; word-break: break-all; }
.diff-toggle { align-self: flex-start; margin-top: 2px; }

/* ===== 右侧操作栏卡片 ===== */
.rail-card { background: var(--glass-bg-card); border: 1px solid var(--border-hairline); border-radius: 16px; padding: var(--space-4); }
.rail-title { font-size: var(--fs-14); font-weight: 700; color: var(--ink); margin-bottom: var(--space-3); }
.stage-value { margin-bottom: var(--space-2); }
.rail-sub { font-size: var(--fs-12); color: var(--ink-soft); margin-top: var(--space-1); }

/* ===== 当前阶段：琥珀色步骤面板（Moka 参考样式） =====
 * 已完成=实心圆+白勾 / 当前=空心圆环 / 待办=浅色小点; 节点间连线在当前位置前为实线、
 * 之后为虚线; 悬浮任一节点以 tooltip 展示阶段名。颜色全部走 token（琥珀 = --c-warning）。 */
.stage-panel {
  background: var(--c-warning-soft);
  border: 1px solid color-mix(in srgb, var(--c-warning) 30%, transparent);
  border-radius: 12px;
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-2);
}
.stage-panel-title { font-size: var(--fs-14); font-weight: 600; color: var(--ink); margin-bottom: var(--space-3); }
.stage-panel-current { font-weight: 700; }
.stage-steps { display: flex; align-items: center; }
.stage-node {
  width: 16px; height: 16px; border-radius: 50%; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  cursor: default;
}
.stage-node.done { background: var(--c-warning); }
.stage-node.done .stage-node-check { color: #fff; font-size: 11px; }
/* 当前阶段: 空心圆环（略大于已完成节点，视觉锚点） */
.stage-node.current { width: 18px; height: 18px; background: transparent; border: 2px solid var(--c-warning); }
/* 待办: 浅色小点 */
.stage-node.todo { width: 10px; height: 10px; background: color-mix(in srgb, var(--c-warning) 32%, transparent); }
/* 节点间连线: 当前位置之前实线, 之后虚线 */
.stage-link {
  flex: 1; min-width: 6px; margin: 0 3px; height: 0;
  border-top: 2px dashed color-mix(in srgb, var(--c-warning) 32%, transparent);
}
.stage-link.done { border-top-style: solid; border-top-color: var(--c-warning); }
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
