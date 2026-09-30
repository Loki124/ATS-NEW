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
      <n-button @click="load">{{ t('pages.settings.permission.RolesTab.s4') }}</n-button>
      <n-button type="info" @click="onCloneFromTemplate">{{ t('pages.settings.permission.RolesTab.s5') }}</n-button>
      <n-button type="primary" class="gradient-btn" @click="onCreate">{{ t('pages.settings.permission.RolesTab.s6') }}</n-button>
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
      v-model:show="cloneModal.show"
      preset="card"
      :title="t('pages.settings.permission.RolesTab.s7')"
      style="max-width: 480px"
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
          <n-button @click="cloneModal.show = false">{{ t('pages.settings.permission.RolesTab.s13') }}</n-button>
          <n-button type="primary" class="gradient-btn" :loading="cloneModal.saving" @click="onSubmitClone">{{ t('pages.settings.permission.RolesTab.s14') }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <RoleEditModal
      v-model:show="editModal.show"
      :role="editModal.role"
      @saved="onEditSaved"
    />

    <RoleDataPermDrawer
      v-model:visible="dataPermDrawer.show"
      :role-id="dataPermDrawer.roleId"
      :role-code="dataPermDrawer.roleCode"
      :role-name="dataPermDrawer.roleName"
      @saved="onDataPermSaved"
    />
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
import { NButton, NSpace, NDataTable, NModal, NForm, NFormItem, NSelect, NInput, NTag, NSwitch, NTooltip, useMessage } from 'naive-ui'
import { listRoles, cloneFromTemplate, deleteRole, updateRole, type RoleV2 } from '@/api/role-v2'
import { listTemplates, type PermissionTemplate } from '@/api/permission-template'
import { localPagination } from '@/composables/useTablePagination'
import RoleEditModal from './RoleEditModal.vue'
import RoleDataPermDrawer from '@/components/role/RoleDataPermDrawer.vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const message = useMessage()
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

const columns = [
  { title: '角色编码', key: 'roleCode', width: 160, render: (r: RoleV2) => r.roleCode || '—' },
  { title: '角色名称', key: 'roleName', width: 160, render: (r: RoleV2) => r.roleName || '—' },
  { title: '模板来源', key: 'templateCode', width: 140, render: (r: RoleV2) => r.templateCode || '—' },
  {
    title: '默认数据范围',
    key: 'defaultDataScopeType',
    width: 140,
    render: (r: RoleV2) => scopeTypeLabels[r.defaultDataScopeType ?? ''] ?? '—',
  },
  {
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
  },
  {
    title: '来源',
    key: 'isSystem',
    width: 90,
    render: (r: RoleV2) =>
      h(NTag, { type: r.isSystem === 1 ? 'default' : 'primary', bordered: false, size: 'small' },
        { default: () => (r.isSystem === 1 ? '预置' : '自定义') }),
  },
  {
    title: '权限码数',
    key: 'permissionCodes',
    width: 100,
    render: (r: RoleV2) => r.permissionCodes?.length ?? 0,
  },
  {
    title: '操作',
    key: 'actions',
    width: 230,
    fixed: 'right' as const,
    render(row: RoleV2) {
      const isSuper = row.roleCode === 'SUPER_ADMIN'
      const dataPermBtn = h(
        NTooltip,
        { disabled: !isSuper },
        {
          trigger: () =>
            h(
              NButton,
              {
                size: 'small',
                tertiary: true,
                type: 'primary',
                disabled: isSuper,
                onClick: () => openDrawer(row),
              },
              () => t('dataperm.entry.button'),
            ),
          default: () => t('dataperm.entry.tooltip.superAdmin'),
        },
      )
      return h(NSpace, { size: 4 }, () => [
        h(NButton, {
          size: 'small',
          tertiary: true,
          type: 'primary',
          onClick: () => onEdit(row),
        }, () => '编辑'),
        dataPermBtn,
        h(NButton, {
          size: 'small',
          tertiary: true,
          type: 'error',
          disabled: row.isSystem === 1,
          onClick: () => onDelete(row),
        }, () => '删除'),
      ])
    },
  },
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

const editModal = reactive({
  show: false,
  role: null as RoleV2 | null,
})

const dataPermDrawer = reactive({
  show: false,
  roleId: '',
  roleCode: '',
  roleName: '',
})

function openDrawer(row: RoleV2) {
  dataPermDrawer.roleId = row.id
  dataPermDrawer.roleCode = row.roleCode
  dataPermDrawer.roleName = row.roleName
  dataPermDrawer.show = true
}

function onDataPermSaved() {
  dataPermDrawer.show = false
}

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
    message.warning('模板 + 新角色编码 + 新角色名称 必填')
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
  try {
    await deleteRole(row.id)
    message.success('已删除')
    await load()
  } catch (e: any) {
    message.error('删除失败: ' + (e?.response?.data?.message ?? e?.message ?? e))
  }
}

onMounted(load)
</script>

<style scoped>
.roles-tab {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  gap: var(--space-3);
}
/* 搜索/筛选输入宽度（对齐 CampusControl rules tab 视觉密度） */
.rule-filter-search { width: 260px; }
.rule-filter-select { width: 150px; }
</style>
