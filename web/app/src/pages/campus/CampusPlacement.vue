<template>
  <div class="page-container">
    <div class="page-body">
      <n-tabs v-model:value="activeTab" type="line" class="page-tabs" @update:value="onTabChange">
        <n-tab-pane name="pool" tab="岗位池" />
        <n-tab-pane name="review" tab="需求审核" />
        <n-tab-pane name="push" tab="志愿推送" />
        <n-tab-pane name="market" tab="人才市场" />
        <n-tab-pane name="progress" tab="双选进度" />
        <n-tab-pane name="perf" tab="绩效展示" />
      </n-tabs>

      <!-- ① 岗位池 -->
      <template v-if="activeTab === 'pool'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">岗位</span>
            <n-input
              v-model:value="poolSearch"
              aria-label="岗位名称"
              class="toolbar-search"
              placeholder="搜索岗位名称或用人部门"
              clearable
              @keyup.enter="loadDemands"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
          </div>
          <div class="spacer"></div>
          <n-button :loading="demandLoading" @click="loadDemands">查询岗位</n-button>
          <n-button @click="openDemandCreate">申请发布需求</n-button>
          <n-button type="primary" @click="openDemandPublish">发布岗位</n-button>
        </div>

        <div v-if="demandError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">岗位池没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，你填的需求内容仍保留在本页，不会丢失。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ demandError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(demandError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="demandLoading" @click="loadDemands">重新加载</n-button>
        </div>

        <div class="card-area">
          <n-skeleton v-if="demandLoading && !demandRows.length" :repeat="4" :x-gap="16" />
          <template v-else-if="demandRows.length">
            <div class="card-grid">
              <n-card v-for="d in demandRows" :key="d.id" size="small" :bordered="true" class="demand-card">
                <div class="card-title" :title="d.name">{{ d.name }}</div>
                <div class="card-line">
                  <span class="card-label">用人部门</span>
                  <span class="card-value" :title="d.dept">{{ d.dept || '—' }}</span>
                </div>
                <div class="card-line">
                  <span class="card-label">业务部门</span>
                  <span class="card-value" :title="d.businessDept">{{ d.businessDept || '—' }}</span>
                </div>
                <div class="card-line">
                  <span class="card-label">需求数量</span>
                  <span class="card-value num">{{ d.headcount ?? 0 }} 人</span>
                </div>
                <div class="card-line">
                  <span class="card-label">负责BP</span>
                  <span class="card-value" :title="d.bpName">{{ d.bpName || '—' }}</span>
                </div>
                <div class="card-line">
                  <span class="card-label">申请人</span>
                  <span class="card-value" :title="d.submitterName">{{ d.submitterName || '—' }}</span>
                </div>
                <div class="card-line">
                  <span class="card-label">状态</span>
                  <span class="card-value">
                    <n-tag :type="needStatusType(d.needStatus)" size="small">{{ d.needStatus || '待审核' }}</n-tag>
                  </span>
                </div>
                <div class="card-line">
                  <span class="card-label">报名开放</span>
                  <span class="card-value">{{ openState(d).text }}</span>
                </div>
                <div class="card-line">
                  <span class="card-label">发布范围</span>
                  <span class="card-value">{{ scopeLabel(d) }}</span>
                </div>
                <template #footer>
                  <div class="card-actions">
                    <n-button size="small" quaternary type="primary" @click="openDemandEdit(d)">编辑需求</n-button>
                    <n-button size="small" quaternary type="primary" @click="goReview(d)">审核需求</n-button>
                    <n-button size="small" quaternary type="primary" @click="toggleOpen(d)">
                      {{ d.openEnabled ? '关闭报名' : '开启报名' }}
                    </n-button>
                    <n-button size="small" quaternary type="error" @click="withdrawDemand(d)">撤回需求</n-button>
                  </div>
                </template>
              </n-card>
            </div>
          </template>
          <n-empty v-else :description="demandEmptyText" size="small">
            <template #extra>
              <n-button v-if="poolHasFilter" size="small" @click="poolSearch = ''; loadDemands()">清空筛选</n-button>
            </template>
          </n-empty>
        </div>
      </template>

      <!-- ② 需求审核 -->
      <template v-if="activeTab === 'review'">
        <div class="toolbar">
          <div class="toolbar-tip">仅展示待审核的岗位需求</div>
          <div class="spacer"></div>
          <n-button :loading="demandLoading" @click="loadDemands">刷新待审</n-button>
        </div>

        <div v-if="demandError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">待审核需求没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，审核队列仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ demandError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(demandError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="demandLoading" @click="loadDemands">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="demandLoading && !reviewRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="reviewColumns"
            :data="reviewRows"
            :loading="demandLoading"
            :bordered="false"
            :scroll-x="REVIEW_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PositionDemand) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty description="暂无数据" size="small" />
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ③ 志愿推送 -->
      <template v-if="activeTab === 'push'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">校招批次</span>
            <!-- 字段级校验（R-221）：批次没选时错误就近显示在选择框下方 -->
            <n-form-item
              :show-label="false"
              :validation-status="pushBatchError ? 'error' : undefined"
              :show-feedback="Boolean(pushBatchError)"
              class="filter-field"
            >
              <n-select
                ref="pushBatchRef"
                v-model:value="pushBatch"
                aria-label="校招批次"
                class="toolbar-select-wide"
                :options="batchOptions"
                placeholder="请选择校招批次"
                filterable
                tag
                @update:value="onPushBatchChange"
              />
              <template #feedback>
                <span class="field-error">
                  <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                  {{ pushBatchError }}
                </span>
              </template>
            </n-form-item>
          </div>
          <n-tag :type="flowStarted ? 'success' : 'warning'" size="small">
            {{ flowStarted ? '撮合已启动' : '撮合未启动' }}
          </n-tag>
          <div class="spacer"></div>
          <n-button :loading="appLoading" @click="loadPushApplications">刷新志愿</n-button>
          <n-button type="primary" :disabled="flowStarted || !pushBatch" @click="askStartFlow">启动撮合</n-button>
        </div>

        <div v-if="appError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">志愿推送列表没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，已填报的志愿仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ appError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(appError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="appLoading" @click="loadPushApplications">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="appLoading && !pushRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="pushColumns"
            :data="pushRows"
            :loading="appLoading"
            :bordered="false"
            :scroll-x="PUSH_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PositionApplication) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="pushEmptyText" size="small">
                <template #extra>
                  <n-button v-if="pushBatch" size="small" @click="pushBatch = null; loadPushApplications()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ④ 人才市场 -->
      <template v-if="activeTab === 'market'">
        <div class="toolbar">
          <div class="toolbar-tip">两志愿均未被选择的校招生在这里等待全员 BP 采纳</div>
          <div class="spacer"></div>
          <n-button :loading="appLoading" @click="loadMarketApplications">刷新人才</n-button>
        </div>

        <div v-if="appError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">人才市场没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，人才市场名单仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ appError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(appError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="appLoading" @click="loadMarketApplications">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="appLoading && !marketRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="marketColumns"
            :data="marketRows"
            :loading="appLoading"
            :bordered="false"
            :scroll-x="MARKET_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PositionApplication) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty description="暂无数据" size="small" />
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ⑤ 双选进度 -->
      <template v-if="activeTab === 'progress'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">校招批次</span>
            <n-select
              v-model:value="progressBatch"
              aria-label="校招批次"
              class="toolbar-select-wide"
              :options="batchOptions"
              placeholder="全部批次"
              clearable
              @update:value="loadProgressApplications"
            />
          </div>
          <div class="spacer"></div>
          <n-button :loading="appLoading" @click="loadProgressApplications">刷新进度</n-button>
        </div>

        <div v-if="appError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">双选进度没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，双选进度仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ appError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(appError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="appLoading" @click="loadProgressApplications">重新加载</n-button>
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="appLoading && !progressRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="progressColumns"
            :data="progressRows"
            :loading="appLoading"
            :bordered="false"
            :scroll-x="PROGRESS_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PlacementProgressRow) => row.personId"
            flex-height
          >
            <template #empty>
              <n-empty description="暂无数据" size="small" />
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- ⑥ 绩效展示 -->
      <template v-if="activeTab === 'perf'">
        <div class="toolbar">
          <div class="filter">
            <span class="filter-label">校招生</span>
            <n-input
              v-model:value="perfSearch"
              aria-label="校招生姓名"
              class="toolbar-search"
              placeholder="搜索校招生姓名"
              clearable
              @keyup.enter="loadPerf"
            >
              <template #prefix><n-icon :component="SearchOutline" /></template>
            </n-input>
          </div>
          <div class="spacer"></div>
          <n-button :loading="perfLoading" @click="loadPerf">刷新名单</n-button>
        </div>

        <div v-if="perfError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">绩效名单没有加载出来</div>
            <div class="error-state-desc">
              没有连上服务器，绩效名单仍保存在服务器上。重试一次即可恢复。
            </div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ perfError }}</pre>
              <n-button size="tiny" quaternary @click="copyText(perfError)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="perfLoading" @click="loadPerf">重新加载</n-button>
        </div>

        <div class="toolbar-note">
          累计均分、月度趋势、标签与推介由考核域提供，考核域接口尚未接入本页，暂以「—」占位。
        </div>

        <div class="table-wrap">
          <n-skeleton v-if="perfLoading && !perfRows.length" :repeat="6" :x-gap="12" />
          <n-data-table
            v-else
            :columns="perfColumns"
            :data="perfRows"
            :loading="perfLoading"
            :bordered="false"
            :scroll-x="PERF_SCROLL_X"
            :pagination="{ pageSize: 50, showSizePicker: false }"
            :row-key="(row: PerfRow) => row.id"
            flex-height
          >
            <template #empty>
              <n-empty :description="perfEmptyText" size="small">
                <template #extra>
                  <n-button v-if="perfSearch" size="small" @click="perfSearch = ''; loadPerf()">清空筛选</n-button>
                </template>
              </n-empty>
            </template>
          </n-data-table>
        </div>
      </template>

      <!-- 岗位需求 新增 / 编辑 弹窗 -->
      <n-modal
        v-model:show="demandFormVisible"
        preset="card"
        :title="demandEditing ? '编辑岗位需求' : '申请发布需求'"
        :style="{ width: '760px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(620px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <!-- 写入失败三段式（R-203）：① 人话标题 ② 数据安全说明 ③ 折叠详情 + 恢复动作 -->
        <div v-if="demandWriteError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">{{ demandWriteError.title }}</div>
            <div class="error-state-desc">{{ demandWriteError.safe }}</div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ demandWriteError.detail }}</pre>
              <n-button size="tiny" quaternary @click="copyText(demandWriteError.detail)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="demandSaving" :disabled="demandSaving" @click="saveDemand">
            重新保存需求
          </n-button>
        </div>

        <n-form :model="demandForm" label-placement="top">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <!-- 字段级校验（R-221）：错误就近显示，图标 + 文字双通道，不只靠颜色 -->
              <n-form-item
                label="岗位名称"
                required
                :validation-status="demandErrors.name ? 'error' : undefined"
                :show-feedback="Boolean(demandErrors.name)"
              >
                <n-input
                  ref="demandNameRef"
                  v-model:value="demandForm.name"
                  placeholder="请输入岗位名称"
                  @update:value="clearDemandError('name')"
                />
                <template #feedback>
                  <span class="field-error">
                    <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                    {{ demandErrors.name }}
                  </span>
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="用人部门"
                required
                :validation-status="demandErrors.dept ? 'error' : undefined"
                :show-feedback="Boolean(demandErrors.dept)"
              >
                <n-input
                  ref="demandDeptRef"
                  v-model:value="demandForm.dept"
                  placeholder="请输入用人部门"
                  @update:value="clearDemandError('dept')"
                />
                <template #feedback>
                  <span class="field-error">
                    <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                    {{ demandErrors.dept }}
                  </span>
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="业务部门"
                required
                :validation-status="demandErrors.businessDept ? 'error' : undefined"
                :show-feedback="Boolean(demandErrors.businessDept)"
              >
                <n-input
                  ref="demandBusinessDeptRef"
                  v-model:value="demandForm.businessDept"
                  placeholder="请输入业务部门"
                  @update:value="clearDemandError('businessDept')"
                />
                <template #feedback>
                  <span class="field-error">
                    <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                    {{ demandErrors.businessDept }}
                  </span>
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="需求数量"
                required
                :validation-status="demandErrors.headcount ? 'error' : undefined"
                :show-feedback="Boolean(demandErrors.headcount)"
              >
                <n-input-number
                  ref="demandHeadcountRef"
                  v-model:value="demandForm.headcount"
                  :min="1"
                  style="width: 100%"
                  @update:value="clearDemandError('headcount')"
                />
                <template #feedback>
                  <span class="field-error">
                    <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                    {{ demandErrors.headcount }}
                  </span>
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="需求时间">
                <n-input v-model:value="demandForm.needTime" placeholder="如 2026 年 9 月到岗" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="工作地点">
                <n-input v-model:value="demandForm.workLocation" placeholder="请输入工作地点" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="负责BP">
                <n-input v-model:value="demandForm.bpName" placeholder="业务BP姓名" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item
                label="发布范围"
                required
                :validation-status="demandErrors.scopeType ? 'error' : undefined"
                :show-feedback="Boolean(demandErrors.scopeType)"
              >
                <n-select
                  ref="demandScopeTypeRef"
                  v-model:value="demandForm.scopeType"
                  :options="scopeTypeOptions"
                  placeholder="请选择发布范围"
                  @update:value="clearDemandError('scopeType')"
                />
                <template #feedback>
                  <span class="field-error">
                    <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                    {{ demandErrors.scopeType }}
                  </span>
                </template>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="面向批次">
                <n-input v-model:value="demandForm.scopeBatch" placeholder="如 2026 秋招" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="开放报名">
                <n-switch v-model:value="demandForm.openEnabled">
                  <template #checked>已开放</template>
                  <template #unchecked>未开放</template>
                </n-switch>
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="报名窗口">
                <n-space :wrap="false" :size="8" style="width: 100%">
                  <n-date-picker v-model:value="demandForm.openStartTs" type="date" style="flex: 1" />
                  <n-date-picker v-model:value="demandForm.openEndTs" type="date" style="flex: 1" />
                </n-space>
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-form-item
            label="需求描述"
            required
            :validation-status="demandErrors.needDesc ? 'error' : undefined"
            :show-feedback="Boolean(demandErrors.needDesc)"
          >
            <n-input
              ref="demandNeedDescRef"
              v-model:value="demandForm.needDesc"
              type="textarea"
              placeholder="岗位要做什么、期望新人具备什么能力"
              @update:value="clearDemandError('needDesc')"
            />
            <template #feedback>
              <span class="field-error">
                <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                {{ demandErrors.needDesc }}
              </span>
            </template>
          </n-form-item>
          <n-form-item label="业务介绍">
            <n-input v-model:value="demandForm.bizIntro" type="textarea" placeholder="业务条线介绍" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="demandFormVisible = false">{{ demandEditing ? '取消编辑' : '取消办理' }}</n-button>
            <n-button type="primary" :loading="demandSaving" :disabled="demandSaving" @click="saveDemand">保存需求</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 驳回原因 弹窗 -->
      <n-modal
        v-model:show="rejectVisible"
        preset="card"
        title="驳回岗位需求"
        :style="{ width: '560px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(360px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <!-- 写入失败三段式（R-203）：① 人话标题 ② 数据安全说明 ③ 折叠详情 + 恢复动作 -->
        <div v-if="rejectWriteError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">{{ rejectWriteError.title }}</div>
            <div class="error-state-desc">{{ rejectWriteError.safe }}</div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ rejectWriteError.detail }}</pre>
              <n-button size="tiny" quaternary @click="copyText(rejectWriteError.detail)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="rejecting" :disabled="rejecting" @click="submitReject">
            重新驳回需求
          </n-button>
        </div>

        <n-form :model="rejectForm" label-placement="top">
          <!-- 字段级校验（R-221）：错误就近显示，图标 + 文字双通道，不只靠颜色 -->
          <n-form-item
            label="驳回原因"
            required
            :validation-status="rejectErrors.note ? 'error' : undefined"
            :show-feedback="Boolean(rejectErrors.note)"
          >
            <n-input
              ref="rejectNoteRef"
              v-model:value="rejectForm.note"
              type="textarea"
              placeholder="写明驳回原因，申请人会看到这段说明"
              @update:value="clearRejectError('note')"
            />
            <template #feedback>
              <span class="field-error">
                <n-icon :component="AlertCircleOutline" aria-hidden="true" />
                {{ rejectErrors.note }}
              </span>
            </template>
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="rejectVisible = false">取消驳回</n-button>
            <n-button type="primary" :loading="rejecting" :disabled="rejecting" @click="submitReject">驳回需求</n-button>
          </div>
        </template>
      </n-modal>

      <!-- 通用确认框（高影响操作：启动撮合 / 录取 / 放弃 / 采纳） -->
      <n-modal
        v-model:show="confirmVisible"
        preset="card"
        :title="confirmTitle"
        :style="{ width: '560px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(320px, calc(88vh - 180px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <!-- 写入失败三段式（R-203）：① 人话标题 ② 数据安全说明 ③ 折叠详情 + 恢复动作 -->
        <div v-if="confirmWriteError" class="error-state" role="alert">
          <n-icon class="error-state-icon" :component="AlertCircleOutline" aria-hidden="true" />
          <div class="error-state-body">
            <div class="error-state-title">{{ confirmWriteError.title }}</div>
            <div class="error-state-desc">{{ confirmWriteError.safe }}</div>
            <details class="error-state-detail">
              <summary>查看详情</summary>
              <pre class="error-state-code">{{ confirmWriteError.detail }}</pre>
              <n-button size="tiny" quaternary @click="copyText(confirmWriteError.detail)">复制错误信息</n-button>
            </details>
          </div>
          <n-button size="small" type="primary" ghost :loading="confirmLoading" :disabled="confirmLoading" @click="confirmSubmit">
            重新{{ confirmActionLabel }}
          </n-button>
        </div>

        <div class="confirm-body">{{ confirmText }}</div>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="confirmVisible = false">{{ confirmCancelText }}</n-button>
            <n-button type="primary" :loading="confirmLoading" :disabled="confirmLoading" @click="confirmSubmit">
              {{ confirmOkText }}
            </n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, nextTick, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NCard,
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
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  useNotification,
} from 'naive-ui'
import { AlertCircleOutline, SearchOutline } from '@vicons/ionicons5'
import {
  acceptApplication,
  assignApplication,
  createPositionDemand,
  createSelectionFlow,
  listApplications,
  listPositionDemands,
  listSelectionFlows,
  openPositionDemand,
  pushApplication,
  rejectApplication,
  reviewPositionDemand,
  startSelectionFlow,
  updatePositionDemand,
  withdrawPositionDemand,
  type PositionApplication,
  type PositionDemand,
  type SelectionFlow,
} from '../../api/campusPlacement'
import { listPersons, type Person } from '../../api/campusControl'
import { buildWriteError, extractError, type WriteErrorInfo } from '../../utils/campus'
import { useFormDraft } from '../../composables/useFormDraft'

const message = useMessage()
const notification = useNotification()

type TabKey = 'pool' | 'review' | 'push' | 'market' | 'progress' | 'perf'
const activeTab = ref<TabKey>('pool')

const SCOPE_TYPE_OPTIONS = [
  { label: '全部校招生', value: 'all' },
  { label: '按校招批次', value: 'batch' },
  { label: '按意向部门', value: 'intentDept' },
]
const scopeTypeOptions = SCOPE_TYPE_OPTIONS

/* ───────────────────────── 通用工具 ───────────────────────── */

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

/** 岗位需求审核状态 → 徽标类型（不只靠颜色，文案本身即状态）。 */
function needStatusType(status?: string) {
  const map: Record<string, any> = { 待审核: 'warning', 已通过: 'success', 已驳回: 'error', 已发布: 'info' }
  return map[status || ''] || 'default'
}

/** 发布范围文案。 */
function scopeLabel(d: PositionDemand) {
  if (d.scopeType === 'batch') return `按批次：${d.scopeBatch || '未指定'}`
  if (d.scopeType === 'intentDept') return '按意向部门'
  return '全部校招生'
}

/**
 * 岗位开放判定顺序（逆向清单 §4.3）：审核状态 → 开放开关 → 窗口期。
 * 返回一段人话，说明当前能不能报名。
 */
function openState(d: PositionDemand) {
  if (d.needStatus !== '已通过' && d.needStatus !== '已发布') {
    return { text: '审核未通过，暂不能报名', ok: false }
  }
  if (!d.openEnabled) return { text: '未开放报名', ok: false }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  if (d.openStart) {
    const s = new Date(d.openStart)
    s.setHours(0, 0, 0, 0)
    if (s.getTime() > today.getTime()) return { text: '报名窗口尚未开始', ok: false }
  }
  if (d.openEnd) {
    const e = new Date(d.openEnd)
    e.setHours(23, 59, 59, 999)
    if (e.getTime() < today.getTime()) return { text: '报名窗口已结束', ok: false }
  }
  return { text: '报名开放中', ok: true }
}

/* ───────────────────────── 通用确认框 ───────────────────────── */

const confirmVisible = ref(false)
const confirmTitle = ref('')
const confirmText = ref('')
const confirmOkText = ref('确认操作')
const confirmCancelText = ref('暂不操作')
const confirmLoading = ref(false)
const confirmAction = ref<null | (() => Promise<void>)>(null)
/** 失败提示里的动宾短语（如「录取志愿」），供 R-203 三段式标题使用。 */
const confirmActionLabel = ref('执行操作')
// 写入失败三段式（R-203）。
const confirmWriteError = ref<WriteErrorInfo | null>(null)

function askConfirm(
  title: string,
  text: string,
  okText: string,
  action: () => Promise<void>,
  actionLabel?: string,
) {
  confirmTitle.value = title
  confirmText.value = text
  confirmOkText.value = okText
  confirmCancelText.value = '暂不操作'
  confirmAction.value = action
  confirmActionLabel.value = actionLabel || okText
  confirmWriteError.value = null
  confirmVisible.value = true
}

async function confirmSubmit() {
  const action = confirmAction.value
  if (!action) return
  confirmLoading.value = true
  confirmWriteError.value = null
  try {
    await action()
    confirmVisible.value = false
  } catch (e: any) {
    // 写入失败 → 三段式（R-203），不再只弹一条原始报文 toast。
    confirmWriteError.value = buildWriteError(e, { action: confirmActionLabel.value })
  } finally {
    confirmLoading.value = false
  }
}

/* ───────────────────────── ① 岗位池 ───────────────────────── */

const demandRows = ref<PositionDemand[]>([])
const demandLoading = ref(false)
const demandError = ref('')
const poolSearch = ref('')

const poolHasFilter = computed(() => Boolean(poolSearch.value.trim()))
const demandEmptyText = computed(() => (poolHasFilter.value ? '没有符合筛选条件的岗位' : '暂无数据'))

async function loadDemands() {
  demandLoading.value = true
  demandError.value = ''
  try {
    const kw = poolSearch.value.trim()
    const rows = await listPositionDemands({ search: kw || undefined })
    demandRows.value = kw
      ? rows.filter((r) => `${r.name}${r.dept}`.includes(kw))
      : rows
  } catch (e: any) {
    demandError.value = extractError(e)
    demandRows.value = []
  } finally {
    demandLoading.value = false
  }
}

const reviewRows = computed(() => demandRows.value.filter((d) => d.needStatus === '待审核'))

/* ── 岗位需求 新增 / 编辑 ── */
const demandFormVisible = ref(false)
const demandSaving = ref(false)
const demandEditing = ref<PositionDemand | null>(null)
const demandForm = reactive({
  name: '',
  dept: '',
  businessDept: '',
  headcount: 1,
  needTime: '',
  workLocation: '',
  bpName: '',
  scopeType: 'all',
  scopeBatch: '',
  openEnabled: false,
  openStartTs: null as number | null,
  openEndTs: null as number | null,
  needDesc: '',
  bizIntro: '',
})

// P0-1 草稿自动保存（R-105）：需求申请 13 项，人工填写耗时 > 1 分钟。
// 编辑态关闭草稿，避免草稿覆盖真实 row 数据。
const demandDraft = useFormDraft('campus-placement-demand', demandForm, {
  enabled: () => !demandEditing.value,
})

// 字段级校验状态（R-221）。
const demandErrors = reactive({
  name: '',
  dept: '',
  businessDept: '',
  headcount: '',
  scopeType: '',
  needDesc: '',
})
const demandNameRef = ref<any>(null)
const demandDeptRef = ref<any>(null)
const demandBusinessDeptRef = ref<any>(null)
const demandHeadcountRef = ref<any>(null)
const demandScopeTypeRef = ref<any>(null)
const demandNeedDescRef = ref<any>(null)

// 写入失败三段式（R-203）。
const demandWriteError = ref<WriteErrorInfo | null>(null)

function clearDemandError(field: keyof typeof demandErrors) {
  demandErrors[field] = ''
}

/** 聚焦第一个出错字段（R-221）。 */
async function focusFirstInvalid(pairs: Array<[string, { value: any }]>) {
  await nextTick()
  for (const [msg, r] of pairs) {
    if (!msg) continue
    const inst = r?.value
    if (inst && typeof inst.focus === 'function') {
      inst.focus()
      return
    }
  }
}

function toDateStr(ts: number | null) {
  if (!ts) return null
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function resetDemandForm() {
  Object.assign(demandForm, {
    name: '',
    dept: '',
    businessDept: '',
    headcount: 1,
    needTime: '',
    workLocation: '',
    bpName: '',
    scopeType: 'all',
    scopeBatch: '',
    openEnabled: false,
    openStartTs: null,
    openEndTs: null,
    needDesc: '',
    bizIntro: '',
  })
}

function openDemandCreate() {
  demandErrors.name = ''
  demandErrors.dept = ''
  demandErrors.businessDept = ''
  demandErrors.headcount = ''
  demandErrors.scopeType = ''
  demandErrors.needDesc = ''
  demandWriteError.value = null
  demandEditing.value = null
  // 先探测草稿再决定要不要重置表单：直接重置会把上次草稿内容抹掉（R-105）。
  if (demandDraft.probe()) {
    demandDraft.restore()
    if (
      demandForm.name.trim() ||
      demandForm.dept.trim() ||
      demandForm.businessDept.trim() ||
      demandForm.needDesc.trim()
    ) {
      notification.create({
        content: '已恢复上次填写的内容',
        duration: 8000,
        keepAliveOnHover: true,
        action: () =>
          h(
            NButton,
            { text: true, type: 'primary', onClick: clearDemandDraft },
            { default: () => '清空' },
          ),
      })
    } else {
      // 空草稿（只打开过弹窗没填写）→ 直接丢弃，不给用户假提示。
      demandDraft.clear()
      resetDemandForm()
    }
  } else {
    resetDemandForm()
  }
  demandFormVisible.value = true
}

/** 「清空」出口：清掉草稿并把恢复出来的内容一并清掉。 */
function clearDemandDraft() {
  demandDraft.clear()
  resetDemandForm()
}

/** 管理员「发布岗位」：默认已通过审核且开放报名。 */
function openDemandPublish() {
  openDemandCreate()
  demandForm.openEnabled = true
}

function openDemandEdit(row: PositionDemand) {
  Object.assign(demandForm, {
    name: row.name || '',
    dept: row.dept || '',
    businessDept: row.businessDept || '',
    headcount: row.headcount ?? 1,
    needTime: row.needTime || '',
    workLocation: row.workLocation || '',
    bpName: row.bpName || '',
    scopeType: row.scopeType || 'all',
    scopeBatch: row.scopeBatch || '',
    openEnabled: Boolean(row.openEnabled),
    openStartTs: row.openStart ? new Date(row.openStart).getTime() : null,
    openEndTs: row.openEnd ? new Date(row.openEnd).getTime() : null,
    needDesc: row.needDesc || '',
    bizIntro: row.bizIntro || '',
  })
  demandEditing.value = row
  demandFormVisible.value = true
}

async function saveDemand() {
  demandErrors.name = demandForm.name.trim() ? '' : '请填写岗位名称'
  demandErrors.dept = demandForm.dept.trim() ? '' : '请填写用人部门'
  demandErrors.businessDept = demandForm.businessDept.trim() ? '' : '请填写业务部门'
  demandErrors.headcount = demandForm.headcount && demandForm.headcount > 0 ? '' : '请填写需求数量'
  demandErrors.scopeType = demandForm.scopeType ? '' : '请选择发布范围'
  demandErrors.needDesc = demandForm.needDesc.trim() ? '' : '请填写需求描述'
  if (
    demandErrors.name ||
    demandErrors.dept ||
    demandErrors.businessDept ||
    demandErrors.headcount ||
    demandErrors.scopeType ||
    demandErrors.needDesc
  ) {
    await focusFirstInvalid([
      [demandErrors.name, demandNameRef],
      [demandErrors.dept, demandDeptRef],
      [demandErrors.businessDept, demandBusinessDeptRef],
      [demandErrors.headcount, demandHeadcountRef],
      [demandErrors.scopeType, demandScopeTypeRef],
      [demandErrors.needDesc, demandNeedDescRef],
    ])
    return
  }
  demandSaving.value = true
  demandWriteError.value = null
  const payload = {
    name: demandForm.name.trim(),
    dept: demandForm.dept.trim(),
    businessDept: demandForm.businessDept.trim(),
    headcount: demandForm.headcount,
    needTime: demandForm.needTime.trim(),
    workLocation: demandForm.workLocation.trim(),
    bpName: demandForm.bpName.trim(),
    scopeType: demandForm.scopeType,
    scopeBatch: demandForm.scopeBatch.trim(),
    openEnabled: demandForm.openEnabled,
    openStart: toDateStr(demandForm.openStartTs),
    openEnd: toDateStr(demandForm.openEndTs),
    needDesc: demandForm.needDesc.trim(),
    bizIntro: demandForm.bizIntro.trim(),
  }
  try {
    if (demandEditing.value) {
      await updatePositionDemand(demandEditing.value.id, payload)
      message.success('岗位需求已更新')
    } else {
      await createPositionDemand(payload)
      message.success('岗位需求已保存')
      // 保存成功后立即清除草稿（R-105），并重置表单避免待写入的定时器把旧内容写回。
      demandDraft.clear()
      resetDemandForm()
    }
    demandFormVisible.value = false
    loadDemands()
  } catch (e: any) {
    // 写入失败 → 三段式（R-203），不再只弹一条原始报文 toast。
    demandWriteError.value = buildWriteError(e, { action: '保存需求' })
  } finally {
    demandSaving.value = false
  }
}

/** 开启 / 关闭报名（中等影响：直接执行 + 结果提示）。 */
async function toggleOpen(row: PositionDemand) {
  const next = !row.openEnabled
  try {
    await openPositionDemand(row.id, next)
    message.success(next ? '已开放报名' : '已关闭报名')
    loadDemands()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/** 撤回需求 = 高影响（撤回后申请人需重新申请）→ 确认框写明后果。 */
function withdrawDemand(row: PositionDemand) {
  askConfirm(
    '撤回岗位需求',
    `撤回「${row.name}」后，该需求将退回申请人重新申请，已开放的名额同时关闭。确认撤回？`,
    '撤回需求',
    async () => {
      await withdrawPositionDemand(row.id)
      message.success('岗位需求已撤回')
      loadDemands()
    },
    '撤回需求',
  )
}

function goReview(row: PositionDemand) {
  activeTab.value = 'review'
  loadDemands()
}

/* ───────────────────────── ② 需求审核 ───────────────────────── */

const reviewColumns = computed(() => [
  { title: '岗位', key: 'name', width: 200, ellipsis: true, render: (row: PositionDemand) => textCell(row.name, 180) },
  { title: '用人部门', key: 'dept', width: 130, ellipsis: true, render: (row: PositionDemand) => textCell(row.dept, 110) },
  { title: '需求数量', key: 'headcount', width: 100, render: (row: PositionDemand) => numCell(row.headcount) },
  { title: '负责BP', key: 'bpName', width: 120, ellipsis: true, render: (row: PositionDemand) => textCell(row.bpName, 100) },
  { title: '申请人', key: 'submitterName', width: 120, ellipsis: true, render: (row: PositionDemand) => textCell(row.submitterName, 100) },
  { title: '状态', key: 'needStatus', width: 100, render: (row: PositionDemand) => h(NTag, { type: needStatusType(row.needStatus), size: 'small' }, { default: () => row.needStatus || '待审核' }) },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render: (row: PositionDemand) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'success', onClick: () => approveDemand(row) }, { default: () => '通过审核' }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => openReject(row) }, { default: () => '驳回需求' }),
        ],
      }),
  },
])

const REVIEW_SCROLL_X = 940

async function approveDemand(row: PositionDemand) {
  try {
    await reviewPositionDemand(row.id, { action: 'approve' })
    message.success(`「${row.name}」已通过审核`)
    loadDemands()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

const rejectVisible = ref(false)
const rejecting = ref(false)
const rejectTarget = ref<PositionDemand | null>(null)
const rejectForm = reactive({ note: '' })

// 字段级校验状态（R-221）。
const rejectErrors = reactive({ note: '' })
const rejectNoteRef = ref<any>(null)

// 写入失败三段式（R-203）。
const rejectWriteError = ref<WriteErrorInfo | null>(null)

function clearRejectError(field: keyof typeof rejectErrors) {
  rejectErrors[field] = ''
}

function openReject(row: PositionDemand) {
  rejectTarget.value = row
  rejectForm.note = ''
  rejectErrors.note = ''
  rejectWriteError.value = null
  rejectVisible.value = true
}

async function submitReject() {
  const row = rejectTarget.value
  if (!row) return
  rejectErrors.note = rejectForm.note.trim() ? '' : '请填写驳回原因'
  if (rejectErrors.note) {
    await focusFirstInvalid([[rejectErrors.note, rejectNoteRef]])
    return
  }
  rejecting.value = true
  rejectWriteError.value = null
  try {
    await reviewPositionDemand(row.id, { action: 'reject', note: rejectForm.note.trim() })
    message.success(`「${row.name}」已驳回`)
    rejectVisible.value = false
    loadDemands()
  } catch (e: any) {
    // 写入失败 → 三段式（R-203），不再只弹一条原始报文 toast。
    rejectWriteError.value = buildWriteError(e, { action: '驳回需求' })
  } finally {
    rejecting.value = false
  }
}

/* ───────────────────────── ③ 志愿推送 ───────────────────────── */

const appRows = ref<PositionApplication[]>([])
const appLoading = ref(false)
const appError = ref('')
const flowRows = ref<SelectionFlow[]>([])
const pushBatch = ref<string | null>(null)
const progressBatch = ref<string | null>(null)

const batchOptions = computed(() =>
  flowRows.value.map((f) => ({ label: f.batch || String(f.id), value: f.batch || String(f.id) })),
)

const currentFlow = computed(() => flowRows.value.find((f) => f.batch === pushBatch.value))
const flowStarted = computed(() => Boolean(currentFlow.value?.started))

const pushRows = computed(() =>
  appRows.value.filter((a) => a.status === '推送中' || a.status === '已填报'),
)
const pushEmptyText = computed(() =>
  pushBatch.value ? '该批次暂无待选志愿' : '请先选择校招批次',
)

async function loadFlows() {
  try {
    flowRows.value = await listSelectionFlows()
  } catch {
    flowRows.value = []
  }
}

/**
 * 载入志愿。
 * ⚠️ PositionApplication 模型本身没有 batch 字段，批次过滤只能由后端做（?batch=），
 *    所以按页签传不同的批次入参，而不是前端筛。
 */
async function loadApplications(batch?: string | null) {
  appLoading.value = true
  appError.value = ''
  try {
    appRows.value = await listApplications({ batch: batch ?? undefined })
  } catch (e: any) {
    appError.value = extractError(e)
    appRows.value = []
  } finally {
    appLoading.value = false
  }
}

/** 批次选择框的字段级错误（R-221）。 */
const pushBatchError = ref('')
const pushBatchRef = ref<any>(null)

function onPushBatchChange(value: string | null) {
  pushBatchError.value = value ? '' : '请先选择校招批次'
  loadPushApplications()
}

function focusBatchField() {
  nextTick(() => {
    const inst = pushBatchRef.value
    if (inst && typeof inst.focus === 'function') inst.focus()
  })
}

/** 启动撮合 = 高影响 → 确认框必须写明「启动后校招生不可再修改志愿」。 */
function askStartFlow() {
  const batch = pushBatch.value
  pushBatchError.value = batch ? '' : '请先选择校招批次'
  if (!batch) {
    // 字段级提示已就地展示（R-221），这里只负责把焦点送回选择框。
    focusBatchField()
    return
  }
  askConfirm(
    '启动双选撮合',
    `启动「${batch}」批次的双选撮合后，校招生不可再修改志愿，已填报的志愿会按顺序推送给岗位所属业务BP。确认启动？`,
    '启动撮合',
    async () => {
      if (currentFlow.value) {
        await startSelectionFlow(currentFlow.value.id)
      } else {
        const flow = await createSelectionFlow({ batch })
        await startSelectionFlow(flow.id)
      }
      message.success('撮合已启动')
      await loadFlows()
      loadApplications(pushBatch.value)
    },
    '启动撮合',
  )
}

/** 志愿推送页：按当前批次取志愿。 */
function loadPushApplications() {
  return loadApplications(pushBatch.value)
}

/** 人才市场页：不按批次过滤，取全部「人才市场」状态的志愿。 */
function loadMarketApplications() {
  return loadApplications(null)
}

/** 双选进度页：按选定批次取志愿（不选 = 全部）。 */
function loadProgressApplications() {
  return loadApplications(progressBatch.value)
}

const pushColumns = computed(() => [
  { title: '校招生', key: 'personName', width: 130, ellipsis: true, render: (row: PositionApplication) => textCell(row.personName, 110) },
  { title: '班级', key: 'className', width: 140, ellipsis: true, render: (row: PositionApplication) => textCell(row.className, 120) },
  { title: '累计均分', key: 'avgScore', width: 110, render: (row: PositionApplication) => numCell(row.avgScore) },
  { title: '志愿岗位', key: 'positionName', width: 180, ellipsis: true, render: (row: PositionApplication) => textCell(row.positionName, 160) },
  { title: '业务部门', key: 'businessDept', width: 130, ellipsis: true, render: (row: PositionApplication) => textCell(row.businessDept, 110) },
  {
    title: '推送时间',
    key: 'pushedAt',
    width: 140,
    render: (row: PositionApplication) => (row.pushedAt ? h('span', { title: new Date(row.pushedAt).toLocaleString('zh-CN') }, relTime(row.pushedAt)) : '—'),
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right' as const,
    render: (row: PositionApplication) =>
      h(NSpace, { size: 8, wrap: false }, {
        default: () => [
          // 已填报但还没推送给业务BP → 触发「推送下一志愿」
          row.status === '已填报'
            ? h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => doPush(row) }, { default: () => '推送下一志愿' })
            : null,
          h(NButton, { size: 'small', quaternary: true, type: 'success', onClick: () => askAccept(row) }, { default: () => '录取' }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => askReject(row) }, { default: () => '放弃' }),
        ].filter(Boolean),
      }),
  },
])

const PUSH_SCROLL_X = 1130

/** 推送下一志愿给岗位所属业务BP。 */
async function doPush(row: PositionApplication) {
  try {
    await pushApplication(row.id)
    message.success('已推送该志愿给岗位所属业务BP')
    loadApplications(pushBatch.value)
  } catch (e: any) {
    message.error(extractError(e))
  }
}

/** 录取 = 高影响 → 确认框写明「后续志愿自动释放」。 */
function askAccept(row: PositionApplication) {
  askConfirm(
    '录取该志愿',
    `录取「${row.personName || '该校招生'}」的「${row.positionName || '该岗位'}」后，他后续填报的志愿会被自动释放，不再参与本轮推送。确认录取？`,
    '确认录取',
    async () => {
      await acceptApplication(row.id)
      message.success('已录取该志愿，后续志愿已释放')
      loadApplications(pushBatch.value)
    },
    '录取志愿',
  )
}

/** 放弃 = 高影响 → 确认框写明「下一志愿自动推送」。 */
function askReject(row: PositionApplication) {
  askConfirm(
    '放弃该志愿',
    `放弃「${row.personName || '该校招生'}」的「${row.positionName || '该岗位'}」后，系统会自动把该生的下一志愿推送给对应业务BP。确认放弃？`,
    '确认放弃',
    async () => {
      await rejectApplication(row.id)
      message.success('已放弃该志愿，下一志愿已顺延推送')
      loadPushApplications()
    },
    '放弃志愿',
  )
}

/* ───────────────────────── ④ 人才市场 ───────────────────────── */

const marketRows = computed(() => appRows.value.filter((a) => a.status === '人才市场'))

const marketColumns = computed(() => [
  { title: '校招生', key: 'personName', width: 140, ellipsis: true, render: (row: PositionApplication) => textCell(row.personName, 120) },
  { title: '班级', key: 'className', width: 150, ellipsis: true, render: (row: PositionApplication) => textCell(row.className, 130) },
  { title: '累计均分', key: 'avgScore', width: 110, render: (row: PositionApplication) => numCell(row.avgScore) },
  { title: '原志愿岗位', key: 'positionName', width: 180, ellipsis: true, render: (row: PositionApplication) => textCell(row.positionName, 160) },
  { title: '业务部门', key: 'businessDept', width: 140, ellipsis: true, render: (row: PositionApplication) => textCell(row.businessDept, 120) },
  {
    title: '操作',
    key: 'actions',
    width: 110,
    fixed: 'right' as const,
    render: (row: PositionApplication) =>
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => askAssign(row) }, { default: () => '采纳' }),
  },
])

const MARKET_SCROLL_X = 720

/** 采纳 = 高影响（定岗结果）→ 确认框写明后果。 */
function askAssign(row: PositionApplication) {
  askConfirm(
    '采纳该校招生',
    `采纳后，「${row.personName || '该校招生'}」将按指定分配进入「${row.positionName || '目标岗位'}」，人才市场名单中不再保留该生。确认采纳？`,
    '确认采纳',
    async () => {
      await assignApplication(row.id)
      message.success('已采纳该校招生')
      loadMarketApplications()
    },
    '采纳该校招生',
  )
}

/* ───────────────────────── ⑤ 双选进度 ───────────────────────── */

/** 双选进度的一行 = 一个校招生（由其全部志愿聚合而成）。 */
interface PlacementProgressRow {
  personId: string
  personName: string
  className: string
  avgScore: number | null
  stage: string
  wishCount: number
  placement: string
  confirmed: string
}

const progressRows = computed<PlacementProgressRow[]>(() => {
  const byPerson = new Map<string, PlacementProgressRow>()
  appRows.value.forEach((a) => {
    const key = String(a.person || a.id)
    const exist = byPerson.get(key)
    if (exist) {
      exist.wishCount += 1
      if (a.status === '已录取') {
        exist.stage = '已录取'
        exist.placement = a.positionName || '—'
        exist.confirmed = a.decision ? '已确认' : '待确认'
      } else if (a.status === '已放弃' && exist.stage !== '已录取') {
        exist.stage = '已放弃'
      } else if (a.status === '人才市场' && exist.stage !== '已录取') {
        exist.stage = '人才市场'
      } else if (a.status === '推送中' && exist.stage === '已填报') {
        exist.stage = '推送中'
      }
      if (a.avgScore != null) exist.avgScore = a.avgScore
      if (!exist.className && a.className) exist.className = a.className
      return
    }
    byPerson.set(key, {
      personId: key,
      personName: a.personName || '—',
      className: a.className || '',
      avgScore: a.avgScore ?? null,
      stage: a.status || '已填报',
      wishCount: 1,
      placement: a.status === '已录取' ? (a.positionName || '—') : '—',
      confirmed: a.decision ? '已确认' : '待确认',
    })
  })
  return [...byPerson.values()]
})

const progressColumns = computed(() => [
  { title: '校招生', key: 'personName', width: 130, ellipsis: true, render: (row: PlacementProgressRow) => textCell(row.personName, 110) },
  { title: '班级', key: 'className', width: 140, ellipsis: true, render: (row: PlacementProgressRow) => textCell(row.className, 120) },
  { title: '累计均分', key: 'avgScore', width: 110, render: (row: PlacementProgressRow) => numCell(row.avgScore) },
  { title: '双选阶段', key: 'stage', width: 110, render: (row: PlacementProgressRow) => h(NTag, { type: stageType(row.stage), size: 'small' }, { default: () => row.stage || '—' }) },
  { title: '填报志愿', key: 'wishCount', width: 110, render: (row: PlacementProgressRow) => numCell(row.wishCount) },
  { title: '定岗结果', key: 'placement', width: 160, ellipsis: true, render: (row: PlacementProgressRow) => textCell(row.placement, 140) },
  { title: '本人确认', key: 'confirmed', width: 110, render: (row: PlacementProgressRow) => row.confirmed },
])

const PROGRESS_SCROLL_X = 760

function stageType(stage?: string) {
  const map: Record<string, any> = {
    已填报: 'default',
    推送中: 'warning',
    已录取: 'success',
    已放弃: 'error',
    已释放: 'default',
    人才市场: 'info',
  }
  return map[stage || ''] || 'default'
}

/* ───────────────────────── ⑥ 绩效展示 ───────────────────────── */

/** 绩效展示的一行（校招生档案 + 定岗维度）。 */
interface PerfRow {
  id: string
  name: string
  className: string
  education: string
  currentRotation: string
  avgScore: number | null
  monthlyTrend: string
  tags: string
  recommend: string
}

const perfRows = ref<PerfRow[]>([])
const perfLoading = ref(false)
const perfError = ref('')
const perfSearch = ref('')
const personRows = ref<Person[]>([])

const perfEmptyText = computed(() => (perfSearch.value.trim() ? '没有符合筛选条件的校招生' : '暂无数据'))

async function loadPerf() {
  perfLoading.value = true
  perfError.value = ''
  try {
    const kw = perfSearch.value.trim()
    const persons = await listPersons()
    personRows.value = persons
    const avgMap = new Map<string, number | null>()
    appRows.value.forEach((a) => {
      if (a.person && a.avgScore != null) avgMap.set(String(a.person), a.avgScore)
    })
    const rows: PerfRow[] = persons.map((p) => ({
      id: String(p.id),
      name: p.name || '—',
      className: p.classRoomName || '',
      education: p.education || '—',
      currentRotation: p.bu || '—',
      avgScore: avgMap.get(String(p.id)) ?? null,
      monthlyTrend: '—',
      tags: '—',
      recommend: '—',
    }))
    perfRows.value = kw ? rows.filter((r) => r.name.includes(kw)) : rows
  } catch (e: any) {
    perfError.value = extractError(e)
    perfRows.value = []
  } finally {
    perfLoading.value = false
  }
}

const perfColumns = computed(() => [
  { title: '排名', key: 'rank', width: 80, render: (_row: PerfRow, index: number) => index + 1 },
  { title: '校招生', key: 'name', width: 130, ellipsis: true, render: (row: PerfRow) => textCell(row.name, 110) },
  { title: '班级', key: 'className', width: 140, ellipsis: true, render: (row: PerfRow) => textCell(row.className, 120) },
  { title: '学历', key: 'education', width: 100, render: (row: PerfRow) => row.education || '—' },
  { title: '当前轮岗', key: 'currentRotation', width: 140, ellipsis: true, render: (row: PerfRow) => textCell(row.currentRotation, 120) },
  { title: '累计均分', key: 'avgScore', width: 110, render: (row: PerfRow) => numCell(row.avgScore) },
  { title: '月度趋势', key: 'monthlyTrend', width: 110, render: (row: PerfRow) => row.monthlyTrend },
  { title: '标签', key: 'tags', width: 130, render: (row: PerfRow) => row.tags },
  { title: '推介', key: 'recommend', width: 110, render: (row: PerfRow) => row.recommend },
])

const PERF_SCROLL_X = 1050

/* ───────────────────────── 生命周期 ───────────────────────── */

function relTime(v?: string | null) {
  if (!v) return '—'
  const t = new Date(v).getTime()
  if (Number.isNaN(t)) return String(v)
  const min = Math.floor((Date.now() - t) / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour} 小时前`
  const day = Math.floor(hour / 24)
  if (day < 30) return `${day} 天前`
  return new Date(v).toLocaleDateString('zh-CN')
}

function onTabChange(tab: TabKey) {
  if (tab === 'pool' || tab === 'review') {
    loadDemands()
  } else if (tab === 'perf') {
    loadPerf()
  } else if (tab === 'push') {
    loadFlows()
    loadPushApplications()
  } else if (tab === 'market') {
    loadMarketApplications()
  } else {
    loadProgressApplications()
  }
}

onMounted(async () => {
  await loadDemands()
  await loadFlows()
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
  width: 260px;
  max-width: 100%;
}
.toolbar-select-wide {
  width: 220px;
  max-width: 100%;
}
.toolbar-tip {
  font-size: var(--text-small);
  color: var(--ink-faint);
}
.toolbar-note {
  font-size: var(--text-meta);
  color: var(--ink-faint);
  flex-shrink: 0;
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
.card-area {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--col-min), 1fr));
  gap: var(--space-4);
}
.demand-card {
  min-width: 0;
}
.card-title {
  font-size: var(--text-h4);
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: var(--space-2);
}
.card-line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) 0;
  font-size: var(--text-small);
}
.card-label {
  flex-shrink: 0;
  width: 72px;
  color: var(--ink-faint);
}
.card-value {
  flex: 1;
  min-width: 0;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-value.num {
  font-variant-numeric: tabular-nums;
}
.card-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
.confirm-body {
  font-size: var(--text-body);
  color: var(--ink-soft);
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.filter {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.filter-label {
  font-size: var(--text-small);
  color: var(--ink-soft);
  white-space: nowrap;
}
/* 工具栏里的字段级校验容器（校招批次） */
.filter-field {
  min-width: 0;
}

/* 字段级校验提示：图标 + 文字双通道（R-221，不只靠颜色） */
.field-error {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-small);
  color: var(--c-error-deep);
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
.error-state-icon,
.error-circle-icon {
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
