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
        <n-button
          size="small"
          quaternary
          class="header-close"
          :aria-label="t('components.common.A11y.s1')"
          @click="goBack"
        >
          <template #icon><n-icon :component="CloseOutline" aria-hidden="true" /></template>
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
            <!-- 应聘职位：点击展开「已投递 N 次」浮层面板（2026-10-21 兵哥需求：申请=每次应聘记录） -->
            <n-tag
              v-if="appliedPosition"
              class="position-tag"
              :bordered="false"
              size="small"
              tag="div"
              :class="{ 'position-tag--clickable': applicationPanelVisible, 'position-tag--multi': applicationRecords.length > 1 }"
              role="button"
              tabindex="0"
              @click="toggleApplicationPanel"
              @keydown.enter.prevent="toggleApplicationPanel"
              @keydown.space.prevent="toggleApplicationPanel"
            >
              <span v-if="applicationRecords.length > 1" class="position-tag__count">{{ applicationRecords.length }}</span>
              <span class="position-tag__text">{{ appliedPosition }}</span>
              <n-icon v-if="applicationRecords.length > 1" :component="ChevronForwardOutline" class="position-tag__caret" />
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

    <!-- 已投递 N 次浮层面板（2026-10-21 兵哥需求：申请=每次应聘记录，展示每次应聘的不同职位）
         锚点=身份条里的应聘职位标签；点击标签开合；点击外部/ESC 关闭 -->
    <div v-if="applicationPanelVisible" class="application-panel" role="dialog" :aria-label="applicationPanelTitle">
      <div class="application-panel__head">{{ applicationPanelTitle }}</div>
      <div class="application-panel__body">
        <div
          v-for="rec in applicationRecords"
          :key="rec.id || rec.createdAt"
          class="application-record"
        >
          <div class="application-record__top">
            <span class="application-record__position">{{ rec.positionTitle || '—' }}</span>
            <span v-if="rec.positionCode || rec.processCode" class="application-record__codes">
              <span v-if="rec.positionCode">（{{ rec.positionCode }}）</span>
              <span v-if="rec.processCode">（{{ rec.processCode }}）</span>
            </span>
            <span v-if="rec.createdAt" class="application-record__time">{{ formatTime(rec.createdAt) }}</span>
          </div>
          <div v-if="rec.processName" class="application-record__sub">{{ rec.processName }}</div>
          <div v-if="rec.currentStage" class="application-record__stage">
            {{ t('pages.candidate.CandidateDetail.applicationPanelStage') }}：{{ rec.currentStage }}
            <span v-if="rec.stageList && rec.stageList.length">（{{ rec.stageList.join(' / ') }}）</span>
          </div>
          <div v-if="rec.state" class="application-record__state">{{ rec.state }}</div>
        </div>
      </div>
    </div>
    <!-- 浮层遮罩：仅用于捕获点击关闭，不遮挡视觉（透明） -->
    <div v-if="applicationPanelVisible" class="application-panel__mask" @click="applicationPanelVisible = false" />
    <div class="detail-layout">
      <div class="main-col">
        <n-card class="tabs-card">
          <!-- 2026-10-21 兵哥：页签重排 —— 原始简历（新）→ 标准简历 → Offer → 待入职 → 操作记录（末位）；页签去 icon -->
          <n-tabs v-model:value="activeTab" type="line" animated>
            <!-- 原始简历（上传的简历原文件在线预览，pdf/图片内嵌，其余格式引导下载） -->
            <n-tab-pane name="resume-raw">
              <template #tab>{{ t('pages.candidate.CandidateDetail.s342') }}</template>
              <div class="raw-resume-section">
                <n-spin v-if="loading" style="margin: 24px 0" />
                <template v-else>
                  <div v-if="resumeFileUrl" class="raw-resume-actions">
                    <n-button type="primary" @click="handleDownloadResume">
                      <template #icon><n-icon :component="DownloadOutline" /></template>
                      {{ t('pages.candidate.CandidateDetail.s34') }}
                    </n-button>
                    <n-button v-permission="'recruit:candidate:edit'" @click="openUploadResumeModal">
                      <template #icon><n-icon :component="CloudUploadOutline" /></template>
                      {{ t('pages.candidate.CandidateDetail.s49') }}
                    </n-button>
                  </div>
                  <template v-if="resumeFileUrl && resumePreviewable">
                    <iframe
                      v-if="resumeObjectUrl"
                      :src="resumeObjectUrl"
                      class="raw-resume-frame"
                      :title="t('pages.candidate.CandidateDetail.s342')"
                    />
                    <n-empty
                      v-else-if="resumePreviewError"
                      :description="t('pages.candidate.CandidateDetail.s345')"
                      style="margin: 24px 0"
                    >
                      <template #extra>
                        <n-button type="primary" @click="handleDownloadResume">
                          <template #icon><n-icon :component="DownloadOutline" /></template>
                          {{ t('pages.candidate.CandidateDetail.s34') }}
                        </n-button>
                      </template>
                    </n-empty>
                    <n-spin v-else style="margin: 24px 0" />
                  </template>
                  <div v-else-if="resumeFileUrl" class="raw-resume-fallback">
                    <n-empty :description="t('pages.candidate.CandidateDetail.s343')" style="margin: 24px 0" />
                  </div>
                  <div v-else class="raw-resume-fallback">
                    <n-empty :description="t('pages.candidate.CandidateDetail.s48')" style="margin: 24px 0">
                      <template #extra>
                        <n-button v-permission="'recruit:candidate:edit'" @click="openUploadResumeModal">
                          <template #icon><n-icon :component="CloudUploadOutline" /></template>
                          {{ t('pages.candidate.CandidateDetail.s49') }}
                        </n-button>
                      </template>
                    </n-empty>
                  </div>
                </template>
              </div>
            </n-tab-pane>

            <!-- 标准简历（原「档案信息」：基本信息 + 简历信息整合，按业务板块分组） -->
            <n-tab-pane name="profile">
              <template #tab>{{ t('pages.candidate.CandidateDetail.s183') }}</template>
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

            <!-- Offer（2026-10-14：原「Offer管理」模块并入候选人管理，按 candidate 过滤） -->
            <n-tab-pane name="offer">
              <template #tab>{{ t('pages.candidate.CandidateDetail.s256') }}</template>
              <CandidateOfferPanel :candidate-id="String(route.params.id || '')" />
            </n-tab-pane>

            <!-- 录用信息（原「待入职」，2026-10-21：原独立「待入职」全局列表页移除，功能并入候选人管理，
                 作为 offer 之后的独立页签呈现；按 candidate 过滤，后端 recruit:candidate:onboarding:list 在数据层兜底权限） -->
            <n-tab-pane name="onboarding">
              <template #tab>{{ t('pages.candidate.CandidateDetail.s320') }}</template>
              <CandidateOnboardingPanel :candidate-id="String(route.params.id || '')" />
            </n-tab-pane>

            <!-- 操作记录（真实操作历史：字段级追踪 + 哈希链完整性校验；2026-10-21 移至末位） -->
            <n-tab-pane name="history">
              <template #tab>{{ t('pages.candidate.CandidateDetail.s50') }}</template>
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

        <!-- 操作（2026-10-19 合并原「简历操作」卡片）：一行两个按钮
             状态驱动：已淘汰 / 已入库后相应按钮转为禁用态，避免重复提交 -->
        <div class="rail-card">
          <div class="rail-title">{{ t('pages.candidate.CandidateDetail.s192') }}</div>
          <div class="action-grid">
            <n-button type="primary" @click="openNotificationModal">
              {{ t('pages.candidate.CandidateDetail.s3') }}
            </n-button>
            <n-button type="warning" @click="bgModalVisible = true">
              {{ t('pages.candidate.InitiateBgCheck.title') }}
            </n-button>
            <n-button type="warning" secondary @click="openSupplementBg">
              {{ t('pages.candidate.InitiateBgCheck.titleSupplement') }}
            </n-button>
            <n-button
              :type="isFollowed ? 'primary' : 'default'"
              :loading="followLoading"
              :aria-pressed="isFollowed"
              @click="toggleFollow"
            >
              {{ isFollowed
                ? t('pages.candidate.CandidateDetail.s293')
                : t('pages.candidate.CandidateDetail.s291') }}
            </n-button>
            <n-button :disabled="forwardLoading" @click="openForwardModal">
              {{ t('pages.candidate.CandidateDetail.s294') }}
            </n-button>
            <n-button :disabled="loadingPositions" @click="openRecommendModal">
              {{ t('pages.candidate.CandidateDetail.s285') }}
            </n-button>
            <n-button :disabled="poolLoading || isInPool" @click="openPoolModal">
              {{ t('pages.candidate.CandidateDetail.s282') }}
            </n-button>
            <n-button
              type="error"
              secondary
              :disabled="eliminateLoading || isEliminated"
              @click="openEliminateModal"
            >
              {{ t('pages.candidate.CandidateDetail.s276') }}
            </n-button>
          </div>
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

    <!-- 上传简历弹窗（2026-10-21 修复：card 弹窗无 positive 按钮，原 @positive-click 永不触发；
         现补 footer 确定按钮 + 真实上传：/media/upload/ 拿 url → PATCH resume_file_url → 刷新详情） -->
    <n-modal
      v-model:show="uploadResumeModalVisible"
      preset="card"
      :title="t('pages.candidate.CandidateDetail.s96')"
      :width="500"
      style="max-width: 90vw"
    >
      <n-upload
        v-model:file-list="fileList"
        :max="1"
        :default-upload="false"
        accept=".pdf,.doc,.docx"
        @before-upload="beforeUpload"
      >
        <n-button :disabled="uploadingResume">
          <template #icon><n-icon :component="CloudUploadOutline" /></template>
          {{ t('pages.candidate.CandidateDetail.s97') }}
        </n-button>
      </n-upload>
      <div class="upload-tip">{{ t('pages.candidate.CandidateDetail.s98') }}</div>
      <template #action>
        <n-space justify="end">
          <n-button :disabled="uploadingResume" @click="uploadResumeModalVisible = false">
            {{ t('pages.candidate.CandidateDetail.s90') }}
          </n-button>
          <n-button
            type="primary"
            :loading="uploadingResume"
            :disabled="fileList.length === 0 || uploadingResume"
            @click="handleUploadResume"
          >
            {{ t('pages.candidate.CandidateDetail.s344') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 发起背调（供应商集成系统） -->
    <InitiateBackgroundCheckModal
      v-model:show="bgModalVisible"
      :candidate="{ id: candidateData.id, name: candidateData.name, phone: candidateData.phone,
                    idCardNo: pickDetail('id_card_no') || '', email: candidateDetail?.email,
                    position: appliedPosition, expectedOnboardingDate: '' }"
      :parent-order-id="bgParentOrderId"
    />

    <!-- 淘汰确认（R-106 不可逆操作：确认框 + 影响预览） -->
    <n-modal
      v-model:show="eliminateModalVisible"
      preset="card"
      :title="t('pages.candidate.CandidateDetail.s276')"
      :width="640"
      style="max-width: 92vw"
    >
      <n-alert type="warning" :bordered="false" style="margin-bottom: 16px">
        {{ t('pages.candidate.CandidateDetail.s279') }}
      </n-alert>
      <!-- 原因库场景规则（2026-10-19）：命中「淘汰」规则时展示原因标签选择 -->
      <ReasonTagPicker
        v-if="eliminateRule"
        v-model:selected="eliminateTagIds"
        v-model:other-reasons="eliminateOtherReasons"
        :rule="eliminateRule"
        style="margin-bottom: 16px"
      />
      <n-form label-placement="top">
        <n-form-item
          :label="t('pages.candidate.CandidateDetail.s277')"
          :validation-status="eliminateReason ? undefined : 'error'"
          :feedback="eliminateReason ? undefined : t('pages.candidate.CandidateDetail.s278')"
          required
        >
          <n-input
            v-model:value="eliminateReason"
            type="textarea"
            :rows="3"
            :placeholder="t('pages.candidate.CandidateDetail.s277')"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="eliminateLoading" @click="eliminateModalVisible = false">
            {{ t('pages.candidate.CandidateDetail.s90') }}
          </n-button>
          <n-button
            type="error"
            :loading="eliminateLoading"
            :disabled="!eliminateReason.trim()"
            @click="handleEliminate"
          >
            {{ t('pages.candidate.CandidateDetail.s276') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 放入人才库 -->
    <n-modal
      v-model:show="poolModalVisible"
      preset="card"
      :title="t('pages.candidate.CandidateDetail.s282')"
      :width="640"
      style="max-width: 92vw"
    >
      <!-- 原因库场景规则（2026-10-19）：命中「放入人才库」规则时展示原因标签选择 -->
      <ReasonTagPicker
        v-if="poolRule"
        v-model:selected="poolTagIds"
        v-model:other-reasons="poolOtherReasons"
        :rule="poolRule"
        style="margin-bottom: 16px"
      />
      <n-form label-placement="top">
        <n-form-item :label="t('pages.candidate.CandidateDetail.s283')">
          <n-input
            v-model:value="poolReason"
            type="textarea"
            :rows="3"
            :placeholder="t('pages.candidate.CandidateDetail.s283')"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="poolLoading" @click="poolModalVisible = false">
            {{ t('pages.candidate.CandidateDetail.s90') }}
          </n-button>
          <n-button type="primary" :loading="poolLoading" @click="handleMoveToPool">
            {{ t('pages.candidate.CandidateDetail.s282') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 推荐其他职位 -->
    <n-modal
      v-model:show="recommendModalVisible"
      preset="card"
      :title="t('pages.candidate.CandidateDetail.s285')"
      :width="520"
      style="max-width: 92vw"
    >
      <n-form label-placement="top">
        <n-form-item
          :label="t('pages.candidate.CandidateDetail.s286')"
          :validation-status="recommendPositionId ? undefined : 'error'"
          :feedback="recommendPositionId ? undefined : t('pages.candidate.CandidateDetail.s288')"
          required
        >
          <n-select
            v-model:value="recommendPositionId"
            :options="positionOptions"
            :loading="loadingPositions"
            filterable
            clearable
            :placeholder="t('pages.candidate.CandidateDetail.s286')"
          />
        </n-form-item>
        <n-form-item :label="t('pages.candidate.CandidateDetail.s287')">
          <n-input
            v-model:value="recommendComment"
            type="textarea"
            :rows="3"
            :placeholder="t('pages.candidate.CandidateDetail.s287')"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="recommendLoading" @click="recommendModalVisible = false">
            {{ t('pages.candidate.CandidateDetail.s90') }}
          </n-button>
          <n-button
            type="primary"
            :loading="recommendLoading"
            :disabled="!recommendPositionId"
            @click="handleRecommend"
          >
            {{ t('pages.candidate.CandidateDetail.s285') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 转发给内部同事 -->
    <n-modal
      v-model:show="forwardModalVisible"
      preset="card"
      :title="t('pages.candidate.CandidateDetail.s294')"
      :width="520"
      style="max-width: 92vw"
    >
      <n-form label-placement="top">
        <n-form-item
          :label="t('pages.candidate.CandidateDetail.s295')"
          :validation-status="forwardTargets.length ? undefined : 'error'"
          :feedback="forwardTargets.length ? undefined : t('pages.candidate.CandidateDetail.s296')"
          required
        >
          <n-select
            v-model:value="forwardTargets"
            multiple
            :options="colleagueOptions"
            :loading="loadingColleagues"
            filterable
            :placeholder="t('pages.candidate.CandidateDetail.s295')"
          />
        </n-form-item>
        <n-form-item :label="t('pages.candidate.CandidateDetail.s297')">
          <n-input
            v-model:value="forwardNote"
            type="textarea"
            :rows="3"
            :placeholder="t('pages.candidate.CandidateDetail.s298')"
          />
        </n-form-item>
      </n-form>

      <!-- 已有转发记录：谁转给了谁（R-104 空态） -->
      <div v-if="forwardRecords.length > 0" class="forward-records">
        <div class="forward-records-title">{{ t('pages.candidate.CandidateDetail.s304') }}</div>
        <div v-for="r in forwardRecords" :key="r.id" class="forward-record">
          <span class="forward-record-text">
            {{ t('pages.candidate.CandidateDetail.s310', { name: r.fromUserName || r.fromUserId }) }}
          </span>
          <span v-if="r.note" class="forward-record-note">{{ r.note }}</span>
        </div>
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button :disabled="forwardLoading" @click="forwardModalVisible = false">
            {{ t('pages.candidate.CandidateDetail.s90') }}
          </n-button>
          <n-button
            type="primary"
            :loading="forwardLoading"
            :disabled="forwardTargets.length === 0"
            @click="handleForward"
          >
            {{ t('pages.candidate.CandidateDetail.s294') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import {
  ChevronBackOutline,
  ChevronForwardOutline,
  MailOutline,
  CallOutline,
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
} from '@vicons/ionicons5'
import {
  getCandidate,
  listCandidates,
  updateCandidate,
  verifyCandidateHistories,
  transitionCandidate,
  recommendCandidateToPosition,
  getCandidateFollowState,
  followCandidate,
  unfollowCandidate,
  forwardCandidate,
  listCandidateForwards,
  type ForwardRow,
} from '../../api/candidate'
import { listPositions } from '../../api/position'
import { listUsers, type User } from '../../api/users'
import { fetchConfig, defaultConfig, type StandardResumeConfig } from '../../api/standard-resume'
import { getResumeFields, putResumeFields } from '../../api/candidate-resume-fields'
import { listFields, type FieldDefinition } from '../../api/dynamic-field'
import InitiateBackgroundCheckModal from './InitiateBackgroundCheckModal.vue'
import CandidateOfferPanel from '../../components/candidate/CandidateOfferPanel.vue'
import CandidateOnboardingPanel from '../../components/candidate/CandidateOnboardingPanel.vue'
import ReasonTagPicker from '../../components/reason-library/ReasonTagPicker.vue'
import { getActiveRule } from '../../api/reason-library'
import type { SceneRule } from '../../types/reason-library'
import { listBackgroundCheckOrders, uploadMedia } from '../../api/integration'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const { t } = useI18n()

// 2026-10-21：默认落「原始简历」首签
const activeTab = ref('resume-raw')

/**
 * 中文标签映射：snake_case fieldKey → i18n key（s102–s157 现有译文）。
 * 权威来源为「标准简历设置」的动态字段（fieldKey 已由迁移 0023 归一为 snake_case，
 * 但组件曾用英文显示标签作键 → 查不到 → 页面直接裸显 about_me 等英文键）。
 * 此表不依赖 listFields 权限（HR 无 recruit:settings:dynamic_fields:list 也可用）。
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
    /** 职位编号（截图「J06279」位） */
    positionCode?: string | null
    /** 所属流程名 */
    processName?: string | null
    /** 流程编号（截图「HC09481」位，code 是流程线号，多版本共用同一 code） */
    processCode?: string | null
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
// 原始简历在线预览：pdf 与图片可内嵌 iframe；doc/docx 浏览器不支持，引导下载
const resumePreviewable = computed(() => /\.(pdf|png|jpe?g|gif|webp|bmp)([?#]|$)/i.test(resumeFileUrl.value ?? ''))

// 2026-10-21 兵哥：预览失败修复 —— 后端对 media 响应下发 X-Frame-Options: DENY，
// dev 下页面在 5212、Vite 代理把 /media 转发到 8000，iframe 直连 src 会被浏览器
// 判定跨源禁嵌 → 显示「预览失败」。改为经鉴权 fetch 取为 blob，再以同源 objectURL
// 内嵌 iframe：① 绕过 X-Frame-Options；② 自动携带 Authorization（secure 下载端点亦可用）。
const resumeObjectUrl = ref('')
const resumePreviewError = ref(false)

function buildAbsoluteMediaUrl(rel: string): string {
  if (/^https?:\/\//i.test(rel)) return rel
  const base = window.location.origin
  return rel.startsWith('/') ? `${base}${rel}` : `${base}/${rel}`
}

async function loadResumePreview() {
  if (resumeObjectUrl.value) {
    URL.revokeObjectURL(resumeObjectUrl.value)
    resumeObjectUrl.value = ''
  }
  resumePreviewError.value = false
  const url = resumeFileUrl.value
  if (!url || !resumePreviewable.value) return
  try {
    const token = localStorage.getItem('accessToken') || localStorage.getItem('token')
    const resp = await fetch(buildAbsoluteMediaUrl(url), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const blob = await resp.blob()
    resumeObjectUrl.value = URL.createObjectURL(blob)
  } catch (e) {
    resumePreviewError.value = true
  }
}

watch(resumeFileUrl, () => { loadResumePreview() }, { immediate: true })
onBeforeUnmount(() => {
  if (resumeObjectUrl.value) URL.revokeObjectURL(resumeObjectUrl.value)
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', onPanelKeydown)
  }
})

/** 应聘记录浮层面板：ESC 关闭（2026-10-21） */
function onPanelKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') applicationPanelVisible.value = false
}
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', onPanelKeydown)
}

// ===== 操作记录渲染（字段级 diff / 阶段·状态流转 / 解析溯源 / 哈希链校验） =====
// 操作类型 → i18n key（s235–s244）；命中不到则回退原始 action 串，避免空白
const ACTION_LABEL_KEY: Record<string, string> = {
  CREATED: 's235', INFO_UPDATED: 's236', RESUME_FIELDS_UPDATED: 's237',
  RESUME_UPLOADED: 's238', RESUME_PARSED: 's239', STAGE_CHANGED: 's240',
  STATE_CHANGED: 's241', BLACKLIST_CHANGED: 's242', BLACKLISTED: 's243',
  UNBLACKLISTED: 's244',
  // 2026-10-19 新增：关注 / 转发。未登记会裸显英文枚举，操作记录不可读。
  FOLLOWED: 's292', UNFOLLOWED: 's293', FORWARDED: 's299',
  REASON_TAGGED: 's316',
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
  UNBLACKLISTED: 'default', FOLLOWED: 'success', UNFOLLOWED: 'default',
  FORWARDED: 'info',
  REASON_TAGGED: 'info',
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
  } else if (action === 'REASON_TAGGED') {
    // 原因库归因（2026-10-19）：detail.scene + 标签数量 + 备注
    const n = Array.isArray(d.tags) ? d.tags.length : 0
    if (d.scene) lines.push(t('pages.candidate.CandidateDetail.s317', { scene: d.scene, n }))
    if (d.note) lines.push(d.note)
  } else if (action === 'RESUME_PARSED') {
    const p = d.parse || {}
    if (p.provider) lines.push(t('pages.candidate.CandidateDetail.s231', { provider: p.provider }))
    if (p.confidence != null) lines.push(t('pages.candidate.CandidateDetail.s232', { confidence: p.confidence }))
    if (p.educations != null) lines.push(t('pages.candidate.CandidateDetail.s233', { n: p.educations }))
    if (p.experiences != null) lines.push(t('pages.candidate.CandidateDetail.s234', { n: p.experiences }))
    if (p.channel) lines.push(`${t('pages.candidate.CandidateDetail.s253')}：${p.channel}`)
  } else if (action === 'FOLLOWED' || action === 'UNFOLLOWED') {
    // 关注是个人级行为，记录里带关注人，便于回看是谁关注的
    const who = d.user?.name || fmtVal(d.user?.id)
    lines.push(`${fmtVal(who)}`)
  } else if (action === 'FORWARDED') {
    const to = d.to?.name || fmtVal(d.to?.id)
    if (to) lines.push(t('pages.candidate.CandidateDetail.s310', { name: to }))
    if (d.note) lines.push(fmtVal(d.note, 120))
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

/**
 * 应聘记录（= 后端 Application 列表，候选人每次应聘一条）
 * 2026-10-21 兵哥需求：「申请」= 候选人的每次应聘，在详情页展示多次投递、每次对应不同职位。
 * 后端 applications 已按 -created_at 排序（最新在前），此处保持原序不再二次排序。
 */
const applicationRecords = computed(() => applications.value ?? [])

/** 浮层面板开关：点击身份条的应聘职位标签开合 */
const applicationPanelVisible = ref(false)

function toggleApplicationPanel() {
  if (!applicationRecords.value.length) return
  applicationPanelVisible.value = !applicationPanelVisible.value
}

/** 面板标题：「此候选人已投递 N 次」（N=1 时也用同一措辞保持稳定） */
const applicationPanelTitle = computed<string>(() => {
  const n = applicationRecords.value.length
  return t('pages.candidate.CandidateDetail.applicationPanelTitle', { count: n })
})

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
  if (id) await loadFollowState(id)
})

// 上一位/下一位切换（同组件仅路由参数变化，onMounted 不重跑，须 watch 重载）
watch(() => route.params.id, async (newId, oldId) => {
  if (!newId || newId === oldId) return
  await loadCandidateData(String(newId))
  const idx = navIds.value.indexOf(String(newId))
  if (idx >= 0) navIndex.value = idx
  else await loadNavContext()
  await loadFollowState(String(newId))
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

// 2026-10-21 修复假上传：原实现只弹成功提示，未调任何 API。
// 真实链路：POST /media/upload/（multipart）→ PATCH candidates/{id} resume_file_url → 刷新详情。
// 审计：resume_file_url 在 RESUME_FILE_FIELDS 内，后端自动记 RESUME_UPLOADED。
const uploadingResume = ref(false)
const handleUploadResume = async () => {
  const raw = fileList.value[0]?.file
  const file = raw instanceof File ? raw : (raw as any)?.file
  if (!file) { message.warning(t('pages.candidate.CandidateDetail.s180')); return }
  const id = route.params.id
  if (!id) return
  uploadingResume.value = true
  try {
    const up = await uploadMedia(file)
    await updateCandidate(String(id), { resume_file_url: up.url })
    message.success(t('pages.candidate.CandidateDetail.s181'))
    uploadResumeModalVisible.value = false
    fileList.value = []
    // 刷新详情，原始简历页签立即可预览
    await loadCandidateData(String(id))
  } catch (e) {
    message.error(t('pages.candidate.CandidateDetail.s179'))
  } finally {
    uploadingResume.value = false
  }
}

const handleSaveNote = () => {
  // 备注后端端点尚未接入：明确提示，不伪造保存成功
  message.info(t('pages.candidate.CandidateDetail.s200'))
}

const handleSendNotification = () => {
  message.success(t('pages.candidate.CandidateDetail.s182'))
  notificationModalVisible.value = false
}

// ============================================================
// 简历操作：淘汰 / 放入人才库 / 推荐其他职位 / 关注 / 转发
// （2026-10-19 新增）
//
// 状态口径：state_display 由后端 current_state 推导，已淘汰(PROCESS_FAILED)/
// 已入库(TALENT_POOL) 时对应按钮转为禁用态，避免对同一状态重复操作。
// ============================================================
const candidateState = computed(() => (pickDetail('current_state') || '').trim())
const isEliminated = computed(() => candidateState.value === 'PROCESS_FAILED')
const isInPool = computed(() => candidateState.value === 'TALENT_POOL')

/** 后端错误码 → 用户可读文案（当前主要是权限类） */
function translateApiError(e: any, fallbackKey: string): string {
  const code = String(e?.code || e?.response?.data?.error || '')
  if (code === 'FORBIDDEN_SCOPE') {
    return t('pages.candidate.CandidateDetail.s306')
  }
  return e?.response?.data?.message || e?.message || t(`pages.candidate.CandidateDetail.${fallbackKey}`)
}

// ---------- 关注（个人级，幂等） ----------
const isFollowed = ref(false)
const followLoading = ref(false)

async function loadFollowState(id: string) {
  try {
    isFollowed.value = await getCandidateFollowState(id)
  } catch {
    // 关注态拉取失败不阻塞详情页（无权限/网络问题），按钮按未关注渲染
    isFollowed.value = false
  }
}

async function toggleFollow() {
  const id = route.params.id
  if (!id || followLoading.value) return
  followLoading.value = true
  const was = isFollowed.value
  // 乐观更新：关注属可逆操作（对应 R-106「可逆 → 直接执行」），失败再回滚
  isFollowed.value = !was
  try {
    if (was) {
      await unfollowCandidate(String(id))
      message.success(t('pages.candidate.CandidateDetail.s293'))
    } else {
      await followCandidate(String(id))
      message.success(t('pages.candidate.CandidateDetail.s292'))
    }
  } catch (e: any) {
    isFollowed.value = was
    message.error(translateApiError(e, 's281'))
  } finally {
    followLoading.value = false
  }
}

// ---------- 淘汰（不可逆 → 确认框 + 原因必填） ----------
const eliminateModalVisible = ref(false)
const eliminateReason = ref('')
const eliminateLoading = ref(false)
// 原因库场景规则（2026-10-19）：命中「淘汰」规则时弹窗内嵌原因标签选择
const eliminateRule = ref<SceneRule | null>(null)
const eliminateTagIds = ref<string[]>([])
const eliminateOtherReasons = ref<Array<{ catId: string; category: string; text: string }>>([])

/** 拉取场景生效规则；失败/无规则均返回 null，弹窗退化为纯备注，不阻塞业务 */
async function loadReasonRule(scene: '淘汰' | '放入人才库'): Promise<SceneRule | null> {
  try {
    return await getActiveRule(scene, pickDetail('recruit_type') || undefined)
  } catch {
    return null
  }
}

function openEliminateModal() {
  eliminateReason.value = ''
  eliminateTagIds.value = []
  eliminateOtherReasons.value = []
  eliminateRule.value = null
  eliminateModalVisible.value = true
  void loadReasonRule('淘汰').then((r) => {
    eliminateRule.value = r
  })
}

async function handleEliminate() {
  const id = route.params.id
  if (!id || eliminateLoading.value) return
  if (!eliminateReason.value.trim()) {
    message.warning(t('pages.candidate.CandidateDetail.s278'))
    return
  }
  eliminateLoading.value = true
  try {
    await transitionCandidate(String(id), 'mark_process_failed', {
      reason: eliminateReason.value.trim(),
      // 原因库归因（2026-10-19）：随主接口提交所选标签，后端按场景规则落归因记录
      ...(eliminateTagIds.value.length
        ? { reason_tag_ids: eliminateTagIds.value }
        : {}),
      // 自定义「其他」原因（末级分类 allowCustom 自由输入），随归因记录落库
      ...(eliminateOtherReasons.value.length
        ? { reason_custom_reasons: eliminateOtherReasons.value }
        : {}),
    })
    message.success(t('pages.candidate.CandidateDetail.s280'))
    eliminateModalVisible.value = false
    await loadCandidateData(String(id))
  } catch (e: any) {
    message.error(translateApiError(e, 's281'))
  } finally {
    eliminateLoading.value = false
  }
}

// ---------- 放入人才库 ----------
const poolModalVisible = ref(false)
const poolReason = ref('')
const poolLoading = ref(false)
// 原因库场景规则（2026-10-19）：命中「放入人才库」规则时弹窗内嵌原因标签选择
const poolRule = ref<SceneRule | null>(null)
const poolTagIds = ref<string[]>([])
const poolOtherReasons = ref<Array<{ catId: string; category: string; text: string }>>([])

function openPoolModal() {
  poolReason.value = ''
  poolTagIds.value = []
  poolOtherReasons.value = []
  poolRule.value = null
  poolModalVisible.value = true
  void loadReasonRule('放入人才库').then((r) => {
    poolRule.value = r
  })
}

async function handleMoveToPool() {
  const id = route.params.id
  if (!id || poolLoading.value) return
  poolLoading.value = true
  try {
    await transitionCandidate(String(id), 'move_to_talent_pool', {
      reason: poolReason.value.trim(),
      entry_source: 'MANUAL',
      // 原因库归因（2026-10-19）：随主接口提交所选标签，后端按场景规则落归因记录
      ...(poolTagIds.value.length ? { reason_tag_ids: poolTagIds.value } : {}),
      // 自定义「其他」原因（末级分类 allowCustom 自由输入），随归因记录落库
      ...(poolOtherReasons.value.length
        ? { reason_custom_reasons: poolOtherReasons.value }
        : {}),
    })
    message.success(t('pages.candidate.CandidateDetail.s284'))
    poolModalVisible.value = false
    await loadCandidateData(String(id))
  } catch (e: any) {
    message.error(translateApiError(e, 's281'))
  } finally {
    poolLoading.value = false
  }
}

// ---------- 推荐其他职位 ----------
const recommendModalVisible = ref(false)
const recommendPositionId = ref<string | null>(null)
const recommendComment = ref('')
const recommendLoading = ref(false)
const positionOptions = ref<Array<{ label: string; value: string }>>([])
const loadingPositions = ref(false)

async function loadPositionOptions() {
  loadingPositions.value = true
  try {
    const rows = await listPositions()
    positionOptions.value = rows.map((p) => ({ label: p.title, value: p.id }))
  } catch {
    positionOptions.value = []
  } finally {
    loadingPositions.value = false
  }
}

function openRecommendModal() {
  recommendPositionId.value = null
  recommendComment.value = ''
  recommendModalVisible.value = true
  // 首次打开才拉职位列表，避免拖慢详情页首屏
  if (positionOptions.value.length === 0) loadPositionOptions()
}

async function handleRecommend() {
  const id = route.params.id
  if (!id || recommendLoading.value) return
  if (!recommendPositionId.value) {
    message.warning(t('pages.candidate.CandidateDetail.s288'))
    return
  }
  recommendLoading.value = true
  try {
    await recommendCandidateToPosition(String(id), recommendPositionId.value, recommendComment.value.trim())
    const name = positionOptions.value.find((o) => o.value === recommendPositionId.value)?.label
    message.success(t('pages.candidate.CandidateDetail.s309', { name: name || '—' }))
    recommendModalVisible.value = false
  } catch (e: any) {
    message.error(translateApiError(e, 's290'))
  } finally {
    recommendLoading.value = false
  }
}

// ---------- 转发给内部同事 ----------
const forwardModalVisible = ref(false)
const forwardTargets = ref<string[]>([])
const forwardNote = ref('')
const forwardLoading = ref(false)
const forwardRecords = ref<ForwardRow[]>([])
const colleagueOptions = ref<Array<{ label: string; value: string }>>([])
const loadingColleagues = ref(false)

/** 当前用户（用于从「可选同事」中排除自己，呼应后端 FORBIDDEN_SELF 规则） */
const currentUserId = computed(() => {
  const raw = localStorage.getItem('user') || localStorage.getItem('userInfo')
  if (!raw) return ''
  try {
    const u = JSON.parse(raw)
    return String(u?.id ?? '')
  } catch {
    return ''
  }
})

async function loadColleagueOptions() {
  loadingColleagues.value = true
  try {
    const users = await listUsers()
    const me = currentUserId.value
    colleagueOptions.value = users
      .map((u: User) => {
        const label = u.realName || u.username || u.email || u.id
        return { label: String(label), value: String(u.id) }
      })
      .filter((o) => o.value !== me)
  } catch {
    colleagueOptions.value = []
  } finally {
    loadingColleagues.value = false
  }
}

async function loadForwardRecords(id: string) {
  try {
    forwardRecords.value = await listCandidateForwards(id)
  } catch {
    forwardRecords.value = []
  }
}

async function openForwardModal() {
  const id = route.params.id
  forwardTargets.value = []
  forwardNote.value = ''
  forwardModalVisible.value = true
  await Promise.all([
    colleagueOptions.value.length ? Promise.resolve() : loadColleagueOptions(),
    id ? loadForwardRecords(String(id)) : Promise.resolve(),
  ])
}

async function handleForward() {
  const id = route.params.id
  if (!id || forwardLoading.value) return
  if (forwardTargets.value.length === 0) {
    message.warning(t('pages.candidate.CandidateDetail.s296'))
    return
  }
  forwardLoading.value = true
  try {
    const res: any = await forwardCandidate(String(id), forwardTargets.value, forwardNote.value.trim())
    const results: any[] = res?.results ?? []
    const ok = results.filter((r) => r.success).length
    const failed = results.length - ok
    if (ok > 0 && failed === 0) {
      message.success(t('pages.candidate.CandidateDetail.s299'))
      forwardModalVisible.value = false
    } else if (ok > 0) {
      // 部分成功：如实告知，不静默吞掉失败的人
      message.warning(t('pages.candidate.CandidateDetail.s308'))
      forwardTargets.value = forwardTargets.value.filter(
        (v) => results.find((r) => String(r.toUserId) === String(v) && r.success !== true),
      )
    } else {
      const code = results[0]?.error
      message.error(
        code === 'FORBIDDEN_SELF'
          ? t('pages.candidate.CandidateDetail.s307')
          : translateApiError({ code }, 's300'),
      )
    }
    if (ok > 0) await loadForwardRecords(String(id))
  } catch (e: any) {
    message.error(translateApiError(e, 's300'))
  } finally {
    forwardLoading.value = false
  }
}
</script>

<style scoped>
.candidate-detail-page { padding: var(--space-6); background: var(--c-info-soft); min-height: 100vh; position: relative; }
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

/* ===== 应聘记录浮层面板（2026-10-21 兵哥需求：申请=每次应聘记录） ===== */
/* 标签可点击态：多次投递才显示次数徽标 + 展开箭头（单次投递保持原静态标签观感） */
.position-tag--clickable { cursor: pointer; }
.position-tag--clickable:hover { background: var(--brand-tint); }
.position-tag--multi { max-width: 420px; }
.position-tag__count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 18px; padding: 0 5px; margin-right: 6px;
  background: var(--brand); color: var(--brand-fg-on-soft); border-radius: 9999px;
  font-size: var(--fs-10); font-weight: 700; line-height: 1;
}
.position-tag__text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.position-tag__caret { margin-left: 4px; flex-shrink: 0; transition: transform var(--dur-fast) var(--ease-out); }
.position-tag--clickable .position-tag__caret { transform: rotate(90deg); }

/* 面板本体：锚定在身份条下方（absolute 挂在 identity-card 之后） */
.application-panel {
  position: absolute; left: var(--page-pad-x); right: var(--page-pad-x);
  top: 96px; z-index: var(--z-dropdown);
  background: var(--glass-bg-elevated); backdrop-filter: var(--glass-blur-panel);
  border: 1px solid var(--glass-border); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated); padding: var(--space-4);
}
.application-panel__head {
  font-size: var(--fs-14); font-weight: 600; color: var(--ink);
  padding-bottom: var(--space-3); margin-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-hairline);
}
.application-panel__body { display: flex; flex-direction: column; gap: var(--space-3); }
.application-record {
  background: var(--surface); border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md); padding: var(--space-3) var(--space-4);
}
.application-record__top { display: flex; align-items: baseline; gap: var(--space-2); flex-wrap: wrap; }
.application-record__position { font-size: var(--fs-14); font-weight: 600; color: var(--ink); }
.application-record__codes { font-size: var(--fs-12); color: var(--ink-soft); font-family: ui-monospace, monospace; }
.application-record__time { margin-left: auto; font-size: var(--fs-12); color: var(--ink-faint); }
.application-record__sub { font-size: var(--fs-12); color: var(--ink-soft); margin-top: var(--space-1); }
.application-record__stage { font-size: var(--fs-12); color: var(--ink-soft); margin-top: var(--space-1); }
.application-record__state { font-size: var(--fs-12); color: var(--brand-fg); margin-top: var(--space-1); }

/* 透明遮罩：仅捕获点击关闭，不遮挡视觉 */
.application-panel__mask { position: fixed; inset: 0; z-index: calc(var(--z-dropdown) - 1); }
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

/* ===== 原始简历（在线预览） ===== */
.raw-resume-section { display: flex; flex-direction: column; gap: var(--space-3); }
.raw-resume-actions { display: flex; gap: var(--space-2); }
.raw-resume-frame {
  width: 100%;
  height: 72vh;
  border: 1px solid var(--border-hairline);
  border-radius: 12px;
  background: var(--surface);
}
.raw-resume-fallback {
  display: flex;
  justify-content: center;
  padding: var(--space-6) 0;
}

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
  background: var(color-mix(in srgb, var(--ink) 2%, transparent));
  border: 1px solid var(--border-hairline);
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
.diff-row + .diff-row { border-top: 1px dashed var(--border-hairline); }
.diff-label { color: var(--ink-soft); white-space: nowrap; }
.diff-label::after { content: '：'; }
.diff-old {
  color: var(--ink-faint, var(--ink-soft));
  text-decoration: line-through;
  text-decoration-color: color-mix(in srgb, var(--c-error) 45%, transparent);
  word-break: break-all;
}
.diff-arrow { color: var(--brand); text-align: center; }
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

/* 操作卡片：一行两个按钮（2026-10-19 合并原「简历操作」） */
.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}

.action-grid :deep(.n-button) {
  width: 100%;
}.application-item { padding: var(--space-2) var(--space-3); background: var(--brand-soft); border-radius: 8px; }
.application-position { font-size: var(--fs-14); font-weight: 600; color: var(--brand-fg); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.application-meta { display: flex; gap: var(--space-3); font-size: var(--fs-12); color: var(--ink-soft); margin-top: 2px; }
.upload-tip { margin-top: var(--space-4); color: var(--ink-faint); font-size: var(--fs-12); }

/* ===== 转发记录（转发弹窗内） ===== */
.forward-records { margin-top: var(--space-4); padding-top: var(--space-3); border-top: 1px solid var(--border-hairline); }
.forward-records-title { font-size: var(--fs-12); font-weight: 600; color: var(--ink-soft); margin-bottom: var(--space-2); }
.forward-record { display: flex; gap: var(--space-2); align-items: baseline; padding: 3px 0; font-size: var(--fs-12); flex-wrap: wrap; }
.forward-record-text { color: var(--ink); }
.forward-record-note { color: var(--ink-soft); overflow-wrap: anywhere; }

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
