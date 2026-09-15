<template>
  <div class="page-container mou-management">
<div class="page-body">
    <div class="page-header">
      <div>
        <h1 class="page-title">管理单元 (Management Unit)</h1>
        <p class="page-subtitle">数据权限的组织范围载体 —— 树形层级 + 组织范围 + 人员范围，并可作为 DataPermissionRule 的配置面</p>
      </div>
      <div class="kpi-row">
        <div class="kpi-card"><span class="kpi-label">管理单元总数</span><span class="kpi-value">{{ allUnits.length }}</span></div>
      </div>
    </div>

    <n-tabs v-model:value="activeTab" type="line">
      <!-- 管理单元树 -->
      <n-tab-pane name="units" tab="管理单元">
        <n-card :bordered="false" class="glass-panel">
          <template #header-extra>
            <n-space>
              <n-button @click="openCreateRoot">
                <template #icon><n-icon :component="AddOutline" /></template>
                新建根单元
              </n-button>
              <n-button :disabled="!selectedKey" @click="openCreateChild">
                <template #icon><n-icon :component="AddOutline" /></template>
                在选中下新建子单元
              </n-button>
              <n-button :disabled="!selectedKey" @click="openEditSelected">
                <template #icon><n-icon :component="CreateOutline" /></template>
                编辑
              </n-button>
              <n-button :disabled="!selectedKey" type="info" :loading="syncing" @click="onSyncSelected">
                <template #icon><n-icon :component="SyncOutline" /></template>
                同步到数据规则
              </n-button>
              <n-popconfirm
                :disabled="!selectedKey"
                positive-text="确认"
                negative-text="取消"
                @positive-click="onDeleteSelected"
              >
                <template #trigger>
                  <n-button :disabled="!selectedKey" type="error">
                    <template #icon><n-icon :component="TrashOutline" /></template>
                    删除
                  </n-button>
                </template>
                确认删除该管理单元？其直接子单元将自动提升为根节点。
              </n-popconfirm>
            </n-space>
          </template>

          <n-grid :cols="2" :x-gap="16" responsive="screen" item-responsive>
            <n-grid-item>
              <n-empty v-if="!treeData.length" description="暂无管理单元，点击「新建根单元」" />
              <n-tree
                v-else
                :data="treeData"
                :selected-keys="selectedKey ? [selectedKey] : []"
                block-line
                expand-on-click
                :default-expand-all="true"
                @update:selected-keys="onTreeSelect"
              />
            </n-grid-item>
            <n-grid-item>
              <n-empty v-if="!selectedNode" description="请选择左侧管理单元查看详情" />
              <n-descriptions v-else title="单元详情" label-placement="top" bordered :column="1">
                <n-descriptions-item label="名称">{{ selectedNode.unitName }}</n-descriptions-item>
                <n-descriptions-item label="类型">{{ unitTypeLabel(selectedNode.unitType) }}</n-descriptions-item>
                <n-descriptions-item label="上级">
                  {{ selectedNode.parentId ? (unitNameById(String(selectedNode.parentId)) || selectedNode.parentId) : '（根节点）' }}
                </n-descriptions-item>
                <n-descriptions-item label="包含子级">
                  <n-tag :type="selectedNode.includeChildren === 1 ? 'success' : 'default'" size="small">
                    {{ selectedNode.includeChildren === 1 ? '包含下级' : '仅本级' }}
                  </n-tag>
                </n-descriptions-item>
                <n-descriptions-item label="状态">
                  <n-tag :type="selectedNode.status === 1 ? 'success' : 'default'" size="small">
                    {{ selectedNode.status === 1 ? '启用' : '禁用' }}
                  </n-tag>
                </n-descriptions-item>
                <n-descriptions-item label="组织范围 (orgScope)">
                  <pre class="json-box">{{ pretty(selectedNode.orgScope) }}</pre>
                </n-descriptions-item>
                <n-descriptions-item label="人员范围 (personnelScope)">
                  <pre class="json-box">{{ pretty(selectedNode.personnelScope) || '（未配置）' }}</pre>
                </n-descriptions-item>
              </n-descriptions>
            </n-grid-item>
          </n-grid>
        </n-card>
      </n-tab-pane>

      <!-- 按应用数据范围 -->
      <n-tab-pane name="per-app" tab="按应用数据范围">
        <n-card :bordered="false" class="glass-panel" title="按应用数据范围 (UserAppDataScope)">
          <template #header-extra>
            <n-space>
              <n-select
                v-model:value="scopeAppFilter"
                placeholder="按应用筛选"
                clearable
                style="width: 160px"
                :options="appCodeOptions"
              />
              <n-button type="primary" @click="openScopeCreate">
                <template #icon><n-icon :component="AddOutline" /></template>
                新建范围
              </n-button>
            </n-space>
          </template>
          <n-data-table
            :data="scopes"
            :columns="scopeColumns"
            :row-key="(row: UserAppDataScope) => row.id"
            :loading="scopeLoading"
            :pagination="{ pageSize: 10 }"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- 管理单元 新建/编辑 弹窗 -->
    <n-modal
      v-model:show="unitModalVisible"
      preset="card"
      :title="editingUnit ? '编辑管理单元' : '新建管理单元'"
      :style="{ width: '600px' }"
      :mask-closable="false"
    >
      <n-form :model="unitForm" label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="单元名称" required>
              <n-input v-model:value="unitForm.unitName" placeholder="如：华东大区" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="单元类型">
              <n-select v-model:value="unitForm.unitType" :options="unitTypeOptions" />
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
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="状态">
              <n-select v-model:value="unitForm.status" :options="statusOptions" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="包含子级">
              <n-radio-group v-model:value="unitForm.includeChildren">
                <n-space>
                  <n-radio :value="1">包含下级</n-radio>
                  <n-radio :value="0">仅本级</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-form-item label="组织范围 orgScope (JSON)">
          <n-input
            v-model:value="unitForm.orgScopeText"
            type="textarea"
            :rows="3"
            placeholder="如：{&quot;name&quot;:&quot;华东大区&quot;,&quot;level&quot;:&quot;REGION&quot;}"
          />
        </n-form-item>
        <n-form-item label="人员范围 personnelScope (JSON)">
          <n-input
            v-model:value="unitForm.personnelScopeText"
            type="textarea"
            :rows="3"
            placeholder="如：{&quot;op&quot;:&quot;or&quot;,&quot;rules&quot;:[{&quot;dimension&quot;:&quot;employment&quot;,&quot;field&quot;:&quot;department&quot;,&quot;op&quot;:&quot;eq&quot;,&quot;value&quot;:&quot;dept-1&quot;,&quot;includeSub&quot;:true}]}"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="unitModalVisible = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="unitSaving" @click="onSaveUnit">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 按应用范围 新建/编辑 弹窗 -->
    <n-modal
      v-model:show="scopeModalVisible"
      preset="card"
      :title="editingScope ? '编辑应用范围' : '新建应用范围'"
      :style="{ width: '560px' }"
      :mask-closable="false"
    >
      <n-form :model="scopeForm" label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="用户ID" required>
              <n-input-number v-model:value="scopeForm.userId" placeholder="用户 ID" style="width: 100%" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="角色编码" required>
              <n-input v-model:value="scopeForm.roleCode" placeholder="如：RECRUITER" />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="应用/模块" required>
              <n-select v-model:value="scopeForm.appCode" :options="appCodeOptions" placeholder="选择应用" />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="管理单元">
              <n-select
                v-model:value="scopeForm.managementUnitIds"
                :options="unitOptions"
                multiple
                clearable
                filterable
                placeholder="不选 = 回退全局范围"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: var(--space-2);">
          <n-button @click="scopeModalVisible = false">取消</n-button>
          <n-button type="primary" class="gradient-btn" :loading="scopeSaving" @click="onSaveScope">保存</n-button>
        </div>
      </template>
    </n-modal>
</div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, onMounted, watch } from 'vue'
import {
  NButton, NSpace, NTag, NIcon, NEmpty, NDescriptions, NDescriptionsItem,
  NPopconfirm, useMessage,
} from 'naive-ui'
import {
  AddOutline, CreateOutline, TrashOutline, SyncOutline,
} from '@vicons/ionicons5'
import {
  listManagementUnits, treeManagementUnits, createManagementUnit, updateManagementUnit,
  deleteManagementUnit, syncManagementUnitRules, type ManagementUnit, type ManagementUnitTreeNode,
} from '@/api/management-unit'
import {
  listUserAppDataScopes, upsertUserAppDataScope, deleteUserAppDataScopeById,
  type UserAppDataScope,
} from '@/api/user-app-data-scope'

const message = useMessage()
const activeTab = ref('units')

// ===== 管理单元树 =====
const allUnits = ref<ManagementUnit[]>([])
const treeNodes = ref<ManagementUnitTreeNode[]>([])
const selectedKey = ref<string | number | null>(null)
const selectedNode = ref<ManagementUnit | null>(null)
const syncing = ref(false)

const unitTypeOptions = [
  { label: '组织', value: 'org' },
  { label: '部门', value: 'dept' },
  { label: '项目', value: 'project' },
  { label: '自定义', value: 'custom' },
]
const statusOptions = [
  { label: '启用', value: 1 },
  { label: '禁用', value: 0 },
]
const unitTypeLabel = (t: string) =>
  (unitTypeOptions.find((o) => o.value === t)?.label) || t

// n-tree 数据（带 children 嵌套）
const treeData = computed(() =>
  treeNodes.value.map((n) => mapTreeNode(n)),
)
function mapTreeNode(n: ManagementUnitTreeNode) {
  return {
    key: n.id as any,
    label: `${n.unitName}${n.status === 0 ? '（禁用）' : ''}`,
    children: (n.children || []).map(mapTreeNode),
  }
}
function unitNameById(id: string): string | undefined {
  return allUnits.value.find((u) => String(u.id) === id)?.unitName
}

// n-tree-select 选项（构建层级，排除正在编辑的节点及其后代以防水环）
const parentOptions = computed(() => {
  const blockId = editingUnit.value?.id
  const flat: ManagementUnit[] = []
  const walk = (nodes: ManagementUnitTreeNode[]) => {
    for (const n of nodes) {
      if (blockId && String(n.id) === String(blockId)) continue
      flat.push({
        id: String(n.id), unitName: n.unitName, unitType: n.unitType,
        parentId: n.parentId, orgScope: n.orgScope, personnelScope: n.personnelScope,
        includeChildren: 1, status: n.status,
      })
      if (n.children?.length) walk(n.children)
    }
  }
  walk(treeNodes.value)
  // 再排除 blockId 的后代：由于已跳过 blockId 本身，其 children 仍会出现，需二次过滤
  const blocked = new Set<string>()
  if (blockId) {
    const collect = (nodes: ManagementUnitTreeNode[]) => {
      for (const n of nodes) {
        if (String(n.id) === String(blockId)) {
          n.children?.forEach((c) => blocked.add(String(c.id)))
        } else {
          n.children?.forEach(collect)
        }
      }
    }
    collect(treeNodes.value)
  }
  const allowed = flat.filter((u) => !blocked.has(String(u.id)))
  // 构建树形 options
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
  unitType: 'org',
  parentId: null as string | number | null,
  status: 1 as number,
  includeChildren: 1 as number,
  orgScopeText: '{}',
  personnelScopeText: '',
})

const pretty = (v: any) => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  try { return JSON.stringify(v, null, 2) } catch { return String(v) }
}

function onTreeSelect(keys: Array<string | number>) {
  const k = keys[0]
  selectedKey.value = k ?? null
  selectedNode.value = k ? (allUnits.value.find((u) => String(u.id) === String(k)) || null) : null
  // 同步详情节点（带 children 的扁平版）也需要更新
  if (k) {
    const node = findNode(treeNodes.value, String(k))
    if (node) {
      selectedNode.value = {
        id: String(node.id), unitName: node.unitName, unitType: node.unitType,
        parentId: node.parentId, orgScope: node.orgScope, personnelScope: node.personnelScope,
        includeChildren: 1, status: node.status,
      }
    }
  }
}
function findNode(nodes: ManagementUnitTreeNode[], id: string): ManagementUnitTreeNode | null {
  for (const n of nodes) {
    if (String(n.id) === id) return n
    if (n.children) {
      const f = findNode(n.children, id)
      if (f) return f
    }
  }
  return null
}

function openCreateRoot() {
  editingUnit.value = null
  Object.assign(unitForm, {
    id: '', unitName: '', unitType: 'org', parentId: null,
    status: 1, includeChildren: 1, orgScopeText: '{}', personnelScopeText: '',
  })
  unitModalVisible.value = true
}
function openCreateChild() {
  if (!selectedNode.value) return
  editingUnit.value = null
  Object.assign(unitForm, {
    id: '', unitName: '', unitType: 'org', parentId: String(selectedNode.value.id),
    status: 1, includeChildren: 1, orgScopeText: '{}', personnelScopeText: '',
  })
  unitModalVisible.value = true
}
function openEditSelected() {
  const n = selectedNode.value
  if (!n) return
  editingUnit.value = n
  Object.assign(unitForm, {
    id: String(n.id), unitName: n.unitName, unitType: n.unitType,
    parentId: n.parentId ? String(n.parentId) : null, status: n.status,
    includeChildren: n.includeChildren ?? 1,
    orgScopeText: pretty(n.orgScope) || '{}',
    personnelScopeText: pretty(n.personnelScope) || '',
  })
  unitModalVisible.value = true
}

async function onSaveUnit() {
  if (!unitForm.unitName.trim()) {
    message.warning('单元名称必填')
    return
  }
  let orgScope: any = null
  let personnelScope: any = null
  try {
    if (unitForm.orgScopeText.trim()) orgScope = JSON.parse(unitForm.orgScopeText)
  } catch {
    message.error('组织范围不是合法 JSON')
    return
  }
  try {
    if (unitForm.personnelScopeText.trim()) personnelScope = JSON.parse(unitForm.personnelScopeText)
  } catch {
    message.error('人员范围不是合法 JSON')
    return
  }
  unitSaving.value = true
  try {
    const payload = {
      unitName: unitForm.unitName.trim(),
      unitType: unitForm.unitType,
      parentId: unitForm.parentId ? Number(unitForm.parentId) : null,
      status: unitForm.status,
      includeChildren: unitForm.includeChildren,
      orgScope,
      personnelScope,
    }
    if (editingUnit.value) {
      await updateManagementUnit(unitForm.id, payload)
      message.success('已更新')
    } else {
      await createManagementUnit(payload)
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

async function onSyncSelected() {
  if (!selectedNode.value) return
  syncing.value = true
  try {
    const res = await syncManagementUnitRules(String(selectedNode.value.id))
    message.success(`已同步到 DataPermissionRule（${res.effectiveUnitIds.length} 个单元）`, { duration: 5000 })
  } catch (e: any) {
    message.error('同步失败: ' + (e?.response?.data?.message || e?.message || e))
  } finally {
    syncing.value = false
  }
}

async function onDeleteSelected() {
  if (!selectedNode.value) return
  try {
    const res = await deleteManagementUnit(String(selectedNode.value.id))
    if (res?.success) {
      message.success('已删除')
      selectedKey.value = null
      selectedNode.value = null
      await loadUnits()
    } else {
      message.error(res?.message || '删除失败')
    }
  } catch (e: any) {
    message.error('删除失败: ' + (e?.response?.data?.message || e?.message || e))
  }
}

async function loadUnits() {
  try {
    const [flat, tree] = await Promise.all([
      listManagementUnits(),
      treeManagementUnits(),
    ])
    allUnits.value = flat
    treeNodes.value = tree
  } catch (e: any) {
    message.error('加载管理单元失败: ' + (e?.message || e))
  }
}

// ===== 按应用数据范围 =====
const scopes = ref<UserAppDataScope[]>([])
const scopeLoading = ref(false)
const scopeAppFilter = ref<string | null>(null)
const appCodeOptions = [
  { label: '招聘 recruit', value: 'recruit' },
  { label: '校招 campus', value: 'campus' },
  { label: '社招 social', value: 'social' },
  { label: '内推 referral', value: 'referral' },
]
const unitOptions = computed(() =>
  allUnits.value.map((u) => ({ label: u.unitName, value: Number(u.id) })),
)

const scopeColumns = [
  { title: '用户ID', key: 'userId', width: 90 },
  { title: '角色编码', key: 'roleCode', width: 140 },
  { title: '应用', key: 'appCode', width: 110,
    render: (row: UserAppDataScope) => h(NTag, { size: 'small' }, { default: () => row.appCode }) },
  { title: '管理单元', key: 'managementUnitIds',
    render: (row: UserAppDataScope) => (row.managementUnitIds || []).map((id: number) => unitNameById(String(id)) || id).join('、') || '—' },
  {
    title: '操作', key: 'action', width: 160,
    render: (row: UserAppDataScope) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => openScopeEdit(row) }, { default: () => '编辑' }),
        h(NPopconfirm, {
          onPositiveClick: () => onDeleteScope(row),
          positiveText: '确认', negativeText: '取消',
        }, {
          default: () => '确认删除该范围配置？',
          trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, { default: () => '删除' }),
        }),
      ],
    }),
  },
]

const scopeModalVisible = ref(false)
const editingScope = ref<UserAppDataScope | null>(null)
const scopeSaving = ref(false)
const scopeForm = reactive({
  userId: null as number | null,
  roleCode: '',
  appCode: 'recruit',
  managementUnitIds: [] as number[],
})

async function loadScopes() {
  scopeLoading.value = true
  try {
    const params: any = {}
    if (scopeAppFilter.value) params.appCode = scopeAppFilter.value
    scopes.value = await listUserAppDataScopes(params)
  } catch (e: any) {
    message.error('加载应用范围失败: ' + (e?.message || e))
  } finally {
    scopeLoading.value = false
  }
}

function openScopeCreate() {
  editingScope.value = null
  Object.assign(scopeForm, { userId: null, roleCode: '', appCode: 'recruit', managementUnitIds: [] })
  scopeModalVisible.value = true
}
function openScopeEdit(row: UserAppDataScope) {
  editingScope.value = row
  Object.assign(scopeForm, {
    userId: Number(row.userId), roleCode: row.roleCode, appCode: row.appCode,
    managementUnitIds: (row.managementUnitIds || []).map(Number),
  })
  scopeModalVisible.value = true
}

async function onSaveScope() {
  if (!scopeForm.userId || !scopeForm.roleCode.trim() || !scopeForm.appCode) {
    message.warning('用户ID + 角色编码 + 应用 必填')
    return
  }
  scopeSaving.value = true
  try {
    await upsertUserAppDataScope({
      userId: scopeForm.userId,
      roleCode: scopeForm.roleCode.trim(),
      appCode: scopeForm.appCode,
      systemCode: 'recruit',
      managementUnitIds: scopeForm.managementUnitIds,
    })
    message.success(editingScope.value ? '已更新' : '已创建')
    scopeModalVisible.value = false
    await loadScopes()
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message || e?.message || e))
  } finally {
    scopeSaving.value = false
  }
}

async function onDeleteScope(row: UserAppDataScope) {
  try {
    await deleteUserAppDataScopeById(row.id)
    message.success('已删除')
    await loadScopes()
  } catch (e: any) {
    message.error('删除失败: ' + (e?.response?.data?.message || e?.message || e))
  }
}

watch(activeTab, (t) => { if (t === 'per-app') loadScopes() })
watch(scopeAppFilter, () => { if (activeTab.value === 'per-app') loadScopes() })

onMounted(() => {
  loadUnits()
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
.json-box {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  background: var(--g2, #f5f5f5);
  padding: 8px;
  border-radius: 6px;
  max-height: 160px;
  overflow: auto;
}
</style>
