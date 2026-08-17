<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">数据字典</h1>
        <p class="page-subtitle">枚举与配置项的统一来源（可维护）</p>
      </div>
    </div>

    <div class="dd-layout">
      <!-- 左栏: 字典类型列表 -->
      <n-card class="dd-left" :bordered="true">
        <div class="dd-left-header">
          <span class="dd-left-title">字典类型</span>
          <n-button size="small" type="primary" @click="openCreateType">新增类型</n-button>
        </div>
        <n-spin :show="typesLoading">
          <n-menu
            :options="menuOptions"
            :value="selectedType?.code"
            @update:value="handleMenuSelect"
          />
          <template v-if="!typesLoading && types.length === 0">
            <n-empty description="暂无字典类型" size="small" />
          </template>
        </n-spin>
      </n-card>

      <!-- 右栏: 选中类型详情 + 字典项 -->
      <n-card class="dd-right" :bordered="true">
        <template v-if="selectedType">
          <div class="dd-detail-header">
            <span class="dd-detail-title">{{ selectedType.name }}</span>
            <n-tag size="small" type="info">{{ selectedType.code }}</n-tag>
            <n-space class="dd-detail-actions" :size="8">
              <n-button size="small" tertiary @click="openEditType">编辑类型</n-button>
              <n-button size="small" tertiary type="error" @click="confirmDeleteType">删除类型</n-button>
              <n-button size="small" type="primary" @click="openCreateItem">新增项</n-button>
            </n-space>
          </div>
          <p v-if="selectedType.description" class="dd-detail-desc">{{ selectedType.description }}</p>

          <n-data-table
            :columns="columns"
            :data="items"
            :loading="itemsLoading"
            :row-key="(r: any) => r.id"
            :pagination="false"
          >
            <template #empty>
              <n-empty description="该类型暂无可展示的字典项" />
            </template>
          </n-data-table>
        </template>
        <template v-else>
          <n-empty
            :description="typesLoading ? '加载中…' : (types.length === 0 ? '暂无字典类型' : '请选择左侧字典类型')"
          />
        </template>
      </n-card>
    </div>

    <!-- 字典类型弹窗 -->
    <n-modal
      v-model:show="showTypeModal"
      :title="typeModalMode === 'create' ? '新增字典类型' : '编辑字典类型'"
      preset="card"
      style="width: 480px"
      :mask-closable="false"
    >
      <n-form
        ref="typeFormRef"
        :model="typeForm"
        :rules="typeRules"
        label-placement="top"
      >
        <n-form-item label="类型编码" path="code">
          <n-input
            v-model:value="typeForm.code"
            placeholder="如 recruitment_stage_type（小写字母/数字/下划线）"
            :disabled="typeModalMode === 'edit'"
          />
        </n-form-item>
        <n-form-item label="类型名称" path="name">
          <n-input v-model:value="typeForm.name" placeholder="如 招聘阶段类型" />
        </n-form-item>
        <n-form-item label="说明" path="description">
          <n-input
            v-model:value="typeForm.description"
            type="textarea"
            placeholder="可选"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="typeSaving" @click="showTypeModal = false">取消</n-button>
          <n-button type="primary" :loading="typeSaving" @click="submitType">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 字典项弹窗 -->
    <n-modal
      v-model:show="showItemModal"
      :title="itemModalMode === 'create' ? '新增字典项' : '编辑字典项'"
      preset="card"
      style="width: 480px"
      :mask-closable="false"
    >
      <n-form
        ref="itemFormRef"
        :model="itemForm"
        :rules="itemRules"
        label-placement="top"
      >
        <n-form-item label="字典项编码" path="key">
          <n-input v-model:value="itemForm.key" placeholder="如 SCREEN" />
        </n-form-item>
        <n-form-item label="展示名" path="value">
          <n-input v-model:value="itemForm.value" placeholder="如 筛选" />
        </n-form-item>
        <n-form-item label="排序" path="sortOrder">
          <n-input-number v-model:value="itemForm.sortOrder" :min="0" />
        </n-form-item>
        <n-form-item label="启用" path="isActive">
          <n-switch v-model:value="itemForm.isActive" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button :disabled="itemSaving" @click="showItemModal = false">取消</n-button>
          <n-button type="primary" :loading="itemSaving" @click="submitItem">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import {
  useMessage,
  useDialog,
  NCard,
  NMenu,
  NDataTable,
  NTag,
  NEmpty,
  NSpin,
  NButton,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSwitch,
  NSpace,
  type FormRules,
} from 'naive-ui'
import {
  listDictionaryTypes,
  listDictionaryItems,
  createDictionaryType,
  updateDictionaryType,
  deleteDictionaryType,
  createDictionaryItem,
  updateDictionaryItem,
  deleteDictionaryItem,
  type DictionaryType,
  type DictionaryItem,
} from '../../api/dictionary'
import { extractApiError } from '../../api/dynamic-field'

const message = useMessage()
const dialog = useDialog()

interface TypeForm {
  code: string
  name: string
  description: string
}

interface ItemForm {
  id: string
  key: string
  value: string
  sortOrder: number
  isActive: boolean
}

const types = ref<DictionaryType[]>([])
const typesLoading = ref(false)
const selectedType = ref<DictionaryType | null>(null)
const items = ref<DictionaryItem[]>([])
const itemsLoading = ref(false)

// 左栏菜单选项: label=类型名称, key=类型 code, extra=code 便于辨识.
const menuOptions = computed(() =>
  types.value.map((t) => ({
    label: t.name,
    key: t.code,
    extra: t.code,
  })),
)

/** 拉取全部字典类型; 成功后选中 selectCode(默认第一个) 并加载其字典项. */
async function loadTypes(selectCode?: string) {
  typesLoading.value = true
  try {
    const list = await listDictionaryTypes()
    types.value = list
    if (list.length > 0) {
      const target = (selectCode && list.find((t) => t.code === selectCode)) || list[0]
      await selectType(target)
    } else {
      selectedType.value = null
      items.value = []
    }
  } catch (e: any) {
    message.error('加载失败')
  } finally {
    typesLoading.value = false
  }
}

/** 选中某字典类型并加载其字典项 (按 sortOrder 升序, 仅启用项). */
async function selectType(t: DictionaryType | null) {
  if (!t) return
  selectedType.value = t
  itemsLoading.value = true
  try {
    items.value = await listDictionaryItems(t.code)
  } catch (e: any) {
    items.value = []
    message.error('加载失败')
  } finally {
    itemsLoading.value = false
  }
}

/** 左栏菜单点击 → 根据 code 找到类型并加载. */
function handleMenuSelect(key: string) {
  const t = types.value.find((x) => x.code === key) || null
  selectType(t)
}

// --- 字典类型弹窗 ----------------------------------------------------------

const showTypeModal = ref(false)
const typeModalMode = ref<'create' | 'edit'>('create')
const typeFormRef = ref<any>(null)
const typeSaving = ref(false)
const typeForm = ref<TypeForm>({ code: '', name: '', description: '' })

const typeRules: FormRules = {
  code: { required: true, message: '请输入类型编码', trigger: ['input', 'blur'] },
  name: { required: true, message: '请输入类型名称', trigger: ['input', 'blur'] },
}

function openCreateType() {
  typeModalMode.value = 'create'
  typeForm.value = { code: '', name: '', description: '' }
  showTypeModal.value = true
}

function openEditType() {
  if (!selectedType.value) return
  typeModalMode.value = 'edit'
  typeForm.value = {
    code: selectedType.value.code,
    name: selectedType.value.name,
    description: selectedType.value.description,
  }
  showTypeModal.value = true
}

async function submitType() {
  if (!typeFormRef.value) return
  try {
    await typeFormRef.value.validate()
  } catch {
    return
  }
  typeSaving.value = true
  try {
    const form = typeForm.value
    if (typeModalMode.value === 'create') {
      await createDictionaryType({ code: form.code, name: form.name, description: form.description })
      message.success('创建成功')
    } else {
      await updateDictionaryType(form.code, { name: form.name, description: form.description })
      message.success('更新成功')
    }
    showTypeModal.value = false
    await loadTypes(form.code) // 重载并保持在当前类型
  } catch (e: any) {
    message.error(extractApiError(e, '操作失败'))
  } finally {
    typeSaving.value = false
  }
}

function confirmDeleteType() {
  if (!selectedType.value) return
  const t = selectedType.value
  dialog.warning({
    title: '删除字典类型',
    content: `确认删除「${t.name}」(${t.code})？删除后该类型下的字典项将一并不可见，此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteDictionaryType(t.code)
        message.success('删除成功')
        await loadTypes() // 回退选中第一个
      } catch (e: any) {
        message.error(extractApiError(e, '删除失败'))
      }
    },
  })
}

// --- 字典项弹窗 ------------------------------------------------------------

const showItemModal = ref(false)
const itemModalMode = ref<'create' | 'edit'>('create')
const itemFormRef = ref<any>(null)
const itemSaving = ref(false)
const itemForm = ref<ItemForm>({ id: '', key: '', value: '', sortOrder: 0, isActive: true })

const itemRules: FormRules = {
  key: { required: true, message: '请输入字典项编码', trigger: ['input', 'blur'] },
  value: { required: true, message: '请输入展示名', trigger: ['input', 'blur'] },
}

function openCreateItem() {
  if (!selectedType.value) return
  itemModalMode.value = 'create'
  itemForm.value = { id: '', key: '', value: '', sortOrder: 0, isActive: true }
  showItemModal.value = true
}

function openEditItem(row: DictionaryItem) {
  itemModalMode.value = 'edit'
  itemForm.value = {
    id: row.id,
    key: row.key,
    value: row.value,
    sortOrder: row.sortOrder,
    isActive: row.isActive,
  }
  showItemModal.value = true
}

async function submitItem() {
  if (!itemFormRef.value) return
  try {
    await itemFormRef.value.validate()
  } catch {
    return
  }
  if (!selectedType.value) return
  const form = itemForm.value
  itemSaving.value = true
  try {
    if (itemModalMode.value === 'create') {
      await createDictionaryItem({
        type: selectedType.value.id,
        key: form.key,
        value: form.value,
        sortOrder: form.sortOrder,
        isActive: form.isActive,
      })
      message.success('创建成功')
    } else {
      await updateDictionaryItem(form.id, {
        key: form.key,
        value: form.value,
        sortOrder: form.sortOrder,
        isActive: form.isActive,
      })
      message.success('更新成功')
    }
    showItemModal.value = false
    if (selectedType.value) await selectType(selectedType.value) // 重载当前类型字典项
  } catch (e: any) {
    message.error(extractApiError(e, '操作失败'))
  } finally {
    itemSaving.value = false
  }
}

function confirmDeleteItem(row: DictionaryItem) {
  dialog.warning({
    title: '删除字典项',
    content: `确认删除「${row.value}」(${row.key})？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteDictionaryItem(row.id)
        message.success('删除成功')
        if (selectedType.value) await selectType(selectedType.value)
      } catch (e: any) {
        message.error(extractApiError(e, '删除失败'))
      }
    },
  })
}

const columns = [
  { title: '字典项编码', key: 'key', width: 180 },
  { title: '展示名', key: 'value', minWidth: 160 },
  { title: '排序', key: 'sortOrder', width: 90 },
  {
    title: '状态',
    key: 'isActive',
    width: 100,
    render: (row: DictionaryItem) =>
      h(
        NTag,
        { type: row.isActive ? 'success' : 'default', size: 'small' },
        { default: () => (row.isActive ? '启用' : '停用') },
      ),
  },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row: DictionaryItem) =>
      h(
        NSpace,
        { align: 'center' },
        {
          default: () => [
            h(NButton, { size: 'small', onClick: () => openEditItem(row) }, { default: () => '编辑' }),
            h(
              NButton,
              { size: 'small', type: 'error', onClick: () => confirmDeleteItem(row) },
              { default: () => '删除' },
            ),
          ],
        },
      ),
  },
]

onMounted(() => {
  loadTypes()
})
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 600; margin: 0; }
.page-subtitle { color: #888; margin: 4px 0 0; font-size: 13px; }

.dd-layout { display: flex; gap: 16px; align-items: flex-start; }
.dd-left { width: 260px; flex: 0 0 260px; }
.dd-right { flex: 1; min-width: 0; }

.dd-left-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.dd-left-title { font-weight: 600; font-size: 14px; }

.dd-detail-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.dd-detail-title { font-size: 18px; font-weight: 600; }
.dd-detail-actions { margin-left: auto; }
.dd-detail-desc { color: #888; margin: 4px 0 16px; font-size: 13px; }
</style>
