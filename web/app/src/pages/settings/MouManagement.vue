<template>
  <div class="page-container mou-management">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">管理单元 (Management Unit)</h1>
        <p class="page-subtitle">数据权限的组织范围载体 —— 树形层级 + 组织范围 + 人员范围，可配置按应用独立的数据范围（组织数据范围 / 人员数据范围）</p>
      </div>
    </div>

    <!-- 管理单元列表（北森交互：表格为主视图，树形展开在「名称」列） -->
    <n-card :bordered="false" class="glass-panel">
          <div class="toolbar">
            <n-select
              v-model:value="unitStatusFilter"
              :options="statusFilterOptions"
              style="width: 160px"
              placeholder="全部状态"
              clearable
            />
            <div class="spacer"></div>
            <n-button type="primary" @click="openCreateRoot">
              <template #icon><n-icon :component="AddOutline" /></template>
              新增
            </n-button>
            <n-button :disabled="!checkedRowKeys.length" @click="batchDisable">
              <template #icon><n-icon :component="StopOutline" /></template>
              停用
            </n-button>
            <n-button :disabled="!allUnits.length" @click="exportDataRange">
              <template #icon><n-icon :component="DownloadOutline" /></template>
              导出数据范围
            </n-button>
          </div>

          <n-data-table
            :data="unitTreeData"
            :columns="unitTableColumns"
            :row-key="(row: ManagementUnit) => String(row.id)"
            :checked-row-keys="checkedRowKeys"
            :scroll-x="760"
            :loading="unitLoading"
            @update:checked-row-keys="(keys: Array<string | number>) => (checkedRowKeys = keys.map(String))"
          />
        </n-card>

    <!-- 管理单元 新建/编辑/详情 融合弹窗（居中；编辑与点击名称共用） -->
    <n-modal
      v-model:show="unitModalVisible"
      preset="card"
      :style="{ width: '900px' }"
      :mask-closable="false"
    >
      <template #header>
        <div v-if="editingUnit" class="unit-detail-header">
          <div class="unit-title-row">
            <h2 class="unit-name">{{ unitForm.unitName }}</h2>
            <n-space>
              <n-button size="small" @click="openBasicInfoEdit">编辑基本信息</n-button>
              <n-button size="small" type="primary" @click="openViewAuth">查看授权用户</n-button>
            </n-space>
          </div>
          <div class="unit-meta-row">
            <span class="meta-item"><label>上级管理单元</label><span class="meta-value">{{ parentUnitName }}</span></span>
            <span class="meta-item"><label>编码</label><span class="meta-value">{{ unitForm.code || '—' }}</span></span>
            <span class="meta-item"><label>显示顺序</label><span class="meta-value">{{ unitForm.displayOrder ?? 0 }}</span></span>
            <span class="meta-item"><label>说明</label><span class="meta-value">{{ unitForm.description || '—' }}</span></span>
          </div>
        </div>
        <span v-else class="modal-title">{{ editingUnit ? '编辑管理单元' : '新建管理单元' }}</span>
      </template>
      <n-form :model="unitForm" label-placement="top">
        <template v-if="!editingUnit">
          <n-grid :cols="2" :x-gap="16">
            <n-grid-item>
              <n-form-item label="单元名称" required>
                <n-input v-model:value="unitForm.unitName" placeholder="如：华东大区" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="编码">
                <n-input v-model:value="unitForm.code" placeholder="如：EAST-CHINA（选填）" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="单元类型">
              <n-select v-model:value="unitForm.unitType" :options="unitTypeOptions" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="显示顺序">
              <n-input-number v-model:value="unitForm.displayOrder" :min="0" style="width: 100%" />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-form-item label="上级单元">
          <n-tree-select
            v-model:value="unitForm.parentId"
            :options="parentOptions"
            clearable
            placeholder="不选 = 根单元"
            :default-expand-all="true"
            key-field="value"
            label-field="label"
          />
        </n-form-item>
        <n-form-item label="说明">
          <n-input v-model:value="unitForm.description" type="textarea" :rows="2" placeholder="选填" />
        </n-form-item>
        </template>
      </n-form>

      <template v-if="detailUnit">
        <n-tabs v-model:value="detailAppTab" type="line" class="detail-tabs">
          <n-tab-pane v-for="app in appTabs" :key="app.value" :name="app.value">
            <template #tab>{{ appTabLabel(app.value) }}</template>
            <div class="detail-app-hint">当前应用：<b>{{ app.label }}</b> —— 以下「组织范围 / 人员范围」均按该应用独立配置，互不干扰</div>

            <!-- 管理组织范围（北森式区块：生效开关 + 标题 + 右侧操作 + 可收起） -->
            <div class="scope-block">
              <div class="scope-block-header">
                <div class="scope-block-title">
                  <n-switch v-model:value="orgBlockEnabled" size="small" />
                  <span>管理组织范围</span>
                </div>
                <n-space :size="4" align="center" :wrap="false">
                  <n-button text type="primary" @click="openDetailOrgScope">配置组织范围</n-button>
                  <span class="scope-block-divider">|</span>
                  <n-button text type="primary" :disabled="!orgCheckedKeys.length" @click="batchRemoveOrgNodes">批量删除</n-button>
                  <span class="scope-block-divider">|</span>
                  <n-button text @click="orgBlockExpanded = !orgBlockExpanded">
                    {{ orgBlockExpanded ? '收起' : '展开' }}
                    <n-icon :component="orgBlockExpanded ? ChevronUpOutline : ChevronDownOutline" />
                  </n-button>
                </n-space>
              </div>
              <template v-if="orgBlockExpanded">
                <n-data-table
                  v-model:checked-row-keys="orgCheckedKeys"
                  :data="detailOrgNodes"
                  :columns="detailOrgColumns"
                  :row-key="(row: OrgScopeNode) => row.deptId"
                  size="small"
                  :scroll-x="620"
                />
                <n-empty v-if="!detailOrgNodes.length" description="该应用下尚未配置组织范围，点击「配置组织范围」按应用设置" class="detail-empty" />
                <div class="scope-block-total">共{{ detailOrgNodes.length }}条</div>
                <div class="scope-readout detail-range-readout">组织数据范围：{{ dataRangeLabel(currentAppOrgDataRange) }}</div>
              </template>
            </div>

            <!-- 管理人员范围（北森式区块） -->
            <div class="scope-block">
              <div class="scope-block-header">
                <div class="scope-block-title">
                  <n-switch v-model:value="personBlockEnabled" size="small" />
                  <span>管理人员范围</span>
                </div>
                <n-space :size="4" align="center" :wrap="false">
                  <n-dropdown :options="memberAddOptions" @select="(t: string) => openDetailAddMember(t as 'DEPT' | 'USER' | 'PERSON')">
                    <n-button text type="primary">添加成员</n-button>
                  </n-dropdown>
                  <span class="scope-block-divider">|</span>
                  <n-button text type="primary" @click="openDetailPersonDataRange">设置数据范围</n-button>
                  <span class="scope-block-divider">|</span>
                  <n-button text @click="personBlockExpanded = !personBlockExpanded">
                    {{ personBlockExpanded ? '收起' : '展开' }}
                    <n-icon :component="personBlockExpanded ? ChevronUpOutline : ChevronDownOutline" />
                  </n-button>
                </n-space>
              </div>
              <template v-if="personBlockExpanded">
                <n-data-table
                  :data="detailMembersFiltered"
                  :columns="detailMemberColumns"
                  :row-key="(row: ManagementUnitMember) => row.id"
                  size="small"
                  :scroll-x="480"
                  :loading="detailMemberLoading"
                />
                <n-empty v-if="!detailMembersFiltered.length" :description="`「${currentAppLabel}」下暂无成员，点击「添加成员」按应用添加`" class="detail-empty" />
                <div class="scope-block-total">共{{ detailMembersFiltered.length }}条</div>
                <div class="scope-readout detail-range-readout">人员数据范围：{{ dataRangeLabel(currentAppPersonDataRange) }}</div>
              </template>
            </div>
          </n-tab-pane>
        </n-tabs>
      </template>
      <n-empty v-else description="保存后可在下方应用 Tab 中按应用配置组织范围 / 人员范围 / 数据范围" />

      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="unitModalVisible = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="unitSaving" @click="onSaveUnit">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 编辑基本信息 弹窗 -->
    <n-modal
      v-model:show="basicInfoModalVisible"
      preset="card"
      title="编辑基本信息"
      :style="{ width: '560px' }"
      :mask-closable="false"
    >
      <n-form :model="basicInfoForm" label-placement="top">
        <n-form-item label="名称" required>
          <n-input v-model:value="basicInfoForm.unitName" placeholder="如：华东大区" />
        </n-form-item>
        <n-form-item label="编码">
          <n-input v-model:value="basicInfoForm.code" placeholder="如：EAST-CHINA（选填）" />
        </n-form-item>
        <n-form-item label="上级管理单元">
          <n-tree-select
            v-model:value="basicInfoForm.parentId"
            :options="parentOptions"
            clearable
            placeholder="不选 = 根单元"
            :default-expand-all="true"
            key-field="value"
            label-field="label"
          />
        </n-form-item>
        <n-form-item label="显示顺序">
          <n-input-number v-model:value="basicInfoForm.displayOrder" :min="0" style="width: 100%" />
        </n-form-item>
        <n-form-item label="说明">
          <n-input v-model:value="basicInfoForm.description" type="textarea" :rows="2" placeholder="选填" />
        </n-form-item>
        <n-form-item label="当前单元是否启用">
          <n-switch v-model:value="basicInfoForm.status" :checked-value="1" :unchecked-value="0">
            <template #checked>启用</template>
            <template #unchecked>停用</template>
          </n-switch>
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="basicInfoModalVisible = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="basicInfoSaving" @click="onSaveBasicInfo">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 成员 添加 弹窗 -->
    <n-modal
      v-model:show="memberModalVisible"
      preset="card"
      :title="memberFormTitle"
      :style="{ width: '560px' }"
      :mask-closable="false"
    >
      <n-form :model="memberForm" label-placement="top">
        <n-form-item label="成员类型">
          <n-radio-group v-model:value="memberForm.memberType">
            <n-space>
              <n-radio value="DEPT">组织节点</n-radio>
              <n-radio value="USER">系统用户</n-radio>
              <n-radio value="PERSON">HR人员</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>

        <n-form-item v-if="memberForm.memberType === 'DEPT'" label="组织节点" required>
          <n-tree-select
            v-model:value="memberForm.departmentId"
            :options="deptTreeOptions"
            :default-expand-all="true"
            clearable
            placeholder="选择组织节点"
            key-field="key"
            label-field="label"
            children-field="children"
          />
        </n-form-item>

        <n-form-item v-else-if="memberForm.memberType === 'USER'" label="系统用户" required>
          <n-select
            v-model:value="memberForm.userId"
            :options="userOptions"
            filterable
            clearable
            placeholder="搜索并选择系统用户"
          />
        </n-form-item>

        <n-form-item v-else label="HR人员" required>
          <n-select
            v-model:value="memberForm.personId"
            :options="personOptions"
            filterable
            clearable
            placeholder="搜索并选择 HR 台账人员"
          />
        </n-form-item>

        <n-form-item label="含子级">
          <n-radio-group v-model:value="memberForm.includeChildren">
            <n-space>
              <n-radio :value="1">是</n-radio>
              <n-radio :value="0">否</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>

        <n-form-item label="备注">
          <n-input v-model:value="memberForm.remark" type="textarea" :rows="2" placeholder="可选" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="memberModalVisible = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="memberSaving" @click="onSaveMember">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 详情「设置人员数据范围」复用 DataRangeModal（按应用回写单元） -->
    <DataRangeModal
      v-model:show="detailPersonDataRangeVisible"
      :value="detailPersonDataRangeValue"
      @confirm="onDetailPersonDataRangeConfirm"
    />
    <!-- 详情「配置组织范围」复用 OrgScopeTreeModal（按应用回写单元） -->
    <OrgScopeTreeModal
      v-model:show="detailOrgScopeVisible"
      :value="detailOrgScopeValue"
      @confirm="onDetailOrgScopeConfirm"
    />

    <!-- 查看授权用户 弹窗 -->
    <n-modal
      v-model:show="viewAuthVisible"
      preset="card"
      title="授权用户"
      :style="{ width: '560px' }"
      :mask-closable="false"
    >
      <n-data-table
        :data="authMembers"
        :columns="authColumns"
        :row-key="(row: ManagementUnitMember) => row.id"
        size="small"
        :loading="authLoading"
        :pagination="{ pageSize: 10 }"
      />
    </n-modal>
</div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, onMounted, watch } from 'vue'
import {
  NButton, NSpace, NIcon, NEmpty,
  NPopconfirm, useMessage,
} from 'naive-ui'
import {
  AddOutline, CreateOutline, TrashOutline,
  StopOutline, DownloadOutline, ChevronUpOutline, ChevronDownOutline,
} from '@vicons/ionicons5'
import {
  listManagementUnits, treeManagementUnits, createManagementUnit, updateManagementUnit,
  deleteManagementUnit,
  listManagementUnitMembers, addManagementUnitMember, removeManagementUnitMember,
  type ManagementUnit, type ManagementUnitTreeNode, type ManagementUnitMember,
} from '@/api/management-unit'
import OrgScopeTreeModal, { type OrgScopeNode } from './OrgScopeTreeModal.vue'
import DataRangeModal from './DataRangeModal.vue'
import { listUsers } from '@/api/users'
import { listPersons } from '@/api/campusControl'
import { useDepartmentStore, type Department } from '@/stores/department'

const message = useMessage()

// ===== 管理单元列表（北森表格主视图） =====
const allUnits = ref<ManagementUnit[]>([])
const treeNodes = ref<ManagementUnitTreeNode[]>([])
const unitLoading = ref(false)
const checkedRowKeys = ref<string[]>([])
const unitStatusFilter = ref<number | null>(null)

const statusFilterOptions = [
  { label: '全部状态', value: null as number | null },
  { label: '启用', value: 1 },
  { label: '禁用', value: 0 },
]

const unitTypeOptions = [
  { label: '组织', value: 'org' },
  { label: '部门', value: 'dept' },
  { label: '项目', value: 'project' },
  { label: '自定义', value: 'custom' },
]

const filteredUnits = computed(() =>
  unitStatusFilter.value == null
    ? allUnits.value
    : allUnits.value.filter((u) => u.status === unitStatusFilter.value),
)

/** 扁平列表 → 树形（n-data-table 以 children 字段渲染展开箭头，第一列「名称」即树列） */
const unitTreeData = computed(() => buildUnitTree(filteredUnits.value))
function buildUnitTree(list: ManagementUnit[]): any[] {
  const byId = new Map<string, any>()
  list.forEach((u) => byId.set(String(u.id), { ...u, key: String(u.id), children: [] as any[] }))
  const roots: any[] = []
  list.forEach((u) => {
    const node = byId.get(String(u.id))!
    const pid = u.parentId != null ? String(u.parentId) : null
    if (pid && byId.has(pid)) byId.get(pid)!.children.push(node)
    else roots.push(node)
  })
  return roots
}

const unitTableColumns = [
  {
    title: '名称', key: 'unitName', minWidth: 200,
    render: (row: ManagementUnit) =>
      h(NButton, { text: true, type: 'primary', onClick: () => openUnitModal(row) }, { default: () => row.unitName }),
  },
  { title: '编码', key: 'code', width: 140, render: (row: ManagementUnit) => row.code || '—' },
  { title: '说明', key: 'description', minWidth: 160, render: (row: ManagementUnit) => row.description || '—' },
  { title: '显示顺序', key: 'displayOrder', width: 100, render: (row: ManagementUnit) => row.displayOrder ?? 0 },
  {
    title: '操作', key: 'action', width: 150,
    render: (row: ManagementUnit) =>
      h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => openUnitModal(row) }, { default: () => '编辑' }),
          h(NPopconfirm, {
            onPositiveClick: () => onDeleteUnit(row),
            positiveText: '确认', negativeText: '取消',
          }, {
            default: () => `确认删除「${row.unitName}」？其直接子单元将自动提升为根节点。`,
            trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, { default: () => '删除' }),
          }),
        ],
      }),
  },
]

// 弹窗标题区的「上级管理单元」只读展示
const parentUnitName = computed(() => {
  if (!unitForm.parentId) return '—'
  return allUnits.value.find((u) => String(u.id) === String(unitForm.parentId))?.unitName || String(unitForm.parentId)
})

// n-tree-select 选项（构建层级，排除正在编辑的节点及其后代以防水环）
const parentOptions = computed(() => {
  const blockId = editingUnit.value?.id
  const flat: ManagementUnit[] = []
  const walk = (nodes: ManagementUnitTreeNode[]) => {
    for (const n of nodes) {
      if (blockId && String(n.id) === String(blockId)) continue
      flat.push({
        id: String(n.id), unitName: n.unitName, unitType: n.unitType,
        parentId: n.parentId, orgScope: n.orgScope,
        includeChildren: 1, status: n.status,
      })
      if (n.children?.length) walk(n.children)
    }
  }
  walk(treeNodes.value)
  const blocked = new Set<string>()
  if (blockId) {
    const collect = (nodes: ManagementUnitTreeNode[]) => {
      for (const n of nodes) {
        if (String(n.id) === String(blockId)) {
          // 阻断被编辑节点及其全部后代，防止形成环
          const addDescendants = (children: ManagementUnitTreeNode[]) => {
            for (const c of children) {
              blocked.add(String(c.id))
              if (c.children?.length) addDescendants(c.children)
            }
          }
          if (n.children?.length) addDescendants(n.children)
        } else if (n.children?.length) {
          collect(n.children)
        }
      }
    }
    collect(treeNodes.value)
  }
  const allowed = flat.filter((u) => !blocked.has(String(u.id)))
  const byId = new Map<string, any>()
  allowed.forEach((u) => byId.set(String(u.id), { label: u.unitName, value: String(u.id), children: [] as any[] }))
  const roots: any[] = []
  allowed.forEach((u) => {
    const node = byId.get(String(u.id))!
    if (u.parentId && byId.has(String(u.parentId)) && !blocked.has(String(u.parentId))) {
      byId.get(String(u.parentId))!.children.push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
})

// ===== 弹窗表单 =====
const unitModalVisible = ref(false)
const editingUnit = ref<ManagementUnit | null>(null)
const unitSaving = ref(false)
const unitForm = reactive({
  id: '' as string,
  unitName: '',
  code: '' as string,
  unitType: 'org',
  parentId: null as string | number | null,
  displayOrder: 0 as number,
  description: '' as string,
  status: 1 as number,
  includeChildren: 1 as number,
})

const basicInfoModalVisible = ref(false)
const basicInfoSaving = ref(false)
const basicInfoForm = reactive({
  unitName: '',
  code: '',
  parentId: null as string | number | null,
  displayOrder: 0 as number,
  description: '',
  status: 1 as number,
})

function deptNameById(id: string): string {
  return deptStore.departments.find((d: any) => String(d.id) === String(id))?.name || String(id)
}
function parentDeptName(id?: string | null): string {
  if (!id) return '—'
  const d = deptStore.departments.find((x: any) => String(x.id) === String(id))
  if (!d || !d.parentId) return '—'
  return deptStore.departments.find((x: any) => String(x.id) === String(d.parentId))?.name || String(d.parentId)
}

/** 把任意 org_scope 形状(结构化列表 / 纯字符串列表 / dict 部门子键)规整为 OrgScopeNode[] 供弹窗回填 */
function toOrgScopeNodes(v: any): OrgScopeNode[] {
  if (!v) return []
  if (Array.isArray(v)) {
    const nodes: OrgScopeNode[] = []
    for (const x of v) {
      if (x && typeof x === 'object' && (x.deptId || x.departmentId || x.department_id)) {
        nodes.push({
          deptId: String(x.deptId ?? x.departmentId ?? x.department_id),
          includeChildren: !!(x.includeChildren ?? x.include_children ?? false),
        })
      } else if (typeof x === 'string') {
        nodes.push({ deptId: x, includeChildren: false })
      }
    }
    return nodes
  }
  if (v && typeof v === 'object') {
    for (const k of ['department_ids', 'dept_ids', 'departments', 'org_ids']) {
      if (Array.isArray(v[k])) {
        return v[k].map((d: any) => ({ deptId: String(d), includeChildren: false }))
      }
    }
  }
  return []
}

function dimLabel(d: string): string {
  return ({ dept: '部门', department: '部门', 部门: '部门', position: '职务', tenure: '司龄' } as Record<string, string>)[d] || d || '维度'
}

function dataRangeLabel(v: any): string {
  if (!v || !Array.isArray(v.groups) || !v.groups.length) return '（未配置）'
  const parts = v.groups.map((g: any, i: number) => {
    const conds = (g.conditions || [])
      .map((c: any) => {
        const name = c.dimension === 'dept' ? deptNameById(String(c.value)) : c.value
        const op = c.operator === 'neq' ? '≠' : '='
        return `${dimLabel(c.dimension)}${op}${name}${c.includeSub ? '(含子级)' : ''}`
      })
      .join(g.op === 'and' ? ' 且 ' : ' 或 ')
    return `组${i + 1}(${conds || '空'})`
  })
  return parts.join(v.op === 'and' ? ' 且 ' : ' 或 ')
}

function openCreateRoot() {
  editingUnit.value = null
  detailUnit.value = null
  Object.assign(unitForm, {
    id: '', unitName: '', code: '', unitType: 'org', parentId: null,
    displayOrder: 0, description: '', status: 1, includeChildren: 1,
  })
  unitModalVisible.value = true
}
/** 编辑与点击名称共用：打开融合弹窗（基本信息 + 按应用组织/人员范围 + 数据范围） */
function openUnitModal(n: ManagementUnit) {
  editingUnit.value = n
  detailUnit.value = n
  detailAppTab.value = 'public'
  Object.assign(unitForm, {
    id: String(n.id), unitName: n.unitName, code: n.code || '', unitType: n.unitType,
    parentId: n.parentId ? String(n.parentId) : null,
    displayOrder: n.displayOrder ?? 0, description: n.description || '', status: n.status,
    includeChildren: n.includeChildren ?? 1,
  })
  unitModalVisible.value = true
  loadDetailMembers(n)
}

/** 打开「编辑基本信息」弹窗，回填当前单元基础字段 */
function openBasicInfoEdit() {
  Object.assign(basicInfoForm, {
    unitName: unitForm.unitName,
    code: unitForm.code,
    parentId: unitForm.parentId,
    displayOrder: unitForm.displayOrder,
    description: unitForm.description,
    status: unitForm.status,
  })
  basicInfoModalVisible.value = true
}

/** 保存「编辑基本信息」弹窗中的基础字段（名称/编码/上级/显示顺序/说明） */
async function onSaveBasicInfo() {
  if (!basicInfoForm.unitName.trim()) {
    message.warning('单元名称必填')
    return
  }
  basicInfoSaving.value = true
  try {
    const payload = {
      unitName: basicInfoForm.unitName.trim(),
      code: basicInfoForm.code.trim() || null,
      parentId: basicInfoForm.parentId ? Number(basicInfoForm.parentId) : null,
      displayOrder: basicInfoForm.displayOrder ?? 0,
      description: basicInfoForm.description.trim() || null,
      status: basicInfoForm.status,
    }
    await updateManagementUnit(unitForm.id, payload)
    message.success('已更新')
    basicInfoModalVisible.value = false
    Object.assign(unitForm, payload)
    await loadUnits()
    const updated = allUnits.value.find((u) => String(u.id) === unitForm.id)
    if (updated) {
      editingUnit.value = updated
      detailUnit.value = updated
    }
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message || e?.message || e))
  } finally {
    basicInfoSaving.value = false
  }
}

async function onSaveUnit() {
  if (!unitForm.unitName.trim()) {
    message.warning('单元名称必填')
    return
  }
  unitSaving.value = true
  try {
    const payload = {
      unitName: unitForm.unitName.trim(),
      code: unitForm.code.trim() || null,
      unitType: unitForm.unitType,
      parentId: unitForm.parentId ? Number(unitForm.parentId) : null,
      displayOrder: unitForm.displayOrder ?? 0,
      description: unitForm.description.trim() || null,
      status: unitForm.status,
      includeChildren: unitForm.includeChildren,
    }
    if (editingUnit.value) {
      await updateManagementUnit(unitForm.id, payload)
      message.success('已更新')
    } else {
      const created = await createManagementUnit(payload)
      editingUnit.value = created as ManagementUnit
      detailUnit.value = created as ManagementUnit
      message.success('已创建')
    }
    unitModalVisible.value = false
    await loadUnits()
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message || e?.message || e))
  } finally {
    unitSaving.value = false
  }
}

async function onDeleteUnit(row: ManagementUnit) {
  try {
    const res = await deleteManagementUnit(String(row.id))
    if (res?.success) {
      message.success('已删除')
      await loadUnits()
    } else {
      message.error(res?.message || '删除失败')
    }
  } catch (e: any) {
    message.error('删除失败: ' + (e?.response?.data?.message || e?.message || e))
  }
}

async function batchDisable() {
  if (!checkedRowKeys.value.length) { message.warning('请先勾选管理单元'); return }
  try {
    for (const id of checkedRowKeys.value) {
      await updateManagementUnit(String(id), { status: 0 })
    }
    message.success(`已停用 ${checkedRowKeys.value.length} 个管理单元`)
    checkedRowKeys.value = []
    await loadUnits()
  } catch (e: any) {
    message.error('批量停用失败: ' + (e?.response?.data?.message || e?.message || e))
  }
}

function exportDataRange() {
  const rows = checkedRowKeys.value.length
    ? allUnits.value.filter((u) => checkedRowKeys.value.includes(String(u.id)))
    : allUnits.value
  const payload = rows.map((u) => ({
    id: u.id, unitName: u.unitName, code: u.code,
    orgScope: u.orgScope, dataRange: u.dataRange,
    personDataRange: u.personDataRange ?? null,
  }))
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'management-unit-data-range.json'
  a.click()
  URL.revokeObjectURL(url)
  message.success(`已导出 ${rows.length} 个管理单元的数据范围`)
}

async function loadUnits() {
  unitLoading.value = true
  try {
    const [flat, tree] = await Promise.all([
      listManagementUnits(),
      treeManagementUnits(),
    ])
    allUnits.value = flat
    treeNodes.value = tree
  } catch (e: any) {
    message.error('加载管理单元失败: ' + (e?.message || e))
  } finally {
    unitLoading.value = false
  }
}

// ===== 融合弹窗：按应用组织/人员范围 + 数据范围 =====
const detailUnit = ref<ManagementUnit | null>(null)
const detailAppTab = ref('public')
// 北森式范围区块 UI 状态：生效开关（默认开，前端展示态）+ 收起/展开
const orgBlockEnabled = ref(true)
const personBlockEnabled = ref(true)
const orgBlockExpanded = ref(true)
const personBlockExpanded = ref(true)
const orgCheckedKeys = ref<string[]>([])
const memberAddOptions = [
  { label: '组织节点', key: 'DEPT' },
  { label: '系统用户', key: 'USER' },
  { label: 'HR人员', key: 'PERSON' },
]
const detailOrgScopeVisible = ref(false)
const detailOrgScopeValue = ref<OrgScopeNode[] | null>(null)
const detailPersonDataRangeVisible = ref(false)
const detailPersonDataRangeValue = ref<any>(null)
const detailMemberLoading = ref(false)
const detailMembers = ref<ManagementUnitMember[]>([])

const appTabs = [
  { label: '公共', value: 'public' },
  { label: '招聘', value: 'recruit' },
  { label: '校招', value: 'campus' },
  { label: '社招', value: 'social' },
  { label: '内推', value: 'referral' },
]

const currentAppLabel = computed(() => {
  const a = appTabs.find((x) => x.value === detailAppTab.value)
  return a ? a.label : detailAppTab.value
})

/** 当前应用 Tab 的组织范围（public 回退单元级 orgScope，其余回退空） */
const detailOrgNodes = computed<OrgScopeNode[]>(() => {
  if (!detailUnit.value) return []
  const app = detailAppTab.value
  if (app === 'public') return toOrgScopeNodes(detailUnit.value.orgScope)
  const perApp = detailUnit.value.orgScopes?.[app]
  return perApp ? toOrgScopeNodes(perApp) : []
})

/** 当前应用 Tab 的组织数据范围（public 回退单元级 dataRange，其余回退空） */
const currentAppOrgDataRange = computed<any>(() => {
  if (!detailUnit.value) return null
  const app = detailAppTab.value
  if (app === 'public') return (detailUnit.value.dataRange as any) ?? null
  return detailUnit.value.dataRanges?.[app] ?? null
})

/** 当前应用 Tab 的人员数据范围（public 回退单元级 personDataRange，其余回退空） */
const currentAppPersonDataRange = computed<any>(() => {
  if (!detailUnit.value) return null
  const app = detailAppTab.value
  if (app === 'public') return (detailUnit.value.personDataRange as any) ?? null
  return detailUnit.value.personDataRanges?.[app] ?? null
})

/** 当前应用 Tab 的成员（public = 无 appCode 的公共成员；其余 = 该 appCode 的专属成员） */
const detailMembersFiltered = computed<ManagementUnitMember[]>(() => {
  if (!detailUnit.value) return []
  const app = detailAppTab.value
  return detailMembers.value.filter((m) => {
    const mc = m.appCode || null
    if (app === 'public') return !mc
    return mc === app
  })
})
const detailOrgColumns = [
  { type: 'selection' as const },
  { title: '组织名称', key: 'orgName', minWidth: 140, render: (row: OrgScopeNode) => deptNameById(row.deptId) },
  { title: '组织编码', key: 'deptId', width: 120, render: (row: OrgScopeNode) => row.deptId },
  { title: '上级组织', key: 'parent', width: 140, render: (row: OrgScopeNode) => parentDeptName(row.deptId) },
  { title: '是否包含下级', key: 'includeChildren', width: 120,
    render: (row: OrgScopeNode) => (row.includeChildren ? '含下级' : '仅本级') },
  {
    title: '操作', key: 'action', width: 80,
    render: (row: OrgScopeNode) =>
      h(NButton, { size: 'small', text: true, type: 'error', onClick: () => onRemoveOrgNode(row) }, { default: () => '删除' }),
  },
]
const detailMemberColumns = [
  {
    title: '姓名', key: 'name', minWidth: 120,
    render: (row: ManagementUnitMember) => row.departmentName || row.userName || row.personName || row.departmentId || row.userId || row.personId || '—',
  },
  // 成员模型暂无邮箱字段，预留列位（后端补 email 后直接展示）
  { title: '邮箱', key: 'email', minWidth: 160, render: (row: any) => (row as any).email || '—' },
  {
    title: '组织', key: 'org', minWidth: 140,
    render: (row: ManagementUnitMember) => (row.departmentId ? deptNameById(row.departmentId) : '—'),
  },
  {
    title: '操作', key: 'action', width: 80,
    render: (row: ManagementUnitMember) =>
      h(NButton, { size: 'small', text: true, type: 'error', onClick: () => onRemoveDetailMember(row) }, { default: () => '删除' }),
  },
]

/** 应用 tab 标签：已配置范围数（组织范围/人员范围 任一非空计 1），如「公共(2)」 */
function appTabLabel(appValue: string): string {
  const app = appTabs.find((x) => x.value === appValue)
  const label = app ? app.label : appValue
  let count = 0
  if (appValue === 'public') {
    if (toOrgScopeNodes(detailUnit.value?.orgScope).length) count += 1
    if (detailUnit.value?.dataRange) count += 1
  } else {
    if (toOrgScopeNodes(detailUnit.value?.orgScopes?.[appValue]).length) count += 1
    if (detailUnit.value?.dataRanges?.[appValue]) count += 1
  }
  return count ? `${label}(${count})` : label
}

/** 把组织节点集写回当前应用（public=单元级 orgScope，其余=orgScopes[app]） */
async function persistOrgNodes(nodes: OrgScopeNode[]) {
  if (!detailUnit.value) return
  const app = detailAppTab.value
  const payloadNodes = nodes && nodes.length ? nodes : null
  if (app === 'public') {
    const updated = await updateManagementUnit(String(detailUnit.value.id), { orgScope: payloadNodes })
    detailUnit.value = { ...detailUnit.value, orgScope: (updated as any).orgScope ?? payloadNodes }
  } else {
    const merged = { ...(detailUnit.value.orgScopes || {}), [app]: payloadNodes }
    const updated = await updateManagementUnit(String(detailUnit.value.id), { orgScopes: merged })
    detailUnit.value = { ...detailUnit.value, orgScopes: (updated as any).orgScopes ?? merged }
  }
}

async function onRemoveOrgNode(row: OrgScopeNode) {
  const next = detailOrgNodes.value.filter((n) => n.deptId !== row.deptId)
  try {
    await persistOrgNodes(next)
    message.success('已删除')
    orgCheckedKeys.value = orgCheckedKeys.value.filter((k) => k !== row.deptId)
  } catch (e: any) {
    message.error('删除失败: ' + (e?.response?.data?.message || e?.message || e))
  }
}

async function batchRemoveOrgNodes() {
  if (!orgCheckedKeys.value.length) { message.warning('请先勾选要删除的组织'); return }
  const next = detailOrgNodes.value.filter((n) => !orgCheckedKeys.value.includes(n.deptId))
  try {
    await persistOrgNodes(next)
    message.success(`已删除 ${orgCheckedKeys.value.length} 个组织节点`)
    orgCheckedKeys.value = []
  } catch (e: any) {
    message.error('批量删除失败: ' + (e?.response?.data?.message || e?.message || e))
  }
}

async function loadDetailMembers(u: ManagementUnit) {
  detailMemberLoading.value = true
  try {
    detailMembers.value = await listManagementUnitMembers(String(u.id))
  } catch (e: any) {
    message.error('加载成员失败: ' + (e?.response?.data?.message || e?.message || e))
  } finally {
    detailMemberLoading.value = false
  }
}


// 人员数据范围（按应用）
function openDetailPersonDataRange() {
  if (!detailUnit.value) return
  detailPersonDataRangeValue.value = currentAppPersonDataRange.value
  detailPersonDataRangeVisible.value = true
}
async function onDetailPersonDataRangeConfirm(range: any) {
  if (!detailUnit.value) return
  detailPersonDataRangeVisible.value = false
  const app = detailAppTab.value
  try {
    if (app === 'public') {
      const updated = await updateManagementUnit(String(detailUnit.value.id), { personDataRange: range ?? null })
      detailUnit.value = { ...detailUnit.value, personDataRange: (updated as any).personDataRange ?? range }
    } else {
      const merged = { ...(detailUnit.value.personDataRanges || {}), [app]: range ?? null }
      const updated = await updateManagementUnit(String(detailUnit.value.id), { personDataRanges: merged })
      detailUnit.value = { ...detailUnit.value, personDataRanges: (updated as any).personDataRanges ?? merged }
    }
    message.success('人员数据范围已保存')
  } catch (e: any) {
    message.error('保存人员数据范围失败: ' + (e?.response?.data?.message || e?.message || e))
  }
}

// 按应用配置「组织范围」
function openDetailOrgScope() {
  if (!detailUnit.value) return
  detailOrgScopeValue.value = detailOrgNodes.value
  detailOrgScopeVisible.value = true
}
async function onDetailOrgScopeConfirm(nodes: OrgScopeNode[]) {
  if (!detailUnit.value) return
  detailOrgScopeVisible.value = false
  try {
    await persistOrgNodes(nodes)
    message.success('组织范围已保存')
  } catch (e: any) {
    message.error('保存组织范围失败: ' + (e?.response?.data?.message || e?.message || e))
  }
}

async function onRemoveDetailMember(row: ManagementUnitMember) {
  if (!editingUnit.value || !detailUnit.value) return
  try {
    await removeManagementUnitMember(String(editingUnit.value.id), row.id)
    message.success('已移除')
    await loadDetailMembers(detailUnit.value)
  } catch (e: any) {
    message.error('移除失败: ' + (e?.response?.data?.message || e?.message || e))
  }
}

// ===== 查看授权用户 =====
const viewAuthVisible = ref(false)
const authMembers = ref<ManagementUnitMember[]>([])
const authLoading = ref(false)
const authColumns = [
  {
    title: '姓名', key: 'name', minWidth: 120,
    render: (row: ManagementUnitMember) => row.userName || row.personName || row.departmentName || row.id,
  },
  {
    title: '类型', key: 'memberType', width: 110,
    render: (row: ManagementUnitMember) =>
      ({ DEPT: '组织节点', USER: '系统用户', PERSON: 'HR人员' } as Record<string, string>)[row.memberType] || row.memberType,
  },
  {
    title: '组织', key: 'org', minWidth: 140,
    render: (row: ManagementUnitMember) => (row.departmentId ? deptNameById(row.departmentId) : '—'),
  },
]
async function openViewAuth() {
  if (!detailUnit.value) return
  authLoading.value = true
  viewAuthVisible.value = true
  try {
    authMembers.value = await listManagementUnitMembers(String(detailUnit.value.id))
  } catch (e: any) {
    message.error('加载授权用户失败: ' + (e?.response?.data?.message || e?.message || e))
  } finally {
    authLoading.value = false
  }
}

// ===== 成员管理（复用融合弹窗内的「人员范围」；添加/移除锚定 editingUnit） =====
const memberModalVisible = ref(false)
const memberSaving = ref(false)
/** 添加成员时携带的 appCode（null = 公共成员），跟随当前应用 Tab */
const memberAppCode = ref<string | null>(null)

const memberForm = reactive({
  memberType: 'DEPT' as 'DEPT' | 'USER' | 'PERSON',
  departmentId: null as string | null,
  userId: null as string | null,
  personId: null as string | null,
  includeChildren: 1 as number,
  remark: '' as string,
})

const memberTypeLabels: Record<string, string> = {
  DEPT: '组织节点', USER: '系统用户', PERSON: 'HR人员',
}
const memberFormTitle = computed(() => {
  const label = memberTypeLabels[memberForm.memberType] || '成员'
  return `添加${label}`
})

// 复用现有接口数据（不新造后端接口）
const deptStore = useDepartmentStore()
const deptTreeOptions = computed(() => buildDeptTree(deptStore.departments))
const userOptions = ref<{ label: string; value: string }[]>([])
const personOptions = ref<{ label: string; value: string }[]>([])

/** 把 flat 部门列表按 parentId 拼成 n-tree-select 需要的 {label,key,children} 树 */
function buildDeptTree(list: Department[]): any[] {
  const byId = new Map<string, any>()
  list.forEach((d) => byId.set(String(d.id), { label: d.name, key: String(d.id), children: [] as any[] }))
  const roots: any[] = []
  list.forEach((d) => {
    const node = byId.get(String(d.id))!
    const pid = d.parentId ? String(d.parentId) : null
    if (pid && byId.has(pid)) byId.get(pid)!.children.push(node)
    else roots.push(node)
  })
  return roots
}

async function openAddMember(type: 'DEPT' | 'USER' | 'PERSON') {
  if (!editingUnit.value) return
  Object.assign(memberForm, {
    memberType: type, departmentId: null, userId: null, personId: null,
    includeChildren: 1, remark: '',
  })
  try { if (!deptStore.departments.length) await deptStore.loadDepartments() } catch { /* 降级 */ }
  if (!userOptions.value.length) {
    try { userOptions.value = (await listUsers()).map((u) => ({ label: u.realName || u.username || String(u.id), value: String(u.id) })) } catch { /* 降级 */ }
  }
  if (!personOptions.value.length) {
    try { personOptions.value = (await listPersons()).map((p) => ({ label: p.name || p.code, value: String(p.id) })) } catch { /* 降级 */ }
  }
  memberModalVisible.value = true
}

/** 融合弹窗内按当前应用 Tab 添加成员（带 appCode） */
function openDetailAddMember(type: 'DEPT' | 'USER' | 'PERSON') {
  memberAppCode.value = detailAppTab.value === 'public' ? null : detailAppTab.value
  openAddMember(type)
}

async function onSaveMember() {
  if (!editingUnit.value) return
  let payload: any
  if (memberForm.memberType === 'DEPT') {
    if (!memberForm.departmentId) { message.warning('请选择组织节点'); return }
    payload = { memberType: 'DEPT', departmentId: memberForm.departmentId, includeChildren: memberForm.includeChildren, remark: memberForm.remark || null }
  } else if (memberForm.memberType === 'USER') {
    if (!memberForm.userId) { message.warning('请选择系统用户'); return }
    payload = { memberType: 'USER', userId: Number(memberForm.userId), includeChildren: memberForm.includeChildren, remark: memberForm.remark || null }
  } else {
    if (!memberForm.personId) { message.warning('请选择 HR 人员'); return }
    payload = { memberType: 'PERSON', personId: memberForm.personId, includeChildren: memberForm.includeChildren, remark: memberForm.remark || null }
  }
  if (memberAppCode.value) payload.appCode = memberAppCode.value
  memberSaving.value = true
  try {
    await addManagementUnitMember(String(editingUnit.value.id), payload)
    message.success('已添加成员')
    memberModalVisible.value = false
    memberAppCode.value = null
    if (detailUnit.value) await loadDetailMembers(detailUnit.value)
  } catch (e: any) {
    message.error('添加成员失败: ' + (e?.response?.data?.message || e?.message || e))
  } finally {
    memberSaving.value = false
  }
}

onMounted(() => {
  loadUnits()
  try { if (!deptStore.departments.length) deptStore.loadDepartments() } catch { /* 降级 */ }
})
</script>

<style scoped>
/* === settings page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款） === */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.scope-edit {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
/* 列表工具条：左=筛选，右=操作（对齐校招管控-规则配置页 .toolbar 范式） */
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.toolbar .spacer {
  flex: 1;
}
.scope-readout {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
/* 融合弹窗内：组织/人员数据范围读出行 */
.detail-range-readout {
  margin-top: var(--space-2);
  padding: 6px 10px;
  background: var(--color-bg-subtle);
  border-radius: 6px;
}
/* 北森式范围区块：开关 + 标题 + 右侧操作 + 可收起 */
.scope-block {
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
}
.scope-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}
.scope-block-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.scope-block-divider {
  color: var(--color-text-tertiary);
  opacity: 0.5;
}
.scope-block-total {
  margin-top: var(--space-1);
  font-size: 12px;
  color: var(--color-text-tertiary);
}
/* 详情元信息（融合弹窗已移除抽屉，保留只读提示样式备用） */
.detail-tabs {
  margin-top: var(--space-2);
}
.detail-app-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  background: var(--color-bg-subtle);
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: var(--space-2);
}
.detail-empty {
  margin-top: var(--space-2);
}
/* 编辑管理单元弹窗 — 标题区只读摘要 + 操作按钮 */
.unit-detail-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
}
.unit-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}
.unit-name {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--color-text-primary);
}
.unit-meta-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-4);
  font-size: 13px;
  color: var(--color-text-secondary);
}
.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.meta-item label {
  color: var(--color-text-tertiary);
}
.meta-value {
  color: var(--color-text-primary);
}
.modal-title {
  font-size: 16px;
  font-weight: 600;
}
</style>
