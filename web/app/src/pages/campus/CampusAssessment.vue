<template>
  <!-- 轮岗考核：逆向清单 §4.3 `assessment` 视图。
       6 个页签：月度数据 / 考核模板 / 排名 / 考试分值统计 / 试用期考核 / 班主任排名。
       口径（逆向清单 A1~A9）：月度总分 = round(KPI×0.6 + 考试×0.4) + 加减分；
       综合得分 = round(KPI×0.5) + round(学习成长×0.3) + round(五行五力×0.2) + 附加分。 -->
  <div class="page-container">
    <div class="page-body">
      <n-tabs
        v-model:value="activeTab"
        type="line"
        display-directive="show:lazy"
        class="ca-tabs"
        @update:value="onTabChange"
      >
        <!-- ① 月度数据 -->
        <n-tab-pane name="monthly" tab="月度数据">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">月份</span>
              <n-select
                v-model:value="monthlyYm"
                :options="ymOptions"
                placeholder="全部月份"
                clearable
                style="width: 180px"
                @update:value="loadMonthly"
              />
            </div>
            <div class="field">
              <span class="field-label">班级</span>
              <n-select
                v-model:value="monthlyClass"
                :options="classOptions"
                placeholder="全部班级"
                clearable
                filterable
                style="width: 200px"
                @update:value="loadMonthly"
              />
            </div>
            <div class="spacer"></div>
            <n-button :loading="monthlyLoading" @click="loadMonthly">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新数据
            </n-button>
          </div>

          <n-alert v-if="monthlyError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>月度考核数据没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="monthlyLoading" @click="loadMonthly">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="monthlyErrorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ monthlyErrorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(monthlyErrorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <div v-if="monthlyLoading && !monthlyRows.length" class="skeleton-wrap">
            <n-skeleton :repeat="6" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="monthlyColumns"
              :data="monthlyRows"
              :loading="monthlyLoading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="MONTHLY_SCROLL_X"
              :row-key="(row: MonthlyAssessmentRow) => row.id"
              flex-height
            >
              <template #empty>
                <n-empty :description="monthlyEmptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>

        <!-- ② 考核模板 -->
        <n-tab-pane name="template" tab="考核模板">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">适用范围</span>
              <n-select
                v-model:value="templateScope"
                :options="scopeFilterOptions"
                style="width: 160px"
                @update:value="loadTemplates"
              />
            </div>
            <div class="spacer"></div>
            <n-button :loading="templateLoading" @click="loadTemplates">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新模板
            </n-button>
            <n-button type="primary" @click="openTemplateCreate">
              <template #icon><n-icon :component="AddOutline" /></template>
              新增模板
            </n-button>
          </div>

          <n-alert v-if="templateError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>考核模板没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="templateLoading" @click="loadTemplates">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="templateErrorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ templateErrorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(templateErrorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <div v-if="templateLoading && !templates.length" class="skeleton-wrap">
            <n-skeleton :repeat="4" animated />
          </div>

          <div v-else class="template-grid">
            <n-empty v-if="!templates.length" class="template-empty" :description="templateEmptyText" />
            <div v-for="tpl in templates" :key="tpl.id" class="template-card">
              <div class="card-head">
                <div class="card-title" :title="tpl.name">{{ tpl.name }}</div>
                <n-switch
                  :value="tpl.enabled"
                  size="small"
                  :aria-label="`${tpl.name}启用开关`"
                  @update:value="(v: boolean) => toggleTemplate(tpl, v)"
                />
              </div>
              <div class="card-tags">
                <n-tag size="small" :bordered="false" type="info">
                  {{ SCOPE_TYPE_LABEL[tpl.scopeType] || tpl.scopeType }}
                </n-tag>
                <n-tag size="small" :bordered="false">
                  {{ PERIOD_TYPE_LABEL[tpl.periodType] || tpl.periodType }}
                </n-tag>
                <n-tag size="small" :bordered="false">
                  {{ STAGE_LABEL[tpl.stage] || tpl.stage }}
                </n-tag>
                <n-tag v-if="!tpl.enabled" size="small" :bordered="false" type="warning">已停用</n-tag>
              </div>
              <div v-if="tpl.scopeType !== 'all' && tpl.scopeValues.length" class="card-scope">
                适用范围：{{ tpl.scopeValues.join('、') }}
              </div>
              <table class="weight-table">
                <thead>
                  <tr><th>维度</th><th>权重</th><th>目标要求</th></tr>
                </thead>
                <tbody>
                  <tr v-for="item in tpl.items" :key="item.name">
                    <td>{{ item.name }}</td>
                    <td class="num-cell">{{ item.weight }}%</td>
                    <td class="target-cell" :title="item.target">{{ item.target || '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <n-alert v-if="tpl.weightSum !== 100" type="warning" :show-icon="true" class="weight-alert">
                权重合计 {{ tpl.weightSum }}%，与 100% 不符，评分结果会失真。
              </n-alert>
              <div class="card-actions">
                <n-button size="small" quaternary type="primary" @click="openTemplateEdit(tpl)">
                  <template #icon><n-icon :component="CreateOutline" /></template>
                  编辑模板
                </n-button>
                <n-button
                  size="small"
                  quaternary
                  type="error"
                  :loading="deletingTemplateId === tpl.id"
                  @click="askDeleteTemplate(tpl)"
                >
                  <template #icon><n-icon :component="TrashOutline" /></template>
                  删除模板
                </n-button>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <!-- ③ 排名 -->
        <n-tab-pane name="ranking" tab="排名">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">排名维度</span>
              <n-radio-group v-model:value="rankDim" @update:value="loadRanking">
                <n-radio-button v-for="d in rankDimOptions" :key="d.value" :value="d.value">
                  {{ d.label }}
                </n-radio-button>
              </n-radio-group>
            </div>
            <div class="field">
              <span class="field-label">月份</span>
              <n-select
                v-model:value="rankYm"
                :options="ymOptions"
                style="width: 160px"
                @update:value="loadRanking"
              />
            </div>
            <div class="spacer"></div>
            <n-button :loading="rankLoading" @click="loadRanking">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新排名
            </n-button>
          </div>

          <n-alert v-if="rankError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>排名没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="rankLoading" @click="loadRanking">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="rankErrorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ rankErrorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(rankErrorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <div v-if="rankLoading && !rankRows.length" class="skeleton-wrap">
            <n-skeleton :repeat="6" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="rankColumns"
              :data="rankRows"
              :loading="rankLoading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="RANK_SCROLL_X"
              :row-key="(row: CompositeRankingRow) => row.person || String(row.rank)"
              flex-height
            >
              <template #empty>
                <n-empty :description="rankEmptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>

        <!-- ④ 考试分值统计 -->
        <n-tab-pane name="exam" tab="考试分值统计">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">月份</span>
              <n-select
                v-model:value="examYm"
                :options="ymFilterOptions"
                style="width: 180px"
                @update:value="loadExamStats"
              />
            </div>
            <div class="spacer"></div>
            <n-button :loading="examLoading" @click="loadExamStats">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新统计
            </n-button>
          </div>

          <div class="stat-row">
            <div v-for="card in examStatCards" :key="card.key" class="stat-card">
              <div class="stat-label">{{ card.label }}</div>
              <div class="stat-value">{{ card.value }}</div>
            </div>
          </div>

          <n-alert v-if="examError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>考试分值统计没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="examLoading" @click="loadExamStats">
                重新加载
              </n-button>
            </div>
          </n-alert>

          <div v-if="examLoading && !examRows.length" class="skeleton-wrap">
            <n-skeleton :repeat="4" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="examColumns"
              :data="examSummaryRows"
              :loading="examLoading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="EXAM_SCROLL_X"
              :row-key="(row: ExamSummaryRow) => row.ym"
              flex-height
            >
              <template #empty>
                <n-empty :description="examEmptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>

        <!-- ⑤ 试用期考核 -->
        <n-tab-pane name="probation" tab="试用期考核">
          <div class="toolbar">
            <div class="spacer"></div>
            <n-button :loading="probationLoading" @click="loadProbations">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新试用期
            </n-button>
          </div>

          <n-alert v-if="probationError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>试用期考核没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="probationLoading" @click="loadProbations">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="probationErrorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ probationErrorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(probationErrorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <div v-if="probationLoading && !probationRows.length" class="skeleton-wrap">
            <n-skeleton :repeat="5" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="probationColumns"
              :data="probationRows"
              :loading="probationLoading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="PROBATION_SCROLL_X"
              :row-key="(row: ProbationRow) => row.id"
              flex-height
            >
              <template #empty>
                <n-empty :description="probationEmptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>

        <!-- ⑥ 班主任排名 -->
        <n-tab-pane name="teacher" tab="班主任排名">
          <div class="toolbar">
            <div class="field">
              <span class="field-label">月份</span>
              <n-select
                v-model:value="teacherYm"
                :options="ymOptions"
                style="width: 160px"
                @update:value="loadTeachers"
              />
            </div>
            <div class="spacer"></div>
            <n-button :loading="teacherLoading" @click="loadTeachers">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              刷新排名
            </n-button>
          </div>

          <n-alert v-if="teacherError" type="error" :show-icon="true" class="load-error">
            <div class="error-head">
              <span>班主任排名没能加载出来，本次查询没有改动任何数据。</span>
              <n-button size="small" tertiary type="error" :loading="teacherLoading" @click="loadTeachers">
                重新加载
              </n-button>
            </div>
            <n-collapse v-if="teacherErrorDetail" class="error-collapse">
              <n-collapse-item title="详情" name="detail">
                <div class="error-detail">
                  <code>{{ teacherErrorDetail }}</code>
                  <n-button size="tiny" quaternary @click="copyDetail(teacherErrorDetail)">复制错误信息</n-button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </n-alert>

          <div v-if="teacherLoading && !teacherRows.length" class="skeleton-wrap">
            <n-skeleton :repeat="5" animated />
          </div>

          <div v-else class="table-wrap">
            <n-data-table
              :columns="teacherColumns"
              :data="teacherRows"
              :loading="teacherLoading"
              :bordered="false"
              :pagination="pagination"
              :scroll-x="TEACHER_SCROLL_X"
              :row-key="(row: TeacherRankingRow) => `${row.teacherName}-${row.rank}`"
              flex-height
            >
              <template #empty>
                <n-empty :description="teacherEmptyText" />
              </template>
            </n-data-table>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- 加减分弹窗 -->
    <n-modal
      v-model:show="adjustVisible"
      preset="card"
      title="调整考核分值"
      :style="{ width: '560px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(360px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <n-form :model="adjustForm" label-placement="top">
        <n-form-item label="调整分值" required>
          <n-input-number
            v-model:value="adjustForm.adjust"
            :min="-100"
            :max="100"
            :step="1"
            style="width: 100%"
            placeholder="正数加分，负数减分"
          />
        </n-form-item>
        <n-form-item label="调整原因" required>
          <n-input
            v-model:value="adjustForm.reason"
            type="textarea"
            :rows="3"
            placeholder="如 创新提案 +3 分 / 迟到 -1 分"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="adjusting" @click="adjustVisible = false">取消调整</n-button>
          <n-button type="primary" :loading="adjusting" :disabled="!canAdjust" @click="submitAdjust">
            保存分值
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 核对通过确认框（R-106：锁定类操作，写明后果） -->
    <n-modal
      v-model:show="checkVisible"
      preset="card"
      title="核对月度数据"
      :style="{ width: '520px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(320px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <p class="confirm-text">
        核对通过后「{{ checkRow?.ym }} · {{ checkRow?.personName || '该校招生' }}」的月度数据将被锁定，并计入当月排名，之后不能再改分值。
      </p>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="checking" @click="checkVisible = false">暂不核对</n-button>
          <n-button type="primary" :loading="checking" @click="confirmCheck">核对通过</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 考核模板新增 / 编辑弹窗 -->
    <n-modal
      v-model:show="templateVisible"
      preset="card"
      :title="editingTemplate ? '编辑考核模板' : '新增考核模板'"
      :style="{ width: '760px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(620px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <n-form :model="templateForm" label-placement="top">
        <n-grid :cols="2" :x-gap="16" responsive="screen" :item-responsive="true">
          <n-grid-item span="2 s:1">
            <n-form-item label="模板名称" required>
              <n-input v-model:value="templateForm.name" placeholder="如 客服部第1阶段月度考核" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item span="2 s:1">
            <n-form-item label="适用范围" required>
              <n-select
                v-model:value="templateForm.scopeType"
                :options="scopeTypeOptions"
                @update:value="onScopeTypeChange"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-form-item v-if="templateForm.scopeType !== 'all'" label="适用范围取值" required>
          <n-dynamic-tags
            v-model:value="templateForm.scopeValues"
            :placeholder="templateForm.scopeType === 'dept' ? '输入部门名称后回车' : '输入班级名称后回车'"
          />
        </n-form-item>
        <n-grid :cols="3" :x-gap="16" responsive="screen" :item-responsive="true">
          <n-grid-item span="3 s:1">
            <n-form-item label="绑定阶段" required>
              <n-select v-model:value="templateForm.stage" :options="stageOptions" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item span="3 s:1">
            <n-form-item label="周期类型" required>
              <n-select v-model:value="templateForm.periodType" :options="periodTypeOptions" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item span="3 s:1">
            <n-form-item label="是否启用">
              <n-switch v-model:value="templateForm.enabled" />
            </n-form-item>
          </n-grid-item>
        </n-grid>

        <div class="items-head">
          <span class="items-title">维度权重</span>
          <span class="items-sum" :class="{ 'items-sum-bad': templateWeightSum !== 100 }">
            合计 {{ templateWeightSum }}%
          </span>
          <n-button size="small" secondary @click="addTemplateItem">
            <template #icon><n-icon :component="AddOutline" /></template>
            添加维度
          </n-button>
        </div>
        <div v-for="(item, idx) in templateForm.items" :key="idx" class="item-row">
          <n-input v-model:value="item.name" placeholder="维度名称，如 业务考核" />
          <n-input-number v-model:value="item.weight" :min="0" :max="100" :step="5" placeholder="权重" />
          <n-input v-model:value="item.target" placeholder="目标要求" />
          <n-button
            size="small"
            quaternary
            type="error"
            :aria-label="`删除维度${idx + 1}`"
            @click="templateForm.items.splice(idx, 1)"
          >
            <template #icon><n-icon :component="TrashOutline" /></template>
          </n-button>
        </div>
        <n-alert v-if="templateWeightSum !== 100" type="warning" :show-icon="true" class="weight-alert">
          权重合计 {{ templateWeightSum }}%，与 100% 不符，请调整维度权重。
        </n-alert>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="savingTemplate" @click="templateVisible = false">取消编辑</n-button>
          <n-button type="primary" :loading="savingTemplate" :disabled="!canSaveTemplate" @click="submitTemplate">
            保存模板
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 删除模板确认框（R-106 高破坏：写明后果与影响范围） -->
    <n-modal
      v-model:show="deleteTemplateVisible"
      preset="card"
      title="删除考核模板"
      :style="{ width: '520px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(320px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <p class="confirm-text">
        删除「{{ deletingTemplate?.name }}」后，该模板的 {{ deletingTemplate?.items.length || 0 }} 个维度权重与目标要求将不再用于后续考核，已产生的考核数据不会被删除。
      </p>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="!!deletingTemplateId" @click="deleteTemplateVisible = false">保留模板</n-button>
          <n-button type="error" :loading="!!deletingTemplateId" @click="confirmDeleteTemplate">删除模板</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 试用期处理弹窗（填写处理类型与备注） -->
    <n-modal
      v-model:show="decideVisible"
      preset="card"
      title="办理试用期考核"
      :style="{ width: '560px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(400px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <n-form :model="decideForm" label-placement="top">
        <n-form-item label="处理类型" required>
          <n-select v-model:value="decideForm.decision" :options="decisionOptions" placeholder="选择处理类型" />
        </n-form-item>
        <n-form-item label="处理说明">
          <n-input
            v-model:value="decideForm.note"
            type="textarea"
            :rows="3"
            placeholder="写明结论依据（可留空）"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="deciding" @click="decideVisible = false">取消办理</n-button>
          <n-button type="primary" :loading="deciding" :disabled="!decideForm.decision" @click="askConfirmDecide">
            确认处理类型
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 试用期处理确认框（R-106 高破坏：影响预览 + 明确后果） -->
    <n-modal
      v-model:show="confirmDecideVisible"
      preset="card"
      title="确认试用期处理结果"
      :style="{ width: '520px', maxWidth: '95vw' }"
      :content-style="{ height: 'min(360px, calc(88vh - 180px))', overflowY: 'auto' }"
      :mask-closable="false"
    >
      <div class="confirm-preview">
        <div class="preview-row">
          <span class="preview-label">校招生</span>
          <span class="preview-value">{{ decideRow?.personName || '—' }}</span>
        </div>
        <div class="preview-row">
          <span class="preview-label">处理类型</span>
          <span class="preview-value">{{ PROBATION_DECISION_LABEL[decideForm.decision] || decideForm.decision }}</span>
        </div>
      </div>
      <p class="confirm-text">
        确认后「{{ decideRow?.personName || '该校招生' }}」的试用期结论将更新为
        「{{ PROBATION_DECISION_LABEL[decideForm.decision] || decideForm.decision }}」，并记录处理人与处理时间，该结论会同步到转正名单。
      </p>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="deciding" @click="confirmDecideVisible = false">返回修改</n-button>
          <n-button type="error" :loading="deciding" @click="confirmDecide">确认处理</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCollapse,
  NCollapseItem,
  NDataTable,
  NDynamicTags,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInput,
  NInputNumber,
  NModal,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSkeleton,
  NSpace,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
} from 'naive-ui'
import { AddOutline, CreateOutline, RefreshOutline, TrashOutline } from '@vicons/ionicons5'
import {
  adjustMonthlyAssessment,
  checkMonthlyAssessment,
  createAssessmentTemplate,
  decideProbation,
  deleteAssessmentTemplate,
  fetchCompositeRanking,
  fetchTeacherRanking,
  listAssessmentTemplates,
  listMonthlyAssessments,
  listProbations,
  updateAssessmentTemplate,
  PERIOD_TYPE_LABEL,
  PROBATION_DECISION_LABEL,
  RANK_DIM_LABEL,
  SCOPE_TYPE_LABEL,
  STAGE_LABEL,
  type AssessmentTemplateRow,
  type CompositeRankingRow,
  type MonthlyAssessmentRow,
  type ProbationRow,
  type TeacherRankingRow,
  type TemplateItem,
} from '../../api/campusAssessment'
import { extractError, searchClassRooms, type SelectOption } from '../../utils/campus'

type AssessTab = 'monthly' | 'template' | 'ranking' | 'exam' | 'probation' | 'teacher'

/** 列表分页（R-108：渲染条目 > 200 必须分页；R-215：分页器固定在表格底部，naive 分页器即表格区最后一个子节点）。 */
const pagination = { pageSize: 50, showSizePicker: false }

const message = useMessage()
const activeTab = ref<AssessTab>('monthly')

/** 最近 12 个月的下拉选项。 */
const ymOptions = computed(() => {
  const out: { label: string; value: string }[] = []
  const now = new Date()
  for (let i = 0; i < 12; i += 1) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    out.push({ label: ym, value: ym })
  }
  return out
})

/** 班级下拉（远程搜索，首次进入时拉一页）。 */
const classOptions = ref<SelectOption[]>([])
async function loadClassOptions(keyword = '') {
  try {
    classOptions.value = await searchClassRooms(keyword)
  } catch {
    classOptions.value = []
  }
}

/* ══════════════════════ ① 月度数据 ══════════════════════ */

const monthlyRows = ref<MonthlyAssessmentRow[]>([])
const monthlyLoading = ref(false)
const monthlyError = ref('')
const monthlyErrorDetail = ref('')
const monthlyYm = ref('')
const monthlyClass = ref<string | null>(null)

const monthlyEmptyText = computed(() =>
  monthlyYm.value || monthlyClass.value ? '没有符合筛选条件的月度数据，换个筛选条件再看看' : '暂无月度考核数据',
)

async function loadMonthly() {
  monthlyLoading.value = true
  monthlyError.value = ''
  monthlyErrorDetail.value = ''
  try {
    monthlyRows.value = await listMonthlyAssessments({
      ...(monthlyYm.value ? { ym: monthlyYm.value } : {}),
      ...(monthlyClass.value ? { class: monthlyClass.value } : {}),
    })
  } catch (e: any) {
    monthlyError.value = extractError(e)
    monthlyErrorDetail.value = String(e?.message ?? e)
  } finally {
    monthlyLoading.value = false
  }
}

const monthlyColumns = [
  { title: '校招生', key: 'personName', width: 120, ellipsis: { tooltip: true } },
  { title: '班级', key: 'classRoomName', width: 140, ellipsis: { tooltip: true } },
  { title: '部门', key: 'dept', width: 160, ellipsis: { tooltip: true } },
  { title: 'KPI', key: 'kpi', width: 90, render: (row: any) => String(row.kpi ?? 0) },
  { title: '考试', key: 'exam', width: 90, render: (row: any) => String(row.exam ?? 0) },
  { title: '加减分', key: 'adjust', width: 90, render: (row: any) => (Number(row.adjust ?? 0) > 0 ? `+${row.adjust}` : String(row.adjust ?? 0)) },
  { title: '总分', key: 'total', width: 90, render: (row: any) => String(row.total ?? 0) },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: any) =>
      h(
        NTag,
        { type: row.status === 'checked' ? 'success' : 'warning', size: 'small', bordered: false },
        { default: () => (row.status === 'checked' ? '已核对' : '待核对') },
      ),
  },
  {
    title: '操作',
    key: 'actions',
    width: 190,
    fixed: 'right' as const,
    render: (row: any) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: 'primary',
              disabled: row.status === 'checked',
              onClick: () => askCheck(row),
            },
            { default: () => '核对通过' },
          ),
          h(
            NButton,
            { size: 'small', quaternary: true, type: 'primary', onClick: () => openAdjust(row) },
            { default: () => '加减分' },
          ),
        ],
      }),
  },
]
const MONTHLY_SCROLL_X = 980

/* ── 加减分 ── */
const adjustVisible = ref(false)
const adjustRow = ref<MonthlyAssessmentRow | null>(null)
const adjusting = ref(false)
const adjustForm = reactive({ adjust: 0 as number | null, reason: '' })
const canAdjust = computed(() => adjustForm.adjust !== null && !!adjustForm.reason.trim() && !adjusting.value)

function openAdjust(row: MonthlyAssessmentRow) {
  adjustRow.value = row
  adjustForm.adjust = row.adjust ?? 0
  adjustForm.reason = ''
  adjustVisible.value = true
}

async function submitAdjust() {
  if (!adjustRow.value || !canAdjust.value) return
  adjusting.value = true
  try {
    await adjustMonthlyAssessment(adjustRow.value.id, {
      adjust: Number(adjustForm.adjust ?? 0),
      reason: adjustForm.reason.trim(),
    })
    message.success('加减分已保存')
    adjustVisible.value = false
    await loadMonthly()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    adjusting.value = false
  }
}

/* ── 核对通过 ── */
const checkVisible = ref(false)
const checkRow = ref<MonthlyAssessmentRow | null>(null)
const checking = ref(false)

function askCheck(row: MonthlyAssessmentRow) {
  checkRow.value = row
  checkVisible.value = true
}

async function confirmCheck() {
  if (!checkRow.value || checking.value) return
  checking.value = true
  try {
    await checkMonthlyAssessment(checkRow.value.id)
    message.success('月度数据已核对通过')
    checkVisible.value = false
    await loadMonthly()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    checking.value = false
  }
}

/* ══════════════════════ ② 考核模板 ══════════════════════ */

const templates = ref<AssessmentTemplateRow[]>([])
const templateLoading = ref(false)
const templateError = ref('')
const templateErrorDetail = ref('')
const templateScope = ref<string>('')

const scopeFilterOptions = [
  { label: '全部模板', value: '' },
  { label: '按全部范围', value: 'all' },
  { label: '按部门', value: 'dept' },
  { label: '按班级', value: 'class' },
]
const scopeTypeOptions = [
  { label: '全部', value: 'all' },
  { label: '按部门', value: 'dept' },
  { label: '按班级', value: 'class' },
]
const stageOptions = Object.entries(STAGE_LABEL).map(([value, label]) => ({ label, value }))
const periodTypeOptions = Object.entries(PERIOD_TYPE_LABEL).map(([value, label]) => ({ label, value }))

const templateEmptyText = computed(() =>
  templateScope.value ? '没有符合该适用范围的模板，换个范围再看看' : '暂无考核模板',
)

async function loadTemplates() {
  templateLoading.value = true
  templateError.value = ''
  templateErrorDetail.value = ''
  try {
    templates.value = await listAssessmentTemplates(
      templateScope.value ? { scopeType: templateScope.value } : undefined,
    )
  } catch (e: any) {
    templateError.value = extractError(e)
    templateErrorDetail.value = String(e?.message ?? e)
  } finally {
    templateLoading.value = false
  }
}

const templateVisible = ref(false)
const editingTemplate = ref<AssessmentTemplateRow | null>(null)
const savingTemplate = ref(false)
const deletingTemplateId = ref('')

const emptyTemplateForm = () => ({
  name: '',
  scopeType: 'all',
  scopeValues: [] as string[],
  stage: 'stage1',
  periodType: 'monthly',
  enabled: true,
  items: [] as TemplateItem[],
})
const templateForm = reactive(emptyTemplateForm())

const templateWeightSum = computed(() => templateForm.items.reduce((sum, it) => sum + (Number(it.weight) || 0), 0))
const canSaveTemplate = computed(
  () =>
    !!templateForm.name.trim() &&
    (templateForm.scopeType === 'all' || templateForm.scopeValues.length > 0) &&
    templateForm.items.length > 0 &&
    !savingTemplate.value,
)

function openTemplateCreate() {
  editingTemplate.value = null
  Object.assign(templateForm, emptyTemplateForm())
  templateVisible.value = true
}

function openTemplateEdit(tpl: AssessmentTemplateRow) {
  editingTemplate.value = tpl
  Object.assign(templateForm, {
    name: tpl.name,
    scopeType: tpl.scopeType,
    scopeValues: [...tpl.scopeValues],
    stage: tpl.stage,
    periodType: tpl.periodType,
    enabled: tpl.enabled,
    items: tpl.items.map((it) => ({ name: it.name, weight: it.weight, target: it.target })),
  })
  templateVisible.value = true
}

function onScopeTypeChange() {
  templateForm.scopeValues = []
}

function addTemplateItem() {
  templateForm.items.push({ name: '', weight: 0, target: '' })
}

async function submitTemplate() {
  if (!canSaveTemplate.value) return
  savingTemplate.value = true
  const payload = {
    name: templateForm.name.trim(),
    scopeType: templateForm.scopeType,
    scopeValues: templateForm.scopeValues.map((v) => String(v).trim()).filter(Boolean),
    stage: templateForm.stage,
    periodType: templateForm.periodType,
    enabled: templateForm.enabled,
    items: templateForm.items.map((it) => ({
      name: it.name.trim(),
      weight: Number(it.weight) || 0,
      target: (it.target ?? '').trim(),
    })),
  }
  try {
    if (editingTemplate.value) {
      await updateAssessmentTemplate(editingTemplate.value.id, payload)
      message.success('考核模板已更新')
    } else {
      await createAssessmentTemplate(payload)
      message.success('考核模板已新增')
    }
    templateVisible.value = false
    await loadTemplates()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    savingTemplate.value = false
  }
}

async function toggleTemplate(tpl: AssessmentTemplateRow, enabled: boolean) {
  try {
    await updateAssessmentTemplate(tpl.id, {
      name: tpl.name,
      scopeType: tpl.scopeType,
      scopeValues: tpl.scopeValues,
      stage: tpl.stage,
      periodType: tpl.periodType,
      enabled,
      items: tpl.items.map((it) => ({ name: it.name, weight: it.weight, target: it.target })),
    })
    message.success(enabled ? '模板已启用' : '模板已停用')
    await loadTemplates()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/* ── 删除模板（高破坏：确认框 + 后果说明）── */
const deleteTemplateVisible = ref(false)
const deletingTemplate = ref<AssessmentTemplateRow | null>(null)

function askDeleteTemplate(tpl: AssessmentTemplateRow) {
  deletingTemplate.value = tpl
  deleteTemplateVisible.value = true
}

async function confirmDeleteTemplate() {
  if (!deletingTemplate.value) return
  deletingTemplateId.value = deletingTemplate.value.id
  try {
    await deleteAssessmentTemplate(deletingTemplate.value.id)
    message.success('考核模板已删除')
    deleteTemplateVisible.value = false
    await loadTemplates()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    deletingTemplateId.value = ''
  }
}

/* ══════════════════════ ③ 排名 ══════════════════════ */

const rankDim = ref<'comp' | 'kpi' | 'learn' | 'force' | 'add'>('comp')
const rankRows = ref<CompositeRankingRow[]>([])
const rankLoading = ref(false)
const rankError = ref('')
const rankErrorDetail = ref('')
const rankYm = ref('')

const rankDimOptions = Object.entries(RANK_DIM_LABEL).map(([value, label]) => ({ label, value })) as {
  label: string
  value: 'comp' | 'kpi' | 'learn' | 'force' | 'add'
}[]

const rankEmptyText = computed(() =>
  rankYm.value ? '该月份没有排名数据，换个月份再看看' : '暂无排名数据',
)

async function loadRanking() {
  rankLoading.value = true
  rankError.value = ''
  rankErrorDetail.value = ''
  try {
    rankRows.value = await fetchCompositeRanking({
      dim: rankDim.value,
      ...(rankYm.value ? { ym: rankYm.value } : {}),
    })
  } catch (e: any) {
    rankError.value = extractError(e)
    rankErrorDetail.value = String(e?.message ?? e)
  } finally {
    rankLoading.value = false
  }
}

/** 维度权重说明（逆向清单 A3：KPI 50% / 学习成长 30% / 五行五力 20%）。 */
const DIM_META: Record<string, { label: string; weight: string }> = {
  kpi: { label: 'KPI', weight: '权重 50%' },
  learn: { label: '学习成长', weight: '权重 30%' },
  force: { label: '五行五力', weight: '权重 20%' },
  add: { label: '附加分', weight: '直接计入' },
}

/**
 * 列头：主标题 + 权重小字说明。
 * ⚠️ 列头由 h() 渲染 → **不带 data-v 属性**，故样式放在非 scoped 块（ca- 前缀，页面唯一）。
 */
function dimTitle(key: string) {
  const meta = DIM_META[key]
  return () =>
    h('div', { class: 'ca-col-title' }, [
      h('span', { class: 'ca-col-name' }, `${meta.label} 实际值`),
      h('span', { class: 'ca-col-sub' }, meta.weight),
    ])
}

function dimScoreTitle(key: string) {
  const meta = DIM_META[key]
  return () =>
    h('div', { class: 'ca-col-title' }, [
      h('span', { class: 'ca-col-name' }, `${meta.label} 折算得分`),
      h('span', { class: 'ca-col-sub' }, meta.weight),
    ])
}

function dimColumn(key: 'kpi' | 'learn' | 'force' | 'add') {
  return {
    title: dimTitle(key),
    key: `actual-${key}`,
    width: 130,
    render: (row: any) => String(row?.actual?.[key] ?? 0),
  }
}

function dimScoreColumn(key: 'kpi' | 'learn' | 'force' | 'add') {
  return {
    title: dimScoreTitle(key),
    key: `score-${key}`,
    width: 140,
    render: (row: any) => String(row?.score?.[key] ?? 0),
  }
}

const rankColumns = computed(() => {
  const base = [
    { title: '排名', key: 'rank', width: 72, render: (row: any) => String(row.rank || '—') },
    { title: '校招生', key: 'personName', width: 120, ellipsis: { tooltip: true } },
    { title: '班级', key: 'classRoomName', width: 140, ellipsis: { tooltip: true } },
  ]
  const dims: ('kpi' | 'learn' | 'force' | 'add')[] =
    rankDim.value === 'comp' ? ['kpi', 'learn', 'force', 'add'] : [rankDim.value as 'kpi' | 'learn' | 'force' | 'add']
  const dimCols = dims.flatMap((d) => [dimColumn(d), dimScoreColumn(d)])
  const compCol = {
    title: () =>
      h('div', { class: 'ca-col-title' }, [
        h('span', { class: 'ca-col-name' }, '综合得分'),
        h('span', { class: 'ca-col-sub' }, 'KPI 50% + 学习 30% + 五力 20% + 附加分'),
      ]),
    key: 'comp',
    width: 120,
    render: (row: any) => String(row.comp ?? 0),
  }
  return [...base, ...dimCols, compCol]
})
const RANK_SCROLL_X = 1280

/* ══════════════════════ ④ 考试分值统计 ══════════════════════ */

/**
 * 考试分值统计：按月聚合月度考核记录里的「考试」分值。
 * ⚠️ 正式考试成绩主数据在 campus_learning 域（exam-scores/），由学习域任务实现；
 *    本页按考核域口径从月度考核记录聚合，口径与月度数据页一致。
 */
interface ExamSummaryRow {
  ym: string
  count: number
  avg: number
  max: number
  min: number
}
const examRows = ref<MonthlyAssessmentRow[]>([])
const examLoading = ref(false)
const examError = ref('')
const examYm = ref('')

const ymFilterOptions = computed(() => [{ label: '全部月份', value: '' }, ...ymOptions.value])

const examEmptyText = computed(() =>
  examYm.value ? '该月份没有考试分值记录，换个月份再看看' : '暂无考试分值记录',
)

const examFilteredRows = computed(() =>
  examYm.value ? examRows.value.filter((r) => r.ym === examYm.value) : examRows.value,
)

const examStatCards = computed(() => {
  const list = examFilteredRows.value
  const scores = list.map((r) => Number(r.exam ?? 0))
  const count = scores.length
  const sum = scores.reduce((a, b) => a + b, 0)
  return [
    { key: 'count', label: '参考人数', value: count },
    { key: 'avg', label: '平均分', value: count ? (Math.round((sum / count) * 10) / 10).toFixed(1) : '—' },
    { key: 'max', label: '最高分', value: count ? Math.max(...scores) : '—' },
    { key: 'min', label: '最低分', value: count ? Math.min(...scores) : '—' },
  ]
})

const examSummaryRows = computed<ExamSummaryRow[]>(() => {
  const groups = new Map<string, number[]>()
  for (const r of examRows.value) {
    if (!r.ym) continue
    const arr = groups.get(r.ym) ?? []
    arr.push(Number(r.exam ?? 0))
    groups.set(r.ym, arr)
  }
  return [...groups.entries()]
    .map(([ym, scores]) => ({
      ym,
      count: scores.length,
      avg: scores.length ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10 : 0,
      max: scores.length ? Math.max(...scores) : 0,
      min: scores.length ? Math.min(...scores) : 0,
    }))
    .sort((a, b) => (a.ym < b.ym ? 1 : -1))
})

async function loadExamStats() {
  examLoading.value = true
  examError.value = ''
  try {
    examRows.value = await listMonthlyAssessments()
  } catch (e: any) {
    examError.value = extractError(e)
  } finally {
    examLoading.value = false
  }
}

const examColumns = [
  { title: '月份', key: 'ym', width: 120 },
  { title: '参考人数', key: 'count', width: 110, render: (row: any) => String(row.count) },
  { title: '平均分', key: 'avg', width: 110, render: (row: any) => String(row.avg) },
  { title: '最高分', key: 'max', width: 110, render: (row: any) => String(row.max) },
  { title: '最低分', key: 'min', width: 110, render: (row: any) => String(row.min) },
]
const EXAM_SCROLL_X = 560

/* ══════════════════════ ⑤ 试用期考核 ══════════════════════ */

const probationRows = ref<ProbationRow[]>([])
const probationLoading = ref(false)
const probationError = ref('')
const probationErrorDetail = ref('')
const probationEmptyText = '暂无试用期考核记录'

async function loadProbations() {
  probationLoading.value = true
  probationError.value = ''
  probationErrorDetail.value = ''
  try {
    probationRows.value = await listProbations()
  } catch (e: any) {
    probationError.value = extractError(e)
    probationErrorDetail.value = String(e?.message ?? e)
  } finally {
    probationLoading.value = false
  }
}

const decisionOptions = Object.entries(PROBATION_DECISION_LABEL).map(([value, label]) => ({ label, value }))

const probationColumns = [
  { title: '校招生', key: 'personName', width: 120, ellipsis: { tooltip: true } },
  { title: '班级', key: 'classRoomName', width: 140, ellipsis: { tooltip: true } },
  {
    title: '定岗部门·岗位',
    key: 'dept',
    width: 200,
    ellipsis: { tooltip: true },
    render: (row: any) => [row.dept, row.post].filter(Boolean).join(' · ') || '—',
  },
  {
    title: '轮岗阶段考核(综合)',
    key: 'rotationResult',
    width: 160,
    render: (row: any) => (row.rotationResult ? String(row.rotationResult) : '—'),
  },
  {
    title: '定岗3个月考核',
    key: 'p3m',
    width: 160,
    render: (row: any) =>
      [row.p3mKpi === null ? null : `KPI ${row.p3mKpi}`, row.p3mCompetency].filter(Boolean).join(' · ') || '—',
  },
  {
    title: '转正结果',
    key: 'decision',
    width: 120,
    render: (row: any) =>
      row.decision
        ? h(
            NTag,
            { type: row.decision === '转正' ? 'success' : row.decision === '不合格' ? 'error' : 'warning', size: 'small', bordered: false },
            { default: () => row.decision },
          )
        : '—',
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
    render: (row: any) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(
            NButton,
            { size: 'small', quaternary: true, type: 'primary', onClick: () => openDecide(row) },
            { default: () => '办理转正' },
          ),
        ],
      }),
  },
]
const PROBATION_SCROLL_X = 900

/* ── 试用期处理（表单 → 确认框 → 执行）── */
const decideVisible = ref(false)
const confirmDecideVisible = ref(false)
const deciding = ref(false)
const decideRow = ref<ProbationRow | null>(null)
const decideForm = reactive({ decision: '', note: '' })

function openDecide(row: ProbationRow) {
  decideRow.value = row
  decideForm.decision = row.decision || ''
  decideForm.note = ''
  decideVisible.value = true
}

function askConfirmDecide() {
  if (!decideForm.decision) return
  decideVisible.value = false
  confirmDecideVisible.value = true
}

async function confirmDecide() {
  if (!decideRow.value || !decideForm.decision || deciding.value) return
  deciding.value = true
  try {
    await decideProbation(decideRow.value.id, { decision: decideForm.decision, note: decideForm.note.trim() })
    message.success('试用期处理结果已更新')
    confirmDecideVisible.value = false
    await loadProbations()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    deciding.value = false
  }
}

/* ══════════════════════ ⑥ 班主任排名 ══════════════════════ */

const teacherRows = ref<TeacherRankingRow[]>([])
const teacherLoading = ref(false)
const teacherError = ref('')
const teacherErrorDetail = ref('')
const teacherYm = ref('')
const teacherEmptyText = computed(() =>
  teacherYm.value ? '该月份没有班主任排名数据，换个月份再看看' : '暂无班主任排名数据',
)

async function loadTeachers() {
  teacherLoading.value = true
  teacherError.value = ''
  teacherErrorDetail.value = ''
  try {
    teacherRows.value = await fetchTeacherRanking(teacherYm.value ? { ym: teacherYm.value } : undefined)
  } catch (e: any) {
    teacherError.value = extractError(e)
    teacherErrorDetail.value = String(e?.message ?? e)
  } finally {
    teacherLoading.value = false
  }
}

const teacherColumns = [
  { title: '排名', key: 'rank', width: 72, render: (row: any) => String(row.rank || '—') },
  { title: '班主任', key: 'teacherName', width: 120, ellipsis: { tooltip: true } },
  { title: '分管班级', key: 'classRooms', width: 200, ellipsis: { tooltip: true }, render: (row: any) => row.classRooms || '—' },
  { title: '学生数', key: 'studentCount', width: 100, render: (row: any) => String(row.studentCount ?? 0) },
  { title: '班级累计均分', key: 'avgTotal', width: 130, render: (row: any) => String(row.avgTotal ?? 0) },
  { title: '综合排名均值', key: 'rankAvgTotal', width: 130, render: (row: any) => String(row.rankAvg?.total ?? 0) },
  { title: 'KPI排名均值', key: 'rankAvgKpi', width: 130, render: (row: any) => String(row.rankAvg?.kpi ?? 0) },
  { title: '考试排名均值', key: 'rankAvgExam', width: 130, render: (row: any) => String(row.rankAvg?.exam ?? 0) },
  { title: '学习排名均值', key: 'rankAvgLearn', width: 130, render: (row: any) => String(row.rankAvg?.learn ?? 0) },
  { title: '考勤排名均值', key: 'rankAvgAttend', width: 130, render: (row: any) => String(row.rankAvg?.attend ?? 0) },
]
const TEACHER_SCROLL_X = 1250

/* ══════════════════════ 页签与通用 ══════════════════════ */

function onTabChange(tab: AssessTab) {
  if (tab === 'template' && !templates.value.length) loadTemplates()
  if (tab === 'ranking' && !rankRows.value.length) loadRanking()
  if (tab === 'exam' && !examRows.value.length) loadExamStats()
  if (tab === 'probation' && !probationRows.value.length) loadProbations()
  if (tab === 'teacher' && !teacherRows.value.length) loadTeachers()
}

async function copyDetail(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制错误信息')
  } catch {
    message.warning('浏览器不允许复制，请手动选中详情文本')
  }
}

onMounted(() => {
  monthlyYm.value = ymOptions.value[0]?.value ?? ''
  loadClassOptions()
  loadMonthly()
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
.ca-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.ca-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
}
.ca-tabs :deep(.n-tab-pane) {
  box-sizing: border-box;
  height: 100%;
  padding: var(--space-2) 0 0 0;
  display: flex;
  flex-direction: column;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  padding-bottom: var(--space-2);
  flex-wrap: wrap;
}
.field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.field-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  white-space: nowrap;
}
.spacer {
  flex: 1;
}
.skeleton-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: var(--space-4);
  background: var(--surface);
  border-radius: var(--radius-md);
}
.load-error {
  flex-shrink: 0;
  margin-bottom: var(--space-2);
}
.error-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.error-collapse {
  margin-top: var(--space-2);
}
.error-detail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: var(--text-small);
  color: var(--ink-soft);
  overflow-wrap: anywhere;
}
/* 统计卡（自适应栅格） */
.stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--col-min), 1fr));
  gap: var(--space-2);
  flex-shrink: 0;
  margin-bottom: var(--space-2);
}
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
}
.stat-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  line-height: 1.5;
}
.stat-value {
  font-size: var(--text-h2);
  font-weight: 600;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}
/* 模板卡片 */
.template-grid {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--col-min), 1fr));
  gap: var(--space-2);
  align-content: start;
}
.template-empty {
  grid-column: 1 / -1;
}
.template-card {
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.card-title {
  font-size: var(--text-h4);
  font-weight: 600;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
.card-scope {
  font-size: var(--text-small);
  color: var(--ink-soft);
  overflow-wrap: anywhere;
}
.weight-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-small);
}
.weight-table th,
.weight-table td {
  text-align: left;
  padding: var(--space-1) var(--space-2);
  border-bottom: 1px solid var(--border-hairline);
  vertical-align: top;
}
.weight-table th {
  color: var(--ink-soft);
  font-weight: 500;
}
.num-cell {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.target-cell {
  overflow-wrap: anywhere;
}
.weight-alert {
  font-size: var(--text-small);
}
.card-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
/* 模板表单里的维度行 */
.items-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.items-title {
  font-size: var(--text-h4);
  font-weight: 600;
  line-height: 1.3;
}
.items-sum {
  font-size: var(--text-small);
  color: var(--ink-soft);
  font-variant-numeric: tabular-nums;
}
.items-sum-bad {
  color: var(--c-warning-deep);
}
.item-row {
  display: grid;
  grid-template-columns: 1fr 120px 1fr 40px;
  gap: var(--space-2);
  align-items: center;
  margin-bottom: var(--space-2);
}
/* 图标按钮命中区 ≥ 44×44px（R-102）：删除维度是纯图标按钮，视觉小但命中区必须够大 */
.item-row :deep(.n-button) {
  min-width: 44px;
  min-height: 44px;
}
.confirm-text {
  margin: 0;
  font-size: var(--text-body);
  line-height: 1.6;
  color: var(--ink);
  overflow-wrap: anywhere;
}
.confirm-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-2);
  background: var(--surface);
}
.preview-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}
.preview-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
}
.preview-value {
  font-size: var(--text-body);
  font-weight: 600;
  overflow-wrap: anywhere;
}
/* 动态数字防抖动（作用于 naive 自身 DOM，不涉及 h() 渲染节点） */
.table-wrap :deep(.n-data-table-td) {
  font-variant-numeric: tabular-nums;
}
</style>

<!--
  列头（实际值 / 折算得分 + 权重小字）由 h() 渲染 → 元素不带 data-v 属性，
  scoped 规则不命中（R-225）。故这部分样式放在**非 scoped** 块，
  类名统一用 ca- 前缀（页面唯一），避免污染其它页面。
-->
<style>
.ca-col-title {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  line-height: 1.3;
}
.ca-col-name {
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--ink);
}
.ca-col-sub {
  font-size: var(--text-meta);
  font-weight: 400;
  color: var(--ink-faint);
}
</style>
