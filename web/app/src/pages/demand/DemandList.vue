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
              <div class="detail-section">
                <div class="section-header">
                  <span class="section-title">系统信息</span>
                </div>
                <div class="info-grid">
                  <div class="info-item">
                    <span class="info-label">需求编号</span>
                    <span class="info-value code">{{ selectedDemand.code }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">需求类型</span>
                    <span class="info-value">
                      <n-tag :type="selectedDemand.demandType === 'SOCIAL' ? 'info' : 'success'" size="small">
                        {{ selectedDemand.demandType === 'SOCIAL' ? '社会招聘' : '校园招聘' }}
                      </n-tag>
                    </span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">需求状态</span>
                    <span class="info-value">
                      <n-tag :type="getStatusType(selectedDemand.state)" size="small">
                        {{ getStatusText(selectedDemand.state) }}
                      </n-tag>
                    </span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">审批状态</span>
                    <span class="info-value">
                      <n-tag :type="approvalInfo.type" size="small">{{ approvalInfo.text }}</n-tag>
                    </span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">所属部门</span>
                    <span class="info-value">{{ selectedDemand.departmentName || selectedDemand.department?.name || '-' }}</span>
                  </div>
                </div>
              </div>

              <!-- 按配置分组渲染的字段 -->
              <div v-for="grp in groupedFields" :key="grp.name" class="detail-section">
                <div class="section-header">
                  <span class="section-title">{{ grp.name }}</span>
                </div>
                <div class="info-grid">
                  <div v-for="f in grp.fields" :key="f.id" class="info-item">
                    <span class="info-label">{{ f.label }}</span>
                    <span class="info-value">{{ displayText(f, fieldValue(f)) }}</span>
                  </div>
                </div>
              </div>

              <!-- 描述信息 (JD / 任职要求, 核心内容, 不受字段管理显隐影响) -->
              <div class="detail-section">
                <div class="section-header">
                  <span class="section-title">描述信息</span>
                </div>
                <div class="desc-content">
                  <div class="desc-item">
                    <span class="desc-label">需求描述</span>
                    <div class="desc-value">{{ selectedDemand.jd || '-' }}</div>
                  </div>
                  <div class="desc-item">
                    <span class="desc-label">候选人要求</span>
                    <div class="desc-value">{{ selectedDemand.requirements || '-' }}</div>
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
        <n-form-item label="需求名称" required>
          <n-input v-model:value="formData.name" placeholder="请输入需求名称" />
        </n-form-item>
        <n-form-item label="所属部门" required>
          <n-select
            v-model:value="formData.departmentId"
            placeholder="请选择部门"
            :options="departmentOptions"
          />
        </n-form-item>
        <n-form-item label="需求类型" required>
          <n-select
            v-model:value="formData.demandType"
            placeholder="请选择"
            :options="demandTypeOptions"
          />
        </n-form-item>
        <n-form-item label="需求人数">
          <n-input-number v-model:value="formData.positionCount" :min="1" :max="100" style="width: 100%" />
        </n-form-item>
        <n-form-item label="优先级">
          <n-select v-model:value="formData.priority" :options="priorityOptions" style="width: 100%" />
        </n-form-item>
        <n-form-item label="职位系列">
          <n-input v-model:value="formData.positionSeries" placeholder="如：技术、产品、运营" />
        </n-form-item>
        <n-form-item label="职级">
          <n-input v-model:value="formData.jobLevel" placeholder="如：P6、M1" />
        </n-form-item>
        <n-form-item label="需求描述">
          <n-input v-model:value="formData.description" type="textarea" :rows="3" placeholder="请输入需求描述" />
        </n-form-item>
        <n-form-item label="候选人要求">
          <n-input v-model:value="formData.requirements" type="textarea" :rows="3" placeholder="请输入候选人要求" />
        </n-form-item>

        <!-- ★ 2026-09-24 需求 4: 动态(非模型映射)配置字段录入 -->
        <template v-if="dynamicFormFields.length">
          <n-divider>扩展字段</n-divider>
          <n-form-item
            v-for="f in dynamicFormFields"
            :key="f.id"
            :label="f.label"
            :required="f.isRequired"
          >
            <!-- 文本类 -->
            <n-input
              v-if="isPlainTextType(f.fieldType)"
              v-model:value="formValues[f.fieldKey]"
              :type="f.fieldType === 'MULTILINE_TEXT' ? 'textarea' : 'text'"
              :placeholder="f.placeholder || ''"
              style="width: 100%"
            />
            <!-- 数字类 -->
            <n-input-number
              v-else-if="isNumberType(f.fieldType)"
              v-model:value="formValues[f.fieldKey]"
              :min="(f.validation as any)?.min ?? undefined"
              :max="(f.validation as any)?.max ?? undefined"
              :placeholder="f.placeholder || '请输入数字'"
              style="width: 100%"
            />
            <!-- 选项类 (含 人员/部门 引用) -->
            <n-select
              v-else-if="isOptionType(f.fieldType)"
              v-model:value="formValues[f.fieldKey]"
              :options="selectOptions(f)"
              :multiple="isMultiType(f.fieldType)"
              :placeholder="f.placeholder || '请选择'"
              style="width: 100%"
            />
            <!-- 日期 / 日期范围 -->
            <n-date-picker
              v-else-if="isDateType(f.fieldType)"
              :value="dateValue(f)"
              :type="f.fieldType === 'DATE_RANGE' ? 'daterange' : 'date'"
              clearable
              style="width: 100%"
              @update:value="(v: number | [number, number] | null) => onDateInput(f, v)"
            />
            <!-- 布尔 -->
            <n-switch v-else-if="f.fieldType === 'BOOLEAN'" v-model:value="formValues[f.fieldKey]" />
            <!-- 附件 / 其他: URL 文本 -->
            <n-input
              v-else
              v-model:value="formValues[f.fieldKey]"
              :placeholder="f.placeholder || '请输入'"
              style="width: 100%"
            />
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

import {
  listFields, getDynamicFieldValues, saveDynamicFieldValues, extractApiError,
  type FieldDefinition, type FieldOption,
} from '../../api/dynamic-field'
const { t } = useI18n()
const message = useMessage()

// --- 需求字段管理配置 (resource=Demand) ---
// ★ 2026-09-24 需求 4: 详情页字段受「系统设置 → 需求字段管理」控制。
// 这些字段定义驱动详情页分组渲染与表单扩展字段录入。
const demandFields = ref<FieldDefinition[]>([])
const dynamicValues = ref<Record<string, any>>({})
const formValues = reactive<Record<string, any>>({})

// 系统固定字段 / 核心描述字段: 不进入「按配置分组」渲染, 避免与下方固定区块重复。
const RESERVED_KEYS = new Set(['code', 'demand_type', 'state', 'jd', 'requirements'])
// 编辑表单已由硬编码输入覆盖的模型字段: 不进入「扩展字段」动态渲染, 避免重复录入。
const FORM_COVERED_KEYS = new Set([
  'demand_type', 'headcount', 'position_title', 'level', 'priority', 'jd', 'requirements',
])

// 模型映射字段: field_key → 在 demand 详情对象上的属性名(camelCase, 经后端渲染)。
// 命中则取 demand 模型值; 否则取 DynamicFieldValue。
const MODEL_ATTR_MAP: Record<string, string> = {
  headcount: 'headcount',
  priority: 'priority',
  level: 'level',
  position_title: 'positionTitle',
}

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

// 详情页「按配置分组」的可见字段 (剔除系统/保留字段, 按分组聚合并按 order_index 排序)
const groupedFields = computed(() => {
  const visible = demandFields.value.filter(
    f => f.isVisible !== false && !RESERVED_KEYS.has(f.fieldKey),
  )
  const order: string[] = []
  const buckets: Record<string, FieldDefinition[]> = {}
  for (const f of visible) {
    const g = f.groupName || '其他'
    if (!buckets[g]) { buckets[g] = []; order.push(g) }
    buckets[g].push(f)
  }
  return order.map(name => ({
    name,
    fields: buckets[name].slice().sort((a, b) => (a.orderIndex ?? 0) - (b.orderIndex ?? 0)),
  }))
})

// 编辑表单的「扩展字段」(配置中可见、且未被硬编码表单覆盖的字段)
const dynamicFormFields = computed(() =>
  demandFields.value
    .filter(f => f.isVisible !== false && !FORM_COVERED_KEYS.has(f.fieldKey))
    .slice()
    .sort((a, b) => (a.orderIndex ?? 0) - (b.orderIndex ?? 0)),
)

// --- 类型判断 (与 DynamicFieldEntry.vue 对齐) ---
const NUMBER_TYPES = ['NUMBER']
const OPTION_TYPES = ['SELECT', 'MULTISELECT', 'LIST_SINGLE', 'LIST_MULTI', 'PERSON', 'DEPARTMENT']
const DATE_TYPES = ['DATE', 'DATE_RANGE']
const PLAIN_TEXT_TYPES = ['TEXT', 'MULTILINE_TEXT', 'ADDRESS', 'URL', 'RICH_TEXT']
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

// 详情页某字段的取值: 模型映射字段取 demand 对象, 否则取 DynamicFieldValue
function fieldValue(f: FieldDefinition): any {
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
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

// 审批状态: 由需求状态推导 (DRAFT/PENDING/APPROVED...)
const approvalInfo = computed(() => {
  const s = selectedDemand.value?.state
  if (s === 'PENDING') return { text: '审批中', type: 'info' as const }
  if (s === 'APPROVED' || s === 'RECRUITING' || s === 'PAUSED' || s === 'COMPLETED') return { text: '已通过', type: 'success' as const }
  if (s === 'REJECTED') return { text: '已驳回', type: 'error' as const }
  return { text: '未发起', type: 'default' as const }
})

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

const loadDemandFields = async () => {
  try {
    demandFields.value = await listFields('Demand')
  } catch (error) {
    // 配置加载失败不应阻断详情/列表; 仅降级为不渲染配置字段
    demandFields.value = []
  }
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

.desc-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.desc-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.desc-label {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

/* v2 bugfix P0-C: #fafafa → var(--glass-bg-input) 让极光底透出 */
.desc-value {
  font-size: var(--fs-14);
  color: var(--ink);
  line-height: 1.6;
  background: var(--glass-bg-input);
  padding: var(--space-3);
  border-radius: 4px;
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
