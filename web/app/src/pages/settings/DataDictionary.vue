<template>
  <div class="page-container">
    <!-- ===================== 列表模式 ===================== -->
    <template v-if="mode === 'list'">
      <div class="page-header">
        <div>
          <h1 class="page-title">数据字典</h1>
          <p class="page-subtitle">管理系统枚举与配置项（树形结构 · 草稿暂存 · 系统/自定义差异化）</p>
        </div>
        <n-button type="primary" @click="openCreateType">新增字典</n-button>
      </div>

      <n-card :bordered="false" class="toolbar">
        <n-space align="center" :wrap="false">
          <n-input
            v-model:value="searchText"
            placeholder="搜索字典名称 / 代码 / 元素名称 / 元素代码"
            clearable
            style="width: 360px"
            @update:value="onSearchInput"
          >
            <template #prefix>
              <span>🔍</span>
            </template>
          </n-input>
          <n-select
            v-model:value="typeFilter"
            :options="typeOptions"
            style="width: 160px"
            @update:value="loadList"
          />
        </n-space>
      </n-card>

      <n-data-table
        :columns="listColumns"
        :data="types"
        :loading="listLoading"
        :row-key="(r: any) => r.code"
        :pagination="false"
      >
        <template #empty>
          <n-empty description="暂无字典" />
        </template>
      </n-data-table>
    </template>

    <!-- ===================== 编辑模式 ===================== -->
    <template v-else-if="currentType">
      <div class="page-header edit-header">
        <n-button text size="small" class="back-btn" @click="backToList">
          <span style="font-size: 16px">←</span> 返回
        </n-button>
        <div class="title-block">
          <h1 class="page-title">编辑字典：{{ headDraft.name || currentType.name }}</h1>
          <p class="page-subtitle">
            <n-tag size="small" :type="currentType.isSystem ? 'warning' : 'success'">
              {{ currentType.isSystem ? '系统预置' : '自定义' }}
            </n-tag>
            <span class="code-pill">{{ currentType.code }}</span>
            <span class="num-pill">编号 {{ currentType.dictNumber }}</span>
          </p>
        </div>
      </div>

      <!-- 顶部提示条 -->
      <n-alert type="warning" :show-icon="false" class="section">
        <ul class="dict-hints">
          <li>支持元素分级（推荐不超过 {{ MAX_TREE_LEVEL }} 级）。</li>
          <li>元素描述支持 hover 提示。</li>
          <li>编辑时仅支持删除新添加的元素，原有元素不支持删除。</li>
          <li>停用及删除仅支持操作没有下级的元素。</li>
          <li>配置项修改后，需提交后才会生效。</li>
        </ul>
      </n-alert>

      <n-card title="字典信息" :bordered="false" class="section">
        <n-form label-placement="top" :model="headDraft">
          <n-grid :cols="4" :x-gap="24" :y-gap="4">
            <n-gi>
              <n-form-item label="字典名称" path="name">
                <n-input v-model:value="headDraft.name" placeholder="请输入" />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item label="字典代码" path="code">
                <n-input :value="currentType.code" disabled placeholder="创建后锁定" />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item label="英文名称" path="englishName">
                <n-input v-model:value="headDraft.englishName" placeholder="如 MAJOR_SUBJECT（可选）" />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item label="是否启用" path="isEnabled">
                <n-switch v-model:value="headDraft.isEnabled" :disabled="currentType.isSystem" />
                <span v-if="currentType.isSystem" class="hint">系统预置字典不可停用</span>
              </n-form-item>
            </n-gi>
            <n-gi :span="4">
              <n-form-item label="字典描述" path="description">
                <n-input
                  v-model:value="headDraft.description"
                  type="textarea"
                  placeholder="请输入"
                  :autosize="{ minRows: 2, maxRows: 4 }"
                />
              </n-form-item>
            </n-gi>
          </n-grid>
        </n-form>
      </n-card>

      <n-card title="字典元素" :bordered="false" class="section">
        <template #header-extra>
          <n-button size="small" @click="addRootItem">+ 新增元素</n-button>
        </template>

        <div style="overflow-x: auto;">
          <div class="el-table">
          <div class="el-row el-head">
            <div class="el-cell" style="flex: 1.4">元素名称</div>
            <div class="el-cell" style="flex: 1.2">元素代码</div>
            <div class="el-cell" style="flex: 1.2">英文名称</div>
            <div class="el-cell" style="flex: 0.6">排序</div>
            <div class="el-cell" style="flex: 1.6">描述</div>
            <div class="el-cell" style="flex: 2.2">操作</div>
          </div>

          <div
            v-for="node in flatTree"
            :key="node.row.clientId"
            class="el-row"
            :class="{ editing: node.row.editing, isnew: node.row.isNew }"
          >
            <!-- 元素名称：仅本列按树形层级缩进 -->
            <div class="el-cell el-name-cell" style="flex: 1.4" :style="{ paddingLeft: 8 + node.depth * 24 + 'px' }">
              <div class="el-cell-content">
                <span v-if="node.depth > 0" class="tree-guide">└</span>
                <template v-if="node.row.editing">
                  <n-input v-model:value="node.row.value" size="small" placeholder="名称" />
                </template>
                <template v-else>
                  <span :class="{ strikethrough: !node.row.isActive }">{{ node.row.value }}</span>
                </template>
              </div>
            </div>
            <!-- 元素代码 -->
            <div class="el-cell" style="flex: 1.2">
              <div class="el-cell-content">
                <template v-if="node.row.editing">
                  <n-input v-model:value="node.row.key" size="small" placeholder="代码" />
                </template>
                <template v-else>
                  <span class="code-text">{{ node.row.key }}</span>
                </template>
              </div>
            </div>
            <!-- 英文名称 -->
            <div class="el-cell" style="flex: 1.2">
              <div class="el-cell-content">
                <template v-if="node.row.editing">
                  <n-input v-model:value="node.row.englishName" size="small" placeholder="英文" />
                </template>
                <template v-else>{{ node.row.englishName }}</template>
              </div>
            </div>
            <!-- 排序 -->
            <div class="el-cell" style="flex: 0.6">
              <div class="el-cell-content">
                <template v-if="node.row.editing">
                  <n-input-number v-model:value="node.row.sortOrder" size="small" :min="0" style="width: 80px" />
                </template>
                <template v-else>{{ node.row.sortOrder }}</template>
              </div>
            </div>
            <!-- 描述 -->
            <div class="el-cell desc-cell" style="flex: 1.6">
              <div class="el-cell-content">
                <template v-if="node.row.editing">
                  <n-input v-model:value="node.row.description" size="small" placeholder="描述" />
                </template>
                <template v-else>
                  <n-ellipsis :line-clamp="1" :tooltip="!!node.row.description">{{ node.row.description }}</n-ellipsis>
                </template>
              </div>
            </div>
            <!-- 操作 -->
            <div class="el-cell" style="flex: 2.2">
              <n-space :size="4" align="center">
                <template v-if="node.row.editing">
                  <n-button size="tiny" type="primary" @click="saveRow(node.row)">保存</n-button>
                  <n-button size="tiny" @click="cancelRow(node.row)">取消</n-button>
                </template>
                <template v-else>
                  <n-button size="tiny" @click="startEdit(node.row)">编辑</n-button>
                  <n-button size="tiny" @click="addSibling(node.row)">加同级</n-button>
                  <n-button
                    size="tiny"
                    :disabled="node.depth >= MAX_TREE_LEVEL - 1"
                    :title="node.depth >= MAX_TREE_LEVEL - 1 ? `已达推荐最大层级（${MAX_TREE_LEVEL} 级），不可再加下级` : ''"
                    @click="addChild(node.row)"
                  >加下级</n-button>
                  <n-button
                    v-if="!node.row.isNew"
                    size="tiny"
                    :type="node.row.isActive ? 'warning' : 'success'"
                    :disabled="hasChildren(node.row)"
                    :title="hasChildren(node.row) ? '请先移除或转移所有子级元素' : ''"
                    @click="toggleActive(node.row)"
                  >
                    {{ node.row.isActive ? '停用' : '启用' }}
                  </n-button>
                  <n-button
                    v-if="node.row.isNew"
                    size="tiny"
                    type="error"
                    @click="deleteRow(node.row)"
                  >
                    删除
                  </n-button>
                </template>
              </n-space>
            </div>
          </div>

          <div v-if="flatTree.length === 0" class="el-empty">暂无元素，点击右上角“新增元素”</div>
          </div>
        </div>
      </n-card>

      <!-- 底部固定提交栏 -->
      <div class="submit-bar">
        <div class="draft-hint" :class="{ 'hint-hidden': !hasUnsavedChanges }">
          <span class="draft-icon">⚠️</span>
          <span>有未保存的草稿，离开将丢失。</span>
        </div>
        <n-space class="submit-actions" justify="end" :size="12" align="center">
          <n-button size="large" :disabled="submitting" @click="backToList">取消</n-button>
          <n-button size="large" type="primary" :loading="submitting" :disabled="!hasUnsavedChanges" @click="submitDraft">
            提交
          </n-button>
        </n-space>
      </div>
    </template>

    <!-- 新增字典弹窗 -->
    <n-modal
      v-model:show="showCreateModal"
      title="新增字典"
      preset="card"
      style="width: 480px"
      :mask-closable="false"
    >
      <n-form ref="createFormRef" :model="createForm" :rules="createRules" label-placement="top">
        <n-form-item label="字典代码" path="code">
          <n-input v-model:value="createForm.code" placeholder="如 major_subject（字母/数字/下划线）" />
        </n-form-item>
        <n-form-item label="字典名称" path="name">
          <n-input v-model:value="createForm.name" placeholder="如 专业学科" />
        </n-form-item>
        <n-form-item label="英文名称" path="englishName">
          <n-input v-model:value="createForm.englishName" placeholder="如 MAJOR_SUBJECT（可选）" />
        </n-form-item>
        <n-form-item label="说明" path="description">
          <n-input v-model:value="createForm.description" type="textarea" placeholder="可选" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="creating" @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" :loading="creating" @click="submitCreate">创建</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted, h } from 'vue'
import {
  useMessage,
  useDialog,
  NButton,
  NCard,
  NDataTable,
  NTag,
  NEmpty,
  NInput,
  NInputNumber,
  NSwitch,
  NSelect,
  NSpace,
  NModal,
  NForm,
  NFormItem,
  NGrid,
  NGi,
  NAlert,
  type FormRules,
  type DataTableColumns,
} from 'naive-ui'
import {
  listDictionaryTypes,
  getDictionaryDetail,
  submitDictionaryDraft,
  createDictionaryType,
  updateDictionaryType,
  deleteDictionaryType,
  type DictionaryType,
  type DictionaryDetail,
  type DictionaryItem,
} from '../../api/dictionary'
import { extractApiError } from '../../api/dynamic-field'

const message = useMessage()
const dialog = useDialog()

// ===================== 状态 =====================
type Mode = 'list' | 'edit'
const mode = ref<Mode>('list')

/** 树形层级软上限：PRD 建议不超过 5 级。超出则该节点禁止再加下级。 */
const MAX_TREE_LEVEL = 5

const types = ref<DictionaryType[]>([])
const listLoading = ref(false)
const searchText = ref('')
const typeFilter = ref<'all' | 'system' | 'custom'>('all')
const typeOptions = [
  { label: '全部', value: 'all' },
  { label: '系统预置', value: 'system' },
  { label: '自定义', value: 'custom' },
]

const currentType = ref<DictionaryType | null>(null)
const headDraft = reactive({ name: '', englishName: '', isEnabled: true, description: '' })
let skipHeadDirty = false
const itemsDraft = ref<ElementRow[]>([])
const hasUnsavedChanges = ref(false)
const submitting = ref(false)

// 监听字典头信息变化，自动标记草稿未保存（初始化时跳过）
watch(
  headDraft,
  () => {
    if (!skipHeadDirty) markDirty()
  },
  { deep: true },
)

let searchTimer: any = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(loadList, 300)
}

// ===================== 元素行模型 =====================
interface ElementRow {
  clientId: string
  id: string | null
  parentId: string | null // 父级为已存在元素时的 db id
  parentClientId: string | null // 父级为新增元素时的 clientId
  key: string
  value: string
  englishName: string
  description: string
  sortOrder: number
  isActive: boolean
  isNew: boolean
  editing: boolean
  _backup?: Partial<ElementRow>
}

let clientSeq = 0
function genClientId(): string {
  clientSeq += 1
  return 'c_' + clientSeq
}

/** 解析某行的父级 key（用于建树 / 判断子级）。 */
function parentKeyOf(row: ElementRow): string | null {
  if (row.parentId) return row.parentId
  if (row.parentClientId) return row.parentClientId
  return null
}

/** 某行是否拥有子级（最终草稿态）。 */
function hasChildren(row: ElementRow): boolean {
  return itemsDraft.value.some(
    (c) => (c.parentId && c.parentId === row.id) || (c.parentClientId && c.parentClientId === row.clientId),
  )
}

/** 将草稿构建为带深度的扁平树（DFS）。 */
const flatTree = computed(() => {
  const list = itemsDraft.value
  const childrenMap = new Map<string | null, ElementRow[]>()
  for (const row of list) {
    const pk = parentKeyOf(row)
    if (!childrenMap.has(pk)) childrenMap.set(pk, [])
    childrenMap.get(pk)!.push(row)
  }
  const out: { row: ElementRow; depth: number }[] = []
  const visit = (parentKey: string | null, depth: number) => {
    const children = (childrenMap.get(parentKey) || []).slice().sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0))
    for (const c of children) {
      out.push({ row: c, depth })
      visit(c.id ?? c.clientId, depth + 1)
    }
  }
  visit(null, 0)
  return out
})

// ===================== 列表 =====================
function formatDateTime(iso: string | undefined): string {
  if (!iso) return ''
  const d = new Date(iso.replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${pad(d.getFullYear() % 100)}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function loadList() {
  listLoading.value = true
  try {
    types.value = await listDictionaryTypes({
      q: searchText.value || undefined,
      type: typeFilter.value,
    })
  } catch (e: any) {
    message.error('加载失败')
  } finally {
    listLoading.value = false
  }
}

const listColumns: DataTableColumns<DictionaryType> = [
  { title: '字典编号', key: 'dictNumber', width: 100 },
  { title: '字典名称', key: 'name', minWidth: 120 },
  { title: '字典代码', key: 'code', width: 180 },
  { title: '英文名称', key: 'englishName', minWidth: 120 },
  { title: '字典描述', key: 'description', minWidth: 160, ellipsis: { tooltip: true } },
  {
    title: '类型',
    key: 'isSystem',
    width: 110,
    render: (row: DictionaryType) =>
      h(NTag, { size: 'small', type: row.isSystem ? 'warning' : 'success' }, { default: () => (row.isSystem ? '系统预置' : '自定义') }),
  },
  {
    title: '启用状态',
    key: 'isEnabled',
    width: 100,
    render: (row: DictionaryType) =>
      h(
        NTag,
        { size: 'small', type: row.isEnabled ? 'success' : 'error' },
        { default: () => (row.isEnabled ? '启用' : '停用') },
      ),
  },
  {
    title: '创建人 / 时间',
    key: 'created',
    width: 170,
    render: (row: DictionaryType) =>
      h('div', { style: { lineHeight: '1.5' } }, [
        h('div', {}, row.createdByName || '-'),
        h('div', { style: { color: '#888', fontSize: '12px' } }, formatDateTime(row.createdAt)),
      ]),
  },
  {
    title: '修改人 / 时间',
    key: 'updated',
    width: 170,
    render: (row: DictionaryType) =>
      h('div', { style: { lineHeight: '1.5' } }, [
        h('div', {}, row.updatedByName || '-'),
        h('div', { style: { color: '#888', fontSize: '12px' } }, formatDateTime(row.updatedAt)),
      ]),
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right',
    render: (row: DictionaryType) =>
      h(
        NSpace,
        { size: 4, align: 'center', wrap: false },
        {
          default: () => {
            const btns = [
              h(NButton, { size: 'small', onClick: () => enterEdit(row) }, { default: () => '编辑' }),
            ]
            if (!row.isSystem) {
              btns.push(
                h(
                  NButton,
                  {
                    size: 'small',
                    type: row.isEnabled ? 'warning' : 'success',
                    onClick: () => toggleType(row),
                  },
                  { default: () => (row.isEnabled ? '停用' : '启用') },
                ),
              )
              btns.push(
                h(
                  NButton,
                  { size: 'small', type: 'error', onClick: () => confirmDeleteType(row) },
                  { default: () => '删除' },
                ),
              )
            }
            return btns
          },
        },
      ),
  },
]

async function toggleType(row: DictionaryType) {
  try {
    await updateDictionaryType(row.code, { isEnabled: !row.isEnabled })
    message.success('操作成功')
    await loadList()
  } catch (e: any) {
    message.error(extractApiError(e, '操作失败'))
  }
}

function confirmDeleteType(row: DictionaryType) {
  dialog.warning({
    title: '删除字典',
    content: `确认删除「${row.name}」(${row.code})？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteDictionaryType(row.code)
        message.success('删除成功')
        await loadList()
      } catch (e: any) {
        message.error(extractApiError(e, '删除失败'))
      }
    },
  })
}

// ===================== 编辑 =====================
async function enterEdit(type: DictionaryType) {
  currentType.value = type
  const detail: DictionaryDetail = await getDictionaryDetail(type.code)
  skipHeadDirty = true
  headDraft.name = detail.name
  headDraft.englishName = detail.englishName
  headDraft.isEnabled = detail.isEnabled
  headDraft.description = detail.description
  skipHeadDirty = false
  itemsDraft.value = (detail.items || []).map((it: DictionaryItem) => ({
    clientId: 'e_' + it.id,
    id: it.id,
    parentId: it.parentId,
    parentClientId: null,
    key: it.key,
    value: it.value,
    englishName: it.englishName,
    description: it.description,
    sortOrder: it.sortOrder,
    isActive: it.isActive,
    isNew: false,
    editing: false,
  }))
  hasUnsavedChanges.value = false
  mode.value = 'edit'
}

function backToList() {
  if (hasUnsavedChanges.value) {
    dialog.warning({
      title: '离开编辑页',
      content: '当前有未保存的草稿，离开将丢失。确认离开？',
      positiveText: '离开',
      negativeText: '取消',
      onPositiveClick: () => {
        mode.value = 'list'
        currentType.value = null
        loadList()
      },
    })
    return
  }
  mode.value = 'list'
  currentType.value = null
  loadList()
}

// --- 行操作 ---
function addRootItem() {
  const row = blankRow()
  itemsDraft.value.push(row)
  markDirty()
}

function addSibling(refRow: ElementRow) {
  const row = blankRow()
  row.parentId = refRow.parentId
  row.parentClientId = refRow.parentClientId
  itemsDraft.value.push(row)
  markDirty()
}

function addChild(refRow: ElementRow) {
  const row = blankRow()
  // 父级为已存在元素 → 用其 id; 父级为新增元素 → 用其 clientId
  if (refRow.id) row.parentId = refRow.id
  else row.parentClientId = refRow.clientId
  itemsDraft.value.push(row)
  markDirty()
}

function blankRow(): ElementRow {
  return {
    clientId: genClientId(),
    id: null,
    parentId: null,
    parentClientId: null,
    key: '',
    value: '',
    englishName: '',
    description: '',
    sortOrder: (itemsDraft.value.length + 1) * 10,
    isActive: true,
    isNew: true,
    editing: true,
  }
}

function startEdit(row: ElementRow) {
  row._backup = { ...row }
  row.editing = true
}

function rowValid(row: ElementRow): string | null {
  if (!row.key.trim()) return '元素代码不能为空'
  if (!/^[A-Za-z0-9_]+$/.test(row.key.trim())) return '元素代码只能含字母、数字、下划线'
  if (!row.value.trim()) return '元素名称不能为空'
  if (row.sortOrder == null || row.sortOrder < 0) return '排序须为非负整数'
  return null
}

function saveRow(row: ElementRow) {
  const err = rowValid(row)
  if (err) {
    message.warning(err)
    return
  }
  row.editing = false
  markDirty()
}

function cancelRow(row: ElementRow) {
  if (row.isNew) {
    itemsDraft.value = itemsDraft.value.filter((r) => r.clientId !== row.clientId)
    return
  }
  if (row._backup) Object.assign(row, row._backup)
  row.editing = false
}

function deleteRow(row: ElementRow) {
  // 仅新增未提交的行可删除（历史元素只能停用）
  itemsDraft.value = itemsDraft.value.filter((r) => r.clientId !== row.clientId)
  markDirty()
}

function toggleActive(row: ElementRow) {
  if (hasChildren(row)) {
    message.warning('该元素包含子级，不可停用，请先移除或转移所有子级元素')
    return
  }
  row.isActive = !row.isActive
  markDirty()
}

function markDirty() {
  hasUnsavedChanges.value = true
}

// ===================== 提交草稿 =====================
async function submitDraft() {
  if (!currentType.value) return
  // 提交前对所有处于编辑态的新行做一次校验
  for (const row of itemsDraft.value) {
    if (row.editing) {
      const err = rowValid(row)
      if (err) {
        message.warning(`元素「${row.value || row.key}」：${err}`)
        return
      }
    }
  }
  submitting.value = true
  try {
    const items = itemsDraft.value.map((row) => ({
      id: row.id,
      client_id: row.isNew ? row.clientId : undefined,
      parent_id: row.parentId || undefined,
      parent_client_id: row.parentClientId || undefined,
      key: row.key.trim(),
      value: row.value.trim(),
      english_name: row.englishName.trim(),
      description: row.description,
      sort_order: row.sortOrder,
      is_active: row.isActive,
    }))
    const payload = {
      head: {
        name: headDraft.name.trim(),
        english_name: headDraft.englishName.trim(),
        is_enabled: headDraft.isEnabled,
        description: headDraft.description,
      },
      items,
    }
    const resp = await submitDictionaryDraft(currentType.value.code, payload)
    if (resp && resp.detail === '提交成功') {
      message.success('提交成功')
      hasUnsavedChanges.value = false
      await enterEdit({ ...currentType.value } as DictionaryType)
    } else {
      message.success('提交成功')
      hasUnsavedChanges.value = false
    }
  } catch (e: any) {
    const data = e?.response?.data
    if (data && (data.headErrors || data.itemErrors)) {
      if (data.headErrors) {
        const msg = Object.entries(data.headErrors).map(([, v]: any) => (Array.isArray(v) ? v[0] : v)).join('；')
        message.error(msg || '字典头校验失败')
      }
      if (data.itemErrors && typeof data.itemErrors === 'object') {
        const fieldLabels: Record<string, string> = {
          key: '元素代码',
          value: '元素名称',
          english_name: '英文名称',
          sort_order: '排序',
          parent_id: '父级',
        }
        const firstKey = Object.keys(data.itemErrors)[0]
        const errs = data.itemErrors[firstKey]
        const errMsg = Object.entries(errs || {})
          .map(([k, v]: any) => {
            const text = Array.isArray(v) ? v[0] : v
            return `${fieldLabels[k] || k}：${text}`
          })
          .join('；')
        const idxNum = Number(firstKey)
        // 后端 item_errors key 为提交数组下标（0-based）
        if (!Number.isNaN(idxNum) && itemsDraft.value[idxNum]) {
          message.error(`第 ${idxNum + 1} 行：${errMsg || '校验失败'}`)
          itemsDraft.value[idxNum].editing = true
        } else {
          // 兜底：非数字 key 或无法定位行时，直接展示元素错误
          message.error(`元素校验失败：${errMsg || '请检查输入'}`)
        }
      }
    } else {
      message.error(extractApiError(e, '提交失败'))
    }
  } finally {
    submitting.value = false
  }
}

function discardDraft() {
  if (!currentType.value) return
  enterEdit(currentType.value)
}

// ===================== 新增字典 =====================
const showCreateModal = ref(false)
const createFormRef = ref<any>(null)
const creating = ref(false)
const createForm = reactive({ code: '', name: '', englishName: '', description: '' })
const createRules: FormRules = {
  code: { required: true, message: '请输入字典代码', trigger: ['input', 'blur'] },
  name: { required: true, message: '请输入字典名称', trigger: ['input', 'blur'] },
}

function openCreateType() {
  createForm.code = ''
  createForm.name = ''
  createForm.englishName = ''
  createForm.description = ''
  showCreateModal.value = true
}

async function submitCreate() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  creating.value = true
  try {
    const created = await createDictionaryType({
      code: createForm.code.trim(),
      name: createForm.name.trim(),
      englishName: createForm.englishName.trim(),
      description: createForm.description,
    })
    message.success('创建成功')
    showCreateModal.value = false
    // 创建成功后直接进入编辑页（详情为空，可继续配置元素）
    if (created && created.code) {
      await enterEdit(created)
    } else {
      await loadList()
    }
  } catch (e: any) {
    message.error(extractApiError(e, '创建失败'))
  } finally {
    creating.value = false
  }
}

// ===================== beforeunload 守卫 =====================
function onBeforeUnload(e: BeforeUnloadEvent) {
  if (hasUnsavedChanges.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}
onMounted(() => {
  loadList()
  window.addEventListener('beforeunload', onBeforeUnload)
})
onUnmounted(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>

<style scoped>
.page-container {
  display: block !important;
  padding: 24px 24px 120px !important;
  width: 100% !important;
  max-width: none !important;
  min-height: 100% !important;
  box-sizing: border-box;
  overflow-x: hidden !important;
  overflow-y: auto !important;
  gap: 0 !important;
}
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; gap: 16px; }
.page-title { font-size: 22px; font-weight: 600; margin: 0; }
.page-subtitle { color: #888; margin: 6px 0 0; font-size: 13px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.code-pill, .num-pill { font-size: 12px; color: #666; background: #f2f3f5; padding: 2px 8px; border-radius: 4px; }
.toolbar { margin-bottom: 16px; }
.section { margin-bottom: 16px; }
.edit-header { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.back-btn { align-self: baseline; margin-top: 6px; }
.title-block { display: flex; flex-direction: column; gap: 4px; }

.hint { color: #aaa; font-size: 12px; margin-left: 8px; }
.dict-hints { margin: 0; padding-left: 18px; font-size: 13px; }
.dict-hints li { margin-bottom: 2px; }

/* 元素树形表格 */
.el-table { border: 1px solid #eee; border-radius: 6px; overflow-x: auto; width: 100%; min-width: 720px; }
.el-row { display: flex; align-items: center; border-bottom: 1px solid #f2f3f5; min-height: 48px; }
.el-row:last-child { border-bottom: none; }
.el-head { background: #fafafa; font-weight: 600; font-size: 13px; color: #555; white-space: nowrap; }
.el-row.editing { background: #fafcff; }
.el-row.isnew { background: #fffbe6; }
.el-row.isnew.editing { background: #fff7cc; }
.el-cell { display: flex; align-items: center; min-height: 48px; padding: 0 12px; font-size: 13px; box-sizing: border-box; }
.el-cell-content { display: flex; align-items: center; gap: 4px; width: 100%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; line-height: 1; }
/* 统一所有直接子元素为 inline-flex，消除 inline 元素基线/line-height 造成的视觉偏移 */
.el-cell-content > * { display: inline-flex; align-items: center; line-height: 1; }
.el-cell-content .n-input, .el-cell-content .n-input-number { display: flex; }
.el-cell .code-text { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: #333; font-size: 13px; }
.el-cell .n-input, .el-cell .n-input-number { min-width: 80px; width: 100%; }
.tree-guide { color: #bbb; margin-right: 4px; }
.strikethrough { text-decoration: line-through; color: #aaa; }
.desc-cell { color: #666; }
.el-empty { padding: 32px; text-align: center; color: #aaa; font-size: 13px; }
/* 操作列不换行、按钮紧凑 */
.el-cell .n-space { flex-wrap: nowrap; }
.el-cell .n-button { white-space: nowrap; }

.draft-hint {
  display: flex; align-items: center; gap: 8px; flex: 1;
  color: #fa8c16; font-size: 13px; font-weight: 500;
  white-space: nowrap;
  transition: opacity 0.2s ease;
}
.draft-hint.hint-hidden { opacity: 0; pointer-events: none; }
.draft-icon { color: #fa8c16; }

.submit-bar {
  position: sticky; bottom: 16px; left: 0; right: 0;
  display: flex; justify-content: space-between; align-items: center;
  background: #fff; border: 1px solid #f0f0f0; border-radius: 12px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
  padding: 12px 24px; margin: 24px 0 0;
  z-index: 10;
  gap: 16px;
}
.submit-actions { margin-left: auto; flex-shrink: 0; }
</style>
