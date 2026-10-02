<template>
  <div class="demand-container">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.demand.DemandList.s1') }}</h1>
      <n-space>
        <n-button type="primary" @click="handleCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          {{ t('pages.demand.DemandList.s4') }}
        </n-button>
      </n-space>
    </div>

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="demand-skeleton">
      <div v-for="i in 6" :key="i" class="skeleton-card">
        <n-skeleton height="16px" width="40%" />
        <n-skeleton height="18px" width="80%" />
        <n-skeleton height="14px" width="60%" />
      </div>
    </div>

    <!-- 空态（无数据） -->
    <div v-else-if="demands.length === 0" class="empty-wrapper">
      <n-empty :description="t('pages.demand.DemandList.s11')">
        <template #extra>
          <n-button type="primary" @click="handleCreate">{{ t('pages.demand.DemandList.s12') }}</n-button>
        </template>
      </n-empty>
    </div>

    <template v-else>
      <!-- KPI 统计条（前端真实聚合） -->
      <div class="kpi-row">
        <div class="kpi-card">
          <span class="kpi-label">{{ t('pages.demand.DemandList.s51') }}</span>
          <span class="kpi-value">{{ kpi.total }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">{{ t('pages.demand.DemandList.s52') }}</span>
          <span class="kpi-value">{{ kpi.inProgress }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">{{ t('pages.demand.DemandList.s53') }}</span>
          <span class="kpi-value">{{ kpi.pending }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">{{ t('pages.demand.DemandList.s54') }}</span>
          <span class="kpi-value">{{ kpi.planned }}</span>
        </div>
      </div>

      <!-- 工具条 -->
      <div class="toolbar">
        <n-input
          v-model:value="searchText"
          :placeholder="t('pages.demand.DemandList.s2')"
          style="width: 260px"
          clearable
          @input="onSearchInput"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <n-select
          v-model:value="filterStatus"
          :placeholder="t('pages.demand.DemandList.s3')"
          style="width: 120px"
          clearable
          :options="statusFilterOptions"
          @update:value="onFilterChange"
        />
        <n-select
          v-model:value="filterType"
          :placeholder="t('pages.demand.DemandList.s6')"
          style="width: 120px"
          clearable
          :options="demandTypeFilterOptions"
          @update:value="onFilterChange"
        />
        <n-select
          v-model:value="sortKey"
          :placeholder="t('pages.demand.DemandList.s57')"
          style="width: 160px"
          :options="sortOptions"
          @update:value="onFilterChange"
        />
        <div class="toolbar-spacer"></div>
        <n-radio-group :value="viewMode" @update:value="onViewModeChange">
          <n-radio-button value="card">{{ t('pages.demand.DemandList.s55') }}</n-radio-button>
          <n-radio-button value="table">{{ t('pages.demand.DemandList.s56') }}</n-radio-button>
        </n-radio-group>
      </div>

      <!-- 筛选无结果 -->
      <div v-if="processedDemands.length === 0" class="empty-wrapper">
        <n-empty :description="t('pages.demand.DemandList.s61')">
          <template #extra>
            <n-button @click="clearFilters">{{ t('pages.demand.DemandList.s62') }}</n-button>
          </template>
        </n-empty>
      </div>

      <template v-else>
        <!-- 卡片视图 -->
        <div v-if="viewMode === 'card'" class="demand-grid">
          <div
            v-for="item in pagedDemands"
            :key="item.id"
            class="demand-card"
            :class="{ 'selected': selectedDemand?.id === item.id }"
            tabindex="0"
            @click="handleCardClick(item)"
            @keydown.enter="handleCardClick(item)"
          >
            <div class="card-top">
              <span class="demand-code">{{ item.code }}</span>
              <span class="priority-pill" :class="priorityPillClass(item.priority)">{{ item.priority }}</span>
              <n-tag :type="getStatusType(item.demandStatus)" size="small" class="status-tag">{{ getStatusText(item.demandStatus) }}</n-tag>
            </div>
            <div class="card-title" :title="item.name">{{ item.name }}</div>
            <div class="card-meta">
              <n-tag :type="getApprovalType(item.approvalStatus)" size="small">{{ getApprovalText(item.approvalStatus) }}</n-tag>
              <span class="meta-dept">{{ item.departmentName || item.department?.name || '-' }}</span>
              <n-tag :type="item.demandType === 'SOCIAL' ? 'info' : 'success'" size="small">
                {{ item.demandType === 'SOCIAL' ? t('pages.demand.DemandList.s70') : t('pages.demand.DemandList.s71') }}
              </n-tag>
            </div>
            <div class="card-owner">
              <span class="owner-label">{{ t('pages.demand.DemandList.s59') }}</span>
              <span class="owner-value">{{ item.hrName || '-' }}</span>
              <span class="time-label">{{ t('pages.demand.DemandList.s60') }}</span>
              <span class="time-value" :title="absoluteTime(item)">{{ relativeTime(item) }}</span>
            </div>
            <div class="card-progress">
              <div class="progress-text">
                {{ t('pages.demand.DemandList.s8') }} {{ filledOf(item) }} / {{ t('pages.demand.DemandList.s20') }} {{ headcountOf(item) }}
              </div>
              <div class="bar">
                <span
                  :style="{ width: progressPct(item) + '%', background: progressPct(item) >= 100 ? 'var(--c-success)' : 'var(--brand)' }"
                ></span>
              </div>
            </div>
            <div class="card-actions">
              <n-button text type="primary" size="small" @click.stop="handleCardClick(item)">{{ t('pages.demand.DemandList.s9') }}</n-button>
              <n-button text size="small" @click.stop="handleEdit(item)">{{ t('pages.demand.DemandList.s50') }}</n-button>
              <n-button v-if="item.demandStatus === 'DRAFT'" text type="primary" size="small" @click.stop="handleSubmitFromCard(item)">{{ t('pages.demand.DemandList.s43') }}</n-button>
            </div>
          </div>
        </div>

        <!-- 表格视图 -->
        <div v-else class="demand-table">
          <n-data-table
            :columns="columns"
            :data="pagedDemands"
            :row-key="(row: any) => row.id"
            :bordered="false"
            :single-line="false"
            size="small"
          />
        </div>

        <!-- 分页 -->
        <div v-if="processedDemands.length > pageSize" class="pagination">
          <n-pagination
            :page="page"
            :page-size="pageSize"
            :item-count="processedDemands.length"
            @update:page="onPageChange"
          />
        </div>
      </template>
    </template>

    <!-- 详情抽屉 -->
    <n-drawer
      v-model:show="detailVisible"
      :width="drawerWidth"
      placement="right"
    >
      <n-drawer-content :native-scrollbar="false">
        <template #header>
          <div class="drawer-header">
            <div class="drawer-header__main">
              <span class="drawer-code">{{ selectedDemand?.code }}</span>
              <span class="drawer-name" :title="selectedDemand?.name">{{ selectedDemand?.name }}</span>
              <n-tag :type="getStatusType(selectedDemand?.demandStatus)" size="small">{{ getStatusText(selectedDemand?.demandStatus) }}</n-tag>
              <n-tag :type="getApprovalType(selectedDemand?.approvalStatus)" size="small">{{ getApprovalText(selectedDemand?.approvalStatus) }}</n-tag>
            </div>
            <div class="drawer-header__actions">
              <n-button v-if="selectedDemand?.state === 'DRAFT'" type="primary" size="small" @click="handleSubmitApproval">{{ t('pages.demand.DemandList.s43') }}</n-button>
              <n-button size="small" @click="handleEdit(selectedDemand)">{{ t('pages.demand.DemandList.s50') }}</n-button>
            </div>
          </div>
        </template>

        <div v-if="detailLoading" class="drawer-skeleton">
          <n-skeleton :repeat="3" />
        </div>
        <template v-else-if="selectedDemand">
          <!-- 概览条 -->
          <div class="overview-bar">
            <div class="overview-item">
              <span class="ov-num">{{ headcountOf(selectedDemand) }}</span>
              <span class="ov-label">{{ t('pages.demand.DemandList.s20') }}</span>
            </div>
            <div class="overview-item">
              <span class="ov-num">{{ filledOf(selectedDemand) }}</span>
              <span class="ov-label">{{ t('pages.demand.DemandList.s8') }}</span>
            </div>
            <div class="overview-item">
              <span class="ov-num">{{ selectedDemand.pendingCount ?? 0 }}</span>
              <span class="ov-label">{{ t('pages.demand.DemandList.s22') }}</span>
            </div>
            <div class="overview-item">
              <span class="ov-num">{{ selectedDemand._count?.positions ?? 0 }}</span>
              <span class="ov-label">{{ t('pages.demand.DemandList.s19') }}</span>
            </div>
            <div class="overview-bar__progress">
              <div class="bar">
                <span
                  :style="{ width: progressPct(selectedDemand) + '%', background: progressPct(selectedDemand) >= 100 ? 'var(--c-success)' : 'var(--brand)' }"
                ></span>
              </div>
            </div>
          </div>

          <n-tabs v-model:value="activeTab" type="line" class="detail-tabs">
            <!-- 基本信息（配置驱动） -->
            <n-tab-pane name="detail" :tab="t('pages.demand.DemandList.s13')">
              <div v-for="b in formBuckets" :key="b.key" class="detail-section">
                <div class="section-header">
                  <span class="section-title">{{ b.group?.name || '其他' }}</span>
                </div>
                <div class="info-grid">
                  <template v-for="m in b.fields" :key="m.field.id">
                    <div
                      v-if="m.field.fieldKey !== 'jd' && m.field.fieldKey !== 'requirements'"
                      class="info-item"
                      :class="{ 'info-item--wide': m.field.fieldType === 'MULTILINE_TEXT' }"
                    >
                      <span class="info-label">{{ m.field.label }}</span>
                      <span v-if="m.field.fieldKey === 'state'" class="info-value">
                        <n-tag :type="getStatusType(fieldValue(m.field))" size="small">
                          {{ getStatusText(fieldValue(m.field)) }}
                        </n-tag>
                      </span>
                      <span v-else-if="m.field.fieldKey === 'demand_type'" class="info-value">
                        <n-tag :type="fieldValue(m.field) === 'SOCIAL' ? 'info' : 'success'" size="small">
                          {{ fieldValue(m.field) === 'SOCIAL' ? t('pages.demand.DemandList.s70') : t('pages.demand.DemandList.s71') }}
                        </n-tag>
                      </span>
                      <span v-else-if="m.field.fieldType === 'RICH_TEXT'" class="info-value info-value--rich">
                        <SafeHtml v-if="fieldValue(m.field)" :html="fieldValue(m.field)" />
                        <template v-else>-</template>
                      </span>
                      <span v-else class="info-value">{{ displayText(m.field, fieldValue(m.field)) }}</span>
                    </div>
                  </template>
                </div>
              </div>
            </n-tab-pane>

            <!-- JD 与任职要求 -->
            <n-tab-pane name="jd" :tab="t('pages.demand.DemandList.s63')">
              <div class="detail-section">
                <div class="section-header">
                  <span class="section-title">{{ t('pages.demand.DemandList.s64') }}</span>
                </div>
                <div class="rich-block">
                  <SafeHtml v-if="selectedDemand.jd" :html="selectedDemand.jd" />
                  <n-empty v-else :description="t('pages.demand.DemandList.s66')" />
                </div>
              </div>
              <div class="detail-section">
                <div class="section-header">
                  <span class="section-title">{{ t('pages.demand.DemandList.s65') }}</span>
                </div>
                <div class="rich-block">
                  <SafeHtml v-if="selectedDemand.requirements" :html="selectedDemand.requirements" />
                  <n-empty v-else :description="t('pages.demand.DemandList.s67')" />
                </div>
              </div>
            </n-tab-pane>

            <!-- 招聘进度 -->
            <n-tab-pane name="progress" :tab="t('pages.demand.DemandList.s18')">
              <div class="detail-section">
                <div class="section-header">
                  <span class="section-title">{{ t('pages.demand.DemandList.s18') }}</span>
                </div>
                <div class="progress-stats">
                  <div class="progress-stat">
                    <span class="stat-num">{{ selectedDemand._count?.positions ?? 0 }}</span>
                    <span class="stat-label">{{ t('pages.demand.DemandList.s19') }}</span>
                  </div>
                  <div class="progress-stat">
                    <span class="stat-num">{{ headcountOf(selectedDemand) }}</span>
                    <span class="stat-label">{{ t('pages.demand.DemandList.s20') }}</span>
                  </div>
                  <div class="progress-stat">
                    <span class="stat-num">{{ filledOf(selectedDemand) }}</span>
                    <span class="stat-label">{{ t('pages.demand.DemandList.s8') }}</span>
                  </div>
                  <div class="progress-stat">
                    <span class="stat-num">{{ selectedDemand.pendingCount ?? 0 }}</span>
                    <span class="stat-label">{{ t('pages.demand.DemandList.s22') }}</span>
                  </div>
                </div>
                <div class="bar" style="margin-top: var(--space-3)">
                  <span
                    :style="{ width: progressPct(selectedDemand) + '%', background: progressPct(selectedDemand) >= 100 ? 'var(--c-success)' : 'var(--brand)' }"
                  ></span>
                </div>
                <div class="progress-caption">
                  {{ t('pages.demand.DemandList.s68', { hired: filledOf(selectedDemand), headcount: headcountOf(selectedDemand) }) }}
                </div>
              </div>
            </n-tab-pane>

            <n-tab-pane name="candidates" :tab="t('pages.demand.DemandList.s23')">
              <n-empty :description="t('pages.demand.DemandList.s24')" />
            </n-tab-pane>

            <n-tab-pane name="records" :tab="t('pages.demand.DemandList.s41')">
              <n-empty :description="t('pages.demand.DemandList.s42')" />
            </n-tab-pane>
          </n-tabs>
        </template>
      </n-drawer-content>
    </n-drawer>

    <!-- 创建/编辑弹窗 -->
    <n-modal
      v-model:show="modalVisible"
      preset="card"
      :title="formData.id ? '编辑需求' : '创建需求'"
      :style="{ width: 'min(920px, 94vw)' }"
      :mask-closable="false"
    >
      <div class="form-body">
        <n-form :model="formData" label-placement="top">
          <div class="form-grid">
            <template v-for="s in editSections" :key="s.key">
              <div v-if="editSections.length > 1" class="form-group-header">{{ s.name }}</div>
              <n-form-item
                v-for="item in s.fields"
                :key="item.field.fieldKey"
                :label="item.field.label"
                :required="item.required"
                :class="{ 'form-item--wide': WIDE_TYPES.includes(item.field.fieldType) }"
              >
                <!-- 模型映射字段: 直接绑 formData[prop] -->
                <template v-if="item.binding">
                  <n-input
                    v-if="item.binding.kind === 'text'"
                    v-model:value="formData[item.binding.prop]"
                    :placeholder="item.field.placeholder || '请输入'"
                    style="width: 100%"
                  />
                  <n-input-number
                    v-else-if="item.binding.kind === 'number'"
                    v-model:value="formData[item.binding.prop]"
                    :min="1" :max="100" style="width: 100%"
                  />
                  <n-select
                    v-else-if="item.binding.kind === 'department'"
                    v-model:value="formData[item.binding.prop]"
                    :options="departmentOptions"
                    :placeholder="t('pages.demand.DemandList.s44')"
                    style="width: 100%"
                  />
                  <n-select
                    v-else-if="item.binding.kind === 'select'"
                    v-model:value="formData[item.binding.prop]"
                    :options="editBindingOptions(item.field.fieldKey)"
                    style="width: 100%"
                  />
                  <n-input
                    v-else-if="item.binding.kind === 'textarea'"
                    v-model:value="formData[item.binding.prop]"
                    type="textarea" :rows="3"
                    :placeholder="item.field.placeholder || '请输入'"
                    style="width: 100%"
                  />
                </template>

                <!-- 扩展(动态)字段: 绑 formValues[fieldKey] -->
                <template v-else>
                  <RichEditor
                    v-if="item.field.fieldType === 'RICH_TEXT'"
                    v-model:html="formValues[item.field.fieldKey]"
                    :placeholder="item.field.placeholder || '请输入'"
                    style="width: 100%"
                  />
                  <n-input
                    v-else-if="isPlainTextType(item.field.fieldType)"
                    v-model:value="formValues[item.field.fieldKey]"
                    :type="item.field.fieldType === 'MULTILINE_TEXT' ? 'textarea' : 'text'"
                    :placeholder="item.field.placeholder || ''"
                    style="width: 100%"
                  />
                  <n-input-number
                    v-else-if="isNumberType(item.field.fieldType)"
                    v-model:value="formValues[item.field.fieldKey]"
                    :min="(item.field.validation as any)?.min ?? undefined"
                    :max="(item.field.validation as any)?.max ?? undefined"
                    :placeholder="item.field.placeholder || '请输入数字'"
                    style="width: 100%"
                  />
                  <!-- 范围数字 (RANGE_NUMBER, 2026-09-28 兵哥): 最小值/最大值 双输入 -->
                  <n-space
                    v-else-if="item.field.fieldType === 'RANGE_NUMBER'"
                    align="center" :size="8" style="width: 100%"
                  >
                    <n-input-number
                      v-model:value="formValues[item.field.fieldKey].min"
                      :min="(item.field.validation as any)?.min ?? undefined"
                      :max="(item.field.validation as any)?.max ?? undefined"
                      :placeholder="t('pages.demand.DemandList.s45')"
                      style="flex: 1; min-width: 0"
                    />
                    <span>~</span>
                    <n-input-number
                      v-model:value="formValues[item.field.fieldKey].max"
                      :min="(item.field.validation as any)?.min ?? undefined"
                      :max="(item.field.validation as any)?.max ?? undefined"
                      :placeholder="t('pages.demand.DemandList.s46')"
                      style="flex: 1; min-width: 0"
                    />
                    <n-text v-if="(item.field.validation as any)?.unit" depth="3">{{ (item.field.validation as any).unit }}</n-text>
                  </n-space>
                  <!-- 选项类 (含 人员/部门 引用) -->
                  <n-select
                    v-else-if="isOptionType(item.field.fieldType)"
                    v-model:value="formValues[item.field.fieldKey]"
                    :options="selectOptions(item.field)"
                    :multiple="isMultiType(item.field.fieldType)"
                    :placeholder="item.field.placeholder || '请选择'"
                    style="width: 100%"
                  />
                  <!-- 日期 / 日期范围 -->
                  <n-date-picker
                    v-else-if="isDateType(item.field.fieldType)"
                    :value="dateValue(item.field)"
                    :type="item.field.fieldType === 'DATE_RANGE' ? 'daterange' : 'date'"
                    clearable
                    style="width: 100%"
                    :is-date-disabled="dateDisabled(item.field) || undefined"
                    @update:value="(v: number | [number, number] | null) => onDateInput(item.field, v)"
                  />
                  <!-- 布尔 -->
                  <n-switch v-else-if="item.field.fieldType === 'BOOLEAN'" v-model:value="formValues[item.field.fieldKey]" />
                  <!-- 附件 / 其他: URL 文本 -->
                  <n-input
                    v-else
                    v-model:value="formValues[item.field.fieldKey]"
                    :placeholder="item.field.placeholder || '请输入'"
                    style="width: 100%"
                  />
                </template>
              </n-form-item>
            </template>
          </div>
        </n-form>
      </div>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="modalVisible = false">{{ t('pages.demand.DemandList.s47') }}</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSave">{{ t('pages.demand.DemandList.s48') }}</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, onMounted, onUnmounted, h } from 'vue'
import { NButton, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import { AddOutline, SearchOutline } from '@vicons/ionicons5'
import { get, post, put } from '../../api/auth'
import dayjs from 'dayjs'
import RichEditor from '../../components/RichEditor.vue'
import SafeHtml from '../../components/SafeHtml.vue'

import {
  listFields, listGroups, getDynamicFieldValues, saveDynamicFieldValues, extractApiError,
  type FieldDefinition, type FieldOption, type FieldGroup,
} from '../../api/dynamic-field'
import {
  fetchFormConfig, mergeFields, groupFieldsByGroup, type FormConfig,
} from '../../api/form-config'
import { resolveDateBound } from '../../utils/fieldValidation'
const { t } = useI18n()
const message = useMessage()

// --- 需求字段管理配置 (resource=Demand) + 表单设置 (FormConfig) ---
// ★ 2026-09-28 (兵哥): 详情页与编辑表单统一由「招聘需求表单设置」驱动 —
// 分组顺序 / 字段显隐 / 必填均与表单设置实时一致。
const demandFields = ref<FieldDefinition[]>([])
const demandGroups = ref<FieldGroup[]>([])
const demandFormConfig = ref<FormConfig>({ fields: [], groupOrder: [] })
const dynamicValues = ref<Record<string, any>>({})
const formValues = reactive<Record<string, any>>({})

// 系统字段 / 核心描述字段: 模型映射字段取 demand 对象, 其余扩展字段取 DynamicFieldValue。
// 模型映射字段: field_key → 在 demand 详情对象上的属性名(camelCase, 经后端渲染)。
// jd/requirements 由固定「描述信息」区块承载, 不在此映射。
// jd/requirements 已纳入系统字段注册表(0022 种子), 值存 Demand 模型列, 经此映射取值。
const MODEL_ATTR_MAP: Record<string, string> = {
  headcount: 'headcount',
  priority: 'priority',
  level: 'level',
  position_title: 'positionTitle',
  jd: 'jd',
  requirements: 'requirements',
}

// 系统字段取值特例 (非简单属性映射): 部门/HR 取序列化后的 *Name
const SYSTEM_VALUE_GETTERS: Record<string, (d: any) => any> = {
  code: (d) => d?.code,
  title: (d) => d?.name,
  state: (d) => d?.state,
  demand_type: (d) => d?.demandType,
  department: (d) => d?.departmentName || d?.department?.name,
  hr: (d) => d?.hrName,
}

// 编辑表单: field_key → formData 属性绑定 (模型字段复用既有 formData 结构)。
// jd/requirements 已纳入系统字段注册表(0022 种子, 2026-09-28 兵哥),
// 随 editSections 走表单设置驱动; 值存 Demand 模型列, 经 binding 回填/收集。
const FORM_MODEL_BINDING: Record<string, { prop: string; kind: 'text' | 'number' | 'select' | 'department' | 'textarea' }> = {
  title: { prop: 'name', kind: 'text' },
  department: { prop: 'departmentId', kind: 'department' },
  demand_type: { prop: 'demandType', kind: 'select' },
  headcount: { prop: 'positionCount', kind: 'number' },
  priority: { prop: 'priority', kind: 'select' },
  position_title: { prop: 'positionSeries', kind: 'text' },
  level: { prop: 'jobLevel', kind: 'text' },
  jd: { prop: 'description', kind: 'textarea' },
  requirements: { prop: 'requirements', kind: 'textarea' },
}
// 编辑表单不渲染的系统字段: 编号(只读标识) / 状态(流程管控) / 负责HR(流程指派)
const EDIT_SKIP_KEYS = new Set(['code', 'state', 'hr'])

const loading = ref(false)
const demands = ref<any[]>([])
const departments = ref<any[]>([])
const selectedDemand = ref<any>(null)
const detailVisible = ref(false)
const modalVisible = ref(false)
const submitting = ref(false)
const detailLoading = ref(false)
const activeTab = ref('detail')

// 列表筛选 / 排序 / 视图 / 分页
const searchText = ref('')
const keyword = ref('')
const filterStatus = ref<string | null>('')
const filterType = ref<string>('ALL')
const sortKey = ref<'updated' | 'priority' | 'headcount'>('updated')
const pageSize = 12
const page = ref(1)
const VIEW_STORAGE_KEY = 'ats-demand-view'
const viewMode = ref<'card' | 'table'>(readInitialView())

const formData = ref<any>({
  id: '',
  name: '',
  departmentId: '',
  demandType: 'SOCIAL',
  positionCount: 1,
  priority: 'P1',
  positionSeries: '',
  jobLevel: '',
  description: '',
  requirements: ''
})

const statusFilterOptions = [
  { label: '草稿', value: 'DRAFT' },
  { label: '进行中', value: 'IN_PROGRESS' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '已暂停', value: 'PAUSED' },
]

const priorityOptions = [
  { label: 'P0-战略', value: 'P0' },
  { label: 'P1-重要', value: 'P1' },
  { label: 'P2-常规', value: 'P2' },
]

const departmentOptions = computed(() =>
  departments.value.map(d => ({ label: d.name, value: d.id }))
)

// 视图偏好持久化（localStorage，异常静默兜底）
function readInitialView(): 'card' | 'table' {
  try {
    const v = localStorage.getItem(VIEW_STORAGE_KEY)
    if (v === 'card' || v === 'table') return v
  } catch (e) {
    /* localStorage 不可用时回退默认 */
  }
  return 'card'
}
function onViewModeChange(v: 'card' | 'table') {
  viewMode.value = v
  page.value = 1
  try {
    localStorage.setItem(VIEW_STORAGE_KEY, v)
  } catch (e) {
    /* localStorage 不可用时忽略 */
  }
}

const demandTypeFilterOptions = computed(() => ([
  { label: t('pages.demand.DemandList.s69'), value: 'ALL' },
  { label: t('pages.demand.DemandList.s70'), value: 'SOCIAL' },
  { label: t('pages.demand.DemandList.s71'), value: 'CAMPUS' },
]))

const sortOptions = computed(() => ([
  { label: t('pages.demand.DemandList.s72'), value: 'updated' },
  { label: t('pages.demand.DemandList.s73'), value: 'priority' },
  { label: t('pages.demand.DemandList.s74'), value: 'headcount' },
]))

// ★ 2026-09-28 (兵哥): 表单设置聚合 — 字段 × FormConfig(显隐/必填) → 启用字段按分组顺序桶。
// 与「系统设置 → 招聘需求表单设置」的实时预览完全同源 (mergeFields + groupFieldsByGroup)。
const formBuckets = computed(() =>
  groupFieldsByGroup(
    mergeFields(demandFields.value, demandFormConfig.value).filter(m => m.enabled),
    demandFormConfig.value.groupOrder,
    demandGroups.value,
  ).filter(b => b.fields.length > 0),
)

// 编辑表单区块: 启用字段按表单设置分组; 模型字段绑 formData, 其余绑 formValues
const editSections = computed(() => formBuckets.value
  .map(b => ({
    key: b.key,
    name: b.group?.name || '其他',
    fields: b.fields
      .filter(m => !EDIT_SKIP_KEYS.has(m.field.fieldKey))
      .map(m => ({
        field: m.field,
        required: m.required,
        binding: FORM_MODEL_BINDING[m.field.fieldKey] || null,
      })),
  }))
  .filter(s => s.fields.length > 0),
)

// 编辑表单中的动态(非模型绑定)字段 — 用于 formValues 初始化/回填/提交收集
const dynamicFormFields = computed(() =>
  editSections.value.flatMap(s => s.fields.filter(m => !m.binding).map(m => m.field)),
)

// 跨列字段（富文本 / 多行文本 / 日期范围 / 地址）
const WIDE_TYPES = ['RICH_TEXT', 'MULTILINE_TEXT', 'DATE_RANGE', 'ADDRESS']

// --- 类型判断 (与 DynamicFieldEntry.vue 对齐) ---
const NUMBER_TYPES = ['NUMBER']
const OPTION_TYPES = ['SELECT', 'MULTISELECT', 'LIST_SINGLE', 'LIST_MULTI', 'PERSON', 'DEPARTMENT']
const DATE_TYPES = ['DATE', 'DATE_RANGE']
const PLAIN_TEXT_TYPES = ['TEXT', 'MULTILINE_TEXT', 'ADDRESS', 'URL']
const isNumberType = (t: string) => NUMBER_TYPES.includes(t)
const isOptionType = (t: string) => OPTION_TYPES.includes(t)
const isDateType = (t: string) => DATE_TYPES.includes(t)
const isPlainTextType = (t: string) => PLAIN_TEXT_TYPES.includes(t)
const isMultiType = (t: string) => t === 'MULTISELECT' || t === 'LIST_MULTI'

function selectOptions(f: FieldDefinition): { label: string; value: any }[] {
  return (f.options || []).map((o: FieldOption) => ({
    label: o.label || o.value, value: o.value,
  }))
}

// 编辑表单中「模型映射 + 选项类」字段(需求类型 / 优先级)的下拉项
function editBindingOptions(key: string): { label: string; value: any }[] {
  if (key === 'demand_type') return demandTypeOptions
  if (key === 'priority') return priorityOptions
  return []
}

// 日期选择器受控: ISO 字符串 <-> 时间戳
function dateValue(f: FieldDefinition): number | [number, number] | null {
  const v = formValues[f.fieldKey]
  if (!v) return null
  if (Array.isArray(v)) {
    const a = Date.parse(v[0]); const b = Date.parse(v[1])
    return (isNaN(a) || isNaN(b)) ? null : [a, b]
  }
  const ts = Date.parse(v)
  return isNaN(ts) ? null : ts
}
function onDateInput(f: FieldDefinition, v: number | [number, number] | null) {
  if (v == null) { formValues[f.fieldKey] = null; return }
  formValues[f.fieldKey] = Array.isArray(v)
    ? [new Date(v[0]).toISOString(), new Date(v[1]).toISOString()]
    : new Date(v).toISOString()
}

// 日期可选范围: 禁用区间外的日期 (minDate/maxDate 可为 YYYY-MM-DD 或相对表达式 T±N)。
function dateDisabled(f: FieldDefinition): ((current: number) => boolean) | undefined {
  const v = f.validation as { minDate?: string | null; maxDate?: string | null } | null
  const lo = resolveDateBound(v?.minDate)
  const hi = resolveDateBound(v?.maxDate)
  if (!lo && !hi) return undefined
  return (current: number) => {
    const dt = new Date(current)
    const ds = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
    if (lo && ds < lo) return true
    if (hi && ds > hi) return true
    return false
  }
}

// 详情页某字段的取值: 系统字段取值特例 → 模型映射属性 → 动态字段值
function fieldValue(f: FieldDefinition): any {
  const getter = SYSTEM_VALUE_GETTERS[f.fieldKey]
  if (getter) return getter(selectedDemand.value)
  const attr = MODEL_ATTR_MAP[f.fieldKey]
  if (attr) return selectedDemand.value?.[attr]
  return dynamicValues.value?.[f.fieldKey]
}

function optionLabel(f: FieldDefinition, val: any): string {
  const found = (f.options || []).find((o: FieldOption) => o.value === val)
  return found ? (found.label || String(found.value)) : String(val ?? '')
}

function formatDateVal(v: any): string {
  if (!v) return '-'
  return dayjs(v).format('YYYY-MM-DD')
}

// 详情页字段值的展示文本 (按类型格式化)
function displayText(f: FieldDefinition, value: any): string {
  if (value == null || value === '') return '-'
  const t = f.fieldType
  if (t === 'BOOLEAN') return value ? '是' : '否'
  if (t === 'MULTISELECT' || t === 'LIST_MULTI') {
    if (!Array.isArray(value) || value.length === 0) return '-'
    return value.map((v: any) => optionLabel(f, v)).join('、')
  }
  if (OPTION_TYPES.includes(t)) return optionLabel(f, value)
  if (t === 'DATE') return formatDateVal(value)
  if (t === 'DATE_RANGE') {
    if (Array.isArray(value) && value.length === 2) return `${formatDateVal(value[0])} ~ ${formatDateVal(value[1])}`
    return String(value)
  }
  if (t === 'RANGE_NUMBER') {
    if (value && typeof value === 'object' && ('min' in value || 'max' in value)) {
      const lo = value.min
      const hi = value.max
      if (lo == null && hi == null) return '-'
      const unit = (f.validation as any)?.unit ? ` ${(f.validation as any).unit}` : ''
      return `${lo ?? '-'} ~ ${hi ?? '-'}${unit}`
    }
    return '-'
  }
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

// 状态颜色（映射为 naive 的 tag type）
const getStatusType = (status: string): any => {
  const types: Record<string, string> = {
    'DRAFT': 'default',
    'NOT_STARTED': 'default',
    'IN_PROGRESS': 'info',
    'COMPLETED': 'success',
    'PAUSED': 'warning',
    'STOPPED': 'error'
  }
  return types[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'DRAFT': '草稿',
    'NOT_STARTED': '未开始',
    'IN_PROGRESS': '进行中',
    'COMPLETED': '已完成',
    'PAUSED': '已暂停',
    'STOPPED': '已停招'
  }
  return texts[status] || status
}

const getApprovalType = (status: string): any => {
  const types: Record<string, string> = {
    'NOT_STARTED': 'default',
    'PENDING': 'info',
    'APPROVED': 'success',
    'REJECTED': 'error'
  }
  return types[status] || 'default'
}

const getApprovalText = (status: string) => {
  const texts: Record<string, string> = {
    'NOT_STARTED': '未发起',
    'PENDING': '审批中',
    'APPROVED': '已通过',
    'REJECTED': '已拒绝'
  }
  return texts[status] || status
}

// ===== 列表展示辅助 =====
function headcountOf(item: any): number {
  return item?.headcount ?? item?.positionCount ?? 0
}
function filledOf(item: any): number {
  return item?.filledCount ?? item?.hiredCount ?? 0
}
function progressPct(item: any): number {
  const h = headcountOf(item)
  if (h <= 0) return 0
  return Math.min(100, Math.round((filledOf(item) / h) * 100))
}
function priorityRank(p: string): number {
  if (p === 'P0') return 0
  if (p === 'P1') return 1
  if (p === 'P2') return 2
  return 9
}
function priorityPillClass(p: string): string {
  if (p === 'P0') return 'priority-pill--error'
  if (p === 'P1') return 'priority-pill--warning'
  if (p === 'P2') return 'priority-pill--info'
  return 'priority-pill--default'
}
function priorityTagType(p: string): any {
  if (p === 'P0') return 'error'
  if (p === 'P1') return 'warning'
  if (p === 'P2') return 'info'
  return 'default'
}
function timeValueOf(item: any): number {
  const raw = item?.updatedAt ?? item?.updated_at ?? item?.createdAt ?? item?.created_at
  const ts = raw ? Date.parse(raw) : NaN
  return isNaN(ts) ? 0 : ts
}
function relativeTime(item: any): string {
  const raw = item?.updatedAt ?? item?.updated_at ?? item?.createdAt ?? item?.created_at
  if (!raw) return '-'
  const d = dayjs(raw)
  if (!d.isValid()) return '-'
  const diffMin = dayjs().diff(d, 'minute')
  if (diffMin < 1) return t('pages.demand.DemandList.s75')
  if (diffMin < 60) return t('pages.demand.DemandList.s76', { n: diffMin })
  const diffHr = dayjs().diff(d, 'hour')
  if (diffHr < 24) return t('pages.demand.DemandList.s77', { n: diffHr })
  const diffDay = dayjs().diff(d, 'day')
  if (diffDay < 30) return t('pages.demand.DemandList.s78', { n: diffDay })
  return d.format('YYYY-MM-DD')
}
function absoluteTime(item: any): string {
  const raw = item?.updatedAt ?? item?.updated_at ?? item?.createdAt ?? item?.created_at
  if (!raw) return '-'
  const d = dayjs(raw)
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm') : '-'
}

// KPI（前端真实聚合）
const kpi = computed(() => ({
  total: demands.value.length,
  inProgress: demands.value.filter(d => d.demandStatus === 'IN_PROGRESS').length,
  pending: demands.value.filter(d => d.approvalStatus === 'PENDING' || d.approval_status === 'PENDING').length,
  planned: demands.value.reduce((s, d) => s + headcountOf(d), 0),
}))

// 搜索防抖（300ms）
let searchTimer: ReturnType<typeof setTimeout> | undefined
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    keyword.value = searchText.value
    page.value = 1
  }, 300)
}
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  keyword.value = searchText.value
  page.value = 1
}

function onFilterChange() {
  page.value = 1
}
function clearFilters() {
  searchText.value = ''
  keyword.value = ''
  filterStatus.value = ''
  filterType.value = 'ALL'
  sortKey.value = 'updated'
  page.value = 1
}

// 前端筛选 + 排序
const processedDemands = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  let list = demands.value
  if (kw) {
    list = list.filter(d => {
      const hay = [d.code, d.name, d.departmentName, d.department?.name, d.hrName]
        .filter(Boolean).join(' ').toLowerCase()
      return hay.includes(kw)
    })
  }
  if (filterStatus.value) {
    list = list.filter(d => d.demandStatus === filterStatus.value)
  }
  if (filterType.value && filterType.value !== 'ALL') {
    list = list.filter(d => d.demandType === filterType.value)
  }
  const sorted = [...list]
  if (sortKey.value === 'priority') {
    sorted.sort((a, b) => priorityRank(a.priority) - priorityRank(b.priority))
  } else if (sortKey.value === 'headcount') {
    sorted.sort((a, b) => headcountOf(b) - headcountOf(a))
  } else {
    sorted.sort((a, b) => timeValueOf(b) - timeValueOf(a))
  }
  return sorted
})

// 前端分页
const pagedDemands = computed(() => {
  const start = (page.value - 1) * pageSize
  return processedDemands.value.slice(start, start + pageSize)
})

function onPageChange(p: number) {
  page.value = p
}

// 表格列定义
const columns = computed<DataTableColumns<any>[]>(() => [
  {
    title: t('pages.demand.DemandList.s79'),
    key: 'code',
    width: 120,
    render: (row: any) => h('span', { class: 'cell-code', title: row.code }, row.code),
  },
  {
    title: t('pages.demand.DemandList.s80'),
    key: 'name',
    minWidth: 180,
    ellipsis: { tooltip: true },
    render: (row: any) => h('span', { title: row.name }, row.name),
  },
  {
    title: t('pages.demand.DemandList.s5'),
    key: 'department',
    width: 140,
    render: (row: any) => row.departmentName || row.department?.name || '-',
  },
  {
    title: t('pages.demand.DemandList.s6'),
    key: 'demandType',
    width: 90,
    render: (row: any) => h(NTag, { size: 'small', type: row.demandType === 'SOCIAL' ? 'info' : 'success' }, { default: () => (row.demandType === 'SOCIAL' ? t('pages.demand.DemandList.s70') : t('pages.demand.DemandList.s71')) }),
  },
  {
    title: t('pages.demand.DemandList.s58'),
    key: 'priority',
    width: 90,
    render: (row: any) => h(NTag, { size: 'small', type: priorityTagType(row.priority) }, { default: () => row.priority || '-' }),
  },
  {
    title: t('pages.demand.DemandList.s20'),
    key: 'headcount',
    width: 100,
    align: 'right',
    render: (row: any) => headcountOf(row),
  },
  {
    title: t('pages.demand.DemandList.s8'),
    key: 'filled',
    width: 100,
    align: 'right',
    render: (row: any) => filledOf(row),
  },
  {
    title: t('pages.demand.DemandList.s81'),
    key: 'status',
    width: 100,
    render: (row: any) => h(NTag, { size: 'small', type: getStatusType(row.demandStatus) }, { default: () => getStatusText(row.demandStatus) }),
  },
  {
    title: t('pages.demand.DemandList.s82'),
    key: 'approval',
    width: 100,
    render: (row: any) => h(NTag, { size: 'small', type: getApprovalType(row.approvalStatus) }, { default: () => getApprovalText(row.approvalStatus) }),
  },
  {
    title: t('pages.demand.DemandList.s83'),
    key: 'actions',
    width: 130,
    render: (row: any) => h('div', { class: 'cell-actions' }, [
      h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleCardClick(row) }, { default: () => t('pages.demand.DemandList.s9') }),
      h(NButton, { text: true, size: 'small', onClick: () => handleEdit(row) }, { default: () => t('pages.demand.DemandList.s50') }),
    ]),
  },
])

// 抽屉宽度自适应
const drawerWidth = ref(680)
function syncDrawerWidth() {
  drawerWidth.value = Math.min(1080, Math.max(720, Math.round(window.innerWidth * 0.72)))
}

const fetchDemands = async () => {
  loading.value = true
  try {
    const res = await get('/demands/')
    if (res.data.success) {
      demands.value = (res.data.data || []).map(normalizeDemand)
    }
  } catch (error) {
    message.error('获取需求列表失败')
  } finally {
    loading.value = false
  }
}

// 列表/详情模板用的是旧契约别名(name/positionCount/demandStatus/hiredCount)。
// 后端经 CamelCaseJSONRenderer 输出 camelCase 键(demandType/filledCount),
// 旧代码读 snake 键(demand_type/filled_count)恒 undefined → 卡片类型恒显校招、
// 入职数恒 0。这里对两种键名都兜底, 并保证 detail 合并后别名不被
// serializer 的 position_count(关联职位数)覆盖 positionCount(需求人数=headcount)。
function normalizeDemand(d: any) {
  return {
    ...d,
    name: d.title,
    positionCount: d.headcount,
    demandStatus: d.state,
    demandType: d.demandType ?? d.demand_type,
    hiredCount: d.filledCount ?? d.filled_count ?? 0,
    onBoardCount: d.filledCount ?? d.filled_count ?? 0,
  }
}

const fetchDepartments = async () => {
  try {
    const res = await get('/users/departments')
    if (res.data.success) {
      departments.value = res.data.data
    }
  } catch (error) {
    message.error(extractApiError(error, '获取部门失败'))
  }
}

// 并行加载: 字段定义 / 分组 / 表单设置, 任一失败都不阻断其余(独立容错)。
const loadDemandFields = async () => {
  const [f, g, c] = await Promise.allSettled([
    listFields('Demand'),
    listGroups('Demand'),
    fetchFormConfig('Demand'),
  ])
  demandFields.value = f.status === 'fulfilled' ? f.value : []
  demandGroups.value = g.status === 'fulfilled' ? g.value : []
  demandFormConfig.value = c.status === 'fulfilled' ? c.value : { fields: [], groupOrder: [] }
}

// 打开详情: 拉取完整详情(含 JD/任职要求) + 动态字段值
const handleCardClick = async (item: any) => {
  selectedDemand.value = item
  detailVisible.value = true
  detailLoading.value = true
  dynamicValues.value = {}
  try {
    const res = await get(`/demands/${item.id}/`)
    const detail = res.data?.data ?? res.data
    if (detail && detail.id) {
      // 合并后重新归一化: 详情 serializer 的 positionCount 是「关联职位数」,
      // 会覆盖列表别名 positionCount(需求人数=headcount); 统一以 headcount 为准,
      // 并对 camelCase 键兜底。
      selectedDemand.value = normalizeDemand({ ...item, ...detail })
    }
  } catch (error) {
    // 保持列表项数据兜底
  }
  try {
    dynamicValues.value = await getDynamicFieldValues('Demand', item.id)
  } catch (error) {
    dynamicValues.value = {}
  } finally {
    detailLoading.value = false
  }
}

const resetFormValues = () => {
  for (const f of dynamicFormFields.value) {
    formValues[f.fieldKey] = defaultForType(f.fieldType)
  }
}

const defaultForType = (t: string): any => {
  if (t === 'BOOLEAN') return false
  if (t === 'RANGE_NUMBER') return { min: null, max: null }
  if (isMultiType(t)) return []
  return ''
}

const handleCreate = () => {
  formData.value = {
    id: '',
    name: '',
    departmentId: '',
    demandType: 'SOCIAL',
    positionCount: 1,
    priority: 'P1',
    positionSeries: '',
    jobLevel: '',
    description: '',
    requirements: ''
  }
  resetFormValues()
  modalVisible.value = true
}

const handleEdit = async (item: any) => {
  // 拉取完整详情, 保证部门 id / JD / 任职要求 / 职级 / 职位系列 / 人数 / 优先级 / 类型
  // 等都正确回填 (列表项与抽屉 selectedDemand 不一定含这些字段)。
  // 注意: serializer 的 positionCount 是「关联职位数」, 需求人数应取 headcount。
  let d: any = item || {}
  try {
    const res = await get(`/demands/${item.id}/`)
    const detail = res.data?.data ?? res.data
    if (detail && detail.id) d = detail
  } catch (error) {
    // 兜底用传入项 (已 normalize): 列表项/抽屉项至少含 id / headcount / demandType 等
  }
  formData.value = {
    id: d.id ?? item?.id ?? '',
    name: d.title ?? d.name ?? '',
    // department 在列表/详情序列化里是外键 PK 字符串(非嵌套对象), 故 d.department 即 id;
    // 兼容个别嵌套场景: 对象取 .id, 字符串直接当 id。
    departmentId: (typeof d.department === 'object' ? d.department?.id : d.department)
      ?? (typeof item?.department === 'object' ? item?.department?.id : item?.department)
      ?? '',
    demandType: d.demandType ?? d.demand_type ?? 'SOCIAL',
    positionCount: d.headcount ?? item?.headcount ?? 1,
    priority: d.priority || 'P1',
    positionSeries: d.positionTitle ?? d.position_title ?? '',
    jobLevel: d.level ?? '',
    description: d.jd ?? '',
    requirements: d.requirements ?? '',
  }
  resetFormValues()
  try {
    const vals = await getDynamicFieldValues('Demand', item.id)
    for (const f of dynamicFormFields.value) {
      formValues[f.fieldKey] = vals[f.fieldKey] ?? defaultForType(f.fieldType)
    }
  } catch (error) {
    // 拉取失败保持默认
  }
  modalVisible.value = true
}

// 卡片上的「提交审批」：先选中再提交
const handleSubmitFromCard = (item: any) => {
  selectedDemand.value = item
  handleSubmitApproval()
}

const handleSave = async () => {
  if (!formData.value.name || !formData.value.departmentId) {
    message.warning('请填写必填项')
    return
  }

  // 收集动态(非模型映射)配置字段值
  const dyn: Record<string, any> = {}
  for (const f of dynamicFormFields.value) {
    const v = formValues[f.fieldKey]
    if (v === '' || v == null || (Array.isArray(v) && v.length === 0)) continue
    // 范围数字: 两端皆空视为空, 跳过 (否则落 {"min":null,"max":null})
    if (f.fieldType === 'RANGE_NUMBER' && v && v.min == null && v.max == null) continue
    dyn[f.fieldKey] = v
  }

  submitting.value = true
  try {
    const data = {
      title: formData.value.name,
      department: formData.value.departmentId,
      headcount: formData.value.positionCount,
      level: formData.value.jobLevel || '',
      position_title: formData.value.positionSeries || '',
      demand_type: formData.value.demandType,
      priority: formData.value.priority,
      jd: formData.value.description || '',
      requirements: formData.value.requirements || '',
    }

    let demandId = formData.value.id
    if (demandId) {
      await put(`/demands/${demandId}/`, data)
      message.success('更新成功')
    } else {
      const r: any = await post('/demands/', data)
      demandId = r?.data?.data?.id || r?.data?.id || ''
      message.success('创建成功')
    }

    // 扩展字段走权威动态值接口落库
    if (demandId && Object.keys(dyn).length) {
      await saveDynamicFieldValues('Demand', demandId, dyn)
    }

    modalVisible.value = false
    fetchDemands()
  } catch (error: any) {
    message.error(extractApiError(error, '操作失败'))
  } finally {
    submitting.value = false
  }
}

const handleSubmitApproval = async () => {
  if (!selectedDemand.value) return
  try {
    await post(`/demands/${selectedDemand.value.id}/submit`)
    message.success('提交审批成功')
    detailVisible.value = false
    fetchDemands()
  } catch (error: any) {
    message.error(extractApiError(error, '提交失败'))
  }
}

onMounted(() => {
  fetchDemands()
  fetchDepartments()
  loadDemandFields()
  syncDrawerWidth()
  window.addEventListener('resize', syncDrawerWidth)
})

onUnmounted(() => {
  window.removeEventListener('resize', syncDrawerWidth)
})
</script>

<style scoped>
.demand-container {
  padding: var(--space-6);
  min-height: 100%;
  background: transparent; /* 让 --aurora-base 透出 */
  animation: wb-fade-up var(--duration-slow) var(--ease-out) both;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.page-title {
  font-size: var(--fs-24);
  font-weight: 600;
  margin: 0;
}

/* KPI 条 */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

/* 工具条 */
.toolbar-spacer {
  flex: 1;
}

/* 卡片网格 */
.demand-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-4);
}

.demand-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  cursor: pointer;
  transition: transform var(--duration-base) var(--ease-out),
    box-shadow var(--duration-base) var(--ease-out),
    border-color var(--duration-base) var(--ease-out);
}

.demand-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card);
  border-color: var(--brand-a22);
}

.demand-card:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}

.demand-card.selected {
  border-color: var(--brand);
}

.card-top {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.demand-code {
  color: var(--c-info);
  font-weight: 600;
  font-size: var(--fs-13);
}

.priority-pill {
  font-size: var(--fs-12);
  font-weight: 600;
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  line-height: 1.6;
}

.priority-pill--error {
  background: var(--c-error-soft);
  color: var(--c-error);
}

.priority-pill--warning {
  background: var(--c-warning-soft);
  color: var(--c-warning);
}

.priority-pill--info {
  background: var(--c-info-soft);
  color: var(--c-info);
}

.priority-pill--default {
  background: var(--g1);
  color: var(--ink-soft);
}

.card-top .status-tag {
  margin-left: auto;
}

.card-title {
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  font-size: var(--fs-13);
  color: var(--ink-faint);
}

.card-meta .meta-dept {
  color: var(--ink-soft);
}

.card-owner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  font-size: var(--fs-13);
  color: var(--ink-faint);
}

.card-owner .owner-value,
.card-owner .time-value {
  color: var(--ink-soft);
}

.card-progress {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.progress-text {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

.bar {
  width: 100%;
  height: 6px;
  border-radius: var(--radius-pill);
  background: var(--glass-bg-input);
  overflow: hidden;
}

.bar > span {
  display: block;
  height: 100%;
  border-radius: var(--radius-pill);
  transition: width var(--duration-base) var(--ease-out);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* 表格视图 */
.demand-table {
  width: 100%;
}

.cell-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.cell-code {
  color: var(--c-info);
  font-weight: 600;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  margin-top: var(--space-4);
}

/* 加载骨架 */
.demand-skeleton {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-4);
}

.skeleton-card {
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.empty-wrapper {
  display: flex;
  justify-content: center;
  padding: 60px;
}

/* 抽屉 */
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  width: 100%;
}

.drawer-header__main {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.drawer-code {
  color: var(--c-info);
  font-weight: 600;
  font-size: var(--fs-13);
  flex-shrink: 0;
}

.drawer-name {
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.drawer-skeleton {
  padding: var(--space-2) 0;
}

.overview-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.overview-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--glass-bg-input);
  border-radius: var(--radius-sm);
}

.ov-num {
  font-size: var(--fs-20);
  font-weight: 600;
  color: var(--ink);
}

.ov-label {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

.overview-bar__progress {
  grid-column: 1 / -1;
}

.rich-block {
  margin-top: var(--space-2);
}

.detail-tabs :deep(.n-tabs-nav) {
  margin-bottom: var(--space-4);
}

.detail-section {
  margin-bottom: var(--space-6);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-hairline);
}

.section-title {
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-3) var(--space-6);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-item--wide {
  grid-column: 1 / -1;
}

.info-label {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

.info-value {
  font-size: var(--fs-14);
  color: var(--ink);
}

.progress-stats {
  display: flex;
  gap: var(--space-4);
}

.progress-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-4);
  background: var(--glass-bg-input);
  border-radius: var(--radius-sm);
}

.stat-num {
  font-size: var(--fs-24);
  font-weight: 600;
  color: var(--ink);
}

.stat-label {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  margin-top: var(--space-1);
}

.progress-caption {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  margin-top: var(--space-2);
}

/* 编辑表单 */
.form-body {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: var(--space-1);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 var(--space-5);
}

.form-grid .form-item--wide {
  grid-column: 1 / -1;
}

.form-group-header {
  grid-column: 1 / -1;
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink);
  margin: var(--space-4) 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-hairline);
}

.form-group-header:first-child {
  margin-top: 0;
}

.rich-editor-wrap {
  max-height: 280px;
  overflow: auto;
  width: 100%;
}

@media (max-width: 768px) {
  .form-grid { grid-template-columns: 1fr; }
  .overview-bar { grid-template-columns: repeat(2, 1fr); }
  .progress-stats { flex-wrap: wrap; }
}
</style>
