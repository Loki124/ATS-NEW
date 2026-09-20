<template>
  <div class="page-container rl-tags-page">
    <div class="page-body">
      <!-- 顶部 toolbar -->
      <div class="toolbar glass-card">
        <n-space align="center" :wrap="false" :wrap-item="false">
          <n-input
            v-model:value="searchText"
            :placeholder="t('reasonLibrary.tags.search.placeholder')"
            clearable
            style="width: 320px"
            @update:value="onSearchInput"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-select
            v-model:value="typeFilter"
            :options="typeOptions"
            :placeholder="t('reasonLibrary.tags.filter.allType')"
            style="width: 140px"
            clearable
            @update:value="onFilterChange"
          />
          <n-select
            v-model:value="statusFilter"
            :options="statusOptions"
            :placeholder="t('reasonLibrary.tags.filter.allStatus')"
            style="width: 140px"
            clearable
            @update:value="onFilterChange"
          />
        </n-space>
        <n-space>
          <n-button @click="loadList">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            {{ t('reasonLibrary.common.refresh') }}
          </n-button>
          <n-button :disabled="!isSuperAdmin" @click="openImportModal">
            <template #icon><n-icon :component="CloudUploadOutline" /></template>
            {{ t('reasonLibrary.tags.btn.import') }}
          </n-button>
          <n-button v-if="isSuperAdmin" type="primary" @click="openCreateModal">
            <template #icon><n-icon :component="AddOutline" /></template>
            {{ t('reasonLibrary.tags.btn.add') }}
          </n-button>
          <n-tooltip v-else placement="top">
            <template #trigger>
              <n-button type="primary" disabled>
                <template #icon><n-icon :component="AddOutline" /></template>
                {{ t('reasonLibrary.tags.btn.add') }}
              </n-button>
            </template>
            {{ t('reasonLibrary.common.systemImmutable') }}
          </n-tooltip>
        </n-space>
      </div>

      <!-- 统计 + 列表 -->
      <div class="stats-row">
        <span>{{ t('reasonLibrary.common.total') }} <b>{{ stats.total }}</b> {{ t('reasonLibrary.common.tag') }}</span>
        <span>{{ t('reasonLibrary.tags.stats.enabled') }} <b>{{ stats.enabled }}</b></span>
        <span>{{ t('reasonLibrary.tags.stats.system') }} <b>{{ stats.system }}</b></span>
        <span>{{ t('reasonLibrary.tags.stats.custom') }} <b>{{ stats.custom }}</b></span>
      </div>

      <!-- 加载失败: 错误态 + 重试入口 (修复「页面加载失败无反馈」) -->
      <n-alert
        v-if="loadError && !loading"
        type="error"
        :show-icon="true"
        class="rl-error-banner"
      >
        <div class="rl-error-body">
          <span>{{ loadError }}</span>
          <n-button size="small" tertiary type="error" @click="loadList">{{ t('reasonLibrary.common.retry') }}</n-button>
        </div>
      </n-alert>

      <n-data-table
        :columns="columns"
        :data="rows"
        :loading="loading"
        :row-key="(r: ReasonTag) => r.id"
        :pagination="false"
        :scroll-x="1100"
        size="medium"
        striped
      >
        <template #empty>
          <n-empty :description="t('reasonLibrary.tags.empty')" />
        </template>
      </n-data-table>

      <!-- 分页 -->
      <div v-if="total > 0" class="pager-row">
        <n-pagination
          v-model:page="page"
          v-model:page-size="pageSize"
          :item-count="total"
          :page-sizes="[10, 20, 50, 100]"
          show-size-picker
          show-quick-jumper
          @update:page="loadList"
          @update:page-size="loadList"
        />
      </div>

      <!-- 新建 / 编辑 Modal -->
      <ReasonTagModal
        v-model:show="modalShow"
        :tag="editingTag"
        :is-super-admin="isSuperAdmin"
        @saved="onSaved"
      />

      <!-- 导入 Modal -->
      <ReasonTagImportModal
        v-model:show="importShow"
        @imported="onImported"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 原因库 - 原因标签 Tab (T-15 + T-16)
 *
 * - 列表: 6 列 (名称/英文名/提示/类型/状态/操作)
 * - 搜索: name/en_name 模糊; type + enabled 过滤
 * - 系统标签: 编辑/停用按钮 disabled + tooltip
 * - 自定义标签: 全功能 (新增/编辑/启停/删除)
 */
import { ref, reactive, computed, h, onMounted } from 'vue'
import { useMessage, NButton, NTag, NSwitch, NTooltip, NSpace, NIcon, NDataTable, NInput, NSelect, NEmpty, NPagination, NAlert } from 'naive-ui'
import { SearchOutline, RefreshOutline, AddOutline, CloudUploadOutline, PencilOutline, TrashOutline, LockClosedOutline } from '@vicons/ionicons5'
import { listTags, updateTag, deleteTag, extractReasonApiError } from '../../../api/reason-library'
import type { ReasonTag } from '../../../types/reason-library'
import { BIZ_CODE, ROLE_SUPER_ADMIN } from '../../../types/reason-library'
import { t } from '../../../locales/zh-CN'
import { useUserStore } from '../../../stores/user'
import ReasonTagModal from '../../../components/reason-library/ReasonTagModal.vue'
import ReasonTagImportModal from '../../../components/reason-library/ReasonTagImportModal.vue'

const message = useMessage()
const userStore = useUserStore()

// ============= 角色判断 =============
const userRoles = computed<string[]>(() => userStore.user?.roles ?? [])
const isSuperAdmin = computed(() => userRoles.value.includes(ROLE_SUPER_ADMIN))

// ============= 查询条件 =============
const searchText = ref('')
const typeFilter = ref<'system' | 'custom' | null>(null)
const statusFilter = ref<'on' | 'off' | null>(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// ============= 数据 =============
const rows = ref<ReasonTag[]>([])
const loading = ref(false)
const loadError = ref<string | null>(null)
let searchDebounce: number | undefined
// latest-wins 令牌: 防止快速切换筛选/搜索时旧响应覆盖新数据 (修复「数据错乱」)
let reqToken = 0
// 全量标签 (用于统计, 避免只统计当前分页导致的数字失真)
const allTagsForStats = ref<ReasonTag[]>([])

const stats = reactive({ total: 0, enabled: 0, system: 0, custom: 0 })

// ============= 选项 =============
const typeOptions = [
  { label: t('reasonLibrary.tags.filter.system'), value: 'system' },
  { label: t('reasonLibrary.tags.filter.custom'), value: 'custom' },
]
const statusOptions = [
  { label: t('reasonLibrary.tags.filter.enabled'), value: 'on' },
  { label: t('reasonLibrary.tags.filter.disabled'), value: 'off' },
]

// ============= 加载 =============
async function loadList() {
  const my = ++reqToken
  loading.value = true
  loadError.value = null
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      pageSize: pageSize.value,
    }
    if (typeFilter.value) params.type = typeFilter.value
    if (statusFilter.value === 'on') params.enabled = true
    else if (statusFilter.value === 'off') params.enabled = false
    if (searchText.value.trim()) params.search = searchText.value.trim()

    const res = await listTags(params)
    if (my !== reqToken) return // 已有更新的请求, 丢弃本次过期结果
    rows.value = res.items ?? []
    total.value = res.total ?? rows.value.length
  } catch (e: any) {
    if (my !== reqToken) return
    loadError.value = extractReasonApiError(e, t('reasonLibrary.common.failed'))
    message.error(loadError.value)
  } finally {
    if (my === reqToken) loading.value = false
  }
}

// 统计基于全量(未过滤)标签, 不受当前分页/筛选影响, 数字才准确
async function loadStats() {
  try {
    const res = await listTags({ page: 1, pageSize: 2000 })
    allTagsForStats.value = res.items ?? []
    recomputeStats()
  } catch {
    // 统计失败不阻断主列表
  }
}
function refreshStats() {
  loadStats()
}

function recomputeStats() {
  const all = allTagsForStats.value
  stats.total = all.length
  stats.enabled = all.filter((r) => r.enabled).length
  stats.system = all.filter((r) => r.type === 'system').length
  stats.custom = all.filter((r) => r.type === 'custom').length
}

function onSearchInput() {
  if (searchDebounce) window.clearTimeout(searchDebounce)
  searchDebounce = window.setTimeout(() => {
    page.value = 1
    loadList()
  }, 300)
}

// 筛选/状态切换: 必须先回到第 1 页, 否则停在 >1 页会显示空页 (假「加载失败」)
function onFilterChange() {
  page.value = 1
  loadList()
}

// ============= 操作 =============
const modalShow = ref(false)
const editingTag = ref<ReasonTag | null>(null)

function openCreateModal() {
  editingTag.value = null
  modalShow.value = true
}

function openEditModal(tag: ReasonTag) {
  if (tag.type === 'system' && !isSuperAdmin.value) {
    message.warning(t('reasonLibrary.common.systemImmutable'))
    return
  }
  editingTag.value = tag
  modalShow.value = true
}

async function toggleEnabled(tag: ReasonTag) {
  if (tag.type === 'system' && !isSuperAdmin.value) {
    message.warning(t('reasonLibrary.tags.toggle.systemImmutable'))
    return
  }
  try {
    await updateTag(tag.id, { enabled: !tag.enabled })
    message.success(tag.enabled ? t('reasonLibrary.tags.toggle.disable') + ' ✓' : t('reasonLibrary.tags.toggle.enable') + ' ✓')
    await loadList()
    refreshStats()
  } catch (e: any) {
    message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
  }
}

async function removeTag(tag: ReasonTag) {
  if (tag.type === 'system') {
    message.warning(t('reasonLibrary.common.systemImmutable'))
    return
  }
  try {
    await deleteTag(tag.id)
    message.success(t('reasonLibrary.common.success'))
    await loadList()
    refreshStats()
  } catch (e: any) {
    if (e?.code === BIZ_CODE.TAG_HAS_REFS) {
      message.error(t('reasonLibrary.errors.TAG_HAS_REFS'))
    } else if (e?.code === BIZ_CODE.SYSTEM_TAG_IMMUTABLE) {
      message.error(t('reasonLibrary.errors.SYSTEM_TAG_IMMUTABLE'))
    } else {
      message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
    }
  }
}

function onSaved() {
  modalShow.value = false
  loadList()
  refreshStats()
}

// ============= 导入 =============
const importShow = ref(false)
function openImportModal() { importShow.value = true }
function onImported() {
  importShow.value = false
  loadList()
  refreshStats()
}

// ============= 列定义 =============
const columns = computed(() => [
  {
    title: t('reasonLibrary.tags.col.name'),
    key: 'name',
    width: 200,
    ellipsis: { tooltip: true },
    render: (row: ReasonTag) => h('span', { style: 'font-weight: 500; color: var(--ink);' }, row.name),
  },
  {
    title: t('reasonLibrary.tags.col.enName'),
    key: 'enName',
    width: 180,
    ellipsis: { tooltip: true },
    render: (row: ReasonTag) =>
      row.enName
        ? h('span', { style: 'color: var(--ink-soft);' }, row.enName)
        : h('span', { style: 'color: var(--ink-faint);' }, '—'),
  },
  {
    title: t('reasonLibrary.tags.col.tip'),
    key: 'tip',
    width: 220,
    ellipsis: { tooltip: true },
    render: (row: ReasonTag) =>
      row.tip
        ? h('span', { style: 'color: var(--ink-soft);' }, row.tip)
        : h('span', { style: 'color: var(--ink-faint);' }, '—'),
  },
  {
    title: t('reasonLibrary.tags.col.type'),
    key: 'type',
    width: 110,
    render: (row: ReasonTag) =>
      h(
        NTag,
        {
          size: 'small',
          type: row.type === 'system' ? 'info' : 'success',
          bordered: false,
        },
        { default: () => (row.type === 'system' ? t('reasonLibrary.common.system') : t('reasonLibrary.common.custom')) },
      ),
  },
  {
    title: t('reasonLibrary.tags.col.status'),
    key: 'enabled',
    width: 110,
    render: (row: ReasonTag) =>
      h(NSwitch, {
        value: row.enabled,
        size: 'small',
        disabled: row.type === 'system' && !isSuperAdmin.value,
        onUpdateValue: () => toggleEnabled(row),
      }),
  },
  {
    title: t('reasonLibrary.tags.col.actions'),
    key: 'actions',
    width: 200,
    fixed: 'right' as const,
    render: (row: ReasonTag) => {
      const isLocked = row.type === 'system' && !isSuperAdmin.value
      const editBtn = h(
        NButton,
        {
          size: 'small',
          quaternary: true,
          disabled: isLocked,
          onClick: () => openEditModal(row),
        },
        {
          icon: () => h(NIcon, null, { default: () => h(isLocked ? LockClosedOutline : PencilOutline) }),
          default: () => t('reasonLibrary.common.edit'),
        },
      )
      const deleteBtn = h(
        NButton,
        {
          size: 'small',
          quaternary: true,
          type: 'error',
          disabled: isLocked,
          onClick: () => removeTag(row),
        },
        {
          icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
          default: () => t('reasonLibrary.common.delete'),
        },
      )
      const editTip = isLocked
        ? h(NTooltip, null, {
            trigger: () => editBtn,
            default: () => t('reasonLibrary.common.systemImmutable'),
          })
        : editBtn
      return h(NSpace, { size: 4 }, () => [editTip, deleteBtn])
    },
  },
])

onMounted(() => {
  loadList()
  refreshStats()
})
</script>

<style scoped>
.rl-tags-page {
  padding: 0;
}
.rl-tags-page :deep(.toolbar) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}
.stats-row {
  display: flex;
  gap: var(--space-5);
  font-size: var(--fs-13);
  color: var(--ink-soft);
  padding: 0 var(--space-1) var(--space-2);
}
.stats-row b {
  color: var(--brand);
  font-weight: 600;
  margin: 0 2px;
}
.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-3);
}
.rl-error-banner { margin-bottom: var(--space-3); }
.rl-error-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
</style>
