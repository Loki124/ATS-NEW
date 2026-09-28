<template>
  <div class="demand-container">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.demand.DemandList.s1') }}</h1>
      <n-space>
        <n-input
          v-model:value="keyword"
          :placeholder="t('pages.demand.DemandList.s2')"
          style="width: 240px"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <n-select
          v-model:value="filterStatus"
          placeholder="需求状态"
          style="width: 120px"
          clearable
          :options="statusFilterOptions"
          @update:value="handleFilter"
        />
        <n-button type="primary" @click="handleCreate">
          <template #icon><n-icon :component="AddOutline" /></template>
          创建需求
        </n-button>
      </n-space>
    </div>

    <!-- 卡片列表 -->
    <div class="demand-list">
      <div
        v-for="item in demands"
        :key="item.id"
        class="demand-card"
        :class="{ 'selected': selectedDemand?.id === item.id }"
      >
        <div class="card-left" @click="handleCardClick(item)">
          <div class="card-main">
            <div class="card-title">
              <span class="demand-code">{{ item.code }}</span>
              <n-tag :type="getStatusType(item.demandStatus)" size="small" class="status-tag">
                {{ getStatusText(item.demandStatus) }}
              </n-tag>
              <n-tag :type="getApprovalType(item.approvalStatus)" size="small" class="status-tag">
                {{ getApprovalText(item.approvalStatus) }}
              </n-tag>
            </div>
            <div class="demand-name">{{ item.name }}</div>
            <div class="demand-meta">
              <span class="meta-item">
                <span class="label">部门：</span>
                <span class="value">{{ item.departmentName || item.department?.name || '-' }}</span>
              </span>
              <span class="meta-item">
                <span class="label">类型：</span>
                <n-tag :type="item.demandType === 'SOCIAL' ? 'info' : 'success'" size="small">
                  {{ item.demandType === 'SOCIAL' ? '社招' : '校招' }}
                </n-tag>
              </span>
            </div>
          </div>
          <div class="card-stats">
            <div class="stat-item">
              <span class="stat-value">{{ item._count?.positions || 0 }}</span>
              <span class="stat-label">职位</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-value">{{ item.hiredCount || 0 }}</span>
              <span class="stat-label">入职</span>
            </div>
          </div>
        </div>
        <div class="card-right">
          <!-- ★ 2026-08-23 V3 §四P0 第5项 (T7.4)：操作列下拉化，对齐 CandidateList 模式 -->
          <n-button text type="primary" size="small" @click.stop="handleCardClick(item)">详情</n-button>
          <n-dropdown
            trigger="click"
            :options="[{ label: '编辑', key: 'edit' }]"
            @select="(k: string) => onDemandRowAction(k, item)"
          >
            <n-button text size="small">更多 ⌄</n-button>
          </n-dropdown>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-spinner">
      <n-spin />
    </div>

    <div v-if="demands.length === 0 && !loading" class="empty-wrapper">
      <n-empty description="暂无需求数据">
        <template #extra>
          <n-button type="primary" @click="handleCreate">创建需求</n-button>
        </template>
      </n-empty>
    </div>

    <!-- 详情抽屉 -->
    <n-drawer
      v-model:show="detailVisible"
      :width="680"
      placement="right"
    >
      <n-drawer-content
        :title="selectedDemand ? (selectedDemand.code + ' ' + selectedDemand.name) : ''"
        closable
      >
        <template v-if="selectedDemand">
          <!-- 基本信息 -->
          <n-tabs v-model:value="activeTab" type="line" class="detail-tabs">
            <n-tab-pane name="detail" tab="详情">
              <!-- ★ 2026-09-24 需求 4: 详情字段受「系统设置 → 需求字段管理」控制。
                   系统固定字段(编号/类型/状态/审批状态/部门) + 按配置分组渲染其余字段；
                   模型映射字段(如 headcount/priority/level/positionTitle)取 demand 对象，
                   其余扩展字段取 DynamicFieldValue。 -->
              <!-- ★ 2026-09-28 (兵哥): 详情展示完全由「招聘需求表单设置」驱动 —
                   分组顺序 / 字段显隐 / 必填与表单设置实时一致; 系统字段/模型字段
                   取 demand 对象, 扩展字段取 DynamicFieldValue; 不渲染任何配置外区块
                   (审批状态在列表卡片与流程记录中可见, 招聘进度为派生统计)。 -->
              <!-- 配置驱动的分组字段 (系统字段 + 模型字段 + 扩展字段) -->
              <div v-for="b in formBuckets" :key="b.key" class="detail-section">
                <div class="section-header">
                  <span class="section-title">{{ b.group?.name || '其他' }}</span>
                </div>
                <div class="info-grid">
                  <div v-for="m in b.fields" :key="m.field.id" class="info-item">
                    <span class="info-label">{{ m.field.label }}</span>
                    <span v-if="m.field.fieldKey === 'state'" class="info-value">
                      <n-tag :type="getStatusType(fieldValue(m.field))" size="small">
                        {{ getStatusText(fieldValue(m.field)) }}
                      </n-tag>
                    </span>
                    <span v-else-if="m.field.fieldKey === 'demand_type'" class="info-value">
                      <n-tag :type="fieldValue(m.field) === 'SOCIAL' ? 'info' : 'success'" size="small">
                        {{ fieldValue(m.field) === 'SOCIAL' ? '社会招聘' : '校园招聘' }}
                      </n-tag>
                    </span>
                    <span v-else class="info-value">{{ displayText(m.field, fieldValue(m.field)) }}</span>
                  </div>
                </div>
              </div>

              <div class="detail-section">
                <div class="section-header">
                  <span class="section-title">招聘进度</span>
                </div>
                <div class="progress-stats">
                  <div class="progress-stat">
                    <span class="stat-num">{{ selectedDemand._count?.positions || 0 }}</span>
                    <span class="stat-label">关联职位</span>
                  </div>
                  <div class="progress-stat">
                    <span class="stat-num">{{ selectedDemand.positionCount || 0 }}</span>
                    <span class="stat-label">需求人数</span>
                  </div>
                  <div class="progress-stat">
                    <span class="stat-num">{{ selectedDemand.hiredCount || 0 }}</span>
                    <span class="stat-label">已入职</span>
                  </div>
                  <div class="progress-stat">
                    <span class="stat-num">{{ selectedDemand.onBoardCount || 0 }}</span>
                    <span class="stat-label">待入职</span>
                  </div>
                </div>
              </div>
            </n-tab-pane>

            <n-tab-pane name="candidates" tab="候选人">
              <n-empty description="暂无候选人数据" />
            </n-tab-pane>

            <n-tab-pane name="profile" tab="职位画像">
              <div class="profile-section">
                <div class="profile-header">
                  <span class="profile-title">职位画像</span>
                  <span class="profile-subtitle">基于需求信息生成</span>
                </div>

                <div class="profile-content">
                  <!-- 硬性要求 -->
                  <div class="profile-block">
                    <div class="block-header">
                      <span class="block-title">硬性要求</span>
                    </div>
                    <div class="block-items">
                      <div class="profile-item">
                        <span class="item-icon">🎓</span>
                        <span class="item-label">学历要求</span>
                        <span class="item-value">{{ getEducationText(selectedDemand) }}</span>
                      </div>
                      <div class="profile-item">
                        <span class="item-icon">💼</span>
                        <span class="item-label">工作经验</span>
                        <span class="item-value">{{ getExperienceText(selectedDemand) }}</span>
                      </div>
                      <div class="profile-item">
                        <span class="item-icon"><n-icon :component="BusinessOutline" :size="16" /></span>
                        <span class="item-label">职级要求</span>
                        <span class="item-value">{{ selectedDemand.level || '-' }}</span>
                      </div>
                      <div class="profile-item">
                        <span class="item-icon"><n-icon :component="PeopleOutline" :size="16" /></span>
                        <span class="item-label">招聘人数</span>
                        <span class="item-value">{{ selectedDemand.positionCount }}人</span>
                      </div>
                    </div>
                  </div>

                  <!-- 技能要求 -->
                  <div class="profile-block">
                    <div class="block-header">
                      <span class="block-title">技能要求</span>
                    </div>
                    <div class="skills-list">
                      <n-tag v-for="skill in getSkillsList(selectedDemand)" :key="skill" type="info" size="small">{{ skill }}</n-tag>
                      <span v-if="getSkillsList(selectedDemand).length === 0" class="no-data">暂无技能要求</span>
                    </div>
                  </div>

                  <!-- 加分项 -->
                  <div class="profile-block">
                    <div class="block-header">
                      <span class="block-title">加分项</span>
                    </div>
                    <div class="bonus-list">
                      <div class="bonus-item">
                        <span class="bonus-icon">🌟</span>
                        <span>知名企业工作经历</span>
                      </div>
                      <div class="bonus-item">
                        <span class="bonus-icon">🌟</span>
                        <span>海外留学背景</span>
                      </div>
                      <div class="bonus-item">
                        <span class="bonus-icon">🌟</span>
                        <span>相关行业经验</span>
                      </div>
                    </div>
                  </div>

                  <!-- 工作地点 -->
                  <div class="profile-block">
                    <div class="block-header">
                      <span class="block-title">工作地点</span>
                    </div>
                    <div class="location-info">
                      <span class="location-icon">📍</span>
                      <span class="location-text">总部 / 远程可选</span>
                    </div>
                  </div>
                </div>
              </div>
            </n-tab-pane>

            <n-tab-pane name="records" tab="流程记录">
              <n-empty description="暂无流程记录" />
            </n-tab-pane>
          </n-tabs>
        </template>

        <template #footer>
          <n-space v-if="selectedDemand">
            <n-button
              v-if="selectedDemand.state === 'DRAFT'"
              type="primary"
              @click="handleSubmitApproval"
            >
              提交审批
            </n-button>
            <n-button @click="handleEdit(selectedDemand)">编辑</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <!-- 创建/编辑弹窗 -->
    <n-modal
      v-model:show="modalVisible"
      preset="card"
      :title="formData.id ? '编辑需求' : '创建需求'"
      :style="{ width: '600px' }"
      :mask-closable="false"
    >
      <n-form :model="formData" label-placement="left" :label-width="100">
        <!-- ★ 2026-09-28 (兵哥): 编辑表单统一由「招聘需求表单设置」驱动 —
             分组顺序 / 字段显隐 / 必填与表单设置实时一致; 模型字段绑 formData, 扩展字段绑 formValues。 -->
        <template v-for="s in editSections" :key="s.key">
          <div v-if="editSections.length > 1" class="form-group-header">{{ s.name }}</div>
          <n-form-item
            v-for="item in s.fields"
            :key="item.field.fieldKey"
            :label="item.field.label"
            :required="item.required"
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
                placeholder="请选择部门"
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
                  placeholder="最小值"
                  style="flex: 1; min-width: 0"
                />
                <span>~</span>
                <n-input-number
                  v-model:value="formValues[item.field.fieldKey].max"
                  :min="(item.field.validation as any)?.min ?? undefined"
                  :max="(item.field.validation as any)?.max ?? undefined"
                  placeholder="最大值"
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
      </n-form>

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="modalVisible = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSave">保存需求</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, onMounted } from 'vue'
import { useMessage, NDropdown } from 'naive-ui'
import { AddOutline, SearchOutline, BusinessOutline, PeopleOutline } from '@vicons/ionicons5'
import { get, post, put } from '../../api/auth'
import dayjs from 'dayjs'
import RichEditor from '../../components/RichEditor.vue'

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
const keyword = ref('')
const filterStatus = ref<string | null>('')
const activeTab = ref('detail')

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

const demandTypeOptions = [
  { label: '社会招聘', value: 'SOCIAL' },
  { label: '校园招聘', value: 'CAMPUS' },
]

const priorityOptions = [
  { label: 'P0-战略', value: 'P0' },
  { label: 'P1-重要', value: 'P1' },
  { label: 'P2-常规', value: 'P2' },
]

const departmentOptions = computed(() =>
  departments.value.map(d => ({ label: d.name, value: d.id }))
)

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
// 相对表达式在运行时解析为具体日期, 使「大于当前时间 N 天」永远相对当下。
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

const formatDate = (date: string) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD')
}

const getEducationText = (demand: any) => {
  if (!demand) return '-'
  if (demand.demandType === 'CAMPUS') return '本科及以上'
  return '大专及以上'
}

const getExperienceText = (demand: any) => {
  if (!demand) return '-'
  if (demand.jobLevel) {
    if (demand.jobLevel.includes('P4') || demand.jobLevel.includes('P5')) return '1-3年'
    if (demand.jobLevel.includes('P6')) return '3-5年'
    if (demand.jobLevel.includes('P7') || demand.jobLevel.includes('P8')) return '5年以上'
  }
  return '不限'
}

const getSkillsList = (demand: any) => {
  if (!demand) return []
  const skills: string[] = []
  if (demand.positionSeries) {
    if (demand.positionSeries.includes('技术') || demand.positionSeries.includes('研发')) {
      skills.push('JavaScript/TypeScript', 'Vue/React', 'Node.js', '数据库', 'API设计')
    }
    if (demand.positionSeries.includes('产品')) {
      skills.push('需求分析', '产品设计', '原型工具', '数据分析', '项目管理')
    }
    if (demand.positionSeries.includes('运营')) {
      skills.push('内容运营', '用户运营', '活动策划', '数据分析', '文案撰写')
    }
  }
  return skills.length > 0 ? skills : []
}

const fetchDemands = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (keyword.value) params.keyword = keyword.value
    if (filterStatus.value) params.status = filterStatus.value

    const res = await get('/demands/', params)
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

// ★ V3 §四P0 第5项 (T7.4)：卡片操作列下拉分发
const onDemandRowAction = (key: string, item: any) => {
  if (key === 'edit') handleEdit(item)
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

const handleSearch = () => fetchDemands()
const handleFilter = () => fetchDemands()

onMounted(() => {
  fetchDemands()
  fetchDepartments()
  loadDemandFields()
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

.demand-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.demand-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: var(--space-4) 20px;
  transition: all var(--duration-base) var(--ease-out);
  border: 2px solid transparent;
}

.demand-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.demand-card.selected {
  border-color: var(--brand);
}

.card-left {
  display: flex;
  align-items: center;
  flex: 1;
  cursor: pointer;
}

.card-main {
  flex: 1;
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: 6px;
}

/* v2 bugfix P0-B: #1890ff → var(--c-info) */
.demand-code {
  color: var(--c-info);
  font-weight: 600;
  font-size: var(--fs-14);
}

.status-tag {
  margin-right: 0;
}

.demand-name {
  font-size: var(--fs-15);
  font-weight: 500;
  color: var(--ink);
  margin-bottom: 6px;
}

.demand-meta {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.meta-item {
  display: flex;
  align-items: center;
  font-size: var(--fs-13);
}

.meta-item .label {
  color: var(--ink-faint);
}

.meta-item .value {
  color: var(--ink-soft);
}

.card-stats {
  display: flex;
  align-items: center;
  margin-left: 40px;
  padding-left: 40px;
  border-left: 1px solid var(--border-hairline);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 48px;
}

.stat-value {
  font-size: var(--fs-18);
  font-weight: 600;
  color: var(--ink);
}

.stat-label {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

/* v2 bugfix P0-B: #f0f0f0 → var(--border-hairline) */
.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--border-hairline);
  margin: 0 var(--space-4);
}

.card-right {
  display: flex;
  gap: var(--space-2);
  margin-left: var(--space-6);
}

.loading-spinner {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.empty-wrapper {
  display: flex;
  justify-content: center;
  padding: 60px;
}

/* v2 bugfix P0-B: #1890ff → var(--c-info) */
.drawer-code {
  color: var(--c-info);
  font-weight: 600;
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

/* 编辑表单: 按表单设置分组渲染时的分组标题 (与详情页 section-title 风格一致) */
.form-group-header {
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

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3) var(--space-6);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-label {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

.info-value {
  font-size: var(--fs-14);
  color: var(--ink);
}

/* v2 bugfix P0-B: #1890ff → var(--c-info) */
.info-value.code {
  color: var(--c-info);
  font-weight: 500;
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
  border-radius: 8px;
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

/* 职位画像样式 */
.profile-section {
  padding-bottom: var(--space-6);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: 20px;
}

.profile-title {
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
}

.profile-subtitle {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* v2 bugfix P0-C: #fafafa → var(--glass-bg-input) */
.profile-block {
  background: var(--glass-bg-input);
  border-radius: 8px;
  padding: var(--space-4);
}

.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.block-title {
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink);
}

.block-items {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.profile-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.item-icon {
  font-size: var(--fs-14);
}

.item-label {
  font-size: var(--fs-13);
  color: var(--ink-faint);
  min-width: 70px;
}

.item-value {
  font-size: var(--fs-13);
  color: var(--ink);
  font-weight: 500;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.no-data {
  font-size: var(--fs-13);
  color: var(--ink-faint);
}

.salary-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.salary-range {
  display: flex;
  align-items: center;
}

/* v2 bugfix P0-B: #1890ff → var(--c-info) */
.salary-num {
  font-size: var(--fs-20);
  font-weight: 600;
  color: var(--c-info);
}

.salary-separator {
  font-size: var(--fs-16);
  color: var(--ink-faint);
  margin: 0 var(--space-1);
}

.salary-unit {
  font-size: var(--fs-13);
  color: var(--ink-faint);
}

.bonus-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.bonus-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--fs-13);
  color: var(--ink-soft);
}

.bonus-icon {
  font-size: var(--fs-12);
}

.location-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.location-icon {
  font-size: var(--fs-14);
}

.location-text {
  font-size: var(--fs-13);
  color: var(--ink);
}

/* === v2 响应式补丁 === */
@media (max-width: 1280px) {
  .demand-container { padding: var(--space-4); }
  .page-title { font-size: var(--text-h2); }
  :deep(.n-data-table-wrapper) {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
@media (max-width: 768px) {
  .demand-container { padding: var(--space-3); }
  .page-header { flex-direction: column; align-items: stretch; gap: var(--space-3); }
  .stats-row { grid-template-columns: repeat(2, 1fr) !important; }
}
@media (max-width: 480px) {
  .stats-row { grid-template-columns: 1fr !important; }
}
</style>
