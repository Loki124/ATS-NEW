<template>
  <div class="page-container">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" class="page-tabs" @update:value="onTabChange">
        <n-tab-pane name="roster" tab="花名册" />
        <n-tab-pane name="goal" tab="目标" />
        <n-tab-pane name="metric" tab="数据" />
        <n-tab-pane name="assessment" tab="考核" />
      </n-tabs>

      <!-- 写入失败三段式（R-203）：① 人话描述发生了什么 ② 你的数据是否安全 ③ 技术详情（折叠 + 一键复制） -->
      <div v-if="writeError" class="error-state" role="alert">
        <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
        <div class="error-state-body">
          <div class="error-state-title">{{ writeError.title }}</div>
          <div class="error-state-desc">{{ writeError.safe }}</div>
          <details class="error-state-detail">
            <summary>查看详情</summary>
            <pre class="error-state-code">{{ writeError.detail }}</pre>
            <n-button size="tiny" quaternary @click="copyText(writeError.detail)">复制错误信息</n-button>
          </details>
        </div>
        <n-button v-if="writeError.retry" size="small" type="primary" ghost @click="runWriteRetry">
          {{ writeError.retryLabel }}
        </n-button>
      </div>

      <!-- ① 花名册 -->
      <template v-if="activeTab === 'roster'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">定岗</span>
            <n-input
              v-model:value="rosterSearch"
              aria-label="姓名或定岗部门"
              class="toolbar-search"
              placeholder="搜索姓名或定岗部门"
              clearable
              @keyup.enter="loadRecords"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
          </div>
          <div class="spacer"></div>
          <n-button :loading="recordLoading" @click="loadRecords">查询名单</n-button>
          <n-button type="primary" @click="openRecordCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增定岗
          </n-button>
        </div>

        <div v-if="recordError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">定岗花名册没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，你填的定岗信息仍保留在本页，不会丢失。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ recordError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(recordError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="recordLoading" @click="loadRecords">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="recordLoading && !recordRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="rosterColumns"
            :data="recordRows"
            :loading="recordLoading"
            :bordered="false"
            :scroll-x="ROSTER_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PlacementRecord) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="rosterEmptyText" size="small">
                <template #extra>
                  <n-button v-if="rosterSearch" size="small" @click="rosterSearch = ''; loadRecords()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ② 目标 -->
      <template v-if="activeTab === 'goal'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">定岗记录</span>
            <n-select
              v-model:value="goalRecord"
              aria-label="定岗记录"
              class="toolbar-select-wide"
              :options="recordOptions"
              placeholder="全部定岗记录"
              clearable
              @update:value="loadGoals"
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="goalLoading" @click="loadGoals">刷新目标</n-button>
          <n-button type="primary" :disabled="!goalRecord" @click="openGoalCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增目标
          </n-button>
        </div>

        <div v-if="goalError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">定岗目标没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，已维护的目标仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ goalError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(goalError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="goalLoading" @click="loadGoals">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="goalLoading && !goalRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="goalColumns"
            :data="goalRows"
            :loading="goalLoading"
            :bordered="false"
            :scroll-x="GOAL_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PlacementGoal) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="goalEmptyText" size="small">
                <template #extra>
                  <n-button v-if="goalRecord" size="small" @click="goalRecord = null; loadGoals()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ③ 数据 -->
      <template v-if="activeTab === 'metric'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">定岗记录</span>
            <n-select
              v-model:value="metricRecord"
              aria-label="定岗记录"
              class="toolbar-select-wide"
              :options="recordOptions"
              placeholder="全部定岗记录"
              clearable
              @update:value="loadMetrics"
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="metricLoading" @click="loadMetrics">刷新数据</n-button>
          <n-button type="primary" :disabled="!metricRecord" @click="openMetricCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增数据
          </n-button>
        </div>

        <div v-if="metricError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">定岗数据没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，已填报的数据仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ metricError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(metricError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="metricLoading" @click="loadMetrics">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="metricLoading && !metricRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="metricColumns"
            :data="metricRows"
            :loading="metricLoading"
            :bordered="false"
            :scroll-x="METRIC_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PlacementMetric) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="metricEmptyText" size="small">
                <template #extra>
                  <n-button v-if="metricRecord" size="small" @click="metricRecord = null; loadMetrics()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ④ 考核 -->
      <template v-if="activeTab === 'assessment'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">定岗记录</span>
            <n-select
              v-model:value="assessmentRecord"
              aria-label="定岗记录"
              class="toolbar-select-wide"
              :options="recordOptions"
              placeholder="全部定岗记录"
              clearable
              @update:value="loadAssessments"
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="assessmentLoading" @click="loadAssessments">刷新考核</n-button>
          <n-button type="primary" :disabled="!assessmentRecord" @click="openAssessmentCreate">
            <template #icon><n-icon :component="AddOutline" /></template>
            新增考核
          </n-button>
        </div>

        <div v-if="assessmentError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">定岗考核没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，已录入的考核仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ assessmentError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(assessmentError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="assessmentLoading" @click="loadAssessments">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="assessmentLoading && !assessmentRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="assessmentColumns"
            :data="assessmentRows"
            :loading="assessmentLoading"
            :bordered="false"
            :scroll-x="ASSESSMENT_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PlacementAssessment) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="assessmentEmptyText" size="small">
                <template #extra>
                  <n-button v-if="assessmentRecord" size="small" @click="assessmentRecord = null; loadAssessments()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- 定岗记录 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="recordFormVisible"
        preset="card"
        :title="recordEditing ? '编辑定岗记录' : '新增定岗记录'"
        :style="{ width: '720px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(560px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="recordForm" label-placement="top">
          <!-- 写入失败三段式（R-203）：弹窗内就地展示，不甩给全局 toast -->
          <div v-if="recordWriteError" class="error-state" role="alert">
            <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
            <div class="error-state-body">
              <div class="error-state-title">{{ recordWriteError.title }}</div>
              <div class="error-state-desc">{{ recordWriteError.safe }}</div>
              <details class="error-state-detail">
                <summary>查看详情</summary>
                <pre class="error-state-code">{{ recordWriteError.detail }}</pre>
                <n-button size="tiny" quaternary @click="copyText(recordWriteError.detail)">复制错误信息</n-button>
              </details>
            </div>
            <n-button v-if="recordWriteError.retry" size="small" type="primary" ghost @click="runRecordRetry">
              {{ recordWriteError.retryLabel }}
            </n-button>
          </div>
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item
                label="校招生"
                required
                :validation-status="recordErrors.person ? 'error' : undefined"
                :show-feedback="!!recordErrors.person"
              >
                <n-select
                  v-model:value="recordForm.person"
                  :options="personOptions"
                  placeholder="搜索并选择校招生"
                  clearable
                  filterable
                  remote
                  :loading="personLoading"
                  :on-search="onPersonSearch"
                  data-error-field="record-person"
                />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ recordErrors.person }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="定岗部门"
                required
                :validation-status="recordErrors.dept ? 'error' : undefined"
                :show-feedback="!!recordErrors.dept"
              >
                <n-input v-model:value="recordForm.dept" placeholder="请输入定岗部门" data-error-field="record-dept" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ recordErrors.dept }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="岗位名称"
                required
                :validation-status="recordErrors.positionName ? 'error' : undefined"
                :show-feedback="!!recordErrors.positionName"
              >
                <n-input
                  v-model:value="recordForm.positionName"
                  placeholder="请输入岗位名称"
                  data-error-field="record-position"
                />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ recordErrors.positionName }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="定岗日期"
                required
                :validation-status="recordErrors.placeDate ? 'error' : undefined"
                :show-feedback="!!recordErrors.placeDate"
              >
                <n-date-picker
                  v-model:value="recordForm.placeDateTs"
                  type="date"
                  style="width: 100%"
                  data-error-field="record-place-date"
                />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ recordErrors.placeDate }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="跟踪年数">
                <n-input-number v-model:value="recordForm.trackYears" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="跟踪状态" required>
                <n-select v-model:value="recordForm.status" :options="recordStatusOptions" placeholder="请选择跟踪状态" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="最近绩效">
                <n-input v-model:value="recordForm.latestPerf" placeholder="如 A / 优" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="closeRecordForm">取消办理</n-button>
            <n-button type="primary" :loading="recordSaving" :disabled="recordSaving" @click="saveRecord">保存定岗</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 目标 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="goalFormVisible"
        preset="card"
        :title="goalEditing ? '编辑定岗目标' : '新增定岗目标'"
        :style="{ width: '680px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(520px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="goalForm" label-placement="top">
          <div v-if="goalWriteError" class="error-state" role="alert">
            <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
            <div class="error-state-body">
              <div class="error-state-title">{{ goalWriteError.title }}</div>
              <div class="error-state-desc">{{ goalWriteError.safe }}</div>
              <details class="error-state-detail">
                <summary>查看详情</summary>
                <pre class="error-state-code">{{ goalWriteError.detail }}</pre>
                <n-button size="tiny" quaternary @click="copyText(goalWriteError.detail)">复制错误信息</n-button>
              </details>
            </div>
            <n-button v-if="goalWriteError.retry" size="small" type="primary" ghost @click="runGoalRetry">
              {{ goalWriteError.retryLabel }}
            </n-button>
          </div>
          <!-- 表单级前置条件（所选定岗记录已失效）→ 就近提示在表单顶部 -->
          <div v-if="goalErrors.record" class="field-error" role="alert">
            <n-icon :component="AlertCircleOutline" aria-hidden="true" />
            {{ goalErrors.record }}
          </div>
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item
                label="目标名称"
                required
                :validation-status="goalErrors.name ? 'error' : undefined"
                :show-feedback="!!goalErrors.name"
              >
                <n-input v-model:value="goalForm.name" placeholder="请输入目标名称" data-error-field="goal-name" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ goalErrors.name }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="衡量指标"
                required
                :validation-status="goalErrors.metric ? 'error' : undefined"
                :show-feedback="!!goalErrors.metric"
              >
                <n-input v-model:value="goalForm.metric" placeholder="如 出勤率" data-error-field="goal-metric" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ goalErrors.metric }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="目标值"
                required
                :validation-status="goalErrors.targetValue ? 'error' : undefined"
                :show-feedback="!!goalErrors.targetValue"
              >
                <n-input v-model:value="goalForm.targetValue" placeholder="如 ≥ 95%" data-error-field="goal-target" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ goalErrors.targetValue }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="权重（%）" required>
                <n-input-number v-model:value="goalForm.weight" :min="0" :max="100" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="截止日期">
                <n-date-picker v-model:value="goalForm.dueDateTs" type="date" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="目标状态" required>
                <n-select v-model:value="goalForm.status" :options="goalStatusOptions" placeholder="请选择目标状态" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="closeGoalForm">取消编辑</n-button>
            <n-button type="primary" :loading="goalSaving" :disabled="goalSaving" @click="saveGoal">保存目标</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 数据 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="metricFormVisible"
        preset="card"
        :title="metricEditing ? '编辑定岗数据' : '新增定岗数据'"
        :style="{ width: '680px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(480px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="metricForm" label-placement="top">
          <div v-if="metricWriteError" class="error-state" role="alert">
            <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
            <div class="error-state-body">
              <div class="error-state-title">{{ metricWriteError.title }}</div>
              <div class="error-state-desc">{{ metricWriteError.safe }}</div>
              <details class="error-state-detail">
                <summary>查看详情</summary>
                <pre class="error-state-code">{{ metricWriteError.detail }}</pre>
                <n-button size="tiny" quaternary @click="copyText(metricWriteError.detail)">复制错误信息</n-button>
              </details>
            </div>
            <n-button v-if="metricWriteError.retry" size="small" type="primary" ghost @click="runMetricRetry">
              {{ metricWriteError.retryLabel }}
            </n-button>
          </div>
          <div v-if="metricErrors.record" class="field-error" role="alert">
            <n-icon :component="AlertCircleOutline" aria-hidden="true" />
            {{ metricErrors.record }}
          </div>
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item
                label="月份"
                required
                :validation-status="metricErrors.ym ? 'error' : undefined"
                :show-feedback="!!metricErrors.ym"
              >
                <n-input v-model:value="metricForm.ym" placeholder="如 2026-09" data-error-field="metric-ym" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ metricErrors.ym }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="指标"
                required
                :validation-status="metricErrors.metric ? 'error' : undefined"
                :show-feedback="!!metricErrors.metric"
              >
                <n-input v-model:value="metricForm.metric" placeholder="请输入指标名称" data-error-field="metric-metric" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ metricErrors.metric }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="完成值"
                required
                :validation-status="metricErrors.actualValue ? 'error' : undefined"
                :show-feedback="!!metricErrors.actualValue"
              >
                <n-input
                  v-model:value="metricForm.actualValue"
                  placeholder="如 96%"
                  data-error-field="metric-actual"
                />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ metricErrors.actualValue }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="备注">
                <n-input v-model:value="metricForm.remark" placeholder="补充说明" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="closeMetricForm">取消调整</n-button>
            <n-button type="primary" :loading="metricSaving" :disabled="metricSaving" @click="saveMetric">保存数据</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 考核 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="assessmentFormVisible"
        preset="card"
        :title="assessmentEditing ? '编辑定岗考核' : '新增定岗考核'"
        :style="{ width: '680px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(480px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="assessmentForm" label-placement="top">
          <div v-if="assessmentWriteError" class="error-state" role="alert">
            <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
            <div class="error-state-body">
              <div class="error-state-title">{{ assessmentWriteError.title }}</div>
              <div class="error-state-desc">{{ assessmentWriteError.safe }}</div>
              <details class="error-state-detail">
                <summary>查看详情</summary>
                <pre class="error-state-code">{{ assessmentWriteError.detail }}</pre>
                <n-button size="tiny" quaternary @click="copyText(assessmentWriteError.detail)">复制错误信息</n-button>
              </details>
            </div>
            <n-button v-if="assessmentWriteError.retry" size="small" type="primary" ghost @click="runAssessmentRetry">
              {{ assessmentWriteError.retryLabel }}
            </n-button>
          </div>
          <div v-if="assessmentErrors.record" class="field-error" role="alert">
            <n-icon :component="AlertCircleOutline" aria-hidden="true" />
            {{ assessmentErrors.record }}
          </div>
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item
                label="考核周期"
                required
                :validation-status="assessmentErrors.period ? 'error' : undefined"
                :show-feedback="!!assessmentErrors.period"
              >
                <n-input v-model:value="assessmentForm.period" placeholder="如 2026 年第三季度" data-error-field="assessment-period" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ assessmentErrors.period }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="考核得分" required>
                <n-input-number v-model:value="assessmentForm.score" :min="0" style="width: 100%" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="绩效等级"
                required
                :validation-status="assessmentErrors.perfLevel ? 'error' : undefined"
                :show-feedback="!!assessmentErrors.perfLevel"
              >
                <n-input v-model:value="assessmentForm.perfLevel" placeholder="如 A / B" data-error-field="assessment-level" />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ assessmentErrors.perfLevel }}
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="评定日期"
                required
                :validation-status="assessmentErrors.assessedAt ? 'error' : undefined"
                :show-feedback="!!assessmentErrors.assessedAt"
              >
                <n-date-picker
                  v-model:value="assessmentForm.assessedAtTs"
                  type="date"
                  style="width: 100%"
                  data-error-field="assessment-date"
                />
                <template #feedback>
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ assessmentErrors.assessedAt }}
                </template>
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-form-item label="评语">
            <n-input v-model:value="assessmentForm.comment" type="textarea" placeholder="考核评语" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="closeAssessmentForm">取消评定</n-button>
            <n-button type="primary" :loading="assessmentSaving" :disabled="assessmentSaving" @click="saveAssessment">保存考核</n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, type Ref } from 'vue'
import {
  NButton,
  NDataTable,
  NDatePicker,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSkeleton,
  NSpace,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  useNotification,
} from 'naive-ui'
import { AddOutline, AlertCircleOutline, CreateOutline, SearchOutline, TrashOutline } from '@vicons/ionicons5'
import {
  createPlacementAssessment,
  createPlacementGoal,
  createPlacementMetric,
  createPlacementRecord,
  deletePlacementAssessment,
  deletePlacementGoal,
  deletePlacementMetric,
  deletePlacementRecord,
  listPlacementAssessments,
  listPlacementGoals,
  listPlacementMetrics,
  listPlacementRecords,
  restorePlacementAssessment,
  restorePlacementGoal,
  restorePlacementMetric,
  restorePlacementRecord,
  updatePlacementAssessment,
  updatePlacementGoal,
  updatePlacementMetric,
  updatePlacementRecord,
  type PlacementAssessment,
  type PlacementGoal,
  type PlacementMetric,
  type PlacementRecord,
} from '../../api/campusPlacement'
import { buildWriteError, extractError, searchPersons, type SelectOption } from '../../utils/campus'
import { useFormDraft } from '../../composables/useFormDraft'

const message = useMessage()
const notification = useNotification()

type TabKey = 'roster' | 'goal' | 'metric' | 'assessment'
const activeTab = ref<TabKey>('roster')

const RECORD_STATUS_OPTIONS = ['待跟踪', '跟踪中', '已结束'].map((v) => ({ label: v, value: v }))
const recordStatusOptions = RECORD_STATUS_OPTIONS
const GOAL_STATUS_OPTIONS = ['未开始', '进行中', '已完成', '已逾期'].map((v) => ({ label: v, value: v }))
const goalStatusOptions = GOAL_STATUS_OPTIONS

/* ───────────────────────── 通用工具 ───────────────────────── */

/**
 * 写入失败的三段式状态（R-203）。
 * ① title 人话描述 ② safe 你的数据是否安全 ③ detail 技术详情（折叠 + 一键复制）。
 */
interface WriteErrorState {
  title: string
  safe: string
  detail: string
  /** 恢复动作（重试…），为空则不渲染恢复按钮 */
  retryLabel?: string
  retry?: () => void | Promise<void>
}

/** 表单级校验错误（R-221）：就近展示在字段旁，图标 + 文字双通道。 */
type FieldErrors = Record<string, string>

/** 聚焦第一个出错的字段（字段上带 data-error-field 标记）。 */
function focusFirstError(field: string) {
  if (typeof document === 'undefined') return
  const el = document.querySelector<HTMLElement>(`[data-error-field="${field}"] input, [data-error-field="${field}"] textarea`)
  el?.focus()
}

function textCell(text: unknown, width = 140) {
  const s = text == null || text === '' ? '—' : String(text)
  return h('span', { title: s, style: { display: 'inline-block', maxWidth: `${width}px`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, s)
}

function numCell(value: unknown) {
  return h('span', { style: { fontVariantNumeric: 'tabular-nums' } }, value == null ? '—' : String(value))
}

async function copyText(text: string) {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      message.success('错误信息已复制')
      return
    }
  } catch {
    /* 降级提示 */
  }
  message.warning('复制失败，请手动选中详情内容复制')
}

function toDateStr(ts: number | null) {
  if (!ts) return undefined
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/* ── 写入失败三段式（R-203）── */

/** 页面级（工具栏写操作 / 读取失败）的写入失败。 */
const writeError = ref<WriteErrorState | null>(null)
/** 各弹窗内的写入失败。 */
const recordWriteError = ref<WriteErrorState | null>(null)
const goalWriteError = ref<WriteErrorState | null>(null)
const metricWriteError = ref<WriteErrorState | null>(null)
const assessmentWriteError = ref<WriteErrorState | null>(null)

/** 读取失败的安全提示（数据仍在服务端，不丢）。 */
const READ_SAFE_HINT = '没有连上服务器，页面上的数据仍是上一次加载到的结果，重试一次即可恢复。'

function setWriteError(
  target: Ref<WriteErrorState | null>,
  err: any,
  action: string,
  opts: { retryLabel?: string; retry?: () => void | Promise<void>; safeHint?: string } = {},
) {
  const info = buildWriteError(err, { action, safeHint: opts.safeHint })
  target.value = {
    title: info.title,
    safe: info.safe,
    detail: info.detail,
    retryLabel: opts.retryLabel,
    retry: opts.retry,
  }
}

function runRetry(target: Ref<WriteErrorState | null>) {
  const fn = target.value?.retry
  if (!fn) return
  target.value = null
  void fn()
}

function runWriteRetry() {
  runRetry(writeError)
}
function runRecordRetry() {
  runRetry(recordWriteError)
}
function runGoalRetry() {
  runRetry(goalWriteError)
}
function runMetricRetry() {
  runRetry(metricWriteError)
}
function runAssessmentRetry() {
  runRetry(assessmentWriteError)
}

/* ── 草稿（R-105）：四张表单各自一份草稿 ── */

/**
 * 打开表单时探测草稿：有内容就恢复并给「清空」出口（R-105）。
 * 草稿与服务端数据一致时静默丢弃 —— 没有需要恢复的内容，不打扰用户。
 */
function restoreDraft(
  draft: { probe: () => boolean; restore: () => void; clear: () => void },
  form: Record<string, unknown>,
  label: string,
) {
  if (!draft.probe()) return
  const before = JSON.stringify(form)
  draft.restore()
  if (JSON.stringify(form) === before) {
    draft.clear()
    return
  }
  const n = notification.create({
    title: '已恢复上次填写的内容',
    content: `上次填写但没有提交的${label}已经放回表单，你可以接着改；不需要就点「清空」。`,
    duration: 8000,
    keepAliveOnHover: true,
    action: () =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          onClick: () => {
            draft.clear()
            n?.destroy()
          },
        },
        { default: () => '清空' },
      ),
  })
}

/* ───────────────────────── ① 花名册 ───────────────────────── */

const recordRows = ref<PlacementRecord[]>([])
const recordLoading = ref(false)
const recordError = ref('')
const rosterSearch = ref('')
const goalRows = ref<PlacementGoal[]>([])

const rosterHasFilter = computed(() => Boolean(rosterSearch.value.trim()))
const rosterEmptyText = computed(() => (rosterHasFilter.value ? '没有符合筛选条件的定岗记录' : '暂无数据'))

const recordOptions = computed(() =>
  recordRows.value.map((r) => ({
    label: `${r.personName || '未命名'} · ${r.positionName || ''}`,
    value: String(r.id),
  })),
)

/** 届数：从校招批次推导（如 2026秋招 → 26 届），无批次时显示「—」。 */
function cohortLabel(batch?: string) {
  const m = String(batch || '').match(/(\d{4})/)
  return m ? `${m[1].slice(2)} 届` : '—'
}

async function loadRecords() {
  recordLoading.value = true
  recordError.value = ''
  try {
    const kw = rosterSearch.value.trim()
    const rows = await listPlacementRecords({ search: kw || undefined })
    recordRows.value = kw
      ? rows.filter((r) => `${r.personName}${r.dept}`.includes(kw))
      : rows
  } catch (e: any) {
    recordError.value = extractError(e)
    recordRows.value = []
  } finally {
    recordLoading.value = false
  }
}

/** 每条定岗记录关联的目标数量与首个目标名（目标列）。 */
function goalSummary(recordId: string) {
  const goals = goalRows.value.filter((g) => String(g.record) === String(recordId))
  if (!goals.length) return '—'
  return `${goals.length} 项 · ${goals[0].name}`
}

const rosterColumns = computed(() => [
  { title: '姓名', key: 'personName', width: 120, ellipsis: true, render: (row: PlacementRecord) => textCell(row.personName, 100) },
  { title: '届数', key: 'cohort', width: 90, render: (row: PlacementRecord) => cohortLabel(row.batch) },
  { title: '校招批次', key: 'batch', width: 130, ellipsis: true, render: (row: PlacementRecord) => textCell(row.batch, 110) },
  { title: '定岗部门', key: 'dept', width: 140, ellipsis: true, render: (row: PlacementRecord) => textCell(row.dept, 120) },
  { title: '岗位', key: 'positionName', width: 160, ellipsis: true, render: (row: PlacementRecord) => textCell(row.positionName, 140) },
  { title: '定岗日期', key: 'placeDate', width: 120, render: (row: PlacementRecord) => row.placeDate || '—' },
  { title: '目标', key: 'goals', width: 200, ellipsis: true, render: (row: PlacementRecord) => textCell(goalSummary(row.id), 180) },
  { title: '最近考核', key: 'latestPerf', width: 100, render: (row: PlacementRecord) => row.latestPerf || '—' },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: PlacementRecord) => {
      const map: Record<string, any> = { 待跟踪: 'warning', 跟踪中: 'success', 已结束: 'default' }
      return h(NTag, { type: map[row.status] || 'default', size: 'small' }, { default: () => row.status || '—' })
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: PlacementRecord) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openRecordEdit(row) }, {
            default: () => '编辑定岗',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeRecord(row) }, {
            default: () => '删除定岗',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const ROSTER_SCROLL_X = 1310

/* ── 定岗记录 新增 / 编辑 ── */
const recordFormVisible = ref(false)
const recordSaving = ref(false)
const recordEditing = ref<PlacementRecord | null>(null)
const personOptions = ref<SelectOption[]>([])
const personLoading = ref(false)
const recordForm = reactive({
  person: null as string | null,
  dept: '',
  positionName: '',
  placeDateTs: null as number | null,
  trackYears: 1,
  status: '待跟踪',
  latestPerf: '',
})

/** 字段级校验错误（R-221）：就近展示在对应字段旁。 */
const recordErrors = reactive<FieldErrors>({ person: '', dept: '', positionName: '', placeDate: '' })

/** 定岗记录草稿（R-105）：编辑态不启用，避免草稿覆盖真实行数据。 */
const recordDraft = useFormDraft('campus-placement-track-record', recordForm as unknown as Record<string, unknown>, {
  enabled: () => !recordEditing.value,
})

async function onPersonSearch(kw: string) {
  personLoading.value = true
  try {
    personOptions.value = await searchPersons(kw)
  } catch {
    personOptions.value = []
  } finally {
    personLoading.value = false
  }
}

function openRecordCreate() {
  Object.assign(recordForm, {
    person: null,
    dept: '',
    positionName: '',
    placeDateTs: Date.now(),
    trackYears: 1,
    status: '待跟踪',
    latestPerf: '',
  })
  Object.assign(recordErrors, { person: '', dept: '', positionName: '', placeDate: '' })
  recordEditing.value = null
  recordWriteError.value = null
  recordFormVisible.value = true
  restoreDraft(recordDraft, recordForm as unknown as Record<string, unknown>, '定岗记录')
}

function openRecordEdit(row: PlacementRecord) {
  Object.assign(recordForm, {
    person: row.person ? String(row.person) : null,
    dept: row.dept || '',
    positionName: row.positionName || '',
    placeDateTs: row.placeDate ? new Date(row.placeDate).getTime() : null,
    trackYears: row.trackYears ?? 1,
    status: row.status || '待跟踪',
    latestPerf: row.latestPerf || '',
  })
  personOptions.value = row.person ? [{ label: row.personName || String(row.person), value: String(row.person) }] : []
  Object.assign(recordErrors, { person: '', dept: '', positionName: '', placeDate: '' })
  recordEditing.value = row
  recordWriteError.value = null
  recordFormVisible.value = true
}

/** 关闭弹窗：清掉校验与写入失败状态，下次打开是干净的。 */
function closeRecordForm() {
  recordFormVisible.value = false
  Object.assign(recordErrors, { person: '', dept: '', positionName: '', placeDate: '' })
  recordWriteError.value = null
}

async function saveRecord() {
  // 就近校验（R-221）：逐字段置错误态 + 聚焦第一个出错字段
  recordErrors.person = recordForm.person ? '' : '请选择校招生'
  recordErrors.dept = recordForm.dept.trim() ? '' : '请填写定岗部门'
  recordErrors.positionName = recordForm.positionName.trim() ? '' : '请填写岗位名称'
  recordErrors.placeDate = recordForm.placeDateTs ? '' : '请选择定岗日期'
  const firstError = recordErrors.person
    ? 'record-person'
    : recordErrors.dept
      ? 'record-dept'
      : recordErrors.positionName
        ? 'record-position'
        : recordErrors.placeDate
          ? 'record-place-date'
          : ''
  if (firstError) {
    focusFirstError(firstError)
    return
  }
  recordSaving.value = true
  const payload = {
    person: String(recordForm.person),
    dept: recordForm.dept.trim(),
    positionName: recordForm.positionName.trim(),
    placeDate: toDateStr(recordForm.placeDateTs),
    trackYears: recordForm.trackYears,
    status: recordForm.status,
    latestPerf: recordForm.latestPerf.trim(),
  }
  try {
    if (recordEditing.value) {
      await updatePlacementRecord(recordEditing.value.id, payload)
      message.success('定岗记录已更新')
    } else {
      await createPlacementRecord(payload)
      message.success('定岗记录已创建')
    }
    recordFormVisible.value = false
    // 提交成功后立即清除草稿（R-105）
    recordDraft.clear()
    loadRecords()
  } catch (e: any) {
    setWriteError(recordWriteError, e, recordEditing.value ? '保存定岗记录' : '创建定岗记录', {
      retryLabel: '重试保存',
      retry: saveRecord,
    })
  } finally {
    recordSaving.value = false
  }
}

/** 撤销删除：把被删掉的定岗记录恢复回来。 */
async function restoreRecord(row: PlacementRecord) {
  try {
    await restorePlacementRecord(row.id)
    message.success('定岗记录已恢复')
    loadRecords()
  } catch (e: any) {
    setWriteError(writeError, e, '恢复定岗记录', { retryLabel: '重试恢复', retry: () => restoreRecord(row) })
  }
}

/** 删除单条定岗记录 = 中等破坏性操作 → 直接执行 + 通知撤销（R-106）。 */
async function removeRecord(row: PlacementRecord) {
  try {
    await deletePlacementRecord(row.id)
    notification.create({
      content: `已删除「${row.personName || '该校招生'}」的定岗记录`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            await restoreRecord(row)
          },
        }, { default: () => '撤销' }),
    })
    loadRecords()
  } catch (e: any) {
    setWriteError(writeError, e, '删除定岗记录', { retryLabel: '重试删除', retry: () => removeRecord(row) })
  }
}

/* ───────────────────────── ② 目标 ───────────────────────── */

const goalLoading = ref(false)
const goalError = ref('')
const goalRecord = ref<string | null>(null)
const goalHasFilter = computed(() => Boolean(goalRecord.value))
const goalEmptyText = computed(() => (goalRecord.value ? '该定岗记录还没有目标' : '暂无数据'))

async function loadGoals() {
  goalLoading.value = true
  goalError.value = ''
  try {
    goalRows.value = await listPlacementGoals({ record: goalRecord.value ?? undefined })
  } catch (e: any) {
    goalError.value = extractError(e)
    goalRows.value = []
  } finally {
    goalLoading.value = false
  }
}

const goalColumns = computed(() => [
  { title: '目标名称', key: 'name', width: 200, ellipsis: true, render: (row: PlacementGoal) => textCell(row.name, 180) },
  { title: '衡量指标', key: 'metric', width: 140, ellipsis: true, render: (row: PlacementGoal) => textCell(row.metric, 120) },
  { title: '目标值', key: 'targetValue', width: 120, ellipsis: true, render: (row: PlacementGoal) => textCell(row.targetValue, 100) },
  { title: '权重', key: 'weight', width: 90, render: (row: PlacementGoal) => numCell(row.weight == null ? '—' : `${row.weight}%`) },
  { title: '截止日期', key: 'dueDate', width: 120, render: (row: PlacementGoal) => row.dueDate || '—' },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: PlacementGoal) => {
      const map: Record<string, any> = { 未开始: 'default', 进行中: 'warning', 已完成: 'success', 已逾期: 'error' }
      return h(NTag, { type: map[row.status] || 'default', size: 'small' }, { default: () => row.status || '—' })
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: PlacementGoal) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openGoalEdit(row) }, {
            default: () => '编辑目标',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeGoal(row) }, {
            default: () => '删除目标',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const GOAL_SCROLL_X = 1010

const goalFormVisible = ref(false)
const goalSaving = ref(false)
const goalEditing = ref<PlacementGoal | null>(null)
const goalForm = reactive({
  name: '',
  metric: '',
  targetValue: '',
  weight: 0,
  dueDateTs: null as number | null,
  status: '未开始',
})

/** 字段级校验错误（R-221）：就近展示在对应字段旁。 */
const goalErrors = reactive<FieldErrors>({ record: '', name: '', metric: '', targetValue: '' })

/** 定岗目标草稿（R-105）：编辑态不启用，避免草稿覆盖真实行数据。 */
const goalDraft = useFormDraft('campus-placement-track-goal', goalForm as unknown as Record<string, unknown>, {
  enabled: () => !goalEditing.value,
})

function openGoalCreate() {
  Object.assign(goalForm, { name: '', metric: '', targetValue: '', weight: 0, dueDateTs: null, status: '未开始' })
  Object.assign(goalErrors, { record: '', name: '', metric: '', targetValue: '' })
  goalEditing.value = null
  goalWriteError.value = null
  goalFormVisible.value = true
  restoreDraft(goalDraft, goalForm as unknown as Record<string, unknown>, '定岗目标')
}

function openGoalEdit(row: PlacementGoal) {
  Object.assign(goalForm, {
    name: row.name || '',
    metric: row.metric || '',
    targetValue: row.targetValue || '',
    weight: row.weight ?? 0,
    dueDateTs: row.dueDate ? new Date(row.dueDate).getTime() : null,
    status: row.status || '未开始',
  })
  Object.assign(goalErrors, { record: '', name: '', metric: '', targetValue: '' })
  goalEditing.value = row
  goalWriteError.value = null
  goalFormVisible.value = true
}

/** 关闭弹窗：清掉校验与写入失败状态，下次打开是干净的。 */
function closeGoalForm() {
  goalFormVisible.value = false
  Object.assign(goalErrors, { record: '', name: '', metric: '', targetValue: '' })
  goalWriteError.value = null
}

async function saveGoal() {
  // 就近校验（R-221）：逐字段置错误态 + 聚焦第一个出错字段
  goalErrors.record = goalRecord.value ? '' : '请先选择定岗记录'
  goalErrors.name = goalForm.name.trim() ? '' : '请填写目标名称'
  goalErrors.metric = goalForm.metric.trim() ? '' : '请填写衡量指标'
  goalErrors.targetValue = goalForm.targetValue.trim() ? '' : '请填写目标值'
  const firstError = goalErrors.record
    ? 'goal-name'
    : goalErrors.name
      ? 'goal-name'
      : goalErrors.metric
        ? 'goal-metric'
        : goalErrors.targetValue
          ? 'goal-target'
          : ''
  if (firstError) {
    focusFirstError(firstError)
    return
  }
  goalSaving.value = true
  const payload = {
    record: String(goalRecord.value),
    name: goalForm.name.trim(),
    metric: goalForm.metric.trim(),
    targetValue: goalForm.targetValue.trim(),
    weight: goalForm.weight,
    dueDate: toDateStr(goalForm.dueDateTs),
    status: goalForm.status,
  }
  try {
    if (goalEditing.value) {
      await updatePlacementGoal(goalEditing.value.id, payload)
      message.success('定岗目标已更新')
    } else {
      await createPlacementGoal(payload)
      message.success('定岗目标已创建')
    }
    goalFormVisible.value = false
    // 提交成功后立即清除草稿（R-105）
    goalDraft.clear()
    loadGoals()
  } catch (e: any) {
    setWriteError(goalWriteError, e, goalEditing.value ? '保存定岗目标' : '创建定岗目标', {
      retryLabel: '重试保存',
      retry: saveGoal,
    })
  } finally {
    goalSaving.value = false
  }
}

/** 撤销删除：把被删掉的定岗目标恢复回来。 */
async function restoreGoal(row: PlacementGoal) {
  try {
    await restorePlacementGoal(row.id)
    message.success('定岗目标已恢复')
    loadGoals()
  } catch (e: any) {
    setWriteError(writeError, e, '恢复定岗目标', { retryLabel: '重试恢复', retry: () => restoreGoal(row) })
  }
}

async function removeGoal(row: PlacementGoal) {
  try {
    await deletePlacementGoal(row.id)
    notification.create({
      content: `已删除目标「${row.name}」`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            await restoreGoal(row)
          },
        }, { default: () => '撤销' }),
    })
    loadGoals()
  } catch (e: any) {
    setWriteError(writeError, e, '删除定岗目标', { retryLabel: '重试删除', retry: () => removeGoal(row) })
  }
}

/* ───────────────────────── ③ 数据 ───────────────────────── */

const metricRows = ref<PlacementMetric[]>([])
const metricLoading = ref(false)
const metricError = ref('')
const metricRecord = ref<string | null>(null)
const metricHasFilter = computed(() => Boolean(metricRecord.value))
const metricEmptyText = computed(() => (metricRecord.value ? '该定岗记录还没有数据' : '暂无数据'))

async function loadMetrics() {
  metricLoading.value = true
  metricError.value = ''
  try {
    metricRows.value = await listPlacementMetrics({ record: metricRecord.value ?? undefined })
  } catch (e: any) {
    metricError.value = extractError(e)
    metricRows.value = []
  } finally {
    metricLoading.value = false
  }
}

const metricColumns = computed(() => [
  { title: '月份', key: 'ym', width: 120, render: (row: PlacementMetric) => row.ym || '—' },
  { title: '指标', key: 'metric', width: 180, ellipsis: true, render: (row: PlacementMetric) => textCell(row.metric, 160) },
  { title: '完成值', key: 'actualValue', width: 140, ellipsis: true, render: (row: PlacementMetric) => textCell(row.actualValue, 120) },
  { title: '备注', key: 'remark', width: 220, ellipsis: true, render: (row: PlacementMetric) => textCell(row.remark, 200) },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: PlacementMetric) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openMetricEdit(row) }, {
            default: () => '编辑数据',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeMetric(row) }, {
            default: () => '删除数据',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const METRIC_SCROLL_X = 830

const metricFormVisible = ref(false)
const metricSaving = ref(false)
const metricEditing = ref<PlacementMetric | null>(null)
const metricForm = reactive({ ym: '', metric: '', actualValue: '', remark: '' })

/** 字段级校验错误（R-221）：就近展示在对应字段旁。 */
const metricErrors = reactive<FieldErrors>({ record: '', ym: '', metric: '', actualValue: '' })

/** 定岗数据草稿（R-105）：编辑态不启用，避免草稿覆盖真实行数据。 */
const metricDraft = useFormDraft('campus-placement-track-metric', metricForm as unknown as Record<string, unknown>, {
  enabled: () => !metricEditing.value,
})

function openMetricCreate() {
  Object.assign(metricForm, { ym: '', metric: '', actualValue: '', remark: '' })
  Object.assign(metricErrors, { record: '', ym: '', metric: '', actualValue: '' })
  metricEditing.value = null
  metricWriteError.value = null
  metricFormVisible.value = true
  restoreDraft(metricDraft, metricForm as unknown as Record<string, unknown>, '定岗数据')
}

function openMetricEdit(row: PlacementMetric) {
  Object.assign(metricForm, {
    ym: row.ym || '',
    metric: row.metric || '',
    actualValue: row.actualValue || '',
    remark: row.remark || '',
  })
  Object.assign(metricErrors, { record: '', ym: '', metric: '', actualValue: '' })
  metricEditing.value = row
  metricWriteError.value = null
  metricFormVisible.value = true
}

/** 关闭弹窗：清掉校验与写入失败状态，下次打开是干净的。 */
function closeMetricForm() {
  metricFormVisible.value = false
  Object.assign(metricErrors, { record: '', ym: '', metric: '', actualValue: '' })
  metricWriteError.value = null
}

async function saveMetric() {
  // 就近校验（R-221）：逐字段置错误态 + 聚焦第一个出错字段
  metricErrors.record = metricRecord.value ? '' : '请先选择定岗记录'
  metricErrors.ym = metricForm.ym.trim() ? '' : '请填写月份'
  metricErrors.metric = metricForm.metric.trim() ? '' : '请填写指标'
  metricErrors.actualValue = metricForm.actualValue.trim() ? '' : '请填写完成值'
  const firstError = metricErrors.record
    ? 'metric-ym'
    : metricErrors.ym
      ? 'metric-ym'
      : metricErrors.metric
        ? 'metric-metric'
        : metricErrors.actualValue
          ? 'metric-actual'
          : ''
  if (firstError) {
    focusFirstError(firstError)
    return
  }
  metricSaving.value = true
  const payload = {
    record: String(metricRecord.value),
    ym: metricForm.ym.trim(),
    metric: metricForm.metric.trim(),
    actualValue: metricForm.actualValue.trim(),
    remark: metricForm.remark.trim(),
  }
  try {
    if (metricEditing.value) {
      await updatePlacementMetric(metricEditing.value.id, payload)
      message.success('定岗数据已更新')
    } else {
      await createPlacementMetric(payload)
      message.success('定岗数据已创建')
    }
    metricFormVisible.value = false
    // 提交成功后立即清除草稿（R-105）
    metricDraft.clear()
    loadMetrics()
  } catch (e: any) {
    setWriteError(metricWriteError, e, metricEditing.value ? '保存定岗数据' : '创建定岗数据', {
      retryLabel: '重试保存',
      retry: saveMetric,
    })
  } finally {
    metricSaving.value = false
  }
}

/** 撤销删除：把被删掉的定岗数据恢复回来。 */
async function restoreMetric(row: PlacementMetric) {
  try {
    await restorePlacementMetric(row.id)
    message.success('定岗数据已恢复')
    loadMetrics()
  } catch (e: any) {
    setWriteError(writeError, e, '恢复定岗数据', { retryLabel: '重试恢复', retry: () => restoreMetric(row) })
  }
}

async function removeMetric(row: PlacementMetric) {
  try {
    await deletePlacementMetric(row.id)
    notification.create({
      content: `已删除「${row.ym}」的数据`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            await restoreMetric(row)
          },
        }, { default: () => '撤销' }),
    })
    loadMetrics()
  } catch (e: any) {
    setWriteError(writeError, e, '删除定岗数据', { retryLabel: '重试删除', retry: () => removeMetric(row) })
  }
}

/* ───────────────────────── ④ 考核 ───────────────────────── */

const assessmentRows = ref<PlacementAssessment[]>([])
const assessmentLoading = ref(false)
const assessmentError = ref('')
const assessmentRecord = ref<string | null>(null)
const assessmentHasFilter = computed(() => Boolean(assessmentRecord.value))
const assessmentEmptyText = computed(() => (assessmentRecord.value ? '该定岗记录还没有考核' : '暂无数据'))

async function loadAssessments() {
  assessmentLoading.value = true
  assessmentError.value = ''
  try {
    assessmentRows.value = await listPlacementAssessments({ record: assessmentRecord.value ?? undefined })
  } catch (e: any) {
    assessmentError.value = extractError(e)
    assessmentRows.value = []
  } finally {
    assessmentLoading.value = false
  }
}

const assessmentColumns = computed(() => [
  { title: '考核周期', key: 'period', width: 180, ellipsis: true, render: (row: PlacementAssessment) => textCell(row.period, 160) },
  { title: '得分', key: 'score', width: 100, render: (row: PlacementAssessment) => numCell(row.score) },
  { title: '绩效等级', key: 'perfLevel', width: 110, render: (row: PlacementAssessment) => row.perfLevel || '—' },
  { title: '评定日期', key: 'assessedAt', width: 120, render: (row: PlacementAssessment) => row.assessedAt || '—' },
  { title: '评语', key: 'comment', width: 240, ellipsis: true, render: (row: PlacementAssessment) => textCell(row.comment, 220) },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: PlacementAssessment) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openAssessmentEdit(row) }, {
            default: () => '编辑考核',
            icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
          }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => removeAssessment(row) }, {
            default: () => '删除考核',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          }),
        ],
      }),
  },
])

const ASSESSMENT_SCROLL_X = 920

const assessmentFormVisible = ref(false)
const assessmentSaving = ref(false)
const assessmentEditing = ref<PlacementAssessment | null>(null)
const assessmentForm = reactive({
  period: '',
  score: 0,
  perfLevel: '',
  assessedAtTs: null as number | null,
  comment: '',
})

/** 字段级校验错误（R-221）：就近展示在对应字段旁。 */
const assessmentErrors = reactive<FieldErrors>({ record: '', period: '', perfLevel: '', assessedAt: '' })

/** 定岗考核草稿（R-105）：编辑态不启用，避免草稿覆盖真实行数据。 */
const assessmentDraft = useFormDraft(
  'campus-placement-track-assessment',
  assessmentForm as unknown as Record<string, unknown>,
  { enabled: () => !assessmentEditing.value },
)

function openAssessmentCreate() {
  Object.assign(assessmentForm, { period: '', score: 0, perfLevel: '', assessedAtTs: Date.now(), comment: '' })
  Object.assign(assessmentErrors, { record: '', period: '', perfLevel: '', assessedAt: '' })
  assessmentEditing.value = null
  assessmentWriteError.value = null
  assessmentFormVisible.value = true
  restoreDraft(assessmentDraft, assessmentForm as unknown as Record<string, unknown>, '定岗考核')
}

function openAssessmentEdit(row: PlacementAssessment) {
  Object.assign(assessmentForm, {
    period: row.period || '',
    score: row.score ?? 0,
    perfLevel: row.perfLevel || '',
    assessedAtTs: row.assessedAt ? new Date(row.assessedAt).getTime() : null,
    comment: row.comment || '',
  })
  Object.assign(assessmentErrors, { record: '', period: '', perfLevel: '', assessedAt: '' })
  assessmentEditing.value = row
  assessmentWriteError.value = null
  assessmentFormVisible.value = true
}

/** 关闭弹窗：清掉校验与写入失败状态，下次打开是干净的。 */
function closeAssessmentForm() {
  assessmentFormVisible.value = false
  Object.assign(assessmentErrors, { record: '', period: '', perfLevel: '', assessedAt: '' })
  assessmentWriteError.value = null
}

async function saveAssessment() {
  // 就近校验（R-221）：逐字段置错误态 + 聚焦第一个出错字段
  assessmentErrors.record = assessmentRecord.value ? '' : '请先选择定岗记录'
  assessmentErrors.period = assessmentForm.period.trim() ? '' : '请填写考核周期'
  assessmentErrors.perfLevel = assessmentForm.perfLevel.trim() ? '' : '请填写绩效等级'
  assessmentErrors.assessedAt = assessmentForm.assessedAtTs ? '' : '请选择评定日期'
  const firstError = assessmentErrors.record
    ? 'assessment-period'
    : assessmentErrors.period
      ? 'assessment-period'
      : assessmentErrors.perfLevel
        ? 'assessment-level'
        : assessmentErrors.assessedAt
          ? 'assessment-date'
          : ''
  if (firstError) {
    focusFirstError(firstError)
    return
  }
  assessmentSaving.value = true
  const payload = {
    record: String(assessmentRecord.value),
    period: assessmentForm.period.trim(),
    score: assessmentForm.score,
    perfLevel: assessmentForm.perfLevel.trim(),
    assessedAt: toDateStr(assessmentForm.assessedAtTs),
    comment: assessmentForm.comment.trim(),
  }
  try {
    if (assessmentEditing.value) {
      await updatePlacementAssessment(assessmentEditing.value.id, payload)
      message.success('定岗考核已更新')
    } else {
      await createPlacementAssessment(payload)
      message.success('定岗考核已创建')
    }
    assessmentFormVisible.value = false
    // 提交成功后立即清除草稿（R-105）
    assessmentDraft.clear()
    loadAssessments()
  } catch (e: any) {
    setWriteError(assessmentWriteError, e, assessmentEditing.value ? '保存定岗考核' : '创建定岗考核', {
      retryLabel: '重试保存',
      retry: saveAssessment,
    })
  } finally {
    assessmentSaving.value = false
  }
}

/** 撤销删除：把被删掉的定岗考核恢复回来。 */
async function restoreAssessment(row: PlacementAssessment) {
  try {
    await restorePlacementAssessment(row.id)
    message.success('定岗考核已恢复')
    loadAssessments()
  } catch (e: any) {
    setWriteError(writeError, e, '恢复定岗考核', { retryLabel: '重试恢复', retry: () => restoreAssessment(row) })
  }
}

async function removeAssessment(row: PlacementAssessment) {
  try {
    await deletePlacementAssessment(row.id)
    notification.create({
      content: `已删除「${row.period}」的考核`,
      duration: 8000,
      keepAliveOnHover: true,
      action: () =>
        h(NButton, {
          text: true,
          type: 'primary',
          onClick: async () => {
            await restoreAssessment(row)
          },
        }, { default: () => '撤销' }),
    })
    loadAssessments()
  } catch (e: any) {
    setWriteError(writeError, e, '删除定岗考核', { retryLabel: '重试删除', retry: () => removeAssessment(row) })
  }
}

/* ───────────────────────── 生命周期 ───────────────────────── */

function onTabChange(tab: TabKey) {
  if (tab === 'roster') {
    loadRecords()
  } else if (tab === 'goal') {
    loadGoals()
  } else if (tab === 'metric') {
    loadMetrics()
  } else {
    loadAssessments()
  }
}

onMounted(async () => {
  await loadRecords()
  await loadGoals()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.page-tabs {
  flex-shrink: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  flex-wrap: wrap;
}
.toolbar-search {
  width: 240px;
}
.toolbar-select-wide {
  width: 260px;
}
.spacer {
  flex: 1;
}
.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
.filter {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
/** 表单级前置条件错误（R-221）：图标 + 文字双通道，就近展示在表单顶部 */
.field-error {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
  font-size: var(--text-small);
  color: var(--c-error-deep);
}
.filter-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  white-space: nowrap;
}

.error-state {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--c-error);
  border-radius: var(--radius-md);
  background: var(--c-error-soft);
  flex-shrink: 0;
}
.error-state-icon {
  color: var(--c-error-deep);
  font-size: var(--text-h4);
  flex-shrink: 0;
}
.error-state-body {
  flex: 1;
  min-width: 0;
}
.error-state-title {
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--c-error-deep);
}
.error-state-desc {
  font-size: var(--text-small);
  color: var(--ink-soft);
  margin-top: var(--space-1);
}
.error-state-detail {
  margin-top: var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.error-state-code {
  margin: var(--space-1) 0;
  padding: var(--space-2);
  background: var(--surface);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
