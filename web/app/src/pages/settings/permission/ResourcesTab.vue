<template>
  <div class="resources-tab">
    <div class="filter-row">
      <n-input
        v-model:value="search"
        :placeholder="t('pages.settings.permission.ResourcesTab.s1')"
        clearable
        class="filter-search"
        @update:value="onFilterChange"
        @keyup.enter="load"
      >
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <n-select
        v-model:value="moduleFilter"
        :options="moduleOptions"
        :placeholder="t('pages.settings.permission.ResourcesTab.s2')"
        clearable
        class="filter-select"
        @update:value="onModuleChange"
      />
      <n-select
        v-model:value="subModuleFilter"
        :options="subModuleOptions"
        :placeholder="t('pages.settings.permission.ResourcesTab.s20')"
        clearable
        :disabled="subModuleOptions.length === 0"
        class="filter-select filter-select-sub"
      />
      <n-button type="primary" :loading="loading" @click="load">{{ t('pages.settings.permission.ResourcesTab.s3') }}</n-button>
    </div>

    <!-- 加载失败：给出就地重试入口，不静默失败（R-104 / R-111） -->
    <n-alert v-if="loadError" type="error" :show-icon="true" class="load-error">
      <!-- NAlert 只有 default/icon/header 插槽，重试按钮放在 default 内 -->
      <div class="error-row">
        <span>{{ loadError }}</span>
        <n-button size="small" tertiary :loading="loading" @click="load">
          {{ t('pages.settings.permission.ResourcesTab.s17') }}
        </n-button>
      </div>
    </n-alert>

    <!-- .table-wrap（全局样式）提供区域滚动链：只有表格滚动，筛选行与分页器固定（R-215） -->
    <div class="table-wrap">
      <n-data-table
        :columns="columns"
        :data="filteredData"
        :loading="loading"
        :bordered="false"
        :pagination="pagination"
        :row-key="(r: PermissionResource) => r.id"
        flex-height
      >
        <template #empty>
          <!-- 区分「无数据」与「筛选无结果」（R-111 状态机） -->
          <n-empty :description="data.length === 0 ? t('pages.settings.permission.ResourcesTab.s14') : t('pages.settings.permission.ResourcesTab.s15')" />
        </template>
      </n-data-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
/**
 * ResourcesTab.vue — 权限资源 tab (T20)
 * 后端: GET /api/v1/permissions/resources/  (ReadOnlyModelViewSet)
 * 资源为代码注册目录（seed/bootstrap 写入），仅只读展示，不提供新增/编辑/删除。
 */
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NInput, NSelect, NDataTable, NAlert, NEmpty, useMessage } from 'naive-ui'
import {
  fetchAllResources,
  type PermissionResource,
  type ResourceType,
} from '@/api/permission-resource'
import { TABLE_PAGE_SIZE, TABLE_PAGE_SIZE_OPTIONS } from '@/composables/useTablePagination'
import {
  resourceModuleLabel,
  buildSubModuleIndex,
  resourceSubModuleLabel,
  type SubModuleIndex,
} from '@/utils/permissionModules'
import { SearchOutline } from '@vicons/ionicons5'

const message = useMessage()
// t 提前声明：下方 pagination.prefix 闭包会用到它
const { t } = useI18n()
const loading = ref(false)
const search = ref('')
const moduleFilter = ref<string | null>(null)
const subModuleFilter = ref<string | null>(null)
const data = ref<PermissionResource[]>([])
const loadError = ref('')

/**
 * 子模块索引（模块 → 子模块 → 中文名），由全量资源推导。
 * settings 下有 32 个二级/三级分栏（如 account / announcements / campus-control），
 * 它们的 module 值都是 settings，只看「模块」列无法区分归属。
 */
const subModuleIndex = computed<SubModuleIndex>(() => buildSubModuleIndex(data.value))

/** 当前可用的子模块选项：随模块筛选联动（未选模块时给全部） */
const subModuleOptions = computed(() => {
  const modules = moduleFilter.value ? [moduleFilter.value] : Object.keys(subModuleIndex.value)
  const opts: Array<{ label: string; value: string }> = []
  for (const m of modules) {
    const subs = subModuleIndex.value[m]
    if (!subs) continue
    for (const [sub, label] of Object.entries(subs)) {
      // 未选模块时用「模块中文名 / 子模块」区分不同模块下的同名子模块
      opts.push({
        label: moduleFilter.value ? label : `${resourceModuleLabel(m)} / ${label}`,
        value: sub,
      })
    }
  }
  return opts.sort((a, b) => a.label.localeCompare(b.label, 'zh'))
})

/**
 * 分页配置 —— 与「校招管控-规则配置」(CampusControl) 规则表一致:
 *   共 N 条 | < 1 2 > | [20 / 页 ▾] | 跳至 [__]
 *
 * 两个关键点（CampusControl 源码注释已踩过坑）:
 * 1. pageSize 必须用 **非受控** defaultPageSize：reactive 里带 pageSize 会让 naive-ui
 *    视为受控，内置分页器 change 不回写，导致「N / 页」选择器失效。
 * 2. page 用 **受控** + onUpdatePage 回写：这样切换筛选条件时能把页码重置回第 1 页，
 *    避免停在一个超出新结果集范围的页码上（R-111）。
 */
const pagination = reactive({
  page: 1,
  defaultPageSize: TABLE_PAGE_SIZE,
  showSizePicker: true,
  pageSizes: TABLE_PAGE_SIZE_OPTIONS,
  showQuickJumper: true,
  prefix: ({ itemCount }: { itemCount?: number }) =>
    t('pages.settings.permission.ResourcesTab.s13', { n: itemCount ?? 0 }),
  onUpdatePage: (p: number) => {
    pagination.page = p
  },
})

/** 筛选条件变化 → 回到第 1 页（前端筛选不重新请求，数据不会丢） */
function onFilterChange() {
  pagination.page = 1
}

/**
 * 切换模块时清空子模块筛选：不同模块的子模块集合不同，
 * 保留旧值会出现「筛不出任何结果」的死状态。
 */
function onModuleChange() {
  if (subModuleFilter.value && !subModuleOptions.value.some((o) => o.value === subModuleFilter.value)) {
    subModuleFilter.value = null
  }
  onFilterChange()
}

/**
 * 前端筛选 + 归属聚拢排序（与参考页 CampusControl 规则表的 filteredRules 同思路）。
 * 后端已恢复服务端分页（单页 20 条），load() 用 fetchAllResources 翻页取全量后，
 * 分页与筛选都在前端切片 —— 切换页码/每页条数不会触发重新请求，天然不丢筛选条件。
 *
 * 排序按「模块 → 子模块 → 资源编码」：settings 有 115 条、32 个子模块，
 * 聚拢后同子模块的行连续出现，归属关系一眼可见。
 */
const filteredData = computed(() => {
  const kw = search.value.trim().toLowerCase()
  const rows = data.value.filter((r) => {
    if (moduleFilter.value && r.module !== moduleFilter.value) return false
    if (subModuleFilter.value) {
      const parts = r.resourceCode.split(':')
      if (parts.length < 4 || parts[2] !== subModuleFilter.value) return false
    }
    if (!kw) return true
    return (
      r.resourceCode.toLowerCase().includes(kw) ||
      r.resourceName.toLowerCase().includes(kw)
    )
  })
  const subOf = (code: string) => {
    const parts = code.split(':')
    return parts.length >= 4 ? parts[2] : ''
  }
  return rows.sort((a, b) => {
    // module 字段可空（历史数据），统一按空串兜底再比较
    if (a.module !== b.module) return (a.module ?? '').localeCompare(b.module ?? '')
    const sa = subOf(a.resourceCode)
    const sb = subOf(b.resourceCode)
    if (sa !== sb) return sa.localeCompare(sb)
    return a.resourceCode.localeCompare(b.resourceCode)
  })
})

// 模块下拉基于**全量**数据推导，避免筛选后选项被自己筛掉
// label 用中文显示名（共享单一数据源），value 仍是后端存的英文 code
const moduleOptions = computed(() => {
  const modules = new Set<string>()
  data.value.forEach((r) => r.module && modules.add(r.module))
  return Array.from(modules)
    .map((m) => ({ value: m }))
    .sort((a, b) => a.value.localeCompare(b.value))
    .map((x) => ({ label: resourceModuleLabel(x.value), value: x.value }))
})

const resourceTypeOptions: { label: string; value: ResourceType }[] = [
  { label: '菜单', value: 'MENU' },
  { label: '按钮', value: 'BUTTON' },
  { label: '字段', value: 'FIELD' },
  { label: 'API', value: 'API' },
]

const columns = [
  // 资源编码形如 recruit:menu:xxx，超长时省略号 + tooltip 查看完整值（R-110）
  { title: '资源编码', key: 'resourceCode', width: 240, ellipsis: { tooltip: true } },
  { title: '资源名称', key: 'resourceName', width: 160, ellipsis: { tooltip: true } },
  {
    title: '类型',
    key: 'resourceType',
    width: 80,
    render: (row: PermissionResource) =>
      h('span', resourceTypeOptions.find((o) => o.value === row.resourceType)?.label ?? row.resourceType),
  },
  // 模块列显示中文名，title 悬浮给出后端原始 code（便于排查 seed 数据问题）
  // 注: naive 的 ellipsis.tooltip 只接受零参 () => string，拿不到当前行，故用 title
  {
    title: '模块',
    key: 'module',
    width: 110,
    render: (row: PermissionResource) =>
      h('span', { title: row.module || undefined }, resourceModuleLabel(row.module, '—')),
  },
  // 子模块列：settings 下 32 个二级/三级分栏（个人信息 / 制度公告 / 校招管控…），
  // module 值同为 settings，仅靠模块列无法区分归属，故单列一列展示中文名。
  {
    title: '子模块',
    key: 'subModule',
    width: 130,
    render: (row: PermissionResource) => {
      const label = resourceSubModuleLabel(row.resourceCode, subModuleIndex.value)
      if (!label) {
        return h('span', { class: 'dim-text' }, '—')
      }
      return h('span', { title: row.resourceCode.split(':')[2] }, label)
    },
  },
  { title: '状态', key: 'status', width: 80, render: (row: PermissionResource) => row.status === 1 ? '启用' : '禁用' },
]

/**
 * 拉取全量资源（fetchAllResources 自动跟随服务端分页翻页），
 * 前端再做筛选 + 分页切片。失败时保留上一次成功数据并给出就地重试入口。
 */
async function load() {
  loading.value = true
  loadError.value = ''
  try {
    data.value = await fetchAllResources()
  } catch (e: any) {
    loadError.value = t('pages.settings.permission.ResourcesTab.s16')
    message.error(loadError.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
/* 高度链：.resources-shell(flex:1) → .resources-tab(flex:1) → .table-wrap(flex:1)
   保证只有表格区域滚动，筛选行与分页器固定（R-215） */
.resources-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex: 1;
  min-height: 0;
}
.filter-row {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.filter-search {
  flex: 1 1 220px;
  max-width: 280px;
  min-width: 160px;
}
.filter-select {
  flex: 0 1 180px;
  min-width: 140px;
}
/* 子模块名较长（「候选人字段管理」），给宽一点 */
.filter-select-sub {
  flex: 0 1 200px;
}
/* 无子模块的行用弱化色，避免与真实归属混淆 */
:deep(.dim-text) {
  color: var(--n-500, #999);
}
.load-error {
  flex-shrink: 0;
}
.error-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}

/* 平板 / 手机：筛选控件占满一行，纵向排列，避免 320px 横向溢出（R-103 / R-201） */
@media (max-width: 768px) {
  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }
  .filter-search,
  .filter-select {
    max-width: none;
    width: 100%;
  }
}
</style>