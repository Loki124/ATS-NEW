<template>
  <div class="page-container">
    <div class="page-body">
      <!-- 二期：去掉页面标题与提示条 —— 页面身份由顶部导航「校招生管理」承载，
           标题下的说明文字与权限提示与本页操作无关，占据首屏且易被误读为限制。 -->

      <div class="toolbar">
        <n-select
          v-model:value="filterBu"
          :options="buChoices"
          placeholder="全部部门"
          clearable
          class="filter-select"
        />
        <!-- 2026-10-22 兵哥指令：常驻筛选项 = 部门 / 轮岗状态 / 导师 / 班主任。
             原「性别」「班级」「在职状态」三个常驻筛选项已移入「高级筛选」弹窗，
             工具栏只保留高频维度，避免首屏筛选项过载。 -->
        <n-select
          v-model:value="filterRotationStatus"
          :options="rotationStatusChoices"
          placeholder="全部轮岗状态"
          clearable
          class="filter-select"
        />
        <n-select
          v-model:value="filterMentor"
          :options="mentorOptions"
          placeholder="全部导师"
          clearable
          filterable
          remote
          class="filter-select"
          :on-search="onMentorSearch"
        />
        <n-select
          v-model:value="filterHeadTeacher"
          :options="headTeacherOptions"
          placeholder="全部班主任"
          clearable
          filterable
          remote
          class="filter-select"
          :on-search="onHeadTeacherSearch"
        />
        <div class="spacer"></div>
        <CampusMockBar :is-mock="isMock" @change="loadList" />
        <n-input
          v-model:value="searchText"
          placeholder="搜索编号 / 姓名"
          clearable
          class="rule-filter-search"
          @keyup.enter="reload"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-button type="primary" :loading="loading" @click="reload">查询</n-button>
        <n-button @click="clearFilters">清空</n-button>
        <n-button @click="openAdvanced">高级筛选</n-button>
      </div>

      <n-tabs
        :value="activeTab"
        type="line"
        justify="start"
        class="status-tabs"
        @update:value="onTabChange"
      >
        <n-tab-pane
          v-for="t in statusTabs"
          :key="t.value"
          :name="t.value"
          :tab="t.label"
        />
      </n-tabs>

      <div class="table-wrap">
        <n-data-table
          :data="list"
          :columns="columns"
          :row-key="(row: any) => row.id"
          :loading="loading"
          :pagination="{ pageSize: 50 }"
          :bordered="false"
          :scroll-x="TABLE_SCROLL_X"
          flex-height
        >
          <template #empty>
            <n-empty description="暂无校招生档案" />
          </template>
        </n-data-table>
      </div>

      <!-- 二期：个人档案详情（点击姓名打开）
           示例数据模式：传 preloaded（本地拼的档案载荷，弹窗不发请求）+ readonly（不显示编辑入口） -->
      <PersonProfileModal
        ref="profileRef"
        v-model:show="profileVisible"
        :person-id="profileRow?.id ?? null"
        :person-name="profileRow?.name ?? ''"
        :preloaded="profilePreloaded"
        :readonly="isMock"
        @edit="onProfileEdit"
      />

      <!-- 2026-10-22：高级筛选（居中弹窗）
           维度：在职状态 / 性别 / 班级 / 院校标签 / 专业标签 / 职务 / 职级 / 招聘月份 / 入职年度
           （性别、班级、在职状态由常驻筛选区移入此处） -->
      <!-- 固定高度（R-223：内容区高度固定，不随内容变化跳动）→ 按 4 个字段实测收紧到 220px，
           避免下半截留一大块空白。
           ⚠️ 注释必须放在标签**外**：写在 <n-modal> 的属性列表中间会让 Vue 模板编译器
              打断属性解析，把后面的 :content-style 等属性当正文渲染出来（真机截图才发现）。 -->
      <n-modal
        v-model:show="advancedVisible"
        preset="card"
        title="高级筛选"
        :style="{ width: '560px', maxWidth: '95vw' }"
        :content-style="{ height: 'min(220px, calc(88vh - 140px))', overflowY: 'auto' }"
        :mask-closable="false"
        :bordered="false"
      >
        <n-form :model="advancedForm" label-placement="top">
          <!-- 2026-10-22 兵哥指令：高级筛选去掉「招聘月份 / 职务 / 职级 / 入职年度 / 在职状态」。
               在职状态改由页面上方的**状态页签唯一**控制（弹窗里不再重复一份，
               避免「页签选在职、弹窗选待入职」这种自相矛盾）。 -->
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="性别">
                <n-select v-model:value="advancedForm.sex" :options="sexChoices" placeholder="全部性别" clearable />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="班级">
                <n-select
                  v-model:value="advancedForm.classRoom"
                  :options="classRoomOptions"
                  placeholder="全部班级"
                  clearable
                  filterable
                  remote
                  :on-search="onClassRoomSearch"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="院校标签">
                <n-select v-model:value="advancedForm.school" :options="schoolChoices" placeholder="全部院校" clearable />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="专业标签">
                <n-select v-model:value="advancedForm.major" :options="majorChoices" placeholder="全部专业" clearable />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        </n-form>

        <template #footer>
          <div class="modal-footer">
            <n-button @click="clearAdvanced">清空条件</n-button>
            <n-button type="primary" class="gradient-btn" @click="applyAdvanced">查询</n-button>
          </div>
        </template>
      </n-modal>

      <n-modal
        v-model:show="modalVisible"
        preset="card"
        :title="editing ? '编辑校招生档案' : '新建校招生档案'"
        :style="{ width: '720px' }"
        :content-style="{ height: 'min(640px, calc(88vh - 140px))', overflowY: 'auto' }"
        :mask-closable="false"
      >
        <n-form :model="formState" label-placement="top">
          <!-- ① 轮岗信息（HRBP / 带教导师 只读 —— 仅可在轮岗安排中填写；其余可编辑） -->
          <div class="form-section">
            <div class="form-section-title">轮岗信息</div>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="意向部门">
                  <n-select
                    v-model:value="formState.intentBu"
                    :options="buChoices"
                    placeholder="请选择意向部门"
                    clearable
                  />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="当前轮岗部门">
                  <n-select
                    v-model:value="formState.bu"
                    :options="buChoices"
                    placeholder="请选择当前轮岗部门"
                  />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="班级">
                  <n-select
                    v-model:value="formState.classRoom"
                    :options="classRoomOptions"
                    placeholder="请选择班级"
                    clearable
                    filterable
                    remote
                    :on-search="onClassRoomSearch"
                  />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="班主任">
                  <n-select
                    v-model:value="formState.headTeacher"
                    :options="headTeacherOptions"
                    placeholder="请选择班主任"
                    clearable
                    filterable
                    remote
                    :on-search="onHeadTeacherSearch"
                  />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="HRBP">
                  <n-select
                    :value="formState.hrbp"
                    :options="hrbpOptions"
                    disabled
                    placeholder="—"
                  />
                  <div class="field-hint">仅可在轮岗安排中填写</div>
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="带教导师">
                  <n-select
                    :value="formState.mentor"
                    :options="mentorOptions"
                    disabled
                    placeholder="—"
                  />
                  <div class="field-hint">仅可在轮岗安排中填写</div>
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="批次">
                  <n-input v-model:value="formState.batch" placeholder="如 2026秋招" />
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </div>
          <!-- ② 基本信息（2026-10-22 兵哥指令：组内字段**全部禁止编辑**）
               身份/入职信息来自招聘系统与工号系统，不在本弹窗维护；
               统一用 disabled（显式灰显锁定），不再混用 readonly（白框看着像能改）；
               标题保留锁图标作锁定标识（不配提示文案，避免弹窗里堆说明） -->
          <div class="form-section">
            <div class="form-section-title">
              基本信息
              <n-icon :component="LockClosedOutline" class="form-section-lock" :aria-hidden="true" />
            </div>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="姓名">
                  <n-input :value="formState.name" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="性别">
                  <n-select :value="formState.sex" :options="sexChoices" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="在职状态">
                  <n-select :value="formState.status" :options="statusChoices" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="工号">
                  <n-input :value="formState.employeeId || '-'" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="预计入职日期">
                  <n-input :value="formState.expectedEntryDateText" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="实际入职日期">
                  <n-input :value="formState.actualEntryDateText" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </div>

          <!-- ③ 毕业院校（原「教育经历」，全部只读）
               院校标签 / 专业标签 展示在分组标题后（只读） -->
          <div class="form-section">
            <div class="form-section-title">
              毕业院校
              <n-icon :component="LockClosedOutline" class="form-section-lock" :aria-hidden="true" />
              <n-tag
                size="small"
                :bordered="false"
                :type="formState.school ? 'info' : 'default'"
                class="section-tag"
              >
                {{ formState.school || '院校标签' }}
              </n-tag>
              <n-tag
                size="small"
                :bordered="false"
                :type="formState.major ? 'info' : 'default'"
                class="section-tag"
              >
                {{ formState.major || '专业标签' }}
              </n-tag>
            </div>
            <n-grid :cols="2" :x-gap="24">
              <n-grid-item>
                <n-form-item label="院校名称">
                  <n-input :value="formState.schoolName" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="专业名称">
                  <n-input :value="formState.majorName" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="学历">
                  <n-select :value="formState.education" :options="educationChoices" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="学位">
                  <n-select :value="formState.degree" :options="degreeChoices" disabled placeholder="—" />
                </n-form-item>
              </n-grid-item>
            </n-grid>
          </div>
        </n-form>

        <template #footer>
          <div class="modal-footer">
            <n-button @click="modalVisible = false">取消</n-button>
            <n-button type="primary" class="gradient-btn" :loading="saving" @click="save">
              保存
            </n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 校招生档案页（校园招聘 · 人员管理）—— 2026-10-21 二期。
 *
 * 边界（重要）：本页只维护校招生人员主数据（apps/campus_control.Person），
 * **不涉及内部账号的新建/停用/删除、不涉及角色身份授权** —— 那些属于
 * 「权限管理 · 用户管理」，是权限域，权限码 recruit:settings:users:*。
 * 本页权限码为校招域 recruit:campus:person:*。
 *
 * 二期变更：
 *  1. 去掉页面标题（h1 + 副标题）与顶部权限提示条（n-alert）。
 *  2. 人员状态页签收敛为 4 档：全部 / 在职 / 待入职 / 离职。
 *     「待入职」= 后端单值状态「待入职」（原三态合并，见 utils/campus.ts 的 STATUS）。
 *  3. 筛选区新增 性别 / 班级 / 导师 / 班主任（+ 原有 部门 / 搜索）。
 *  4. 姓名可点击 → 打开「个人档案」详情弹窗（PersonProfileModal）。
 *  5. 2026-10-21：姓名 / 工号 / 简历编号 / 院校 / 专业 / 预计入职日期 / 入职日期 调整为只读。
 *  6. 2026-10-22 兵哥指令：「基本信息」「毕业院校」两组**全部字段禁止编辑** →
 *     统一用 disabled（显式灰显锁定，此前混用 readonly，白框看着像能改），
 *     并在分组标题加锁图标 + 来源说明；本页已无「新建」入口（档案由招聘系统认人产生）。
 */
import { ref, reactive, h, computed, watch, onMounted } from 'vue'
import {
  NButton,
  NDataTable,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInput,
  NModal,
  NPopconfirm,
  NSelect,
  NSpace,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  NPopover,
  useMessage,
} from 'naive-ui'
import {
  CreateOutline,
  SearchOutline,
  TrashOutline,
  TimeOutline,
  CheckmarkCircleOutline,
  LockClosedOutline,
} from '@vicons/ionicons5'
import { api } from '../../utils/request'
import {
  extractList,
  extractError,
  searchUsers,
  searchClassRooms,
  DEPTS,
  SCHOOLS,
  MAJORS,
  SEXES,
  STATUS,
  EDUCATIONS,
  DEGREES,
  isPendingStatus,
  validatePersonEntryFields,
  ROTATION_STATUS,
  formatSlashDate,
  type SelectOption,
} from '../../utils/campus'
import { column } from '../../composables/useTableColumns'
import PersonProfileModal from '../../components/campus/PersonProfileModal.vue'
import CampusMockBar from '../../components/campus/CampusMockBar.vue'
import { useCampusMock } from '../../composables/useCampusMock'
import { MOCK_PERSONS, buildMockPersonProfile } from '../../mocks/campus'

const message = useMessage()

const list = ref<any[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const editing = ref<any | null>(null)
const saving = ref(false)

const searchText = ref('')
const filterBu = ref<string | null>(null)
const filterMentor = ref<string | null>(null)
const filterHeadTeacher = ref<string | null>(null)
// 2026-10-22 兵哥指令：常驻筛选 = 部门 / 轮岗状态 / 导师 / 班主任；
//   「性别」「班级」「在职状态」移入高级筛选弹窗。
const filterRotationStatus = ref<string | null>(null)

// 高级筛选（仅在「高级筛选」弹窗中编辑，与工具栏筛选共用同一份查询状态）
const advancedVisible = ref(false)
const advancedForm = reactive({
  // 2026-10-22 兵哥指令：去掉 招聘月份 / 职务 / 职级 / 入职年度 / 在职状态
  //   （在职状态改由上方状态页签唯一控制）
  /** 性别 */
  sex: null as string | null,
  /** 班级（外键 id） */
  classRoom: null as string | null,
  /** 院校标签 */
  school: null as string | null,
  /** 专业标签 */
  major: null as string | null,
})

// 二期：个人档案详情弹窗
const profileVisible = ref(false)
const profileRow = ref<any | null>(null)
/** 示例数据模式下本地拼出的档案载荷（真实数据模式为 null → 弹窗走接口） */
const profilePreloaded = ref<any | null>(null)
/** 档案详情组件实例（保存基础信息后用它刷新详情数据） */
const profileRef = ref<InstanceType<typeof PersonProfileModal> | null>(null)

// S5-05（需求 2-1）+ 二期：状态页签。
// 「待入职」映射后端单值状态「待入职」（后端 status 参数仍支持逗号多值，向后兼容）。
const statusTabs = [
  { label: '全部', value: '' },
  { label: '在职', value: '在职' },
  // 2026-10-21 兵哥口径：待入职已是单值状态（原「在途Offer」「在途待入职」「候选池」三态合并）
  { label: '待入职', value: '待入职' },
  { label: '离职', value: '离职' },
]
const activeTab = ref<string>('')
const onTabChange = (v: string) => {
  // 2026-10-22 兵哥指令：在职状态筛选已从高级筛选弹窗移除 → 状态页签是**唯一**入口
  activeTab.value = v
  reload()
}

// 示例数据（真实为空时兜底；只读，页面已禁用新建/编辑/删除）
const { pick, isMock, isMockOnly } = useCampusMock()
const mockRows = computed(() => {
  let rows = [...MOCK_PERSONS]
  // 状态页签：待入职 = 后端单值状态「待入职」
  if (activeTab.value) {
    const wanted = activeTab.value.split(',')
    rows = rows.filter((r) => wanted.includes(r.status))
  }
  if (filterBu.value) rows = rows.filter((r) => r.bu === filterBu.value)
  if (advancedForm.sex) rows = rows.filter((r) => r.sex === advancedForm.sex)
  if (advancedForm.classRoom) {
    const targetName = classRoomNameMap.value[String(advancedForm.classRoom)] ?? ''
    rows = rows.filter((r) => String(r.classRoomName ?? '') === targetName)
  }
  // 轮岗状态（示例数据模式本地过滤；真实数据模式由后端 rotation_status 参数过滤）
  if (filterRotationStatus.value) {
    rows = rows.filter((r) => r.rotationStatus === filterRotationStatus.value)
  }
  const kw = searchText.value.trim()
  if (kw) {
    rows = rows.filter(
      (r) => String(r.name).includes(kw) || String(r.employeeId).includes(kw),
    )
  }
  if (advancedForm.school) rows = rows.filter((r) => r.school === advancedForm.school)
  if (advancedForm.major) rows = rows.filter((r) => r.major === advancedForm.major)
  return rows
})

// 枚举单一真源见 utils/campus（与后端 apps/campus_control/constants.py 保持一致，G-08 已收敛）

const toChoices = (arr: string[]) => arr.map((v) => ({ label: v, value: v }))
const buChoices = toChoices(DEPTS)
const schoolChoices = toChoices(SCHOOLS)
const majorChoices = toChoices(MAJORS)
const sexChoices = toChoices(SEXES)
const statusChoices = toChoices(STATUS)
/** 轮岗状态下拉（value = 轮岗安排阶段 code，后端按同口径过滤） */
const rotationStatusChoices = ROTATION_STATUS
const educationChoices = toChoices(EDUCATIONS)
const degreeChoices = toChoices(DEGREES)

const emptyForm = () => ({
  id: null as string | null,
  code: '',
  name: '',
  employeeId: '',
  phone: '',
  bu: null as string | null,
  intentBu: null as string | null,
  school: null as string | null,
  schoolName: '',
  major: null as string | null,
  majorName: '',
  education: null as string | null,
  degree: null as string | null,
  hrbp: null as string | null,
  batch: '',
  sex: null as string | null,
  month: '',
  status: '待入职' as string,
  position: '' as string,
  level: '' as string,
  headTeacher: null as string | null,
  classRoom: null as string | null,
  mentor: null as string | null,
  expectedEntryDate: null as number | null,
  actualEntryDate: null as number | null,
  // 只读展示用（基本信息组）：日期/工号的文本形态
  expectedEntryDateText: '',
  actualEntryDateText: '',
  counted: true,
  candidate: null as string | null,
  candidateCode: '',
  candidateName: '',
})
const formState = reactive(emptyForm())

// 2026-10-21 兵哥口径：工号 / 入职日期 / 预计入职日期 随在职状态走。
//   待入职：无工号、无实际入职日期，有预计入职日期；
//   在职 / 离职：有工号（8 位纯数字）、有实际入职日期。
const isPending = computed(() => isPendingStatus(formState.status))

/**
 * 2026-10-21 兵哥口径：姓名 / 工号 / 简历编号 / 院校 / 专业 / 预计入职日期 / 入职日期 调整为只读
 * （这些字段由候选人导入与轮岗流程维护，人员管理不手改）。
 *
 * ⚠️ 2026-10-22 兵哥指令：「基本信息」「毕业院校」两组**全部字段禁止编辑** —— 统一走 `disabled`
 *   （此前混用：输入框 `readonly` 白框、看着像能改；下拉 `disabled` 灰显），
 *   并在分组标题加锁图标 + 来源说明。
 *   「空值可补录」的豁免已随之取消：**缺值也不可补**（工号 / 实际入职日期同样锁死）。
 *   本页已无「新建」入口（校招生档案由招聘系统按姓名+手机号自动认人产生），
 *   故不存在「新建态要能填」的冲突。
 */

/* ============================ 编号自动获取（招聘系统 · 候选人管理） ============================
 * 编号不由前端填：后端保存时按「姓名(+手机号)」到候选人管理（校招分区）自动认人，
 * 认得出就把档案编号换成该候选人的编号（同号即同人）；认不出则沿用本地补号。
 * 前端只负责把编号显示出来（只读），并在保存后提示编号是否被同步。
 */
const formCodeText = computed(() => {
  if (editing.value) return formState.code
  return '自动获取（取自招聘系统候选人管理）'
})
/** 关联候选人只读回显：编号 · 姓名（认到人时才有值） */
const formCandidateText = computed(() => {
  if (!formState.candidate) return ''
  if (formState.candidateCode) return `${formState.candidateCode} · ${formState.candidateName || ''}`.trim()
  return formState.candidateName || ''
})
// 2026-10-22：「关联候选人」字段已从表单下线（编号仍只读回显）→ formCandidateText 仅存档用。

// 状态切到「待入职」时清空工号与实际入职日期（切回在职时由 HR 重新补录）
watch(
  () => formState.status,
  (v) => {
    if (isPendingStatus(v)) {
      formState.employeeId = ''
      formState.actualEntryDate = null
    }
  },
)

// S5-04：班级 / 班主任 远程搜索（复用 utils/campus.searchClassRooms / searchUsers）
const classRoomOptions = ref<SelectOption[]>([])
/**
 * 班级选项 id → 名称。
 * ⚠️ 示例数据模式按**名称**过滤（mock 行只有 classRoomName，没有班级 id）；
 *   若直接拿筛选值（id）比名称，永远筛不出任何行（历史遗留的静默失效）。
 */
const classRoomNameMap = computed(() => {
  const m: Record<string, string> = {}
  classRoomOptions.value.forEach((o) => {
    m[String(o.value)] = String(o.label ?? '')
  })
  return m
})
const headTeacherOptions = ref<SelectOption[]>([])
const mentorOptions = ref<SelectOption[]>([])
const hrbpOptions = ref<SelectOption[]>([])
const onClassRoomSearch = async (kw: string) => {
  classRoomOptions.value = await searchClassRooms(kw)
}
const onHeadTeacherSearch = async (kw: string) => {
  headTeacherOptions.value = await searchUsers(kw)
}
const onMentorSearch = async (kw: string) => {
  mentorOptions.value = await searchUsers(kw)
}

/** 预置筛选下拉的首屏选项（否则下拉打开是空白，必须先输入才有内容）。 */
const loadFilterOptions = async () => {
  try {
    const [rooms, users] = await Promise.all([searchClassRooms(''), searchUsers('')])
    classRoomOptions.value = rooms
    headTeacherOptions.value = users
    mentorOptions.value = users
  } catch {
    // 筛选下拉预置失败不阻断页面：下拉仍可远程搜索
  }
}

/** 后端日期字段接受 YYYY-MM-DD；空值统一转 null，避免传空串触发 400。 */
const toDateStr = (ts: number | null): string | null => {
  if (!ts) return null
  const d = new Date(ts)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const loadList = async () => {
  loading.value = true
  try {
    if (isMockOnly.value) {
      list.value = mockRows.value
      return
    }
    const params: Record<string, any> = { page: 1, page_size: 200 }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    if (filterBu.value) params.bu = filterBu.value
    if (advancedForm.sex) params.sex = advancedForm.sex
    if (advancedForm.classRoom) params.class_room = advancedForm.classRoom
    if (filterMentor.value) params.mentor = filterMentor.value
    if (filterHeadTeacher.value) params.head_teacher = filterHeadTeacher.value
    // 高级筛选条件
    if (advancedForm.school) params.school = advancedForm.school
    if (advancedForm.major) params.major = advancedForm.major
    // 在职状态：唯一来源 = 上方状态页签（高级筛选弹窗里已移除该项）
    if (activeTab.value) params.status = activeTab.value
    // 2026-10-22：轮岗状态筛选（后端按「存在该阶段的轮岗安排」过滤）
    if (filterRotationStatus.value) params.rotation_status = filterRotationStatus.value
    const resp = await api.get('/campus/persons/', { params })
    list.value = pick(extractList(resp), mockRows.value)
  } catch (e: any) {
    // 接口失败：auto 模式用示例数据兜底
    list.value = pick([], mockRows.value)
    message.error(extractError(e))
  } finally {
    loading.value = false
  }
}

const reload = () => loadList()

/** 打开高级筛选弹窗（沿用当前已选条件，不重置）。 */
const openAdvanced = () => {
  advancedVisible.value = true
}

/** 清空全部筛选条件并重新查询。 */
const clearFilters = () => {
  searchText.value = ''
  filterBu.value = null
  filterMentor.value = null
  filterHeadTeacher.value = null
  filterRotationStatus.value = null
  // 在职状态与状态页签同维度：清空条件 → 状态页签回到「全部」
  activeTab.value = ''
  clearAdvanced()
  reload()
}

/** 清空高级筛选条件（不自动查询，由用户点「查询」生效）。 */
const clearAdvanced = () => {
  // 注：在职状态不在高级筛选里（由状态页签唯一控制）→ 这里不动 activeTab
  advancedForm.sex = null
  advancedForm.classRoom = null
  advancedForm.school = null
  advancedForm.major = null
}

/** 应用高级筛选并查询（关闭弹窗）。 */
const applyAdvanced = () => {
  advancedVisible.value = false
  reload()
}

/**
 * 打开编辑弹窗。
 * 入参既可以是列表行（headTeacher / classRoom 为外键 id），
 * 也可以是档案详情聚合里的 person（headTeacherId / classRoomId）—— 二期两者并存。
 */
const openEdit = (row: any) => {
  const headTeacherId = row.headTeacher ?? row.headTeacherId ?? null
  const classRoomId = row.classRoom ?? row.classRoomId ?? null
  Object.assign(formState, emptyForm(), {
    id: row.id,
    code: row.code,
    name: row.name || '',
    employeeId: row.employeeId || '',
    phone: row.phone || '',
    bu: row.bu || null,
    intentBu: row.intentBu != null ? String(row.intentBu) || null : null,
    school: row.school || null,
    schoolName: row.schoolName || '',
    major: row.major || null,
    majorName: row.majorName || '',
    education: row.education || null,
    degree: row.degree || null,
    hrbp: row.hrbp != null ? String(row.hrbp) : null,
    batch: row.batch || '',
    sex: row.sex || null,
    month: row.month || '',
    status: row.status || '待入职',
    position: row.position || '',
    level: row.level || '',
    headTeacher: headTeacherId != null ? String(headTeacherId) : null,
    classRoom: classRoomId != null ? String(classRoomId) : null,
    mentor: row.mentor != null ? String(row.mentor) : null,
    expectedEntryDate: row.expectedEntryDate ? new Date(row.expectedEntryDate).getTime() : null,
    actualEntryDate: row.actualEntryDate ? new Date(row.actualEntryDate).getTime() : null,
    // 基本信息组只读展示用（日期文本）
    expectedEntryDateText: row.expectedEntryDate || '',
    actualEntryDateText: row.actualEntryDate || '',
    counted: row.counted !== false,
    candidate: row.candidate ?? null,
    candidateCode: row.candidateCode || '',
    candidateName: row.candidateName || '',
  })
  editing.value = row
  // HRBP：只读展示（人员侧只显示名字，选项用假 id 回显）
  hrbpOptions.value = row.hrbp != null
    ? [{ label: row.hrbpName || String(row.hrbp), value: String(row.hrbp) }]
    : []
  // 预置已选班级 / 班主任 / 导师，保证编辑时选择器回显当前值
  classRoomOptions.value = classRoomId != null
    ? [{ label: row.classRoomName || String(classRoomId), value: String(classRoomId) }]
    : []
  headTeacherOptions.value = headTeacherId != null
    ? [{ label: row.headTeacherName || String(headTeacherId), value: String(headTeacherId) }]
    : []
  mentorOptions.value = row.mentor != null
    ? [{ label: row.mentorName || String(row.mentor), value: String(row.mentor) }]
    : []
  modalVisible.value = true
}

/**
 * 二期：打开个人档案详情。
 *
 * ⚠️ 示例数据模式：mock 行的 id 形如 `MOCK_PS_01`，**后端没有这条记录**，
 *    若照常请求 `GET /campus/persons/MOCK_PS_01/profile/` 必然 404。
 *    故示例数据下由本地拼好档案载荷交给弹窗直接渲染（不发请求），
 *    并置只读（隐藏「编辑基础信息」，示例数据不落库）。
 */
const openProfile = (row: any) => {
  profileRow.value = row
  profilePreloaded.value = isMock.value ? buildMockPersonProfile(row) : null
  profileVisible.value = true
}

/**
 * 二期：详情弹窗「编辑基础信息」→ **档案页不消失**，
 * 编辑弹窗叠在档案页之上；保存后档案页自动刷新（数据不陈旧）。
 */
const onProfileEdit = (profile: any) => {
  if (isMock.value) {
    message.warning('示例数据仅供查看，请切回真实数据后再操作')
    return
  }
  openEdit(profile.person)
}

const save = async () => {
  if (isMock.value) {
    message.warning('示例数据仅供查看，请切回真实数据后再操作')
    return
  }
  if (!formState.name.trim()) {
    message.warning('请填写姓名')
    return
  }
  if (!formState.bu) {
    message.warning('请选择部门')
    return
  }
  // 2026-10-21 兵哥口径：工号 / 入职日期 / 预计入职日期 随在职状态走（前端先拦一道，后端再兜一道）
  const employeeId = (formState.employeeId || '').trim()
  const entryError = validatePersonEntryFields({
    status: formState.status,
    employeeId,
    expectedEntryDate: toDateStr(formState.expectedEntryDate),
    actualEntryDate: toDateStr(formState.actualEntryDate),
  })
  if (entryError) {
    message.warning(entryError)
    return
  }
  saving.value = true
  const payload: any = {
    name: formState.name.trim(),
    employee_id: isPending.value ? '' : employeeId,
    phone: formState.phone || '',
    bu: formState.bu,
    intent_bu: formState.intentBu || '',
    school: formState.school || '',
    school_name: formState.schoolName || '',
    major: formState.major || '',
    major_name: formState.majorName || '',
    education: formState.education || '',
    degree: formState.degree || '',
    hrbp: formState.hrbp || null,
    batch: formState.batch || '',
    sex: formState.sex || '',
    month: formState.month || '',
    status: formState.status,
    position: formState.position || '',
    level: formState.level || '',
    head_teacher: formState.headTeacher,
    class_room: formState.classRoom,
    mentor: formState.mentor,
    expectedEntryDate: toDateStr(formState.expectedEntryDate),
    actualEntryDate: isPending.value ? '' : toDateStr(formState.actualEntryDate),
    counted: formState.counted,
    // 编号不在前端传：后端保存时自动到「招聘系统 · 候选人管理」认人并取其编号
    // （也不传 candidate，避免把已认定的候选人置空）
  }
  const codeBefore = formState.code
  try {
    if (editing.value) {
      const resp = await api.put(`/campus/persons/${editing.value.id}/`, payload)
      message.success('更新成功')
      notifyCodeSync(codeBefore, resp)
    } else {
      const resp = await api.post('/campus/persons/', payload)
      message.success('创建成功')
      notifyCodeSync(codeBefore, resp)
    }
    modalVisible.value = false
    loadList()
    // 档案页不消失 → 改完同步刷新档案详情，避免详情页停留在旧值
    if (profileVisible.value) profileRef.value?.reload()
  } catch (e: any) {
    message.error(extractError(e))
  } finally {
    saving.value = false
  }
}

/** 编号被自动同步成候选人编号时给出明确提示（避免用户以为编号被莫名改掉）。 */
function notifyCodeSync(codeBefore: string, resp: any) {
  const data = resp?.data?.data ?? resp?.data ?? {}
  const code = data?.code || ''
  if (!code || code === codeBefore) return
  message.info(`编号已自动同步为候选人编号：${code}`)
}

const remove = async (row: any) => {
  if (isMock.value) {
    message.warning('示例数据仅供查看，请切回真实数据后再操作')
    return
  }
  try {
    await api.delete(`/campus/persons/${row.id}/`)
    message.success('已删除该档案')
    loadList()
  } catch (e: any) {
    message.error(extractError(e))
  }
}

const statusTagType = (s: string) => {
  if (s === '在职') return 'success'
  if (s === '待入职') return 'warning'
  return 'default'
}

// 2026-10-22 兵哥指令：列顺序调整为
//   姓名 → 工号 → 性别 → 在职状态 → 入职日期(预/实同列) → 带教导师 → HRBP
//   → 当前轮岗部门 → 批次 → 班级 → 学校 → 专业 → 综合评分
// （原「入职时间 + 预计入职日期」两列合并为一列；原「班主任 / 职务 / 职级」三列按兵哥清单下线；
//   原「部门」列更名为「当前轮岗部门」，原「院校」列更名为「学校」。）
// D-02：隐藏「候选人编号」列（库字段 code 保留）。
// S5-08：列对齐接入 useTableColumns 单一真源（数据列表尽量居中，操作列 control 档）
// 二期：姓名列改为可点击（打开个人档案详情），并补 title 便于查看超长姓名全称。
/**
 * 列宽口径（2026-10-22 列重排后重算 → 同日按**浏览器实测**再校准）：
 * 0. **按实测容器宽度配宽**（不是拍脑袋）：1440 视口下侧栏 64 + 页面内边距 32
 *    → 表格容器可用 1344px（用 playwright 量到的 clientWidth）。
 *    原合计 1380px 超出 36px → 末尾「综合评分」被 fixed:'right' 的操作列盖住、
 *    「当前轮岗部门」表头（6 字 ≈108px）被裁 → 现合计 **1324px**。
 * 1. **总宽 ≤ 容器宽** —— 14 列一屏放下，不触发横向滚动；
 *    「入职日期」合并列刻意用**两行**（预：/ 实：）而不是一行并排，
 *    就是为了把这个列压到 124px、把总宽守在 1400 以内（S5-34 一屏放下的既有要求）。
 * 2. **操作列 ≥ 168px** —— 「编辑 + 删除」两个带图标文字按钮（small 档 14px/28px 高）
 *    实际占位约 148px + 单元格左右内边距 24px，140px 会把「删除」按钮裁掉半截。
 * 3. 日期/编码类列用「短值」档（居中），长文本（班级/导师/部门/学校/专业）保留 ellipsis。
 */
const columns = [
  column({
    title: '姓名', key: 'name', width: 84, ellipsis: true,
    render: (row: any) =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          title: row.name || '查看个人档案',
          onClick: () => openProfile(row),
        },
        { default: () => row.name || '-' },
      ),
  }),
  column({ title: '工号', key: 'employeeId', width: 88, render: (row: any) => row.employeeId || '-' }),
  column({ title: '性别', key: 'sex', width: 52, render: (row: any) => row.sex || '-' }),
  column(
    {
      title: '在职状态', key: 'status', width: 84,
      render: (row: any) =>
        h(NTag, { type: statusTagType(row.status), size: 'small' }, { default: () => row.status || '-' }),
    },
    'short',
  ),
  // 入职日期：预计 + 实际合并到同一列（兵哥 2026-10-22 口径「预：2026/12/02 实：2026/12/31」）
  //   2026-10-21 兵哥口径：预计入职日期全员有（待入职必填）；待入职无实际入职日期
  column(
    {
      // 2026-10-22 兵哥指令：「预」「实」两个文字改用 icon 表达，并保持换行（两行）
      //   预 = 时钟（计划时间）  实 = 对勾圈（已实际发生）
      //   icon 单独出现会失去语义 → 必带 title（悬停提示）+ aria-label（R-217）
      title: '入职日期', key: 'entryDate', width: 120,
      render: (row: any) =>
        h('div', { class: 'entry-date-cell' }, [
          h('span', { class: 'entry-date-cell__row', title: '预计入职日期' }, [
            h(
              NIcon,
              { size: 13, class: 'entry-date-cell__icon', 'aria-label': '预计入职日期' },
              { default: () => h(TimeOutline) },
            ),
            h('span', { class: 'entry-date-cell__val' }, formatSlashDate(row.expectedEntryDate) || '—'),
          ]),
          h('span', { class: 'entry-date-cell__row', title: '实际入职日期' }, [
            h(
              NIcon,
              { size: 13, class: 'entry-date-cell__icon', 'aria-label': '实际入职日期' },
              { default: () => h(CheckmarkCircleOutline) },
            ),
            h('span', { class: 'entry-date-cell__val' }, formatSlashDate(row.actualEntryDate) || '—'),
          ]),
        ]),
    },
    'short',
  ),
  column({ title: '带教导师', key: 'mentorName', width: 84, ellipsis: true, render: (row: any) => row.mentorName || '-' }),
  column({ title: 'HRBP', key: 'hrbpName', width: 72, ellipsis: true, render: (row: any) => row.hrbpName || '-' }),
  // 当前轮岗部门：轮岗安排的 current_dept；无安排时后端回退人员自身的 bu
  column({ title: '当前轮岗部门', key: 'rotationDept', width: 112, ellipsis: true, render: (row: any) => row.rotationDept || row.bu || '-' }),
  column({ title: '批次', key: 'batch', width: 84, render: (row: any) => row.batch || '-' }),
  column({ title: '班级', key: 'classRoomName', width: 112, ellipsis: true, render: (row: any) => row.classRoomName || '-' }),
  // 学校 / 专业：优先真实名称（schoolName / majorName），缺则回退标签（school / major）
  column({ title: '学校', key: 'schoolName', width: 92, ellipsis: true, render: (row: any) => row.schoolName || row.school || '-' }),
  column({ title: '专业', key: 'majorName', width: 88, ellipsis: true, render: (row: any) => row.majorName || row.major || '-' }),
  // 综合评分 = 轮岗均分（无评分显示「—」，不臆造 0 分）
  column(
    {
      title: '综合评分', key: 'overallScore', width: 84,
      render: (row: any) =>
        row.overallScore == null || row.overallScore === ''
          ? '—'
          : Number(row.overallScore).toFixed(1),
    },
    'numeric',
  ),
  column(
    {
      title: '操作', key: 'actions', width: 168, fixed: 'right' as const,
      render: (row: any) =>
        h(NSpace, { size: 8, wrap: false }, {
          default: () => [
            h(NButton, { size: 'small', quaternary: true, type: 'primary', disabled: isMock.value, onClick: () => openEdit(row) },
              { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
            h(NPopconfirm, { onPositiveClick: () => remove(row), positiveText: '确认', negativeText: '取消' }, {
              default: () => '确认删除该校招生档案？',
              trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error', disabled: isMock.value },
                { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }),
            }),
          ],
        }),
    },
    'control',
  ),
]

/**
 * 表格横向滚动宽度 = 各列 width 之和。
 * naive-ui 必须显式给 `scroll-x` 才会横向滚动；不给时列宽总和超出容器会被直接裁掉，
 * 且 `fixed:'right'` 的操作列会盖住相邻列（此前「专业」列被压住、「删除」按钮被截半）。
 * ⚠️ 必须与上方列宽之和保持一致 —— 由 `CampusPerson.tableLayout.test.ts` 断言锁死。
 */
const TABLE_SCROLL_X = columns.reduce((sum, c) => sum + (typeof c.width === 'number' ? c.width : 100), 0)

onMounted(() => {
  loadList()
  loadFilterOptions()
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
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
/* 数字类列（工号 / 入职时间 / 预计入职日期 / 职级）用等宽数字：
   刷新、排序、状态切换时数字宽度不变 → 列不抖动（R-204 动态数字防抖动）。 */
.table-wrap :deep(.n-data-table-td) {
  font-variant-numeric: tabular-nums;
}
/* 编辑弹窗字段分组：基本信息 / 院校与专业 / 岗位与归属 / 状态与入职 */
.form-section {
  margin-bottom: var(--space-4);
}
.form-section:last-child {
  margin-bottom: 0;
}
/* 分组标题后的锁图标（2026-10-22：基本信息 / 毕业院校两组「全部禁止编辑」的显式标识） */
.form-section-lock {
  color: var(--ink-faint);
  font-size: var(--fs-13);
}
.form-section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
}
.form-section-title::before {
  content: '';
  width: 3px;
  height: 12px;
  border-radius: 2px;
  background: var(--brand);
}
/* 2026-10-22：分组标题后的标签（院校标签 / 专业标签）——只读展示 */
.section-tag {
  font-weight: 500;
}
/* 2026-10-22：只读字段的补充说明（如 HRBP / 带教导师 仅可在轮岗安排中填写） */
.field-hint {
  margin-top: var(--space-1);
  font-size: var(--fs-12);
  line-height: 1.5;
  color: var(--ink-soft);
}
/* S5-05：状态页签栏（替代原状态下拉）；与工具栏分离成独立一行。
 * ⚠️ 2026-10-22 兵哥反馈「页签分栏和数据列表容器的间距太大」——**不符合前端标准**：
 *   ① 本行的 `margin-bottom: var(--space-2)` 与 `.page-body` 的 flex gap **叠加**，
 *      再叠 naive 空 tab-pane 的内建 `padding-top: 12px`（panePaddingMedium）
 *      → 页签到数据列表容器之间出现约 28px 空带。
 *      同款病根仓库在 2026-09-18 已治过一次（glass.css「双重间距根治」段：
 *      「间距唯一来源 = 容器 gap，元素自身 margin 清零」），此处按同一规则收口。
 *   ② 空 pane 的 12px 上内边距是纯留白（数据列表是 tabs 的**兄弟节点**，不在 pane 内）→ 清零。
 *   收口后间距 = `.page-body` 的 gap（--space-2，8px）单一来源。 */
.status-tabs {
  margin: 0;
}
.status-tabs :deep(.n-tab-pane) {
  padding: 0;
}
/* 二期：筛选下拉增至 6 个（部门/性别/班级/导师/班主任 + 搜索），
 * 为控制工具栏单行不换行，搜索框收窄至 220px
 * （全局 .rule-filter-search 为 240px）。属有意例外，非遗漏。 */
.rule-filter-search {
  width: 220px;
}
.filter-select {
  width: 130px;
}
.spacer {
  flex: 1;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

</style>

<!--
  ⚠️ 必须**非 scoped**：入职日期单元格是列 render 里用 h() 动态造的 VNode，
     Vue 的 scoped 依赖编译期给**模板元素**注入 data-v-xxx —— h() 造的元素不带该属性
     → scoped 规则对它**完全不命中**（实测：规则在、计算样式却是 display:block）。
     2026-10-22 因此连续两轮改 CSS「看起来对、实际没生效」。
     同款坑见 docs/04-ui/NAIVE_UI_PITFALLS.md §7.1（Teleport 版），此处是**动态渲染版**。
     类名带 entry-date- 前缀，天然不与其它页面冲突。 -->
<style>
/* 入职日期合并列：预 / 实 两行（兵哥 2026-10-22 口径「预：2026/12/02 实：2026/12/31」）
   - 「预」「实」两个文字改用 **icon**（时钟 = 预计 / 对勾圈 = 实际），文字只留日期；
     icon 必带 title + aria-label（R-217：纯图标必须可理解）。
   - 两行用 flex 列；每行 = 图标 + 日期同行。 */
.entry-date-cell {
  display: flex;
  flex-direction: column;
  line-height: 1.5;
  text-align: left;
}
.entry-date-cell__row {
  display: flex;
  align-items: center;
  gap: var(--space-1); /* 图标与文字 4px（规范 §图标 7：4–8px） */
}
.entry-date-cell__icon {
  flex-shrink: 0;
  color: var(--ink-faint);
}
.entry-date-cell__val {
  font-variant-numeric: tabular-nums;
  /* 日期不允许断行：否则在「/」处折行，图标留在上一行 → 出现「🕐—⊖」+ 日期两行的错位 */
  white-space: nowrap;
}
</style>

