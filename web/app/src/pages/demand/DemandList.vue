<template>
  <div class="demand-container">
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
      <!-- ① 高级筛选区 -->
      <div class="filter-region">
        <div class="filter-row">
          <n-select
            v-model:value="departmentFilter"
            :placeholder="'需求部门'"
            style="width: 180px"
            clearable
            :options="departmentOptions"
            @update:value="() => (page = 1)"
          />
          <n-select
            v-model:value="hrbpFilter"
            placeholder="HRBP"
            style="width: 150px"
            clearable
            :options="personNameOptions('hrbp_name')"
            @update:value="() => (page = 1)"
          />
          <n-select
            v-model:value="hiringManagerFilter"
            placeholder="用人经理"
            style="width: 150px"
            clearable
            :options="personNameOptions('hiring_manager_name')"
            @update:value="() => (page = 1)"
          />
          <n-select
            v-model:value="hiringManagerSuperiorFilter"
            placeholder="用人经理上级"
            style="width: 160px"
            clearable
            :options="personNameOptions('hiring_manager_superior_name')"
            @update:value="() => (page = 1)"
          />
          <n-input
            v-model:value="searchText"
            placeholder="搜索需求名称 / 编号 / 部门"
            style="width: 260px"
            clearable
            @input="onSearchInput"
            @keyup.enter="handleSearch"
          >
            <template #prefix><n-icon :component="SearchOutline" /></template>
          </n-input>
          <n-button quaternary @click="showAdvanced = !showAdvanced">
            {{ showAdvanced ? '收起筛选' : '高级筛选' }}
          </n-button>
        </div>
        <div v-if="showAdvanced" class="filter-row filter-row--advanced">
          <n-select
            v-model:value="priorityFilter"
            placeholder="优先级"
            style="width: 150px"
            clearable
            :options="priorityOptions"
            @update:value="() => (page = 1)"
          />
          <n-select
            v-model:value="demandTypeFilter"
            placeholder="招聘类型"
            style="width: 150px"
            clearable
            :options="demandTypeFilterOptions"
            @update:value="() => (page = 1)"
          />
        </div>
      </div>

      <!-- ② 双层状态页签 -->
      <div class="tab-strip">
        <div class="tab-group">
          <n-button
            v-for="tab in processTabs"
            :key="'p-' + tab.key"
            size="small"
            :type="activeProcess === tab.key ? 'primary' : 'default'"
            secondary
            @click="activeProcess = tab.key; page = 1"
          >
            {{ tab.label }}
            <n-badge :value="processTabCounts[tab.key]" :show-zero="false" :max="9999" class="tab-badge" />
          </n-button>
        </div>
        <div class="tab-divider"></div>
        <div class="tab-group">
          <n-button
            v-for="tab in approvalTabs"
            :key="'a-' + tab.key"
            size="small"
            :type="activeApproval === tab.key ? 'primary' : 'default'"
            secondary
            @click="activeApproval = tab.key; page = 1"
          >
            {{ tab.label }}
            <n-badge :value="approvalTabCounts[tab.key]" :show-zero="false" :max="9999" class="tab-badge" />
          </n-button>
        </div>
      </div>

      <!-- ③ 批量操作栏 -->
      <div class="batch-bar">
        <n-checkbox
          :checked="selectAllChecked"
          :indeterminate="selectSomeChecked"
          @update:checked="toggleSelectAll"
        >
          全选（{{ selectedIds.length }}/{{ processedDemands.length }}）
        </n-checkbox>
        <n-button type="primary" size="small" @click="handleCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          创建需求
        </n-button>
        <n-button size="small" :disabled="!selectedIds.length" @click="openBatchPeople">
          <template #icon><n-icon :component="PeopleOutline" /></template>
          批量变更人员
        </n-button>
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
        <!-- ④ 卡片列表 -->
        <div class="demand-grid">
          <div
            v-for="item in pagedDemands"
            :key="item.id"
            class="demand-card"
            :class="{ 'selected': selectedDemand?.id === item.id }"
            :style="{ '--state-bar': stateBarColor(item.state || item.demandStatus) }"
            tabindex="0"
            @click="handleCardClick(item)"
            @keydown.enter="handleCardClick(item)"
          >
            <div class="card-check">
              <n-checkbox
                :checked="selectedIds.includes(item.id)"
                @update:checked="(v: boolean) => toggleCard(item.id, v)"
                @click.stop
              />
            </div>

            <!-- ⑤ 单卡信息：标题行 + 三栏 -->
            <div class="card-body">
              <!-- 标题行 -->
              <div class="card-headline">
                <span class="demand-code">{{ item.code }}</span>
                <span class="demand-title" :title="item.title || item.name">{{ item.title || item.name }}</span>
                <n-tag :type="priorityTagType(item.priority)" size="small" :bordered="false">{{ item.priority }}</n-tag>
                <n-tag :type="item.demandType === 'SOCIAL' ? 'info' : 'success'" size="small" :bordered="false">
                  {{ item.demandType === 'SOCIAL' ? '社会招聘' : '校园招聘' }}
                </n-tag>
                <div class="headline-spacer"></div>
                <!-- 右上角流程状态直切下拉 -->
                <n-dropdown
                  trigger="click"
                  :options="transitionDropdownOptions(item.state || item.demandStatus)"
                  @select="(k: string) => changeState(item, k)"
                  @click.stop
                >
                  <n-tag size="small" :type="getStatusType(item.state || item.demandStatus)" class="state-dropdown">
                    {{ getStatusText(item.state || item.demandStatus) }}
                    <n-icon :component="ChevronDownOutline" />
                  </n-tag>
                </n-dropdown>
              </div>

              <!-- 三栏 -->
              <div class="card-cols">
                <!-- 左栏：任职要求 + 责任人 -->
                <div class="card-col">
                  <div class="req-line">
                    <span v-if="item.talentNature" class="req-chip">{{ talentNatureText(item.talentNature) }}</span>
                    <span v-if="item.educationRequirement" class="req-chip">{{ item.educationRequirement }}</span>
                    <span v-if="item.experienceRequirement" class="req-chip">{{ item.experienceRequirement }}</span>
                    <span v-if="item.salaryRange" class="req-chip">{{ item.salaryRange }}</span>
                    <span v-if="item.positionSequence" class="req-chip">{{ item.positionSequence }}</span>
                    <span v-if="!hasRequirement(item)" class="req-chip req-chip--muted">未填写任职要求</span>
                  </div>
                  <div class="people-block">
                    <div class="people-row"><span class="people-label">TBP</span><span class="people-value">{{ item.hrName || '—' }}</span></div>
                    <div class="people-row"><span class="people-label">HRBP</span><span class="people-value">{{ item.hrbpName || '—' }}</span></div>
                  </div>
                </div>

                <!-- 中栏：部门 + 关联职位 -->
                <div class="card-col">
                  <div class="meta-row"><span class="meta-label">所属部门</span><span class="meta-value" :title="item.departmentName || item.department?.name">{{ item.departmentName || item.department?.name || '—' }}</span></div>
                  <div class="meta-row meta-row--top">
                    <span class="meta-label">关联职位</span>
                    <span class="meta-value">
                      <template v-if="item.positionCodes && item.positionCodes.length">
                        <n-tag
                          v-for="code in item.positionCodes"
                          :key="code"
                          size="tiny"
                          :bordered="false"
                          class="position-tag"
                        >{{ code }}</n-tag>
                      </template>
                      <span v-else class="meta-muted">暂无关联职位</span>
                    </span>
                  </div>
                </div>

                <!-- 右栏：进度 -->
                <div class="card-col card-col--progress">
                  <div class="date-line">
                    <n-icon :component="CalendarOutline" class="date-icon" />
                    <span v-if="item.dateRange && item.dateRange.length === 2">{{ formatDemandDate(item.dateRange[0]) }}-{{ formatDemandDate(item.dateRange[1]) }}</span>
                    <span v-else class="meta-muted">未设置起止日期</span>
                  </div>
                  <div v-if="timeProgress(item) !== null" class="progress-line">
                    <span class="progress-pct" :class="{ 'progress-pct--warn': (timeProgress(item) || 0) > 80 }">{{ timeProgress(item) }}%</span>
                  </div>
                  <div class="funnel">
                    <div class="funnel-item"><span class="funnel-num">{{ headcountOf(item) }}</span><span class="funnel-label">需求</span></div>
                    <div class="funnel-item"><span class="funnel-num">{{ item.applicantCount ?? 0 }}</span><span class="funnel-label">应聘</span></div>
                    <div class="funnel-item funnel-item--ok"><span class="funnel-num">{{ filledOf(item) }}</span><span class="funnel-label">入职</span></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
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
              <span class="drawer-name" :title="selectedDemand?.name || selectedDemand?.title">{{ selectedDemand?.name || selectedDemand?.title }}</span>
              <n-tag :type="getStatusType(selectedDemand?.state || selectedDemand?.demandStatus)" size="small">{{ getStatusText(selectedDemand?.state || selectedDemand?.demandStatus) }}</n-tag>
              <n-tag v-if="selectedDemand?.approvalStatus || selectedDemand?.approval_status" :type="getApprovalType(selectedDemand?.approvalStatus || selectedDemand?.approval_status)" size="small">{{ getApprovalText(selectedDemand?.approvalStatus || selectedDemand?.approval_status) }}</n-tag>
            </div>
            <div class="drawer-header__actions">
              <n-button v-if="(selectedDemand?.state || selectedDemand?.demandStatus) === 'DRAFT'" type="primary" size="small" @click="handleSubmitApproval">{{ t('pages.demand.DemandList.s43') }}</n-button>
              <n-button size="small" @click="handleEdit(selectedDemand)">{{ t('pages.demand.DemandList.s50') }}</n-button>
            </div>
          </div>
        </template>

        <div v-if="detailLoading" class="drawer-skeleton">
          <n-skeleton :repeat="3" />
        </div>
        <template v-else-if="selectedDemand">
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
              <span class="ov-num">{{ selectedDemand.applicantCount ?? 0 }}</span>
              <span class="ov-label">应聘</span>
            </div>
            <div class="overview-item">
              <span class="ov-num">{{ selectedDemand._count?.positions ?? selectedDemand.positionCodes?.length ?? 0 }}</span>
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
            <n-tab-pane name="detail" :tab="t('pages.demand.DemandList.s13')">
              <div v-for="b in formBuckets" :key="b.key" class="detail-section">
                <div class="section-header">
                  <span class="section-title">{{ b.group?.name || '其他' }}</span>
                </div>
                <div class="info-grid">
                  <template v-for="m in b.fields" :key="m.field.id">
                    <div
                      class="info-item"
                      :class="{ 'info-item--wide': WIDE_TYPES.includes(m.field.fieldType) }"
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
                    :options="editBindingOptions(item.field)"
                    style="width: 100%"
                  />
                  <n-select
                    v-else-if="item.binding.kind === 'multiselect'"
                    v-model:value="formData[item.binding.prop]"
                    :options="editBindingOptions(item.field)"
                    multiple
                    :placeholder="item.field.placeholder || '请选择'"
                    style="width: 100%"
                  />
                  <n-date-picker
                    v-else-if="item.binding.kind === 'daterange'"
                    :value="formDateRangeValue(item.binding.prop)"
                    type="daterange"
                    clearable
                    style="width: 100%"
                    :is-date-disabled="dateDisabled(item.field) || undefined"
                    @update:value="(v: number | [number, number] | null) => onFormDateRangeInput(item.binding.prop, v)"
                  />
                  <RichEditor
                    v-else-if="item.binding.kind === 'richtext'"
                    v-model:html="formData[item.binding.prop]"
                    :placeholder="item.field.placeholder || '请输入'"
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
                  <n-select
                    v-else-if="isOptionType(item.field.fieldType)"
                    v-model:value="formValues[item.field.fieldKey]"
                    :options="selectOptions(item.field)"
                    :multiple="isMultiType(item.field.fieldType)"
                    :placeholder="item.field.placeholder || '请选择'"
                    style="width: 100%"
                  />
                  <n-date-picker
                    v-else-if="isDateType(item.field.fieldType)"
                    :value="dateValue(item.field)"
                    :type="item.field.fieldType === 'DATE_RANGE' ? 'daterange' : 'date'"
                    clearable
                    style="width: 100%"
                    :is-date-disabled="dateDisabled(item.field) || undefined"
                    @update:value="(v: number | [number, number] | null) => onDateInput(item.field, v)"
                  />
                  <n-switch v-else-if="item.field.fieldType === 'BOOLEAN'" v-model:value="formValues[item.field.fieldKey]" />
                  <AttachmentUploader
                    v-else-if="item.field.fieldType === 'ATTACHMENT'"
                    :model-value="asAttachmentList(formValues[item.field.fieldKey])"
                    @update:model-value="(v: AttachmentItem[]) => (formValues[item.field.fieldKey] = v)"
                  />
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

    <!-- 批量变更人员弹窗 -->
    <n-modal
      v-model:show="batchPeopleModal"
      preset="card"
      title="批量变更人员"
      :style="{ width: 'min(520px, 94vw)' }"
      :mask-closable="false"
    >
      <n-form label-placement="top">
        <n-form-item label="HRBP">
          <n-select v-model:value="batchPeople.hrbp" :options="userPersonOptions" clearable placeholder="不修改则留空" />
        </n-form-item>
        <n-form-item label="用人经理">
          <n-select v-model:value="batchPeople.hiringManager" :options="userPersonOptions" clearable placeholder="不修改则留空" />
        </n-form-item>
        <n-form-item label="用人经理上级">
          <n-select v-model:value="batchPeople.hiringManagerSuperior" :options="userPersonOptions" clearable placeholder="不修改则留空" />
        </n-form-item>
        <p class="batch-hint">将应用到已选中的 {{ selectedIds.length }} 条需求（留空的字段保持不变）。</p>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="batchPeopleModal = false">取消</n-button>
          <n-button type="primary" :loading="batchSaving" :disabled="!selectedIds.length" @click="applyBatchPeople">确定</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, onMounted, onUnmounted, h } from 'vue'
import { NButton, NTag, NBadge, useMessage, type DataTableColumns } from 'naive-ui'
import { AddOutline, SearchOutline, ChevronDownOutline, CalendarOutline, PeopleOutline } from '@vicons/ionicons5'
import { get, post, put } from '../../api/auth'
import dayjs from 'dayjs'
import RichEditor from '../../components/RichEditor.vue'
import SafeHtml from '../../components/SafeHtml.vue'
import AttachmentUploader from '../../components/AttachmentUploader.vue'

import {
  listFields, listGroups, getDynamicFieldValues, saveDynamicFieldValues, extractApiError,
  type FieldDefinition, type FieldOption, type FieldGroup, type AttachmentItem,
} from '../../api/dynamic-field'
import {
  fetchFormConfig, mergeFields, groupFieldsByGroup, type FormConfig,
} from '../../api/form-config'
import { resolveDateBound } from '../../utils/fieldValidation'
const { t } = useI18n()
const message = useMessage()

// --- 需求字段管理配置 (resource=Demand) + 表单设置 (FormConfig) ---
const demandFields = ref<FieldDefinition[]>([])
const demandGroups = ref<FieldGroup[]>([])
const demandFormConfig = ref<FormConfig>({ fields: [], groupOrder: [] })
const dynamicValues = ref<Record<string, any>>({})
const formValues = reactive<Record<string, any>>({})

const MODEL_ATTR_MAP: Record<string, string> = {
  headcount: 'headcount',
  priority: 'priority',
  level: 'level',
  position_title: 'positionTitle',
  jd: 'jd',
  requirements: 'requirements',
  talent_level: 'talentLevel',
  talent_nature: 'talentNature',
  date_range: 'dateRange',
  sharers: 'sharers',
}

const SYSTEM_VALUE_GETTERS: Record<string, (d: any) => any> = {
  code: (d) => d?.code,
  title: (d) => d?.title || d?.name,
  state: (d) => d?.state || d?.demandStatus,
  demand_type: (d) => d?.demandType,
  department: (d) => d?.departmentName || d?.department?.name,
  hr: (d) => d?.hrName,
}

const FORM_MODEL_BINDING: Record<string, { prop: string; kind: 'text' | 'number' | 'select' | 'department' | 'textarea' | 'daterange' | 'multiselect' | 'richtext' }> = {
  title: { prop: 'name', kind: 'text' },
  department: { prop: 'departmentId', kind: 'department' },
  demand_type: { prop: 'demandType', kind: 'select' },
  headcount: { prop: 'positionCount', kind: 'number' },
  priority: { prop: 'priority', kind: 'select' },
  position_title: { prop: 'positionSeries', kind: 'text' },
  level: { prop: 'jobLevel', kind: 'text' },
  jd: { prop: 'description', kind: 'richtext' },
  requirements: { prop: 'requirements', kind: 'richtext' },
  talent_level: { prop: 'talentLevel', kind: 'text' },
  talent_nature: { prop: 'talentNature', kind: 'select' },
  date_range: { prop: 'dateRange', kind: 'daterange' },
  sharers: { prop: 'sharers', kind: 'multiselect' },
}
const EDIT_SKIP_KEYS = new Set(['code', 'state', 'approval_status'])

const loading = ref(false)
const demands = ref<any[]>([])
const departments = ref<any[]>([])
const selectedDemand = ref<any>(null)
const detailVisible = ref(false)
const modalVisible = ref(false)
const submitting = ref(false)
const detailLoading = ref(false)
const activeTab = ref('detail')

// 列表筛选 / 分页 / 选中
const searchText = ref('')
const keyword = ref('')
const departmentFilter = ref<string | null>(null)
const hrbpFilter = ref<string | null>(null)
const hiringManagerFilter = ref<string | null>(null)
const hiringManagerSuperiorFilter = ref<string | null>(null)
const priorityFilter = ref<string | null>(null)
const demandTypeFilter = ref<string | null>(null)
const showAdvanced = ref(false)
const pageSize = 12
const page = ref(1)
const selectedIds = ref<string[]>([])

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
  requirements: '',
  talentLevel: '',
  talentNature: '',
  dateRange: null,
  sharers: [],
})

// 双层状态页签定义（与后端 DemandState 对齐；审批状态为 state 派生值）
const processTabs = [
  { key: '', label: '全部' },
  { key: 'DRAFT', label: '草稿' },
  { key: 'PENDING', label: '待审批' },
  { key: 'APPROVED', label: '已通过' },
  { key: 'RECRUITING', label: '招聘中' },
  { key: 'PAUSED', label: '已暂停' },
  { key: 'COMPLETED', label: '已完成' },
  { key: 'CANCELLED', label: '已取消' },
  { key: 'REJECTED', label: '已驳回' },
]
const approvalTabs = [
  { key: '', label: '全部' },
  { key: 'PENDING', label: '审批中' },
  { key: 'REJECTED', label: '已拒绝' },
  { key: 'APPROVED', label: '已通过' },
]
const activeProcess = ref('')
const activeApproval = ref('')

const priorityOptions = [
  { label: 'P0-战略', value: 'P0' },
  { label: 'P1-重要', value: 'P1' },
  { label: 'P2-常规', value: 'P2' },
]

const departmentOptions = computed(() =>
  departments.value.map(d => ({ label: d.name, value: d.id })),
)

const demandTypeFilterOptions = computed(() => ([
  { label: '全部类型', value: null },
  { label: '社会招聘', value: 'SOCIAL' },
  { label: '校园招聘', value: 'CAMPUS' },
]))

// 人员筛选下拉项：从已加载需求里抽取去重姓名
function personNameOptions(key: string) {
  const set = new Set<string>()
  for (const d of demands.value) {
    const v = d[key]
    if (v) set.add(v)
  }
  return [...set].map(v => ({ label: v, value: v }))
}

// 批量变更人员：复用 hrbp 字段的 options_source（internal_user 已解析为 {value:id,label:姓名}）
const userPersonOptions = computed(() => {
  const f = demandFields.value.find(x => x.fieldKey === 'hrbp')
  return (f?.options || []).map((o: any) => ({ label: o.label || o.value, value: o.value }))
})

const processTabCounts = computed(() => {
  const c: Record<string, number> = {}
  for (const tab of processTabs) c[tab.key] = 0
  for (const d of demands.value) {
    const k = d.state || d.demandStatus || ''
    c['']++
    if (k in c) c[k]++
  }
  return c
})

const approvalTabCounts = computed(() => {
  const c: Record<string, number> = { '': demands.value.length }
  for (const d of demands.value) {
    const k = d.approvalStatus || d.approval_status || ''
    if (k in c) c[k]++
  }
  return c
})

const formBuckets = computed(() =>
  groupFieldsByGroup(
    mergeFields(demandFields.value, demandFormConfig.value).filter(m => m.enabled),
    demandFormConfig.value.groupOrder,
    demandGroups.value,
  ).filter(b => b.fields.length > 0),
)

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

const dynamicFormFields = computed(() =>
  editSections.value.flatMap(s => s.fields.filter(m => !m.binding).map(m => m.field)),
)

const WIDE_TYPES = ['RICH_TEXT', 'MULTILINE_TEXT', 'DATE_RANGE', 'ADDRESS']

const NUMBER_TYPES = ['NUMBER']
const OPTION_TYPES = ['SELECT', 'MULTISELECT', 'LIST_SINGLE', 'LIST_MULTI', 'PERSON', 'DEPARTMENT']
const DATE_TYPES = ['DATE', 'DATE_RANGE']
const PLAIN_TEXT_TYPES = ['TEXT', 'MULTILINE_TEXT', 'ADDRESS', 'URL']
const isNumberType = (t: string) => NUMBER_TYPES.includes(t)
const isOptionType = (t: string) => OPTION_TYPES.includes(t)
const isDateType = (t: string) => DATE_TYPES.includes(t)
const isPlainTextType = (t: string) => PLAIN_TEXT_TYPES.includes(t)
const isMultiType = (t: string) => t === 'MULTISELECT' || t === 'LIST_MULTI'

function asAttachmentList(v: unknown): AttachmentItem[] {
  if (Array.isArray(v)) return v as AttachmentItem[]
  if (typeof v === 'string' && v) return [{ id: v, name: v, url: v }]
  return []
}

function selectOptions(f: FieldDefinition): { label: string; value: any }[] {
  return (f.options || []).map((o: FieldOption) => ({
    label: o.label || o.value, value: o.value,
  }))
}

function editBindingOptions(f: FieldDefinition): { label: string; value: any }[] {
  if (f.fieldKey === 'demand_type') return demandTypeOptions
  if (f.fieldKey === 'priority') return priorityOptions
  return selectOptions(f)
}

// 编辑表单「需求类型」下拉项
const demandTypeOptions = [
  { label: '社会招聘', value: 'SOCIAL' },
  { label: '校园招聘', value: 'CAMPUS' },
]

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

function formDateRangeValue(prop: string): [number, number] | null {
  const v = formData.value[prop]
  if (!Array.isArray(v) || v.length !== 2) return null
  const a = Date.parse(v[0]); const b = Date.parse(v[1])
  return (isNaN(a) || isNaN(b)) ? null : [a, b]
}
function onFormDateRangeInput(prop: string, v: number | [number, number] | null) {
  if (v == null) { formData.value[prop] = null; return }
  formData.value[prop] = Array.isArray(v)
    ? [new Date(v[0]).toISOString(), new Date(v[1]).toISOString()]
    : new Date(v).toISOString()
}

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

function displayText(f: FieldDefinition, value: any): string {
  if (value == null || value === '') return '-'
  const t = f.fieldType
  if (t === 'BOOLEAN') return value ? '是' : '否'
  if (t === 'MULTISELECT' || t === 'LIST_MULTI') {
    if (!Array.isArray(value) || value.length === 0) return '-'
    return value.map((v: any) => optionLabel(f, v)).join('、')
  }
  if (OPTION_TYPES.includes(t)) return optionLabel(f, value)
  if (t === 'ATTACHMENT') {
    if (Array.isArray(value) && value.length) {
      return value.map((x: any) => x?.name || x?.url).filter(Boolean).join('、')
    }
    if (typeof value === 'string' && value) return value
    return '-'
  }
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

// 状态颜色（naive tag type + 整卡色条）
const getStatusType = (status: string): any => {
  const types: Record<string, string> = {
    'DRAFT': 'default',
    'PENDING': 'info',
    'APPROVED': 'success',
    'RECRUITING': 'success',
    'PAUSED': 'warning',
    'COMPLETED': 'default',
    'CANCELLED': 'error',
    'REJECTED': 'error',
  }
  return types[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'DRAFT': '草稿',
    'PENDING': '待审批',
    'APPROVED': '已通过',
    'RECRUITING': '招聘中',
    'PAUSED': '已暂停',
    'COMPLETED': '已完成',
    'CANCELLED': '已取消',
    'REJECTED': '已驳回',
  }
  return texts[status] || status
}

const getApprovalType = (status: string): any => {
  const types: Record<string, string> = {
    'NONE': 'default',
    'PENDING': 'info',
    'APPROVED': 'success',
    'REJECTED': 'error',
  }
  return types[status] || 'default'
}

const getApprovalText = (status: string) => {
  const texts: Record<string, string> = {
    'NONE': '未发起',
    'PENDING': '审批中',
    'APPROVED': '已通过',
    'REJECTED': '已拒绝',
  }
  return texts[status] || status
}

// 整卡状态色条
const STATE_BAR_COLOR: Record<string, string> = {
  DRAFT: 'var(--c-gray-600, #888780)',
  PENDING: 'var(--c-blue-600, #185FA5)',
  APPROVED: 'var(--c-teal-600, #0F6E56)',
  RECRUITING: 'var(--brand, #534AB7)',
  PAUSED: 'var(--c-amber-600, #854F0B)',
  COMPLETED: 'var(--c-green-600, #3B6D11)',
  CANCELLED: 'var(--c-red-600, #A32D2D)',
  REJECTED: 'var(--c-red-600, #A32D2D)',
}
function stateBarColor(state: string): string {
  return STATE_BAR_COLOR[state] || 'var(--c-gray-600, #888780)'
}

// FSM 流转：当前 state → 可执行的下一步动作
const TERMINAL_STATES = new Set(['COMPLETED', 'CANCELLED'])
const FSM_TRANSITIONS: Record<string, { action: string; label: string }[]> = {
  DRAFT: [{ action: 'submit', label: '提交审批' }],
  PENDING: [{ action: 'approve', label: '通过' }, { action: 'reject', label: '驳回' }],
  APPROVED: [{ action: 'start_recruiting', label: '开始招聘' }],
  RECRUITING: [{ action: 'pause', label: '暂停' }],
  PAUSED: [{ action: 'resume', label: '恢复' }],
}
function transitionOptions(state: string) {
  const base = FSM_TRANSITIONS[state] || []
  const extra: { action: string; label: string }[] = []
  if (!TERMINAL_STATES.has(state)) {
    extra.push({ action: 'complete', label: '标记完成' }, { action: 'cancel', label: '取消需求' })
  }
  return [...base, ...extra]
}
function transitionDropdownOptions(state: string) {
  return transitionOptions(state).map(o => ({ label: o.label, key: o.action }))
}
async function changeState(item: any, action: string) {
  try {
    await post(`/demands/${item.id}/transition`, { action, reason: '' })
    message.success('状态已更新')
    fetchDemands()
  } catch (error: any) {
    message.error(extractApiError(error, '操作失败'))
  }
}

// ===== 列表展示辅助 =====
function headcountOf(item: any): number {
  return item?.headcount ?? item?.positionCount ?? 0
}
function filledOf(item: any): number {
  return item?.filledCount ?? item?.filled_count ?? item?.hiredCount ?? 0
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
function priorityTagType(p: string): any {
  if (p === 'P0') return 'error'
  if (p === 'P1') return 'warning'
  if (p === 'P2') return 'info'
  return 'default'
}
// 起止日期按东八区（UTC+8）显示：后端存 UTC，浏览器时区不定，固定 +8h 换算后用 UTC 取值
function formatDemandDate(v: any): string {
  if (!v) return ''
  const ts = Date.parse(v)
  if (isNaN(ts)) return String(v)
  const d = new Date(ts + 8 * 3600 * 1000)
  return `${d.getUTCFullYear()}/${String(d.getUTCMonth() + 1).padStart(2, '0')}/${String(d.getUTCDate()).padStart(2, '0')}`
}
// 时间进度%：起止日期区间内当前所处比例
function timeProgress(item: any): number | null {
  const dr = item?.dateRange || item?.date_range
  if (!Array.isArray(dr) || dr.length !== 2) return null
  const s = Date.parse(dr[0]); const e = Date.parse(dr[1])
  if (isNaN(s) || isNaN(e) || e <= s) return null
  const now = Date.now()
  const pct = ((now - s) / (e - s)) * 100
  return Math.max(0, Math.min(100, Math.round(pct)))
}
function talentNatureText(v: string): string {
  const map: Record<string, string> = {
    FULLTIME: '全职', PARTTIME: '兼职', INTERN: '实习', OUTSOURCE: '外包',
  }
  return map[v] || v
}
function hasRequirement(item: any): boolean {
  return !!(item.talentNature || item.educationRequirement || item.experienceRequirement || item.salaryRange || item.positionSequence)
}

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

function clearFilters() {
  searchText.value = ''
  keyword.value = ''
  departmentFilter.value = null
  hrbpFilter.value = null
  hiringManagerFilter.value = null
  hiringManagerSuperiorFilter.value = null
  priorityFilter.value = null
  demandTypeFilter.value = null
  activeProcess.value = ''
  activeApproval.value = ''
  page.value = 1
}

// 前端筛选（列表已全量加载，与既有模式一致）
const processedDemands = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return demands.value.filter(d => {
    if (kw) {
      const hay = [d.code, d.title || d.name, d.departmentName, d.department?.name, d.hrName,
        d.hrbpName, d.hiringManagerName, d.hiringManagerSuperiorName]
        .filter(Boolean).join(' ').toLowerCase()
      if (!hay.includes(kw)) return false
    }
    if (departmentFilter.value && (d.department === departmentFilter.value || d.departmentId === departmentFilter.value)) {
      // department 列表返回的是 id
    }
    if (departmentFilter.value && d.department !== departmentFilter.value) return false
    if (hrbpFilter.value && d.hrbpName !== hrbpFilter.value) return false
    if (hiringManagerFilter.value && d.hiringManagerName !== hiringManagerFilter.value) return false
    if (hiringManagerSuperiorFilter.value && d.hiringManagerSuperiorName !== hiringManagerSuperiorFilter.value) return false
    if (priorityFilter.value && d.priority !== priorityFilter.value) return false
    if (demandTypeFilter.value && d.demandType !== demandTypeFilter.value) return false
    if (activeProcess.value && (d.state || d.demandStatus) !== activeProcess.value) return false
    if (activeApproval.value && (d.approvalStatus || d.approval_status) !== activeApproval.value) return false
    return true
  })
})

const pagedDemands = computed(() => {
  const start = (page.value - 1) * pageSize
  return processedDemands.value.slice(start, start + pageSize)
})

function onPageChange(p: number) {
  page.value = p
}

// 批量选中
const selectAllChecked = computed(() => processedDemands.value.length > 0 && selectedIds.value.length === processedDemands.value.length)
const selectSomeChecked = computed(() => selectedIds.value.length > 0 && !selectAllChecked.value)
function toggleCard(id: string, v: boolean) {
  if (v) {
    if (!selectedIds.value.includes(id)) selectedIds.value = [...selectedIds.value, id]
  } else {
    selectedIds.value = selectedIds.value.filter(x => x !== id)
  }
}
function toggleSelectAll(v: boolean) {
  if (v) selectedIds.value = processedDemands.value.map(d => d.id)
  else selectedIds.value = []
}

// 批量变更人员
const batchPeopleModal = ref(false)
const batchSaving = ref(false)
const batchPeople = reactive({ hrbp: '', hiringManager: '', hiringManagerSuperior: '' })
function openBatchPeople() {
  if (!selectedIds.value.length) {
    message.warning('请先勾选需求')
    return
  }
  batchPeople.hrbp = ''
  batchPeople.hiringManager = ''
  batchPeople.hiringManagerSuperior = ''
  batchPeopleModal.value = true
}
async function applyBatchPeople() {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  const payload: any = {}
  if (batchPeople.hrbp) payload.hrbp = batchPeople.hrbp
  if (batchPeople.hiringManager) payload.hiringManager = batchPeople.hiringManager
  if (batchPeople.hiringManagerSuperior) payload.hiringManagerSuperior = batchPeople.hiringManagerSuperior
  if (!Object.keys(payload).length) {
    message.warning('请至少选择一个要变更的人员')
    return
  }
  batchSaving.value = true
  let ok = 0
  let fail = 0
  for (const id of ids) {
    try {
      await saveDynamicFieldValues('Demand', id, payload)
      ok++
    } catch (e) {
      fail++
    }
  }
  batchSaving.value = false
  batchPeopleModal.value = false
  message.success(`已更新 ${ok} 条${fail ? `，失败 ${fail} 条` : ''}`)
  fetchDemands()
}

// 表格列定义
const columns = computed<DataTableColumns<any>>(() => [
  { title: t('pages.demand.DemandList.s79'), key: 'code', width: 120, render: (row: any) => h('span', { class: 'cell-code', title: row.code }, row.code) },
  { title: t('pages.demand.DemandList.s80'), key: 'name', minWidth: 180, ellipsis: { tooltip: true }, render: (row: any) => h('span', { title: row.title || row.name }, row.title || row.name) },
  { title: t('pages.demand.DemandList.s5'), key: 'department', width: 140, render: (row: any) => row.departmentName || row.department?.name || '-' },
  { title: t('pages.demand.DemandList.s6'), key: 'demandType', width: 90, render: (row: any) => h(NTag, { size: 'small', type: row.demandType === 'SOCIAL' ? 'info' : 'success' }, { default: () => (row.demandType === 'SOCIAL' ? '社会招聘' : '校园招聘') }) },
  { title: t('pages.demand.DemandList.s58'), key: 'priority', width: 90, render: (row: any) => h(NTag, { size: 'small', type: priorityTagType(row.priority) }, { default: () => row.priority || '-' }) },
  { title: t('pages.demand.DemandList.s20'), key: 'headcount', width: 100, align: 'right', render: (row: any) => headcountOf(row) },
  { title: t('pages.demand.DemandList.s8'), key: 'filled', width: 100, align: 'right', render: (row: any) => filledOf(row) },
  { title: t('pages.demand.DemandList.s81'), key: 'status', width: 100, render: (row: any) => h(NTag, { size: 'small', type: getStatusType(row.state || row.demandStatus) }, { default: () => getStatusText(row.state || row.demandStatus) }) },
  { title: t('pages.demand.DemandList.s82'), key: 'approval', width: 100, render: (row: any) => (row.approvalStatus || row.approval_status) ? h(NTag, { size: 'small', type: getApprovalType(row.approvalStatus || row.approval_status) }, { default: () => getApprovalText(row.approvalStatus || row.approval_status) }) : '-' },
  { title: t('pages.demand.DemandList.s83'), key: 'actions', width: 130, render: (row: any) => h('div', { class: 'cell-actions' }, [
    h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleCardClick(row) }, { default: () => t('pages.demand.DemandList.s9') }),
    h(NButton, { text: true, size: 'small', onClick: () => handleEdit(row) }, { default: () => t('pages.demand.DemandList.s50') }),
  ]) },
])

const drawerWidth = ref(680)
function syncDrawerWidth() {
  drawerWidth.value = Math.min(1080, Math.max(720, Math.round(window.innerWidth * 0.72)))
}

const fetchDemands = async () => {
  loading.value = true
  try {
    const res = await get('/demands/')
    if (res.data.success) {
      const list = (res.data.data || []).map(normalizeDemand)
      // 切回全量时清空过期选中
      const valid = new Set(list.map((d: any) => d.id))
      selectedIds.value = selectedIds.value.filter(id => valid.has(id))
      demands.value = list
    }
  } catch (error) {
    message.error('获取需求列表失败')
  } finally {
    loading.value = false
  }
}

function normalizeDemand(d: any) {
  return {
    ...d,
    name: d.title || d.name,
    positionCount: d.headcount ?? d.positionCount,
    demandStatus: d.state || d.demandStatus,
    demandType: d.demandType ?? d.demand_type,
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

const handleCardClick = async (item: any) => {
  selectedDemand.value = item
  detailVisible.value = true
  detailLoading.value = true
  dynamicValues.value = {}
  try {
    const res = await get(`/demands/${item.id}/`)
    const detail = res.data?.data ?? res.data
    if (detail && detail.id) {
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
    requirements: '',
    talentLevel: '',
    talentNature: '',
    dateRange: null,
    sharers: [],
  }
  resetFormValues()
  modalVisible.value = true
}

const handleEdit = async (item: any) => {
  let d: any = item || {}
  try {
    const res = await get(`/demands/${item.id}/`)
    const detail = res.data?.data ?? res.data
    if (detail && detail.id) d = detail
  } catch (error) {
    // 兜底用传入项
  }
  formData.value = {
    id: d.id ?? item?.id ?? '',
    name: d.title ?? d.name ?? '',
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
    talentLevel: d.talentLevel ?? d.talent_level ?? '',
    talentNature: d.talentNature ?? d.talent_nature ?? '',
    dateRange: Array.isArray(d.dateRange) ? d.dateRange : (Array.isArray(d.date_range) ? d.date_range : null),
    sharers: Array.isArray(d.sharers) ? d.sharers : [],
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

const handleSubmitFromCard = (item: any) => {
  selectedDemand.value = item
  handleSubmitApproval()
}

const handleSave = async () => {
  if (!formData.value.name || !formData.value.departmentId) {
    message.warning('请填写必填项')
    return
  }

  const dyn: Record<string, any> = {}
  for (const f of dynamicFormFields.value) {
    const v = formValues[f.fieldKey]
    if (v === '' || v == null || (Array.isArray(v) && v.length === 0)) continue
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
      talent_level: formData.value.talentLevel || '',
      talent_nature: formData.value.talentNature || '',
      date_range: formData.value.dateRange || [],
      sharers: formData.value.sharers || [],
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

    if (demandId && Object.keys(dyn).length) {
      const sv: any = await saveDynamicFieldValues('Demand', demandId, dyn)
      if (sv && Array.isArray(sv.skipped) && sv.skipped.length) {
        message.warning(`部分字段未保存(字段定义缺失): ${sv.skipped.join('、')}`)
      }
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
  background: transparent;
  animation: wb-fade-up var(--duration-slow) var(--ease-out) both;
}

/* ① 高级筛选区 */
.filter-region {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
}
.filter-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.filter-row--advanced {
  padding-top: var(--space-2);
  border-top: 1px dashed var(--glass-border);
}

/* ② 双层状态页签（两组分类两端对齐） */
.tab-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--space-3);
}
.tab-group {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-wrap: wrap;
}
.tab-divider {
  width: 1px;
  align-self: stretch;
  background: var(--glass-border);
}
.tab-badge {
  margin-left: 4px;
}

/* ③ 批量操作栏 */
.batch-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-3);
  background: var(--glass-bg-input);
  border-radius: var(--radius-md);
}

/* ④ 卡片列表 */
.demand-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-3);
}

.demand-card {
  position: relative;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: var(--space-3);
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-left: 4px solid var(--state-bar, var(--c-gray-600, #888780));
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
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
.card-check {
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

/* 标题行 */
.card-headline {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  min-width: 0;
}
.demand-code {
  color: var(--c-info-deep);
  font-weight: 600;
  font-size: var(--fs-13);
}
.demand-title {
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}
.headline-spacer {
  flex: 1;
}
.state-dropdown {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

/* 三栏 */
.card-cols {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-4);
  align-items: start;
}
.card-col {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}
.card-col--progress {
  gap: var(--space-1);
}

.req-line {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
.req-chip {
  font-size: var(--fs-12);
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: var(--g1);
  color: var(--ink-soft);
  white-space: nowrap;
}
.req-chip--muted {
  color: var(--ink-faint);
}

.people-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.people-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--fs-13);
}
.people-label {
  flex: none;
  width: 88px;
  color: var(--ink-faint);
}
.people-value {
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--fs-13);
}
.meta-row--top {
  align-items: flex-start;
}
.meta-label {
  flex: none;
  width: 64px;
  color: var(--ink-faint);
}
.meta-value {
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.meta-muted {
  color: var(--ink-faint);
}
.position-tag {
  background: var(--c-info-soft);
  color: var(--c-info-deep);
}

/* 右栏进度 */
.date-line {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--fs-13);
  color: var(--ink-soft);
}
.date-icon {
  font-size: 14px;
  color: var(--ink-faint);
}
.progress-line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.bar {
  flex: 1;
  height: 6px;
  border-radius: var(--radius-pill);
  background: var(--glass-bg-input);
  overflow: hidden;
}
.bar > span {
  display: block;
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--brand);
  transition: width var(--duration-base) var(--ease-out);
}
.progress-pct {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  white-space: nowrap;
}
.progress-pct--warn {
  color: var(--c-red-deep);
  font-weight: 600;
}
.funnel {
  display: flex;
  gap: var(--space-4);
  margin-top: 2px;
}
.funnel-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.funnel-num {
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
  line-height: 1.3;
}
.funnel-item--ok .funnel-num {
  color: var(--c-green-deep);
}
.funnel-label {
  font-size: var(--fs-12);
  color: var(--ink-faint);
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
  grid-template-columns: 1fr;
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
  color: var(--c-info-deep);
  font-weight: 600;
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
  color: var(--c-info-deep);
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.overview-item {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  min-width: 0;
  padding: var(--space-1) var(--space-3);
  background: var(--glass-bg-input);
  border-radius: var(--radius-sm);
}
.ov-num {
  font-size: var(--fs-16);
  font-weight: 600;
  line-height: 1.3;
  color: var(--ink);
}
.ov-label {
  font-size: var(--fs-12);
  line-height: 1.3;
  color: var(--ink-faint);
  white-space: nowrap;
}
.overview-bar__progress {
  grid-column: 1 / -1;
  margin-top: var(--space-1);
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
.batch-hint {
  margin: 0;
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

/* 响应式：窄屏三栏塌缩为单列 */
@media (max-width: 1100px) {
  .card-cols {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 768px) {
  .form-grid { grid-template-columns: 1fr; }
  .overview-bar { grid-template-columns: repeat(2, 1fr); }
  .demand-card { padding: var(--space-3) var(--space-4); }
  .demand-title { white-space: normal; max-width: none; }
}
</style>
