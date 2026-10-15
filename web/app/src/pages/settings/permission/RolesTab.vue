<template>
  <div class="roles-tab">
    <!-- 工具条：左=搜索+筛选，右=操作（对齐校招管控-规则配置页 .toolbar 范式） -->
    <div class="toolbar">
      <n-input
        v-model:value="kw"
        :placeholder="t('pages.settings.permission.RolesTab.s1')"
        clearable
        class="rule-filter-search"
      />
      <n-select
        v-model:value="statusFilter"
        :options="statusOptions"
        :placeholder="t('pages.settings.permission.RolesTab.s2')"
        class="rule-filter-select"
      />
      <n-select
        v-model:value="systemFilter"
        :options="systemOptions"
        :placeholder="t('pages.settings.permission.RolesTab.s3')"
        class="rule-filter-select"
      />
      <div class="spacer"></div>
      <!--
        工具栏按钮组（2026-10-15 兵哥纠偏 · 按 frontend-layout-standard §1.8.1 + frontend-DESIGN §Data Table）：
        - 全部 quaternary 文字按钮，同组按钮统一带 14–16px outline icon（§1.8.1 禁止半带半不带）
        - 仅「新建身份」保留 primary 实心作为主路径；其余为 default 灰阶
        - 模板管理入口移入本组，排在「刷新」之后（用户指定顺序）
      -->
      <n-button v-if="isSuperAdmin" quaternary @click="actionManageShow = true">
        <template #icon><n-icon :component="ShieldCheckmarkOutline" /></template>
        {{ t('dataperm.actions.title') }}
      </n-button>
      <n-button quaternary @click="load">
        <template #icon><n-icon :component="RefreshOutline" /></template>
        {{ t('pages.settings.permission.RolesTab.s4') }}
      </n-button>
      <n-button quaternary @click="emit('open-templates')">
        <template #icon><n-icon :component="GridOutline" /></template>
        {{ t('pages.settings.PermissionManagement.s3') }}
      </n-button>
      <n-button quaternary @click="onCloneFromTemplate">
        <template #icon><n-icon :component="CopyOutline" /></template>
        {{ t('pages.settings.permission.RolesTab.s5') }}
      </n-button>
      <n-button type="primary" class="gradient-btn" @click="onCreate">
        <template #icon><n-icon :component="AddOutline" /></template>
        {{ t('pages.settings.permission.RolesTab.s6') }}
      </n-button>
    </div>

    <!-- 表格：复用全局 .table-wrap + flex-height（仅表体内部滚动，对齐 CampusControl 规则表） -->
    <div class="table-wrap">
      <n-data-table
        :columns="columns"
        :data="filteredRows"
        :loading="loading"
        :bordered="false"
        :row-key="(r: RoleV2) => r.id"
        :pagination="rolePagination"
        flex-height
      >
        <template #empty>
          <n-empty :description="data.length === 0 ? t('pages.settings.permission.RolesTab.s15') : t('pages.settings.permission.RolesTab.s16')" />
        </template>
      </n-data-table>
    </div>

    <!-- 从模板克隆 modal -->
    <n-modal
      :show="cloneModal.show"
      preset="card"
      :title="t('pages.settings.permission.RolesTab.s7')"
      style="max-width: 480px"
      :mask-closable="false"
      :on-mask-click="requestCloseClone"
      @update:show="(v: boolean) => !v && requestCloseClone()"
    >
      <n-form :model="cloneModal.form" label-placement="left" label-width="100">
        <n-form-item :label="t('pages.settings.permission.RolesTab.s8')" required>
          <n-select
            v-model:value="cloneModal.form.templateCode"
            :options="templateOptions"
            :placeholder="t('pages.settings.permission.RolesTab.s9')"
          />
        </n-form-item>
        <n-form-item :label="t('pages.settings.permission.RolesTab.s10')" required>
          <n-input v-model:value="cloneModal.form.roleCode" placeholder="e.g. CUSTOM_HR" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.permission.RolesTab.s11')" required>
          <n-input v-model:value="cloneModal.form.roleName" :placeholder="t('pages.settings.permission.RolesTab.s12')" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="requestCloseClone">{{ t('pages.settings.permission.RolesTab.s13') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="cloneModal.saving" @click="onSubmitClone">{{ t('pages.settings.permission.RolesTab.s14') }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <RoleEditModal
      v-model:show="editModal.show"
      :role="editModal.role"
      @saved="onEditSaved"
    />

    <!-- 权限 v2：动作字典 / 预设包管理 -->
    <ActionManageModal v-model:show="actionManageShow" />
  </div>
</template>

<script setup lang="ts">
/**
 * RolesTab.vue — V2 角色管理 tab (T20 + T21)
 *
 * 后端: GET/POST/PUT/DELETE /api/v1/roles/
 *       POST /api/v1/roles/clone-from-template/
 *
 * 2026-09-19 一致性调整：对齐「校招管控-规则配置」页交互格式 ——
 *   - 工具条.search + 状态/来源筛选（左），操作按钮右对齐（spacer 分隔）
 *   - 状态列内联 NSwitch 启停（对齐 CampusControl 指标管理「启用」列写法）
 *   - 统一分页 useTablePagination（本地分页，§4.x 强制外观：共N条/20每页/跳至）
 *   - 表格包 .table-wrap + flex-height（仅表体内部滚动）；空状态区分「无数据/无筛选结果」
 */
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NSpace, NDataTable, NModal, NForm, NFormItem, NSelect, NInput, NTag, NSwitch, NIcon, useMessage, useDialog } from 'naive-ui'
import { AddOutline, CopyOutline, CreateOutline, GridOutline, RefreshOutline, ShieldCheckmarkOutline, TrashOutline } from '@vicons/ionicons5'
import { listRoles, cloneFromTemplate, deleteRole, updateRole, type RoleV2 } from '@/api/role-v2'
import { listTemplates, type PermissionTemplate } from '@/api/permission-template'
import { listAclRules } from '@/api/field-acl'
import { localPagination } from '@/composables/useTablePagination'
// 列对齐与操作列规格的单一真源（四档规则见该文件头）
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
import RoleEditModal from './RoleEditModal.vue'
import ActionManageModal from '@/components/role/ActionManageModal.vue'
import { useUserStore } from '@/stores/user'
import { useCloseGuard } from '@/composables/useCloseGuard'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

// 模板管理弹窗由父组件 PermissionManagement 持有（弹窗体含 TemplatesTab，本组件只发信号）
const emit = defineEmits<{ (e: 'open-templates'): void }>()

// 权限 v2：动作字典管理入口仅超管可见（后端 IsSuperAdmin 双保险）
const userStore = useUserStore()
const isSuperAdmin = computed(() => (userStore.user?.roles ?? []).includes('SUPER_ADMIN'))
const actionManageShow = ref(false)

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const data = ref<RoleV2[]>([])
const templates = ref<PermissionTemplate[]>([])

const templateOptions = computed(() =>
  templates.value.map((t) => ({ label: `${t.templateName} (${t.templateCode})`, value: t.templateCode })),
)

// ===== 筛选状态（对齐 CampusControl rules tab：keyboard search + 状态/维度 select）=====
const kw = ref('')
const statusFilter = ref<'all' | 0 | 1>('all')
const systemFilter = ref<'all' | 0 | 1>('all')

const statusOptions = [
  { label: '全部状态', value: 'all' as const },
  { label: '启用', value: 1 as const },
  { label: '停用', value: 0 as const },
]
const systemOptions = [
  { label: '全部来源', value: 'all' as const },
  { label: '预置', value: 1 as const },
  { label: '自定义', value: 0 as const },
]

const filteredRows = computed<RoleV2[]>(() => {
  const k = kw.value.trim().toLowerCase()
  return data.value.filter((r) => {
    if (statusFilter.value !== 'all' && r.status !== statusFilter.value) return false
    if (systemFilter.value !== 'all' && r.isSystem !== systemFilter.value) return false
    if (k && !`${r.roleCode} ${r.roleName}`.toLowerCase().includes(k)) return false
    return true
  })
})

// 统一分页（本地分页：一次性取全量，n-data-table 前端切片，§4.x）
const rolePagination = localPagination()

const scopeTypeLabels: Record<string, string> = {
  SELF: '仅本人',
  DEPT: '本部门',
  DEPT_AND_SUB: '本部门及下属',
  ALL: '全公司',
}

// 列对齐统一走 useTableColumns 工厂（四档规则，A 短值/B 控件/C 数值 居中，D 长文本 左对齐）。
// 依据 useTableColumns.ts 文件头规则表；勿在本页另立对齐口径。
const columns = [
  column({ title: '身份编码', key: 'roleCode', width: 160, render: (r: RoleV2) => r.roleCode || '—' }, 'short'),
  column({ title: '身份名称', key: 'roleName', width: 160, render: (r: RoleV2) => r.roleName || '—' }, 'short'),
  column({ title: '模板来源', key: 'templateCode', width: 140, render: (r: RoleV2) => r.templateCode || '—' }, 'short'),
  column({
    title: '默认数据范围',
    key: 'defaultDataScopeType',
    width: 140,
    render: (r: RoleV2) => scopeTypeLabels[r.defaultDataScopeType ?? ''] ?? '—',
  }, 'short'),
  column({
    // 状态列内联 NSwitch 启停（对齐 CampusControl 指标管理「启用」列写法）
    title: '状态',
    key: 'status',
    width: 90,
    render: (r: RoleV2) =>
      h(NSwitch, {
        value: r.status === 1,
        size: 'small',
        'onUpdate:value': async (v: boolean) => {
          const next = v ? 1 : 0
          try {
            await updateRole(r.id, { status: next })
            r.status = next
            message.success(v ? '已启用' : '已停用')
          } catch (e: any) {
            message.error('切换失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
          }
        },
      }),
  }, 'control'),
  column({
    // 来源标签：中性灰，不参与语义区分（预置/自定义语义同级，用文字承载）。
    // 原 primary 紫与品牌按钮撞色确属问题，此项收敛保留。
    title: '来源',
    key: 'isSystem',
    width: 90,
    render: (r: RoleV2) =>
      h(NTag, { bordered: false, size: 'small', class: 'neutral-tag' },
        { default: () => (r.isSystem === 1 ? '预置' : '自定义') }),
  }, 'short'),
  column({
    title: '权限码数',
    key: 'permissionCodes',
    width: 100,
    render: (r: RoleV2) => r.permissionCodes?.length ?? 0,
  }, 'numeric'),
  column({
    // 行内操作：按 frontend-DESIGN §Data Table —— quaternary 文字按钮，
    // 编辑 type=primary、删除 type=error（危险色是安全信号，不做单色化）。
    // §1.8.1：同组按钮统一带 14–16px outline icon；size 取 OP_ACTION_BUTTON_SIZE
    // （small=14px，与表格正文同层级；旧 tiny=12px 比正文小 2px 会「矮一截」）。
    title: '操作',
    key: 'actions',
    width: 176,
    fixed: 'right' as const,
    render(row: RoleV2) {
      return h(NSpace, { size: 8, wrap: false }, () => [
        h(NButton, {
          size: OP_ACTION_BUTTON_SIZE,
          quaternary: true,
          type: 'primary',
          onClick: () => onEdit(row),
        }, { icon: () => h(NIcon, null, { default: () => h(CreateOutline) }), default: () => '编辑' }),
        h(NButton, {
          size: OP_ACTION_BUTTON_SIZE,
          quaternary: true,
          type: 'error',
          disabled: row.isSystem === 1,
          onClick: () => onDelete(row),
        }, { icon: () => h(NIcon, null, { default: () => h(TrashOutline) }), default: () => '删除' }),
      ])
    },
  }, 'control'),
]

const cloneModal = reactive({
  show: false,
  saving: false,
  form: {
    templateCode: '' as string,
    roleCode: '',
    roleName: '',
  },
})

// 弹窗关闭守卫（方案B）：遮罩/ESC/X 三条路径统一走脏检查二次确认
const { requestClose: requestCloseClone } = useCloseGuard({
  isSaving: () => cloneModal.saving,
  isDirty: () => true,
  onClose: () => { cloneModal.show = false },
})

const editModal = reactive({
  show: false,
  role: null as RoleV2 | null,
})

async function load() {
  loading.value = true
  try {
    const [roles, tpls] = await Promise.all([listRoles(), listTemplates()])
    data.value = roles
    templates.value = tpls
  } catch (e: any) {
    message.error('加载失败: ' + (e?.message ?? e))
  } finally {
    loading.value = false
  }
}

function onCreate() {
  // 打开 RoleEditModal 不带 role, 用空 form 让用户从 0 创建
  editModal.role = null
  editModal.show = true
}

function onCloneFromTemplate() {
  cloneModal.form = { templateCode: '', roleCode: '', roleName: '' }
  cloneModal.show = true
}

async function onSubmitClone() {
  const { templateCode, roleCode, roleName } = cloneModal.form
  if (!templateCode || !roleCode || !roleName) {
    message.warning('模板 + 新身份编码 + 新身份名称 必填')
    return
  }
  cloneModal.saving = true
  try {
    await cloneFromTemplate({ templateCode, roleCode, roleName })
    message.success(`已从模板 ${templateCode} 克隆出 ${roleCode}`)
    cloneModal.show = false
    await load()
  } catch (e: any) {
    message.error('克隆失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  } finally {
    cloneModal.saving = false
  }
}

function onEdit(row: RoleV2) {
  editModal.role = row
  editModal.show = true
}

function onEditSaved() {
  editModal.show = false
  load()
}

async function onDelete(row: RoleV2) {
  // R3 / C5 (P0-3) R-106：破坏性删除告知 —— 角色删除会级联清功能授权 + 字段可见性规则。
  // N = 功能授权数（角色已带 permissionCodes）；M = 字段可见性规则数（按 roleCode 查 field-acl）。
  // 先取 M 再弹确认框，保证告知文案数字准确（参考 useRuleActions.ts 禁用原生 confirm 范式）。
  const funcCount = row.permissionCodes?.length ?? 0
  let fieldAclCount = 0
  try {
    const rules = await listAclRules({ roleCode: row.roleCode })
    fieldAclCount = rules?.length ?? 0
  } catch {
    // 取字段级规则数失败不影响删除确认，按 0 兜底（告知文案仍可点删）
  }
  dialog.warning({
    title: t('pages.settings.permission.RolesTab.s17'),
    content: t('pages.settings.permission.RolesTab.s18', { n: funcCount, m: fieldAclCount }),
    positiveText: t('pages.settings.permission.RolesTab.s19'),
    negativeText: t('pages.settings.permission.RolesTab.s13'),
    onPositiveClick: async () => {
      try {
        await deleteRole(row.id)
        message.success('已删除')
        await load()
      } catch (e: any) {
        message.error('删除失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
      }
    },
  })
}

onMounted(load)
</script>

<style scoped>
.roles-tab {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  gap: var(--space-2);
}
/* 搜索/筛选输入宽度（对齐 CampusControl rules tab 视觉密度） */
.rule-filter-search { width: 240px; }
.rule-filter-select { width: 136px; }

/* === 2026-10-15 兵哥纠偏：撤回过度单色化，回归前端标准
 * 初版把工具栏全改 ghost、删除改「hover 才转红」，与两处权威规范冲突：
 *   - frontend-DESIGN §Data Table：操作列按钮用 quaternary + type=primary/error
 *   - frontend-layout-standard §1.8.1：删除 type="error"
 * 危险色是安全信号，不是视觉噪音 —— 正确做法是「降低其他元素的色量」，
 * 而不是「把危险信号也一起去掉」。现仅保留来源标签中性灰（原 primary 撞品牌色确实是问题）。 */

/* 来源标签：中性灰，不参与语义区分（预置/自定义语义同级，用文字承载） */
.roles-tab :deep(.neutral-tag) {
  --n-color: transparent;
  --n-text-color: var(--ink-soft);
  background: var(--border-hairline);
}
</style>
